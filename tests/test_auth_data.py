import ast
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from src.modules.auth.identity_aliases import (
    IdentityAliasConfigurationError,
    IdentityAliasConflictError,
    compute_govbr_identity_aliases,
    resolve_govbr_identity,
)
from src.modules.auth.models import AUTH_SCHEMA, AuthBase

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_FILE = ROOT / "migrations" / "versions" / "0001_identity_data.py"


EXPECTED_TABLES = {
    "app_users",
    "app_auth_identities",
    "app_auth_identity_keys",
    "app_local_credentials",
    "app_sessions",
    "app_roles",
    "app_user_roles",
    "app_role_permissions",
    "app_user_permission_grants",
    "app_user_professionals",
    "app_user_units",
    "app_login_attempts",
    "app_audit_logs",
    "app_system_controls",
}


def test_auth_metadata_contains_only_app_schema_tables() -> None:
    tables = set(AuthBase.metadata.tables.values())

    assert {table.name for table in tables} == EXPECTED_TABLES
    assert {table.schema for table in tables} == {AUTH_SCHEMA}
    for table in tables:
        for foreign_key in table.foreign_keys:
            assert foreign_key.column.table.schema == AUTH_SCHEMA


def test_identity_constraints_prevent_provider_alias_duplicates() -> None:
    identities = AuthBase.metadata.tables[f"{AUTH_SCHEMA}.app_auth_identities"]
    aliases = AuthBase.metadata.tables[f"{AUTH_SCHEMA}.app_auth_identity_keys"]
    credentials = AuthBase.metadata.tables[f"{AUTH_SCHEMA}.app_local_credentials"]

    identity_uniques = {
        tuple(constraint.columns.keys())
        for constraint in identities.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    alias_uniques = {
        tuple(constraint.columns.keys())
        for constraint in aliases.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("user_id", "provider", "issuer") in identity_uniques
    identity_checks = " ".join(
        str(constraint.sqltext)
        for constraint in identities.constraints
        if isinstance(constraint, CheckConstraint)
    )
    assert "status IN ('active', 'disabled')" in identity_checks
    assert "disabled_at IS NULL" in identity_checks
    assert ("provider", "issuer", "key_version", "subject_hmac") in alias_uniques
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and tuple(constraint.columns.keys()) == ("identity_id", "provider")
        for constraint in credentials.constraints
    )
    assert any(
        isinstance(constraint, CheckConstraint)
        and "provider = 'local'" in str(constraint.sqltext)
        for constraint in credentials.constraints
    )


def test_sessions_cannot_outlive_absolute_expiration() -> None:
    sessions = AuthBase.metadata.tables[f"{AUTH_SCHEMA}.app_sessions"]
    checks = " ".join(
        str(constraint.sqltext)
        for constraint in sessions.constraints
        if isinstance(constraint, CheckConstraint)
    )

    assert "idle_expires_at <= expires_at" in checks
    assert "revocation_reason IS NULL OR revoked_at IS NOT NULL" in checks


def test_bootstrap_state_and_exceptional_grants_have_database_guards() -> None:
    controls = AuthBase.metadata.tables[f"{AUTH_SCHEMA}.app_system_controls"]
    grants = AuthBase.metadata.tables[f"{AUTH_SCHEMA}.app_user_permission_grants"]
    audit = AuthBase.metadata.tables[f"{AUTH_SCHEMA}.app_audit_logs"]

    assert list(controls.primary_key.columns.keys()) == ["singleton_id"]
    assert any(
        isinstance(constraint, CheckConstraint)
        and "singleton_id = 1" in str(constraint.sqltext)
        for constraint in controls.constraints
    )
    grant_checks = " ".join(
        str(constraint.sqltext)
        for constraint in grants.constraints
        if isinstance(constraint, CheckConstraint)
    )
    assert "justification" in grant_checks
    assert "expires_at > starts_at" in grant_checks
    assert "revoked_at" in grant_checks
    assert any(
        isinstance(constraint, CheckConstraint)
        and "initial_admin_bootstrap" in str(constraint.sqltext)
        and "operator_identifiers" in str(constraint.sqltext)
        and "authorization_reference" in str(constraint.sqltext)
        for constraint in audit.constraints
    )


def test_permissions_are_separate_from_roles_and_no_admin_is_seeded() -> None:
    roles = AuthBase.metadata.tables[f"{AUTH_SCHEMA}.app_roles"]
    role_permissions = AuthBase.metadata.tables[f"{AUTH_SCHEMA}.app_role_permissions"]
    user_grants = AuthBase.metadata.tables[f"{AUTH_SCHEMA}.app_user_permission_grants"]

    assert "role_code" in roles.c
    assert "permission_code" in role_permissions.c
    assert "permission_code" in user_grants.c
    migration = MIGRATION_FILE.read_text(encoding="utf-8")
    assert "INSERT INTO app_auth.app_system_controls" in migration
    assert "INSERT INTO app_auth.app_roles" not in migration
    assert "INSERT INTO app_auth.app_users" not in migration
    assert "view_all_reports" not in migration


def test_hmac_aliases_support_key_rotation_without_changing_identity() -> None:
    old_key = os.urandom(32)
    new_key = os.urandom(32)

    old_alias = compute_govbr_identity_aliases(
        issuer="issuer-test",
        subject="subject-synthetic",
        keys={3: old_key},
    )
    both_aliases = compute_govbr_identity_aliases(
        issuer="issuer-test",
        subject="subject-synthetic",
        keys={3: old_key, 4: new_key},
    )
    different_issuer = compute_govbr_identity_aliases(
        issuer="other-issuer",
        subject="subject-synthetic",
        keys={3: old_key},
    )

    assert len(old_alias) == 1
    assert [alias.key_version for alias in both_aliases] == [3, 4]
    assert both_aliases[0] == old_alias[0]
    assert both_aliases[1].digest != old_alias[0].digest
    assert different_issuer[0].digest != old_alias[0].digest


@pytest.mark.parametrize(
    ("issuer", "subject", "keys", "error"),
    [
        ("", "subject", {1: os.urandom(32)}, ValueError),
        ("issuer", "", {1: os.urandom(32)}, ValueError),
        ("issuer", "subject", {}, IdentityAliasConfigurationError),
        ("issuer", "subject", {0: os.urandom(32)}, IdentityAliasConfigurationError),
        ("issuer", "subject", {32768: os.urandom(32)}, IdentityAliasConfigurationError),
        ("issuer", "subject", {1: b"short"}, IdentityAliasConfigurationError),
    ],
)
def test_hmac_alias_configuration_fails_closed(
    issuer: str, subject: str, keys: dict[int, bytes], error: type[Exception]
) -> None:
    with pytest.raises(error):
        compute_govbr_identity_aliases(issuer=issuer, subject=subject, keys=keys)


class _ScalarsResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _AliasLookupSession:
    def __init__(self, identities):
        self.identities = identities
        self.statement = None

    async def scalars(self, statement):
        self.statement = statement
        return _ScalarsResult(self.identities)


def test_alias_resolution_accepts_old_and_new_versions_for_same_identity() -> None:
    identity_id = uuid4()
    session = _AliasLookupSession([identity_id, identity_id])

    import asyncio

    resolved = asyncio.run(
        resolve_govbr_identity(
            session,
            issuer="issuer-test",
            subject="subject-test",
            keys={3: os.urandom(32), 4: os.urandom(32)},
        )
    )

    assert resolved == identity_id
    assert session.statement is not None


def test_alias_resolution_rejects_conflicting_identities() -> None:
    import asyncio

    session = _AliasLookupSession([uuid4(), uuid4()])

    with pytest.raises(IdentityAliasConflictError):
        asyncio.run(
            resolve_govbr_identity(
                session,
                issuer="issuer-test",
                subject="subject-test",
                keys={3: os.urandom(32), 4: os.urandom(32)},
            )
        )


def test_alias_resolution_returns_none_when_no_alias_matches() -> None:
    import asyncio

    session = _AliasLookupSession([])

    assert (
        asyncio.run(
            resolve_govbr_identity(
                session,
                issuer="issuer-test",
                subject="subject-test",
                keys={1: os.urandom(32)},
            )
        )
        is None
    )


def test_migration_uses_only_app_schema_and_is_reversible() -> None:
    module_spec = importlib.util.spec_from_file_location(
        "auth_identity_migration", MIGRATION_FILE
    )
    assert module_spec is not None
    assert module_spec.loader is not None
    migration = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(migration)

    tree = ast.parse(MIGRATION_FILE.read_text(encoding="utf-8"))
    create_tables = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "create_table"
    ]
    assert create_tables
    assert all(
        isinstance(node.args[0], ast.Constant)
        and str(node.args[0].value).startswith("app_")
        and any(
            keyword.arg == "schema"
            and isinstance(keyword.value, ast.Name)
            and keyword.value.id == "SCHEMA"
            for keyword in node.keywords
        )
        for node in create_tables
    )

    migration_source = MIGRATION_FILE.read_text(encoding="utf-8")
    assert 'SCHEMA = "app_auth"' in migration_source
    assert "GRANT INSERT ON app_auth.app_audit_logs TO app_runtime" in migration_source
    assert "GRANT UPDATE ON app_auth.app_audit_logs" not in migration_source
    assert "app_auth.app_system_controls" in migration_source
    assert "op.drop_table" in migration_source
    assert "schema=SCHEMA" in migration_source


def test_alembic_environment_requires_migration_credential_not_runtime_config() -> None:
    env_source = (ROOT / "migrations" / "env.py").read_text(encoding="utf-8")

    assert 'os.environ.get("APP_MIGRATION_DATABASE_URL")' in env_source
    assert 'os.environ.get("DATABASE_URL")' not in env_source
    assert "version_table_schema=AUTH_SCHEMA" in env_source
    assert "include_name=include_name" in env_source
    assert "app_migrator" in env_source
    assert "app_runtime" in env_source
    assert "pg_auth_members" in env_source
    assert "has_database_privilege" in env_source
    assert "has_sequence_privilege" in env_source
    assert "'TRIGGER'" in env_source

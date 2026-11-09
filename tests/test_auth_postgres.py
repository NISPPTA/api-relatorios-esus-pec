from __future__ import annotations

import asyncio
import os
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[1]
CONFIRMATION = "DISPOSABLE_POSTGRES_AUTH_PHASE1"
EXPECTED_AUTH_TABLES = {
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


def _test_database_settings() -> tuple[str, str, str]:
    if os.environ.get("AUTH_PHASE1_TEST_CONFIRMATION") != CONFIRMATION:
        pytest.skip("Explicit disposable PostgreSQL confirmation is not configured")

    admin_url = os.environ.get("AUTH_PHASE1_TEST_ADMIN_DATABASE_URL")
    migration_url = os.environ.get("AUTH_PHASE1_TEST_MIGRATION_DATABASE_URL")
    runtime_role = os.environ.get("AUTH_PHASE1_TEST_RUNTIME_ROLE")
    if not admin_url or not migration_url or not runtime_role:
        pytest.skip("Dedicated admin/migration URLs and runtime role are required")

    admin = make_url(admin_url)
    migration = make_url(migration_url)
    if (
        admin.get_backend_name() != "postgresql"
        or migration.get_backend_name() != "postgresql"
        or not admin.database
        or not migration.database
        or admin.database != migration.database
        or "test" not in admin.database.lower()
        or not admin.host
        or not migration.host
        or "neon.tech" in admin.host.lower()
        or "neon.tech" in migration.host.lower()
    ):
        pytest.fail(
            "Migration tests require a dedicated non-Neon PostgreSQL test database"
        )
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", runtime_role):
        pytest.fail("Runtime role must be a PostgreSQL identifier")
    return admin_url, migration_url, runtime_role


def _run(coro) -> None:
    asyncio.run(coro)


async def _fetch_all(url: str, statement: str, parameters: dict | None = None):
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            return (await connection.execute(text(statement), parameters or {})).all()
    finally:
        await engine.dispose()


def test_migration_isolated_schema_privileges_and_transactional_guards(
    monkeypatch,
) -> None:
    admin_url, migration_url, runtime_role = _test_database_settings()
    admin = make_url(admin_url)
    migration = make_url(migration_url)
    if admin.host != migration.host or admin.port != migration.port:
        pytest.fail(
            "Migration and admin URLs must target the same isolated test server"
        )

    role_name = f'"{runtime_role}"'
    probe_schema = f"auth_phase1_probe_{uuid.uuid4().hex}"
    probe_table = "synthetic_e_sus_fixture"
    probe_schema_quoted = f'"{probe_schema}"'
    probe_table_quoted = f'"{probe_table}"'
    probe_url = admin_url
    app_schema_tables = _fetch_all_sync(
        admin_url,
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'app_auth' ORDER BY table_name",
    )
    if app_schema_tables:
        pytest.fail(
            "Use a fresh disposable test database with an empty app_auth schema"
        )

    _run(
        _prepare_probe(
            admin_url,
            probe_schema_quoted,
            probe_table_quoted,
            role_name,
        )
    )
    before_probe = _fetch_all_sync(
        probe_url, f"SELECT id, marker FROM {probe_schema_quoted}.{probe_table_quoted}"
    )

    previous_url = os.environ.get("APP_MIGRATION_DATABASE_URL")
    monkeypatch.setenv("APP_MIGRATION_DATABASE_URL", migration_url)
    alembic_config = Config(str(ROOT / "alembic.ini"))

    try:
        command.upgrade(alembic_config, "head")

        assert _fetch_all_sync(
            admin_url,
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'app_auth' AND table_name LIKE 'app\\_%' "
            "ORDER BY table_name",
        ) == [(name,) for name in sorted(EXPECTED_AUTH_TABLES)]

        _assert_role_privileges(
            admin_url, runtime_role, migration.username, probe_schema, probe_table
        )
        _assert_migration_role_does_not_modify_probe(
            migration_url, probe_schema_quoted, probe_table_quoted
        )
        _assert_bootstrap_lock_and_grant_revocation(migration_url)

        assert (
            _fetch_all_sync(
                probe_url,
                f"SELECT id, marker FROM {probe_schema_quoted}.{probe_table_quoted}",
            )
            == before_probe
        )

        command.downgrade(alembic_config, "base")
        remaining = _fetch_all_sync(
            admin_url,
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'app_auth' AND table_name LIKE 'app\\_%'",
        )
        assert remaining == []
        assert (
            _fetch_all_sync(
                probe_url,
                f"SELECT id, marker FROM {probe_schema_quoted}.{probe_table_quoted}",
            )
            == before_probe
        )
        assert _fetch_all_sync(
            admin_url,
            "SELECT has_schema_privilege(:runtime, 'app_auth', 'USAGE'), "
            "has_table_privilege(:runtime, 'app_auth.alembic_version', 'SELECT')",
            {"runtime": runtime_role},
        ) == [(False, False)]
        command.upgrade(alembic_config, "head")
        assert _fetch_all_sync(
            admin_url,
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'app_auth' AND table_name LIKE 'app\\_%' "
            "ORDER BY table_name",
        ) == [(name,) for name in sorted(EXPECTED_AUTH_TABLES)]
    finally:
        if previous_url is None:
            monkeypatch.delenv("APP_MIGRATION_DATABASE_URL", raising=False)
        else:
            monkeypatch.setenv("APP_MIGRATION_DATABASE_URL", previous_url)
        _run(_drop_probe(admin_url, probe_schema_quoted))


def _fetch_all_sync(
    url: str, statement: str, parameters: dict | None = None
) -> list[tuple]:
    return asyncio.run(_fetch_all(url, statement, parameters))


async def _prepare_probe(url: str, schema: str, table: str, runtime_role: str) -> None:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA {schema}"))
            await connection.execute(
                text(
                    f"CREATE TABLE {schema}.{table} "
                    "(id integer PRIMARY KEY, marker text NOT NULL)"
                )
            )
            await connection.execute(
                text(
                    f"INSERT INTO {schema}.{table} (id, marker) "
                    "VALUES (1, 'synthetic-only')"
                )
            )
            await connection.execute(
                text(f"GRANT USAGE ON SCHEMA {schema} TO {runtime_role}")
            )
            await connection.execute(
                text(f"GRANT SELECT ON {schema}.{table} TO {runtime_role}")
            )
    finally:
        await engine.dispose()


async def _drop_probe(url: str, schema: str) -> None:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
    finally:
        await engine.dispose()


def _assert_role_privileges(
    url: str,
    runtime_role: str,
    migration_role: str | None,
    probe_schema: str,
    probe_table: str,
) -> None:
    assert migration_role == "app_migrator"

    async def verify() -> None:
        engine = create_async_engine(url)
        try:
            async with engine.connect() as connection:
                result = await connection.execute(
                    text(
                        "SELECT "
                        "has_schema_privilege(:runtime, 'app_auth', 'CREATE'), "
                        "has_table_privilege(:runtime, 'app_auth.app_audit_logs', 'INSERT'), "
                        "has_table_privilege(:runtime, 'app_auth.app_audit_logs', 'UPDATE'), "
                        "has_table_privilege(:runtime, 'app_auth.app_audit_logs', 'DELETE'), "
                        "has_table_privilege(:runtime, 'app_auth.app_system_controls', 'UPDATE'), "
                        "has_table_privilege(:runtime, 'app_auth.app_roles', 'INSERT'), "
                        "has_table_privilege(:runtime, 'app_auth.app_roles', 'UPDATE'), "
                        "has_table_privilege(:runtime, 'app_auth.app_role_permissions', 'INSERT'), "
                        "has_table_privilege(:runtime, 'app_auth.app_role_permissions', 'DELETE'), "
                        "has_schema_privilege(:migration, :probe_schema, 'CREATE'), "
                        "has_table_privilege(:migration, :probe_table, 'INSERT'), "
                        "has_table_privilege(:migration, :probe_table, 'UPDATE'), "
                        "has_table_privilege(:migration, :probe_table, 'DELETE'), "
                        "has_table_privilege(:runtime, :probe_table, 'SELECT'), "
                        "has_table_privilege(:runtime, :probe_table, 'INSERT'), "
                        "has_table_privilege(:runtime, :probe_table, 'UPDATE'), "
                        "has_table_privilege(:runtime, :probe_table, 'DELETE')"
                    ),
                    {
                        "runtime": runtime_role,
                        "migration": migration_role,
                        "probe_schema": probe_schema,
                        "probe_table": f"{probe_schema}.{probe_table}",
                    },
                )
                values = result.one()
                assert values == (
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                )
        finally:
            await engine.dispose()

    asyncio.run(verify())


def _assert_migration_role_does_not_modify_probe(
    url: str, schema: str, table: str
) -> None:
    assert _fetch_all_sync(url, f"SELECT id, marker FROM {schema}.{table}") == [
        (1, "synthetic-only")
    ]


def _assert_bootstrap_lock_and_grant_revocation(url: str) -> None:
    _run(_exercise_bootstrap_and_grants(url))


async def _exercise_bootstrap_and_grants(url: str) -> None:
    engine = create_async_engine(url)
    now = datetime.now(UTC)
    user_ids = [uuid.uuid4(), uuid.uuid4()]
    created: list[bool] = []

    async def attempt_bootstrap(user_id: uuid.UUID, operator: str) -> None:
        async with engine.begin() as connection:
            state = (
                await connection.execute(
                    text(
                        "SELECT bootstrap_status FROM app_auth.app_system_controls "
                        "WHERE singleton_id = 1 FOR UPDATE"
                    )
                )
            ).scalar_one()
            if state != "pending":
                created.append(False)
                return

            await connection.execute(
                text(
                    "INSERT INTO app_auth.app_users "
                    "(id, status, created_at, updated_at) "
                    "VALUES (:id, 'active', :now, :now)"
                ),
                {"id": user_id, "now": now},
            )
            await connection.execute(
                text(
                    "UPDATE app_auth.app_system_controls SET "
                    "bootstrap_status = 'completed', completed_at = :now, "
                    "initial_admin_user_id = :user_id, "
                    "responsible_operators = CAST(:operators AS jsonb), "
                    "authorization_reference = :reference, result = 'success', "
                    "updated_at = :now WHERE singleton_id = 1"
                ),
                {
                    "now": now,
                    "user_id": user_id,
                    "operators": f'["{operator}"]',
                    "reference": "SYNTHETIC-BOOTSTRAP-TEST",
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO app_auth.app_audit_logs "
                    "(id, actor_type, event_type, result, target_user_id, "
                    "authorization_reference, operator_identifiers, metadata) "
                    "VALUES (:id, 'bootstrap_operators', 'initial_admin_bootstrap', "
                    "'success', :user_id, :reference, CAST(:operators AS jsonb), "
                    "'{}'::jsonb)"
                ),
                {
                    "id": uuid.uuid4(),
                    "user_id": user_id,
                    "reference": "SYNTHETIC-BOOTSTRAP-TEST",
                    "operators": f'["{operator}"]',
                },
            )
            await asyncio.sleep(0.1)
            created.append(True)

    try:
        await asyncio.gather(
            attempt_bootstrap(user_ids[0], "synthetic-operator-a"),
            attempt_bootstrap(user_ids[1], "synthetic-operator-b"),
        )
        assert sum(created) == 1
        control = await _fetch_all(
            url,
            "SELECT bootstrap_status, initial_admin_user_id, "
            "authorization_reference, result FROM app_auth.app_system_controls",
        )
        assert len(control) == 1
        assert control[0][0] == "completed"
        assert control[0][1] in user_ids
        assert control[0][2:] == ("SYNTHETIC-BOOTSTRAP-TEST", "success")

        await _assert_identity_constraints(engine, now)
        grant_id, grantee_id, grantor_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO app_auth.app_users "
                    "(id, status, created_at, updated_at) "
                    "VALUES (:id, 'active', :now, :now)"
                ),
                [
                    {"id": grantee_id, "now": now},
                    {"id": grantor_id, "now": now},
                ],
            )
            await connection.execute(
                text(
                    "INSERT INTO app_auth.app_user_permission_grants "
                    "(id, user_id, permission_code, scope_type, scope_identifier, "
                    "justification, granted_by_user_id, starts_at, expires_at) "
                    "VALUES (:id, :user, 'view_sensitive_aggregates', 'unit', "
                    "'1234567', 'Synthetic test authorization', :grantor, "
                    ":starts, :expires)"
                ),
                {
                    "id": grant_id,
                    "user": grantee_id,
                    "grantor": grantor_id,
                    "starts": now - timedelta(minutes=1),
                    "expires": now + timedelta(hours=1),
                },
            )
        active = await _fetch_all(
            url,
            "SELECT id FROM app_auth.app_user_permission_grants WHERE id = :id "
            "AND starts_at <= now() AND expires_at > now() AND revoked_at IS NULL",
            {"id": grant_id},
        )
        assert active == [(grant_id,)]
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE app_auth.app_user_permission_grants "
                    "SET revoked_at = now() WHERE id = :id"
                ),
                {"id": grant_id},
            )
        revoked = await _fetch_all(
            url,
            "SELECT id FROM app_auth.app_user_permission_grants WHERE id = :id "
            "AND starts_at <= now() AND expires_at > now() AND revoked_at IS NULL",
            {"id": grant_id},
        )
        assert revoked == []

        expired_grant = uuid.uuid4()
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO app_auth.app_user_permission_grants "
                    "(id, user_id, permission_code, scope_type, scope_identifier, "
                    "justification, granted_by_user_id, starts_at, expires_at) "
                    "VALUES (:id, :user, 'view_reports', 'report', 'synthetic', "
                    "'Synthetic expired grant', :grantor, :starts, :expires)"
                ),
                {
                    "id": expired_grant,
                    "user": grantee_id,
                    "grantor": grantor_id,
                    "starts": now - timedelta(hours=2),
                    "expires": now - timedelta(hours=1),
                },
            )
        expired = await _fetch_all(
            url,
            "SELECT id FROM app_auth.app_user_permission_grants WHERE id = :id "
            "AND starts_at <= now() AND expires_at > now() AND revoked_at IS NULL",
            {"id": expired_grant},
        )
        assert expired == []
    finally:
        await engine.dispose()


async def _assert_identity_constraints(engine, now: datetime) -> None:
    first_user, second_user = uuid.uuid4(), uuid.uuid4()
    first_identity, second_identity = uuid.uuid4(), uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_auth.app_users (id, status, created_at, updated_at) "
                "VALUES (:first, 'active', :now, :now), "
                "(:second, 'active', :now, :now)"
            ),
            {"first": first_user, "second": second_user, "now": now},
        )
        await connection.execute(
            text(
                "INSERT INTO app_auth.app_auth_identities "
                "(id, user_id, provider, issuer) "
                "VALUES (:id, :user, 'govbr', 'issuer-test')"
            ),
            {"id": first_identity, "user": first_user},
        )
        await connection.execute(
            text(
                "INSERT INTO app_auth.app_auth_identities "
                "(id, user_id, provider, issuer) "
                "VALUES (:id, :user, 'govbr', 'issuer-test')"
            ),
            {"id": second_identity, "user": second_user},
        )
        await connection.execute(
            text(
                "INSERT INTO app_auth.app_auth_identity_keys "
                "(identity_id, provider, issuer, key_version, subject_hmac) "
                "VALUES (:identity, 'govbr', 'issuer-test', 1, :digest)"
            ),
            {"identity": first_identity, "digest": b"h" * 32},
        )

    with pytest.raises(IntegrityError):
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO app_auth.app_auth_identities "
                    "(id, user_id, provider, issuer) "
                    "VALUES (:id, :user, 'govbr', 'issuer-test')"
                ),
                {"id": uuid.uuid4(), "user": first_user},
            )

    with pytest.raises(IntegrityError):
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO app_auth.app_auth_identity_keys "
                    "(identity_id, provider, issuer, key_version, subject_hmac) "
                    "VALUES (:identity, 'govbr', 'issuer-test', 1, :digest)"
                ),
                {"identity": second_identity, "digest": b"h" * 32},
            )

    with pytest.raises(IntegrityError):
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO app_auth.app_local_credentials "
                    "(identity_id, provider, login_identifier_normalized, password_hash) "
                    "VALUES (:identity, 'local', 'synthetic-login', 'synthetic-hash')"
                ),
                {"identity": first_identity},
            )

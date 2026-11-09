"""Create application-owned identity and authorization data structures.

Revision ID: 0001_identity_data
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_identity_data"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "app_auth"


def upgrade() -> None:
    op.create_table(
        "app_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deactivated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')", name="ck_app_users_status_allowed"
        ),
        sa.CheckConstraint(
            "(status = 'active' AND deactivated_at IS NULL) OR "
            "(status = 'disabled' AND deactivated_at IS NOT NULL)",
            name="ck_app_users_status_deactivation_consistent",
        ),
        schema=SCHEMA,
    )
    op.create_table(
        "app_auth_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("issuer", sa.String(512), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("disabled_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "provider IN ('local', 'govbr')",
            name="ck_app_auth_identities_provider_allowed",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_app_auth_identities_status_allowed",
        ),
        sa.CheckConstraint(
            "(status = 'active' AND disabled_at IS NULL) OR "
            "(status = 'disabled' AND disabled_at IS NOT NULL)",
            name="ck_app_auth_identities_status_disabled_at_consistent",
        ),
        sa.CheckConstraint(
            "(provider = 'local' AND issuer = 'local') OR "
            "(provider = 'govbr' AND issuer <> 'local')",
            name="ck_app_auth_identities_issuer_matches_provider",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.app_users.id"],
            name="fk_app_auth_identities_identity_user",
        ),
        sa.UniqueConstraint(
            "user_id",
            "provider",
            "issuer",
            name="uq_app_auth_identities_user_provider_issuer",
        ),
        sa.UniqueConstraint(
            "id", "provider", name="uq_app_auth_identities_id_provider"
        ),
        sa.UniqueConstraint(
            "id", "provider", "issuer", name="uq_app_auth_identities_id_provider_issuer"
        ),
        schema=SCHEMA,
    )
    op.create_table(
        "app_auth_identity_keys",
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(16), primary_key=True),
        sa.Column("issuer", sa.String(512), primary_key=True),
        sa.Column("key_version", sa.SmallInteger(), primary_key=True),
        sa.Column("subject_hmac", sa.LargeBinary(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "provider = 'govbr'", name="ck_app_auth_identity_keys_govbr_only"
        ),
        sa.CheckConstraint(
            "key_version > 0", name="ck_app_auth_identity_keys_key_version_positive"
        ),
        sa.CheckConstraint(
            "octet_length(subject_hmac) = 32",
            name="ck_app_auth_identity_keys_subject_hmac_sha256_length",
        ),
        sa.ForeignKeyConstraint(
            ["identity_id", "provider", "issuer"],
            [
                f"{SCHEMA}.app_auth_identities.id",
                f"{SCHEMA}.app_auth_identities.provider",
                f"{SCHEMA}.app_auth_identities.issuer",
            ],
            name="fk_app_auth_identity_keys_identity_provider_issuer",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "provider",
            "issuer",
            "key_version",
            "subject_hmac",
            name="uq_app_auth_identity_keys_provider_issuer_key_digest",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_app_auth_identity_keys_identity_version",
        "app_auth_identity_keys",
        ["identity_id", "key_version"],
        schema=SCHEMA,
    )
    op.create_table(
        "app_local_credentials",
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(16), nullable=False, server_default="local"),
        sa.Column("login_identifier_normalized", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "credential_created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "provider = 'local'", name="ck_app_local_credentials_local_provider_only"
        ),
        sa.CheckConstraint(
            "length(login_identifier_normalized) > 0",
            name="ck_app_local_credentials_login_identifier_not_empty",
        ),
        sa.CheckConstraint(
            "length(password_hash) > 0",
            name="ck_app_local_credentials_password_hash_not_empty",
        ),
        sa.ForeignKeyConstraint(
            ["identity_id", "provider"],
            [
                f"{SCHEMA}.app_auth_identities.id",
                f"{SCHEMA}.app_auth_identities.provider",
            ],
            name="fk_app_local_credentials_local_identity_provider",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "login_identifier_normalized",
            name="uq_app_local_credentials_login_identifier_normalized",
        ),
        schema=SCHEMA,
    )
    op.create_table(
        "app_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revocation_reason", sa.String(64)),
        sa.CheckConstraint(
            "octet_length(token_hash) = 32",
            name="ck_app_sessions_token_hash_sha256_length",
        ),
        sa.CheckConstraint(
            "expires_at > created_at AND idle_expires_at > created_at "
            "AND idle_expires_at <= expires_at",
            name="ck_app_sessions_expiration_after_creation",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_app_sessions_revocation_after_creation",
        ),
        sa.CheckConstraint(
            "revocation_reason IS NULL OR revoked_at IS NOT NULL",
            name="ck_app_sessions_revocation_reason_requires_revocation",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], [f"{SCHEMA}.app_users.id"], name="fk_app_sessions_session_user"
        ),
        sa.UniqueConstraint("token_hash", name="uq_app_sessions_token_hash"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_app_sessions_user_expiration",
        "app_sessions",
        ["user_id", "expires_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_app_sessions_expiration", "app_sessions", ["expires_at"], schema=SCHEMA
    )
    op.create_table(
        "app_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role_code", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("role_code", name="uq_app_roles_role_code"),
        schema=SCHEMA,
    )
    op.create_table(
        "app_user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("grant_source", sa.String(20), nullable=False),
        sa.Column("authorization_reference", sa.String(256)),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "grant_source IN ('administrator', 'bootstrap')",
            name="ck_app_user_roles_grant_source_allowed",
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at > granted_at",
            name="ck_app_user_roles_grant_expiration",
        ),
        sa.CheckConstraint(
            "(grant_source = 'bootstrap' AND granted_by_user_id IS NULL AND authorization_reference IS NOT NULL) OR "
            "(grant_source = 'administrator' AND granted_by_user_id IS NOT NULL)",
            name="ck_app_user_roles_grant_actor_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.app_users.id"],
            name="fk_app_user_roles_role_assignment_user",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            [f"{SCHEMA}.app_roles.id"],
            name="fk_app_user_roles_role_assignment_role",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            [f"{SCHEMA}.app_users.id"],
            name="fk_app_user_roles_role_assignment_grantor",
        ),
        sa.UniqueConstraint(
            "user_id",
            "role_id",
            "granted_at",
            name="uq_app_user_roles_user_role_granted_at",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_app_user_roles_unrevoked",
        "app_user_roles",
        ["user_id", "role_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_table(
        "app_role_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_code", sa.String(64), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False, server_default="global"),
        sa.Column(
            "scope_identifier", sa.String(128), nullable=False, server_default=""
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "length(permission_code) > 0",
            name="ck_app_role_permissions_permission_code_not_empty",
        ),
        sa.CheckConstraint(
            "scope_type IN ('global', 'report', 'professional', 'unit')",
            name="ck_app_role_permissions_scope_type_allowed",
        ),
        sa.CheckConstraint(
            "(scope_type = 'global' AND scope_identifier = '') OR "
            "(scope_type <> 'global' AND length(scope_identifier) > 0)",
            name="ck_app_role_permissions_scope_identifier_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            [f"{SCHEMA}.app_roles.id"],
            name="fk_app_role_permissions_role_permission_role",
        ),
        sa.UniqueConstraint(
            "role_id",
            "permission_code",
            "scope_type",
            "scope_identifier",
            name="uq_app_role_permissions_role_permission_scope",
        ),
        schema=SCHEMA,
    )
    op.create_table(
        "app_user_permission_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_code", sa.String(64), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("scope_identifier", sa.String(128), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "length(permission_code) > 0",
            name="ck_app_user_permission_grants_permission_code_not_empty",
        ),
        sa.CheckConstraint(
            "scope_type IN ('report', 'professional', 'unit')",
            name="ck_app_user_permission_grants_scope_type_allowed",
        ),
        sa.CheckConstraint(
            "length(scope_identifier) > 0",
            name="ck_app_user_permission_grants_scope_identifier_required",
        ),
        sa.CheckConstraint(
            "length(trim(justification)) > 0",
            name="ck_app_user_permission_grants_justification_required",
        ),
        sa.CheckConstraint(
            "expires_at > starts_at",
            name="ck_app_user_permission_grants_grant_expiration_required",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= starts_at",
            name="ck_app_user_permission_grants_revocation_after_start",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.app_users.id"],
            name="fk_app_user_permission_grants_permission_grant_user",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            [f"{SCHEMA}.app_users.id"],
            name="fk_app_user_permission_grants_permission_grant_grantor",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_app_user_permission_grants_active",
        "app_user_permission_grants",
        ["user_id", "permission_code", "expires_at"],
        schema=SCHEMA,
    )
    op.create_table(
        "app_user_professionals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_id", sa.Integer(), nullable=False),
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "starts_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "professional_id > 0",
            name="ck_app_user_professionals_professional_id_positive",
        ),
        sa.CheckConstraint(
            "ends_at IS NULL OR ends_at > starts_at",
            name="ck_app_user_professionals_link_period",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.app_users.id"],
            name="fk_app_user_professionals_professional_link_user",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            [f"{SCHEMA}.app_users.id"],
            name="fk_app_user_professionals_professional_link_grantor",
        ),
        sa.UniqueConstraint(
            "user_id",
            "professional_id",
            "starts_at",
            name="uq_app_user_professionals_user_professional_start",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_app_user_professionals_professional",
        "app_user_professionals",
        ["professional_id", "ends_at"],
        schema=SCHEMA,
    )
    op.create_table(
        "app_user_units",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cnes", sa.String(7), nullable=False),
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "starts_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "length(cnes) BETWEEN 1 AND 7", name="ck_app_user_units_cnes_length"
        ),
        sa.CheckConstraint("cnes ~ '^[0-9]+$'", name="ck_app_user_units_cnes_numeric"),
        sa.CheckConstraint(
            "ends_at IS NULL OR ends_at > starts_at",
            name="ck_app_user_units_link_period",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.app_users.id"],
            name="fk_app_user_units_unit_link_user",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            [f"{SCHEMA}.app_users.id"],
            name="fk_app_user_units_unit_link_grantor",
        ),
        sa.UniqueConstraint(
            "user_id", "cnes", "starts_at", name="uq_app_user_units_user_unit_start"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_app_user_units_cnes", "app_user_units", ["cnes", "ends_at"], schema=SCHEMA
    )
    op.create_table(
        "app_login_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("key_version", sa.SmallInteger(), nullable=False),
        sa.Column("identifier_digest", sa.LargeBinary(32), nullable=False),
        sa.Column("source_digest", sa.LargeBinary(32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True)),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "provider IN ('local', 'govbr')",
            name="ck_app_login_attempts_provider_allowed",
        ),
        sa.CheckConstraint(
            "key_version > 0", name="ck_app_login_attempts_key_version_positive"
        ),
        sa.CheckConstraint(
            "octet_length(identifier_digest) = 32",
            name="ck_app_login_attempts_identifier_digest_length",
        ),
        sa.CheckConstraint(
            "octet_length(source_digest) = 32",
            name="ck_app_login_attempts_source_digest_length",
        ),
        sa.CheckConstraint(
            "attempt_count > 0", name="ck_app_login_attempts_attempt_count_positive"
        ),
        sa.UniqueConstraint(
            "provider",
            "key_version",
            "identifier_digest",
            "source_digest",
            "window_started_at",
            name="uq_app_login_attempts_rate_limit_bucket",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_app_login_attempts_blocked_until",
        "app_login_attempts",
        ["blocked_until"],
        schema=SCHEMA,
    )
    op.create_table(
        "app_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_type", sa.String(24), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("justification", sa.Text()),
        sa.Column("scope_type", sa.String(20)),
        sa.Column("scope_identifier", sa.String(128)),
        sa.Column("authorization_reference", sa.String(256)),
        sa.Column(
            "operator_identifiers",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "actor_type IN ('user', 'bootstrap_operators', 'system')",
            name="ck_app_audit_logs_actor_type_allowed",
        ),
        sa.CheckConstraint(
            "result IN ('success', 'failure')", name="ck_app_audit_logs_result_allowed"
        ),
        sa.CheckConstraint(
            "(actor_type = 'user' AND actor_user_id IS NOT NULL) OR "
            "(actor_type <> 'user' AND actor_user_id IS NULL)",
            name="ck_app_audit_logs_actor_identity_consistent",
        ),
        sa.CheckConstraint(
            "event_type <> 'initial_admin_bootstrap' OR "
            "(actor_type = 'bootstrap_operators' AND "
            "jsonb_typeof(operator_identifiers) = 'array' AND "
            "jsonb_array_length(operator_identifiers) > 0 AND "
            "authorization_reference IS NOT NULL AND target_user_id IS NOT NULL)",
            name="ck_app_audit_logs_bootstrap_audit_complete",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            [f"{SCHEMA}.app_users.id"],
            name="fk_app_audit_logs_audit_actor",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            [f"{SCHEMA}.app_users.id"],
            name="fk_app_audit_logs_audit_target",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_app_audit_logs_occurred_at",
        "app_audit_logs",
        ["occurred_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_app_audit_logs_actor_time",
        "app_audit_logs",
        ["actor_user_id", "occurred_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_app_audit_logs_event_time",
        "app_audit_logs",
        ["event_type", "occurred_at"],
        schema=SCHEMA,
    )
    op.create_table(
        "app_system_controls",
        sa.Column("singleton_id", sa.SmallInteger(), primary_key=True),
        sa.Column(
            "bootstrap_status", sa.String(16), nullable=False, server_default="pending"
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("initial_admin_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "responsible_operators",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("authorization_reference", sa.String(256)),
        sa.Column("result", sa.String(16)),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "singleton_id = 1", name="ck_app_system_controls_singleton_row"
        ),
        sa.CheckConstraint(
            "(bootstrap_status = 'pending' AND completed_at IS NULL "
            "AND initial_admin_user_id IS NULL AND result IS NULL) OR "
            "(bootstrap_status = 'completed' AND completed_at IS NOT NULL "
            "AND initial_admin_user_id IS NOT NULL AND result = 'success' "
            "AND authorization_reference IS NOT NULL "
            "AND jsonb_typeof(responsible_operators) = 'array' "
            "AND jsonb_array_length(responsible_operators) > 0)",
            name="ck_app_system_controls_bootstrap_state_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["initial_admin_user_id"],
            [f"{SCHEMA}.app_users.id"],
            name="fk_app_system_controls_bootstrap_initial_admin",
        ),
        schema=SCHEMA,
    )
    op.execute(
        sa.text(
            "INSERT INTO app_auth.app_system_controls "
            "(singleton_id, bootstrap_status, responsible_operators) "
            "VALUES (1, 'pending', '[]'::jsonb)"
        )
    )
    op.execute("REVOKE ALL ON SCHEMA app_auth FROM PUBLIC")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA app_auth FROM PUBLIC")
    op.execute("GRANT USAGE ON SCHEMA app_auth TO app_runtime")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA app_auth TO app_runtime")
    op.execute("GRANT INSERT, UPDATE ON app_auth.app_users TO app_runtime")
    op.execute("GRANT INSERT, UPDATE ON app_auth.app_auth_identities TO app_runtime")
    op.execute("GRANT INSERT, DELETE ON app_auth.app_auth_identity_keys TO app_runtime")
    op.execute("GRANT INSERT, UPDATE ON app_auth.app_local_credentials TO app_runtime")
    op.execute("GRANT INSERT, UPDATE, DELETE ON app_auth.app_sessions TO app_runtime")
    op.execute("GRANT INSERT, UPDATE ON app_auth.app_user_roles TO app_runtime")
    op.execute(
        "GRANT INSERT, UPDATE ON app_auth.app_user_permission_grants TO app_runtime"
    )
    op.execute("GRANT INSERT, UPDATE ON app_auth.app_user_professionals TO app_runtime")
    op.execute("GRANT INSERT, UPDATE ON app_auth.app_user_units TO app_runtime")
    op.execute(
        "GRANT INSERT, UPDATE, DELETE ON app_auth.app_login_attempts TO app_runtime"
    )
    op.execute("GRANT INSERT ON app_auth.app_audit_logs TO app_runtime")
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE app_migrator IN SCHEMA app_auth "
        "REVOKE ALL ON TABLES FROM PUBLIC"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE app_migrator IN SCHEMA app_auth "
        "GRANT SELECT ON TABLES TO app_runtime"
    )


def downgrade() -> None:
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE app_migrator IN SCHEMA app_auth "
        "REVOKE SELECT ON TABLES FROM app_runtime"
    )
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA app_auth FROM app_runtime")
    op.drop_table("app_system_controls", schema=SCHEMA)
    op.drop_index(
        "ix_app_audit_logs_event_time", table_name="app_audit_logs", schema=SCHEMA
    )
    op.drop_index(
        "ix_app_audit_logs_actor_time", table_name="app_audit_logs", schema=SCHEMA
    )
    op.drop_index(
        "ix_app_audit_logs_occurred_at", table_name="app_audit_logs", schema=SCHEMA
    )
    op.drop_table("app_audit_logs", schema=SCHEMA)
    op.drop_index(
        "ix_app_login_attempts_blocked_until",
        table_name="app_login_attempts",
        schema=SCHEMA,
    )
    op.drop_table("app_login_attempts", schema=SCHEMA)
    op.drop_index("ix_app_user_units_cnes", table_name="app_user_units", schema=SCHEMA)
    op.drop_table("app_user_units", schema=SCHEMA)
    op.drop_index(
        "ix_app_user_professionals_professional",
        table_name="app_user_professionals",
        schema=SCHEMA,
    )
    op.drop_table("app_user_professionals", schema=SCHEMA)
    op.drop_index(
        "ix_app_user_permission_grants_active",
        table_name="app_user_permission_grants",
        schema=SCHEMA,
    )
    op.drop_table("app_user_permission_grants", schema=SCHEMA)
    op.drop_table("app_role_permissions", schema=SCHEMA)
    op.drop_index(
        "uq_app_user_roles_unrevoked", table_name="app_user_roles", schema=SCHEMA
    )
    op.drop_table("app_user_roles", schema=SCHEMA)
    op.drop_table("app_roles", schema=SCHEMA)
    op.drop_index(
        "ix_app_sessions_expiration", table_name="app_sessions", schema=SCHEMA
    )
    op.drop_index(
        "ix_app_sessions_user_expiration", table_name="app_sessions", schema=SCHEMA
    )
    op.drop_table("app_sessions", schema=SCHEMA)
    op.drop_table("app_local_credentials", schema=SCHEMA)
    op.drop_index(
        "ix_app_auth_identity_keys_identity_version",
        table_name="app_auth_identity_keys",
        schema=SCHEMA,
    )
    op.drop_table("app_auth_identity_keys", schema=SCHEMA)
    op.drop_table("app_auth_identities", schema=SCHEMA)
    op.drop_table("app_users", schema=SCHEMA)
    op.execute("REVOKE USAGE ON SCHEMA app_auth FROM app_runtime")

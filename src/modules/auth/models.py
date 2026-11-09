from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

AUTH_SCHEMA = "app_auth"

_JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class AuthBase(DeclarativeBase):
    metadata = MetaData(
        schema=AUTH_SCHEMA,
        naming_convention={
            "pk": "pk_%(table_name)s",
            "fk": "fk_%(table_name)s_%(constraint_name)s",
            "uq": "uq_%(table_name)s_%(constraint_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "ix": "ix_%(table_name)s_%(column_0_name)s",
        },
    )


class AppUser(AuthBase):
    __tablename__ = "app_users"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled')", name="status_allowed"),
        CheckConstraint(
            "(status = 'active' AND deactivated_at IS NULL) OR "
            "(status = 'disabled' AND deactivated_at IS NOT NULL)",
            name="status_deactivation_consistent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AppAuthIdentity(AuthBase):
    __tablename__ = "app_auth_identities"
    __table_args__ = (
        CheckConstraint("provider IN ('local', 'govbr')", name="provider_allowed"),
        CheckConstraint("status IN ('active', 'disabled')", name="status_allowed"),
        CheckConstraint(
            "(status = 'active' AND disabled_at IS NULL) OR "
            "(status = 'disabled' AND disabled_at IS NOT NULL)",
            name="status_disabled_at_consistent",
        ),
        CheckConstraint(
            "(provider = 'local' AND issuer = 'local') OR "
            "(provider = 'govbr' AND issuer <> 'local')",
            name="issuer_matches_provider",
        ),
        UniqueConstraint("user_id", "provider", "issuer", name="user_provider_issuer"),
        UniqueConstraint("id", "provider", name="id_provider"),
        UniqueConstraint("id", "provider", "issuer", name="id_provider_issuer"),
        ForeignKeyConstraint(
            ["user_id"], [f"{AUTH_SCHEMA}.app_users.id"], name="identity_user"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    issuer: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AppAuthIdentityKey(AuthBase):
    __tablename__ = "app_auth_identity_keys"
    __table_args__ = (
        CheckConstraint("provider = 'govbr'", name="govbr_only"),
        CheckConstraint("key_version > 0", name="key_version_positive"),
        CheckConstraint(
            "octet_length(subject_hmac) = 32", name="subject_hmac_sha256_length"
        ),
        UniqueConstraint(
            "provider",
            "issuer",
            "key_version",
            "subject_hmac",
            name="provider_issuer_key_digest",
        ),
        ForeignKeyConstraint(
            ["identity_id", "provider", "issuer"],
            [
                f"{AUTH_SCHEMA}.app_auth_identities.id",
                f"{AUTH_SCHEMA}.app_auth_identities.provider",
                f"{AUTH_SCHEMA}.app_auth_identities.issuer",
            ],
            name="identity_provider_issuer",
            ondelete="CASCADE",
        ),
        Index(
            "ix_app_auth_identity_keys_identity_version", "identity_id", "key_version"
        ),
    )

    identity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    provider: Mapped[str] = mapped_column(String(16), primary_key=True)
    issuer: Mapped[str] = mapped_column(String(512), primary_key=True)
    key_version: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    subject_hmac: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AppLocalCredential(AuthBase):
    __tablename__ = "app_local_credentials"
    __table_args__ = (
        CheckConstraint("provider = 'local'", name="local_provider_only"),
        CheckConstraint(
            "length(login_identifier_normalized) > 0",
            name="login_identifier_not_empty",
        ),
        CheckConstraint("length(password_hash) > 0", name="password_hash_not_empty"),
        ForeignKeyConstraint(
            ["identity_id", "provider"],
            [
                f"{AUTH_SCHEMA}.app_auth_identities.id",
                f"{AUTH_SCHEMA}.app_auth_identities.provider",
            ],
            name="local_identity_provider",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "login_identifier_normalized", name="login_identifier_normalized"
        ),
    )

    identity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    provider: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="local"
    )
    login_identifier_normalized: Mapped[str] = mapped_column(
        String(320), nullable=False
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    credential_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AppSession(AuthBase):
    __tablename__ = "app_sessions"
    __table_args__ = (
        CheckConstraint(
            "octet_length(token_hash) = 32", name="token_hash_sha256_length"
        ),
        CheckConstraint(
            "expires_at > created_at AND idle_expires_at > created_at "
            "AND idle_expires_at <= expires_at",
            name="expiration_after_creation",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="revocation_after_creation",
        ),
        CheckConstraint(
            "revocation_reason IS NULL OR revoked_at IS NOT NULL",
            name="revocation_reason_requires_revocation",
        ),
        ForeignKeyConstraint(
            ["user_id"], [f"{AUTH_SCHEMA}.app_users.id"], name="session_user"
        ),
        UniqueConstraint("token_hash", name="token_hash"),
        Index("ix_app_sessions_user_expiration", "user_id", "expires_at"),
        Index("ix_app_sessions_expiration", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    idle_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None] = mapped_column(String(64))


class AppRole(AuthBase):
    __tablename__ = "app_roles"
    __table_args__ = (UniqueConstraint("role_code", name="role_code"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    role_code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AppUserRole(AuthBase):
    __tablename__ = "app_user_roles"
    __table_args__ = (
        CheckConstraint(
            "grant_source IN ('administrator', 'bootstrap')",
            name="grant_source_allowed",
        ),
        CheckConstraint(
            "expires_at IS NULL OR expires_at > granted_at", name="grant_expiration"
        ),
        CheckConstraint(
            "(grant_source = 'bootstrap' AND granted_by_user_id IS NULL "
            "AND authorization_reference IS NOT NULL) OR "
            "(grant_source = 'administrator' AND granted_by_user_id IS NOT NULL)",
            name="grant_actor_consistent",
        ),
        ForeignKeyConstraint(
            ["user_id"], [f"{AUTH_SCHEMA}.app_users.id"], name="role_assignment_user"
        ),
        ForeignKeyConstraint(
            ["role_id"], [f"{AUTH_SCHEMA}.app_roles.id"], name="role_assignment_role"
        ),
        ForeignKeyConstraint(
            ["granted_by_user_id"],
            [f"{AUTH_SCHEMA}.app_users.id"],
            name="role_assignment_grantor",
        ),
        UniqueConstraint(
            "user_id", "role_id", "granted_at", name="user_role_granted_at"
        ),
        Index(
            "uq_app_user_roles_unrevoked",
            "user_id",
            "role_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    granted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    grant_source: Mapped[str] = mapped_column(String(20), nullable=False)
    authorization_reference: Mapped[str | None] = mapped_column(String(256))
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AppRolePermission(AuthBase):
    __tablename__ = "app_role_permissions"
    __table_args__ = (
        CheckConstraint(
            "length(permission_code) > 0", name="permission_code_not_empty"
        ),
        CheckConstraint(
            "scope_type IN ('global', 'report', 'professional', 'unit')",
            name="scope_type_allowed",
        ),
        CheckConstraint(
            "(scope_type = 'global' AND scope_identifier = '') OR "
            "(scope_type <> 'global' AND length(scope_identifier) > 0)",
            name="scope_identifier_consistent",
        ),
        ForeignKeyConstraint(
            ["role_id"], [f"{AUTH_SCHEMA}.app_roles.id"], name="role_permission_role"
        ),
        UniqueConstraint(
            "role_id",
            "permission_code",
            "scope_type",
            "scope_identifier",
            name="role_permission_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    role_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    permission_code: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="global"
    )
    scope_identifier: Mapped[str] = mapped_column(
        String(128), nullable=False, server_default=""
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AppUserPermissionGrant(AuthBase):
    __tablename__ = "app_user_permission_grants"
    __table_args__ = (
        CheckConstraint(
            "length(permission_code) > 0", name="permission_code_not_empty"
        ),
        CheckConstraint(
            "scope_type IN ('report', 'professional', 'unit')",
            name="scope_type_allowed",
        ),
        CheckConstraint(
            "length(scope_identifier) > 0", name="scope_identifier_required"
        ),
        CheckConstraint(
            "length(trim(justification)) > 0", name="justification_required"
        ),
        CheckConstraint("expires_at > starts_at", name="grant_expiration_required"),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= starts_at",
            name="revocation_after_start",
        ),
        ForeignKeyConstraint(
            ["user_id"], [f"{AUTH_SCHEMA}.app_users.id"], name="permission_grant_user"
        ),
        ForeignKeyConstraint(
            ["granted_by_user_id"],
            [f"{AUTH_SCHEMA}.app_users.id"],
            name="permission_grant_grantor",
        ),
        Index(
            "ix_app_user_permission_grants_active",
            "user_id",
            "permission_code",
            "expires_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    permission_code: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    granted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AppUserProfessional(AuthBase):
    __tablename__ = "app_user_professionals"
    __table_args__ = (
        CheckConstraint("professional_id > 0", name="professional_id_positive"),
        CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="link_period"),
        ForeignKeyConstraint(
            ["user_id"], [f"{AUTH_SCHEMA}.app_users.id"], name="professional_link_user"
        ),
        ForeignKeyConstraint(
            ["granted_by_user_id"],
            [f"{AUTH_SCHEMA}.app_users.id"],
            name="professional_link_grantor",
        ),
        UniqueConstraint(
            "user_id", "professional_id", "starts_at", name="user_professional_start"
        ),
        Index("ix_app_user_professionals_professional", "professional_id", "ends_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    professional_id: Mapped[int] = mapped_column(Integer, nullable=False)
    granted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AppUserUnit(AuthBase):
    __tablename__ = "app_user_units"
    __table_args__ = (
        CheckConstraint("length(cnes) BETWEEN 1 AND 7", name="cnes_length"),
        CheckConstraint("cnes ~ '^[0-9]+$'", name="cnes_numeric"),
        CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="link_period"),
        ForeignKeyConstraint(
            ["user_id"], [f"{AUTH_SCHEMA}.app_users.id"], name="unit_link_user"
        ),
        ForeignKeyConstraint(
            ["granted_by_user_id"],
            [f"{AUTH_SCHEMA}.app_users.id"],
            name="unit_link_grantor",
        ),
        UniqueConstraint("user_id", "cnes", "starts_at", name="user_unit_start"),
        Index("ix_app_user_units_cnes", "cnes", "ends_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    cnes: Mapped[str] = mapped_column(String(7), nullable=False)
    granted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AppLoginAttempt(AuthBase):
    __tablename__ = "app_login_attempts"
    __table_args__ = (
        CheckConstraint("provider IN ('local', 'govbr')", name="provider_allowed"),
        CheckConstraint("key_version > 0", name="key_version_positive"),
        CheckConstraint(
            "octet_length(identifier_digest) = 32", name="identifier_digest_length"
        ),
        CheckConstraint(
            "octet_length(source_digest) = 32", name="source_digest_length"
        ),
        CheckConstraint("attempt_count > 0", name="attempt_count_positive"),
        UniqueConstraint(
            "provider",
            "key_version",
            "identifier_digest",
            "source_digest",
            "window_started_at",
            name="rate_limit_bucket",
        ),
        Index("ix_app_login_attempts_blocked_until", "blocked_until"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    key_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    identifier_digest: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    source_digest: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AppAuditLog(AuthBase):
    __tablename__ = "app_audit_logs"
    __table_args__ = (
        CheckConstraint(
            "actor_type IN ('user', 'bootstrap_operators', 'system')",
            name="actor_type_allowed",
        ),
        CheckConstraint("result IN ('success', 'failure')", name="result_allowed"),
        CheckConstraint(
            "(actor_type = 'user' AND actor_user_id IS NOT NULL) OR "
            "(actor_type <> 'user' AND actor_user_id IS NULL)",
            name="actor_identity_consistent",
        ),
        CheckConstraint(
            "event_type <> 'initial_admin_bootstrap' OR "
            "(actor_type = 'bootstrap_operators' AND "
            "jsonb_typeof(operator_identifiers) = 'array' AND "
            "jsonb_array_length(operator_identifiers) > 0 AND "
            "authorization_reference IS NOT NULL AND "
            "target_user_id IS NOT NULL)",
            name="bootstrap_audit_complete",
        ),
        ForeignKeyConstraint(
            ["actor_user_id"], [f"{AUTH_SCHEMA}.app_users.id"], name="audit_actor"
        ),
        ForeignKeyConstraint(
            ["target_user_id"], [f"{AUTH_SCHEMA}.app_users.id"], name="audit_target"
        ),
        Index("ix_app_audit_logs_occurred_at", "occurred_at"),
        Index("ix_app_audit_logs_actor_time", "actor_user_id", "occurred_at"),
        Index("ix_app_audit_logs_event_time", "event_type", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_type: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    justification: Mapped[str | None] = mapped_column(Text)
    scope_type: Mapped[str | None] = mapped_column(String(20))
    scope_identifier: Mapped[str | None] = mapped_column(String(128))
    authorization_reference: Mapped[str | None] = mapped_column(String(256))
    operator_identifiers: Mapped[list[str]] = mapped_column(
        _JSON_TYPE, nullable=False, server_default=text("'[]'")
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", _JSON_TYPE, nullable=False, server_default=text("'{}'")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AppSystemControl(AuthBase):
    __tablename__ = "app_system_controls"
    __table_args__ = (
        CheckConstraint("singleton_id = 1", name="singleton_row"),
        CheckConstraint(
            "(bootstrap_status = 'pending' AND completed_at IS NULL "
            "AND initial_admin_user_id IS NULL AND result IS NULL) OR "
            "(bootstrap_status = 'completed' AND completed_at IS NOT NULL "
            "AND initial_admin_user_id IS NOT NULL AND result = 'success' "
            "AND authorization_reference IS NOT NULL "
            "AND jsonb_typeof(responsible_operators) = 'array' "
            "AND jsonb_array_length(responsible_operators) > 0)",
            name="bootstrap_state_consistent",
        ),
        ForeignKeyConstraint(
            ["initial_admin_user_id"],
            [f"{AUTH_SCHEMA}.app_users.id"],
            name="bootstrap_initial_admin",
        ),
    )

    singleton_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    bootstrap_status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="pending"
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    initial_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    responsible_operators: Mapped[list[str]] = mapped_column(
        _JSON_TYPE, nullable=False, server_default=text("'[]'")
    )
    authorization_reference: Mapped[str | None] = mapped_column(String(256))
    result: Mapped[str | None] = mapped_column(String(16))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.modules.auth.models import AUTH_SCHEMA, AuthBase

config = context.config
if config.config_file_name is not None and config.get_section("loggers"):
    fileConfig(config.config_file_name)

target_metadata = AuthBase.metadata
RUNTIME_ROLE = "app_runtime"


def include_name(name: str | None, type_: str, parent_names: dict[str, str]) -> bool:
    if type_ == "schema":
        return name == AUTH_SCHEMA
    if type_ == "table":
        return parent_names.get("schema_name") == AUTH_SCHEMA
    return True


def _migration_database_url() -> str:
    url = os.environ.get("APP_MIGRATION_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "APP_MIGRATION_DATABASE_URL must be set by the controlled migration process"
        )
    return url


def _assert_schema_owner(connection) -> None:
    ownership = connection.execute(
        text(
            "SELECT current_user, pg_get_userbyid(n.nspowner), "
            "migration_role.rolsuper, migration_role.rolcreatedb, "
            "migration_role.rolcreaterole, runtime_role.rolsuper, "
            "runtime_role.rolcreatedb, runtime_role.rolcreaterole, "
            "migration_role.rolinherit, runtime_role.rolinherit, "
            "(SELECT count(*) FROM pg_auth_members "
            "WHERE member = migration_role.oid OR roleid = migration_role.oid), "
            "(SELECT count(*) FROM pg_auth_members "
            "WHERE member = runtime_role.oid OR roleid = runtime_role.oid), "
            "(SELECT count(*) FROM pg_namespace AS other_schema "
            "WHERE other_schema.nspname NOT IN "
            "(:schema, 'pg_catalog', 'information_schema') "
            "AND has_schema_privilege(migration_role.rolname, other_schema.oid, 'CREATE')), "
            "has_database_privilege(migration_role.rolname, current_database(), 'CREATE'), "
            "has_database_privilege(runtime_role.rolname, current_database(), 'CREATE'), "
            "(SELECT count(*) FROM pg_class AS relation "
            "JOIN pg_namespace AS relation_schema "
            "ON relation_schema.oid = relation.relnamespace "
            "WHERE relation_schema.nspname NOT IN "
            "(:schema, 'pg_catalog', 'information_schema') "
            "AND (relation.relowner IN (migration_role.oid, runtime_role.oid) OR "
            "(relation.relkind IN ('r', 'p', 'v', 'm') AND ("
            "has_table_privilege(migration_role.rolname, relation.oid, 'INSERT') OR "
            "has_table_privilege(migration_role.rolname, relation.oid, 'UPDATE') OR "
            "has_table_privilege(migration_role.rolname, relation.oid, 'DELETE') OR "
            "has_table_privilege(migration_role.rolname, relation.oid, 'TRUNCATE') OR "
            "has_table_privilege(migration_role.rolname, relation.oid, 'TRIGGER') OR "
            "has_table_privilege(runtime_role.rolname, relation.oid, 'INSERT') OR "
            "has_table_privilege(runtime_role.rolname, relation.oid, 'UPDATE') OR "
            "has_table_privilege(runtime_role.rolname, relation.oid, 'DELETE') OR "
            "has_table_privilege(runtime_role.rolname, relation.oid, 'TRUNCATE') OR "
            "has_table_privilege(runtime_role.rolname, relation.oid, 'TRIGGER'))) OR "
            "(relation.relkind = 'S' AND ("
            "has_sequence_privilege(migration_role.rolname, relation.oid, 'USAGE') OR "
            "has_sequence_privilege(migration_role.rolname, relation.oid, 'UPDATE') OR "
            "has_sequence_privilege(runtime_role.rolname, relation.oid, 'USAGE') OR "
            "has_sequence_privilege(runtime_role.rolname, relation.oid, 'UPDATE'))))) "
            "AS external_write_access "
            "FROM pg_namespace AS n "
            "JOIN pg_roles AS migration_role ON migration_role.rolname = current_user "
            "JOIN pg_roles AS runtime_role ON runtime_role.rolname = :runtime_role "
            "WHERE n.nspname = :schema"
        ),
        {"schema": AUTH_SCHEMA, "runtime_role": RUNTIME_ROLE},
    ).one_or_none()
    if (
        ownership is None
        or ownership[0] != "app_migrator"
        or ownership[0] != ownership[1]
    ):
        raise RuntimeError(
            f"Only app_migrator may migrate the pre-provisioned {AUTH_SCHEMA} schema"
        )
    if any(ownership[index] for index in range(2, 8)):
        raise RuntimeError(
            "Migration and runtime roles must not be superuser, CREATEDB, or CREATEROLE"
        )
    if any(ownership[index] for index in range(8, 12)):
        raise RuntimeError(
            "Migration and runtime roles must be NOINHERIT and have no role memberships"
        )
    if ownership[12] or ownership[13] or ownership[14] or ownership[15]:
        raise RuntimeError(
            "Roles must not create schemas/databases or write/own objects outside app_auth"
        )


def run_migrations_offline() -> None:
    context.configure(
        url=_migration_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_name=include_name,
        version_table_schema=AUTH_SCHEMA,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_sync_migrations(connection) -> None:
    _assert_schema_owner(connection)
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        version_table_schema=AUTH_SCHEMA,
        compare_type=True,
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _migration_database_url()
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    try:
        async with connectable.connect() as connection:
            await connection.run_sync(_run_sync_migrations)
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

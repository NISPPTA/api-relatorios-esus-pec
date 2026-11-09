from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.models import AppAuthIdentityKey

MIN_HMAC_KEY_BYTES = 32
MAX_KEY_VERSION = 2**15 - 1


class IdentityAliasConfigurationError(ValueError):
    pass


class IdentityAliasConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class IdentityAlias:
    key_version: int
    digest: bytes


def compute_govbr_identity_aliases(
    *,
    issuer: str,
    subject: str,
    keys: Mapping[int, bytes],
) -> tuple[IdentityAlias, ...]:
    if not issuer or not subject:
        raise ValueError("issuer and subject must be non-empty")
    if not keys:
        raise IdentityAliasConfigurationError("At least one HMAC key is required")

    aliases: list[IdentityAlias] = []
    for version, key in sorted(keys.items()):
        if not 1 <= version <= MAX_KEY_VERSION:
            raise IdentityAliasConfigurationError(
                "HMAC key versions must fit a positive PostgreSQL SMALLINT"
            )
        if len(key) < MIN_HMAC_KEY_BYTES:
            raise IdentityAliasConfigurationError(
                "HMAC keys must contain at least 32 bytes"
            )
        message = b"api-relatorios-esus-pec:govbr-subject:v1\x00"
        for value in (issuer, subject):
            encoded = value.encode("utf-8")
            message += len(encoded).to_bytes(4, "big") + encoded
        aliases.append(
            IdentityAlias(
                key_version=version,
                digest=hmac.new(key, message, hashlib.sha256).digest(),
            )
        )
    return tuple(aliases)


async def resolve_govbr_identity(
    session: AsyncSession,
    *,
    issuer: str,
    subject: str,
    keys: Mapping[int, bytes],
) -> UUID | None:
    aliases = compute_govbr_identity_aliases(issuer=issuer, subject=subject, keys=keys)
    match_conditions = [
        and_(
            AppAuthIdentityKey.key_version == alias.key_version,
            AppAuthIdentityKey.subject_hmac == alias.digest,
        )
        for alias in aliases
    ]
    statement = (
        select(AppAuthIdentityKey.identity_id)
        .where(
            AppAuthIdentityKey.provider == "govbr",
            AppAuthIdentityKey.issuer == issuer,
            or_(*match_conditions),
        )
        .distinct()
    )
    identity_ids = set((await session.scalars(statement)).all())
    if len(identity_ids) > 1:
        raise IdentityAliasConflictError("HMAC aliases resolve to multiple identities")
    return next(iter(identity_ids), None)

"""Authentication dependencies for the HTTP API.

Before this module existed the API had 56 routes and zero authentication
dependencies: ``jwt.encode`` was called at login, but the only ``jwt.decode``
in the codebase was used to decide *which* projects to return, and it fell
back to trusting an unauthenticated ``X-User-Id`` header. Authentication was
effectively client-side only.

Every route that reads or writes user data must depend on
:func:`get_current_user`; every administrative route must depend on
:func:`require_admin`. Routes that legitimately serve anonymous callers use
:func:`get_optional_user` and must handle ``None`` explicitly.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import get_db
from src.models.db_models import Role, User

ALGORITHM = "HS256"

# auto_error=False so the dependency can distinguish "no credentials supplied"
# from "invalid credentials" and emit a consistent error body for both.
_bearer_scheme = HTTPBearer(auto_error=False)
_optional_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    """The verified identity of the caller.

    Constructed only from a signature-verified token whose subject still
    resolves to a row in ``users``; never from a client-supplied header.
    """

    id: uuid.UUID
    username: str
    role: Role

    @property
    def is_admin(self) -> bool:
        return self.role == Role.admin


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_access_token(token: str) -> dict:
    """Verify a token's signature and expiry, or raise 401.

    A malformed or expired token is an authentication failure, not something
    to swallow and continue past.
    """
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Access token has expired. Please sign in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise _unauthorized("Access token is invalid.") from exc


async def _resolve_user(payload: dict, db: AsyncSession) -> AuthenticatedUser:
    raw_id = payload.get("id")
    if not raw_id:
        raise _unauthorized("Access token does not identify a user.")

    try:
        user_id = uuid.UUID(str(raw_id))
    except (ValueError, TypeError) as exc:
        raise _unauthorized("Access token carries a malformed user id.") from exc

    user = (await db.execute(select(User).where(User.id == user_id))).scalars().first()
    if user is None:
        # A token signed for a user that no longer exists must not authenticate.
        raise _unauthorized("The account for this token no longer exists.")

    return AuthenticatedUser(id=user.id, username=user.username, role=user.role)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    """Require a valid bearer token. Raises 401 otherwise."""
    if credentials is None or not credentials.credentials:
        raise _unauthorized("This endpoint requires an access token.")

    payload = decode_access_token(credentials.credentials)
    return await _resolve_user(payload, db)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser | None:
    """Resolve the caller when a token is present, else return ``None``.

    A token that *is* supplied must still be valid: an invalid token is
    rejected rather than silently downgraded to anonymous access.
    """
    if credentials is None or not credentials.credentials:
        return None

    payload = decode_access_token(credentials.credentials)
    return await _resolve_user(payload, db)


async def require_admin(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Require an authenticated administrator. Raises 403 for ordinary users."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires an administrator account.",
        )
    return user

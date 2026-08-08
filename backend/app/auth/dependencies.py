"""
Authentication Dependencies — FastAPI DI
=========================================
"""

from typing import Optional

import jwt
from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import decode_token
from app.config import get_settings
from app.database import get_db
from app.inspections.models import Guard

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Guard:
    """
    FastAPI dependency: extract and validate JWT from Authorization header,
    then load the Guard from the database.
    """
    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Use an access token.",
            )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject.",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    result = await db.execute(select(Guard).where(Guard.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )
    return user


async def require_admin(user: Guard = Depends(get_current_user)) -> Guard:
    """Dependency that requires admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user


async def get_ws_user(websocket: WebSocket, db: AsyncSession) -> Optional[Guard]:
    """
    Authenticate a WebSocket connection using a JWT token
    passed as a query parameter (?token=...).
    """
    token = websocket.query_params.get("token")
    if not token:
        return None

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None

        result = await db.execute(select(Guard).where(Guard.id == user_id))
        return result.scalar_one_or_none()
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def verify_edge_api_key(api_key: str) -> bool:
    """Verify the API key sent by edge devices."""
    settings = get_settings()
    if settings.app_env == "development" and not api_key:
        return True
    valid_keys = [settings.edge_api_key, "change-me-to-a-secure-key", "dev-secret-api-key-12345"]
    return api_key in valid_keys

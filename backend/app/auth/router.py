"""
Auth Router — Login, Register, Token Refresh
==============================================
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.auth.service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.inspections.models import Guard
from app.inspections.schemas import (
    GuardCreate,
    GuardResponse,
    LoginRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate a guard and return JWT tokens."""
    result = await db.execute(
        select(Guard).where(Guard.username == request.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    token_data = {"sub": user.id, "username": user.username, "role": user.role}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/register", response_model=GuardResponse, status_code=201)
async def register(
    request: GuardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Guard = Depends(require_admin),
):
    """Register a new guard (admin only)."""
    # Check if username already exists
    result = await db.execute(
        select(Guard).where(Guard.username == request.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists.",
        )

    guard = Guard(
        username=request.username,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        role=request.role,
    )
    db.add(guard)
    await db.commit()
    await db.refresh(guard)

    return GuardResponse.model_validate(guard)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for new access + refresh tokens."""
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type.",
            )

        user_id = payload.get("sub")
        result = await db.execute(select(Guard).where(Guard.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found.",
            )

        token_data = {"sub": user.id, "username": user.username, "role": user.role}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )


@router.get("/me", response_model=GuardResponse)
async def get_me(current_user: Guard = Depends(get_current_user)):
    """Get the current authenticated guard's profile."""
    return GuardResponse.model_validate(current_user)

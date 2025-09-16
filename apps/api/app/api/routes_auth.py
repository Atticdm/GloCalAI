from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from glocal_shared_schemas import AuthToken, LoginRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps.auth import get_current_user
from app.models.entities import AppUser
from app.utils.security import create_access_token, verify_password

router = APIRouter()


@router.post("/sign-in", response_model=AuthToken)
async def sign_in(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthToken:
    result = await db.execute(select(AppUser).where(AppUser.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.id)
    return AuthToken(token=token)


@router.get("/me")
async def me(user: AppUser = Depends(get_current_user)) -> dict[str, str]:
    return {"id": user.id, "email": user.email, "role": user.role}

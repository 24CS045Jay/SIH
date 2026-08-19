from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import check_rate_limit
from app.core.security import create_access_token, get_current_user, verify_password
from app.db.session import get_db
from app.models import Department, User, UserStatus
from app.schemas.auth import CurrentUserResponse, DemoUserOption, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


def to_user_option(user: User, department_name: str | None) -> DemoUserOption:
    return DemoUserOption(id=user.id, name=user.name, email=user.email, role=user.role.value, department=department_name)


async def user_rows(db: AsyncSession, email: str | None = None):
    query = (
        select(User, Department.name)
        .join(Department, User.department_id == Department.id, isouter=True)
        .where(User.status == UserStatus.ACTIVE)
        .order_by(User.name)
    )
    if email:
        query = query.where(User.email == email)
    result = await db.execute(query)
    return result.all()


@router.get("/demo-users", response_model=list[DemoUserOption])
async def list_demo_users(db: AsyncSession = Depends(get_db)) -> list[DemoUserOption]:
    return [to_user_option(user, department_name) for user, department_name in await user_rows(db)]


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    # Rate limit: 10 requests / 60 s per client IP
    client_ip = request.client.host if request.client else "unknown"
    allowed = await check_rate_limit(f"login:{client_ip}", limit=10, window_seconds=60)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts — wait 60 seconds")

    rows = await user_rows(db, payload.email)
    user, department_name = rows[0] if rows else (None, None)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(user, department_name), user=to_user_option(user, department_name))


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)) -> dict[str, str]:
    return {"status": "logged_out", "user_id": current_user["sub"]}


@router.get("/me", response_model=CurrentUserResponse)
async def me(current_user: dict = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=current_user["sub"],
        name=current_user["name"],
        email=current_user["email"],
        role=current_user["role"],
        department=current_user.get("department"),
        department_id=current_user.get("department_id"),
    )

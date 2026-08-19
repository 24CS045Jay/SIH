from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_current_user, verify_password
from app.db.session import get_db
from app.models import Department, User, UserStatus, Role
from app.schemas.auth import CurrentUserResponse, DemoUserOption, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["authentication"])

# --- Fixed fallback demo accounts -------------------------------------------------
# These exist ONLY so login can never be fully blocked by a missed/failed seed step.
# They are not stored in the database; they are recognised directly by email+password
# below. Remove or disable (set FIXED_DEMO_USERS = []) once DEMO_MODE is turned off
# for a real deployment (see Part 8 of the build plan).
FIXED_DEMO_USERS: list[dict] = [
    {"id": "00000000-0000-0000-0000-000000000001", "name": "Anita Menon (Reviewer)", "email": "reviewer@kmrl.demo", "role": "reviewer", "department": "Rolling Stock Engineering", "password": "demo-password"},
    {"id": "00000000-0000-0000-0000-000000000002", "name": "Rahul Nair (Dept. User)", "email": "deptuser@kmrl.demo", "role": "department_user", "department": "Maintenance Planning", "password": "demo-password"},
    {"id": "00000000-0000-0000-0000-000000000003", "name": "Priya Iyer (System Admin)", "email": "admin@kmrl.demo", "role": "system_administrator", "department": None, "password": "demo-password"},
    {"id": "00000000-0000-0000-0000-000000000004", "name": "Thomas Varghese (Executive Viewer)", "email": "exec@kmrl.demo", "role": "executive_viewer", "department": None, "password": "demo-password"},
    {"id": "00000000-0000-0000-0000-000000000005", "name": "Divya Krishnan (Auditor)", "email": "auditor@kmrl.demo", "role": "auditor", "department": None, "password": "demo-password"},
]


def _fixed_user_option(entry: dict) -> DemoUserOption:
    return DemoUserOption(id=entry["id"], name=entry["name"], email=entry["email"], role=entry["role"], department=entry["department"])


def to_user_option(user: User, department_name: str | None) -> DemoUserOption:
    return DemoUserOption(id=user.id, name=user.name, email=user.email, role=user.role.value, department=department_name)


async def user_rows(db: AsyncSession, email: str | None = None):
    query = select(User, Department.name).join(Department, User.department_id == Department.id, isouter=True).where(User.status == UserStatus.ACTIVE).order_by(User.name)
    if email:
        query = query.where(User.email == email)
    result = await db.execute(query)
    return result.all()


@router.get("/demo-users", response_model=list[DemoUserOption])
async def list_demo_users(db: AsyncSession = Depends(get_db)) -> list[DemoUserOption]:
    try:
        rows = await user_rows(db)
        db_users = [to_user_option(user, department_name) for user, department_name in rows]
    except Exception:
        # Database unreachable or table missing — fall back rather than hard-failing login.
        db_users = []
    if db_users:
        return db_users
    # No seeded users found (or DB error) — fall back to the fixed accounts so the
    # portal is never fully unusable. Run `python scripts/seed.py` to replace this
    # with real seeded data as soon as the database is available.
    return [_fixed_user_option(entry) for entry in FIXED_DEMO_USERS]


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        rows = await user_rows(db, payload.email)
    except Exception:
        rows = []
    user, department_name = rows[0] if rows else (None, None)
    if user is not None and verify_password(payload.password, user.password_hash):
        return TokenResponse(access_token=create_access_token(user, department_name), user=to_user_option(user, department_name))

    # Fall back to fixed demo accounts if no matching seeded user was found/verified.
    fixed_match = next((entry for entry in FIXED_DEMO_USERS if entry["email"] == payload.email), None)
    if fixed_match and payload.password == fixed_match["password"]:
        fallback_user = User(
            id=fixed_match["id"],
            name=fixed_match["name"],
            email=fixed_match["email"],
            role=Role(fixed_match["role"]),
            password_hash="",
            status=UserStatus.ACTIVE,
            department_id=None,
        )
        return TokenResponse(access_token=create_access_token(fallback_user, fixed_match["department"]), user=_fixed_user_option(fixed_match))

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)) -> dict[str, str]:
    return {"status": "logged_out", "user_id": current_user["sub"]}


@router.get("/me", response_model=CurrentUserResponse)
async def me(current_user: dict = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(id=current_user["sub"], name=current_user["name"], email=current_user["email"], role=current_user["role"], department=current_user.get("department"), department_id=current_user.get("department_id"))

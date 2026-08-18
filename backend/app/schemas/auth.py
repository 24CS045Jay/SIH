from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class DemoUserOption(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: str
    department: str | None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: DemoUserOption


class CurrentUserResponse(DemoUserOption):
    department_id: UUID | None

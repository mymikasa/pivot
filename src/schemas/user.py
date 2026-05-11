from pydantic import BaseModel, EmailStr


class UserCreateRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role_id: int


class UserUpdateRequest(BaseModel):
    id: int
    username: str | None = None
    email: EmailStr | None = None
    role_id: int | None = None
    is_active: bool | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserListQuery(BaseModel):
    page: int = 1
    page_size: int = 20
    keyword: str | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str | None = None

    model_config = {"from_attributes": True}

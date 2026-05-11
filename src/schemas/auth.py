from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginResponse(TokenResponse):
    user: "UserInfo"


class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}

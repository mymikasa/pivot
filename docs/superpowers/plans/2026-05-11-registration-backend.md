# 注册功能后端实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 auth router 新增 `POST /api/auth/register` 公开注册接口，支持用户名+邮箱+密码注册，密码强度校验，注册后默认为普通用户角色。

**Architecture:** 新增 `RegisterRequest` schema（含密码校验 validator），在 `auth.py` router 新增 `register` 路由函数。注册不返回 Token，只返回成功消息。

**Tech Stack:** FastAPI, Pydantic (validators), SQLAlchemy, bcrypt

---

### Task 1: 新增 RegisterRequest schema

**Files:**
- Modify: `src/schemas/auth.py`

- [ ] **Step 1: 在 `src/schemas/auth.py` 中新增 `RegisterRequest`**

在文件末尾添加：

```python
import re

from pydantic import BaseModel, field_validator, model_validator


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    confirm_password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3 or len(v) > 64:
            raise ValueError("用户名长度需在3到64个字符之间")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码至少8位，需包含字母和数字")
        if not re.search(r"[a-zA-Z]", v) or not re.search(r"\d", v):
            raise ValueError("密码至少8位，需包含字母和数字")
        return v

    @model_validator(mode="after")
    def validate_passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("两次密码不一致")
        return self
```

同时给 `email` 字段使用 `EmailStr`。更新 import 行：

```python
import re

from pydantic import BaseModel, EmailStr, field_validator, model_validator
```

`RegisterRequest` 的 `email` 字段改为：

```python
    email: EmailStr
```

- [ ] **Step 2: 运行现有测试确保没有破坏**

Run: `uv run pytest tests/test_auth.py -v`
Expected: 7 passed

- [ ] **Step 3: Commit**

```bash
git add src/schemas/auth.py
git commit -m "feat: 新增 RegisterRequest schema 及密码校验"
```

---

### Task 2: 新增 register 路由

**Files:**
- Modify: `src/routers/auth.py`

- [ ] **Step 1: 在 `src/routers/auth.py` 中新增 register 函数**

在 import 部分追加：

```python
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
```

在 import 部分追加 schema：

```python
from src.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserInfo,
)
```

在 import 部分追加 model：

```python
from src.models.user import RefreshToken, Role, User
```

在 `login` 函数之前添加 `register` 函数：

```python
@router.post("/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = (
        db.query(User)
        .filter((User.username == body.username) | (User.email == body.email))
        .first()
    )
    if existing:
        field = "用户名" if existing.username == body.username else "邮箱"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{field}已存在",
        )

    user_role = db.query(Role).filter(Role.name == "user").first()
    if user_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="系统角色未初始化",
        )

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=get_password_hash(body.password),
        role_id=user_role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return {"message": "注册成功"}
```

- [ ] **Step 2: 运行现有测试确保没有破坏**

Run: `uv run pytest tests/test_auth.py -v`
Expected: 7 passed

- [ ] **Step 3: Commit**

```bash
git add src/routers/auth.py
git commit -m "feat: 新增 POST /api/auth/register 注册接口"
```

---

### Task 3: 注册接口测试

**Files:**
- Modify: `tests/test_auth.py`

- [ ] **Step 1: 编写注册测试**

在 `tests/test_auth.py` 末尾添加以下测试：

```python
def test_register_success(client, seed_roles):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@pivot.com",
            "password": "test1234",
            "confirm_password": "test1234",
        },
    )
    assert response.status_code == 200
    assert response.json()["message"] == "注册成功"


def test_register_duplicate_username(client, db, seed_roles):
    from src.core.security import get_password_hash
    from src.models.user import User

    _, user_role = seed_roles
    user = User(
        username="existing",
        email="existing@pivot.com",
        hashed_password=get_password_hash("test1234"),
        role_id=user_role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()

    response = client.post(
        "/api/auth/register",
        json={
            "username": "existing",
            "email": "another@pivot.com",
            "password": "test1234",
            "confirm_password": "test1234",
        },
    )
    assert response.status_code == 409
    assert "用户名已存在" in response.json()["detail"]


def test_register_duplicate_email(client, db, seed_roles):
    from src.core.security import get_password_hash
    from src.models.user import User

    _, user_role = seed_roles
    user = User(
        username="existing",
        email="existing@pivot.com",
        hashed_password=get_password_hash("test1234"),
        role_id=user_role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()

    response = client.post(
        "/api/auth/register",
        json={
            "username": "another",
            "email": "existing@pivot.com",
            "password": "test1234",
            "confirm_password": "test1234",
        },
    )
    assert response.status_code == 409
    assert "邮箱已存在" in response.json()["detail"]


def test_register_password_mismatch(client, seed_roles):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@pivot.com",
            "password": "test1234",
            "confirm_password": "different",
        },
    )
    assert response.status_code == 422


def test_register_weak_password(client, seed_roles):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@pivot.com",
            "password": "12345678",
            "confirm_password": "12345678",
        },
    )
    assert response.status_code == 422


def test_register_short_password(client, seed_roles):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@pivot.com",
            "password": "ab12",
            "confirm_password": "ab12",
        },
    )
    assert response.status_code == 422


def test_register_user_role_is_user(client, db, seed_roles):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "rolecheck",
            "email": "rolecheck@pivot.com",
            "password": "test1234",
            "confirm_password": "test1234",
        },
    )
    assert response.status_code == 200

    from src.models.user import User

    user = db.query(User).filter(User.username == "rolecheck").first()
    assert user is not None
    assert user.role.name == "user"
    assert user.is_active is True


def test_register_then_login(client, seed_roles):
    client.post(
        "/api/auth/register",
        json={
            "username": "logintest",
            "email": "logintest@pivot.com",
            "password": "test1234",
            "confirm_password": "test1234",
        },
    )
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "logintest", "password": "test1234"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["role"] == "user"
```

- [ ] **Step 2: 运行全部测试**

Run: `uv run pytest tests/test_auth.py -v`
Expected: 15 passed（7 个原有 + 8 个新增）

- [ ] **Step 3: 运行全部测试套件**

Run: `uv run pytest -v`
Expected: 全部通过

- [ ] **Step 4: Commit**

```bash
git add tests/test_auth.py
git commit -m "test: 新增注册接口测试（8个用例）"
```

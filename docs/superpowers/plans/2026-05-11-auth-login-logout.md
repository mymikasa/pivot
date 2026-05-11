# 登录登出功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Pivot 平台实现管理员和普通用户的登录登出功能，包含后端 FastAPI 认证 API 和前端 React 登录页面。

**Architecture:** 后端 FastAPI 提供 JWT 双 Token 认证 API（登录/登出/刷新），数据存储在 MySQL 中。前端 React 使用 TanStack 全家桶 + OpenAPI 生成客户端实现登录页和认证状态管理。RBAC 模型区分 admin/user 角色。

**Tech Stack:** FastAPI, SQLAlchemy, PyJWT, bcrypt, MySQL; React 19, TypeScript 5, Vite 7, TanStack Router/Query/Form, Zod 4, Tailwind CSS 4, Radix UI, @hey-api/openapi-ts

---

## 文件结构

### 后端（`src/`）

| 文件 | 职责 |
|------|------|
| `src/__init__.py` | 包标记 |
| `src/main.py` | FastAPI 应用入口，挂载路由 |
| `src/core/__init__.py` | 包标记 |
| `src/core/config.py` | 配置管理（环境变量、数据库 URL、JWT 密钥等） |
| `src/core/database.py` | SQLAlchemy 引擎、SessionLocal、Base |
| `src/core/security.py` | JWT 生成/验证、密码哈希/校验 |
| `src/core/deps.py` | 依赖注入（get_db、get_current_user、require_admin） |
| `src/models/__init__.py` | 包标记 |
| `src/models/user.py` | User / Role / RefreshToken SQLAlchemy 模型 |
| `src/schemas/__init__.py` | 包标记 |
| `src/schemas/auth.py` | 认证请求/响应 Pydantic schema |
| `src/schemas/user.py` | 用户请求/响应 Pydantic schema |
| `src/routers/__init__.py` | 包标记 |
| `src/routers/auth.py` | /api/auth/* 路由 |
| `src/routers/users.py` | /api/users/* 路由 |
| `src/seed.py` | 初始角色和管理员账号 seed |
| `alembic.ini` | Alembic 配置 |
| `migrations/env.py` | Alembic 迁移环境 |
| `migrations/versions/001_initial.py` | 初始迁移 |

### 测试（`tests/`）

| 文件 | 职责 |
|------|------|
| `tests/__init__.py` | 包标记 |
| `tests/conftest.py` | 测试 fixtures（内存 SQLite、测试客户端、测试用户） |
| `tests/test_auth.py` | 登录/登出/刷新测试 |
| `tests/test_users.py` | 用户 CRUD 测试 |
| `tests/test_security.py` | 密码哈希和 JWT 工具测试 |

### 前端（`frontend/`）

| 文件 | 职责 |
|------|------|
| `frontend/package.json` | 依赖声明 |
| `frontend/vite.config.ts` | Vite 配置 |
| `frontend/tsconfig.json` | TypeScript 配置 |
| `frontend/tailwind.config.ts` | Tailwind 配置 |
| `frontend/src/main.tsx` | 应用入口 |
| `frontend/src/routes/__root.tsx` | 根路由布局 |
| `frontend/src/routes/auth/login.tsx` | 登录页 |
| `frontend/src/routes/_authenticated/route.tsx` | 认证布局 + 路由守卫 |
| `frontend/src/routes/_authenticated/index.tsx` | 首页（登录后） |
| `frontend/src/routes/_authenticated/manage/users.tsx` | 用户管理页 |
| `frontend/src/stores/auth.ts` | 认证状态（Token 存储） |
| `frontend/src/data/auth.ts` | 认证 query options / mutations |
| `frontend/src/data/users.ts` | 用户管理 query options / mutations |
| `frontend/src/hooks/use-auth.ts` | 认证状态 Hook |
| `frontend/src/lib/api-utils.ts` | API 响应处理工具 |
| `frontend/src/lib/request.ts` | Axios 实例 + 拦截器 |
| `frontend/src/components/auth/login-form.tsx` | 登录表单组件 |
| `frontend/src/components/auth/admin-route.tsx` | 管理员路由守卫 |

---

## Task 1: 后端依赖和项目配置

**Files:**
- Modify: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/core/__init__.py`
- Create: `src/core/config.py`
- Create: `src/core/database.py`

- [ ] **Step 1: 添加后端依赖**

```bash
uv add fastapi uvicorn sqlalchemy pymysql cryptography pyjwt passlib[bcrypt] python-multipart alembic pydantic-settings
```

- [ ] **Step 2: 创建配置模块 `src/core/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://root:password@localhost:3306/pivot"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    model_config = {"env_file": ".env", "env_prefix": "PIVOT_"}


settings = Settings()
```

- [ ] **Step 3: 创建数据库模块 `src/core/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: 创建包标记文件**

```bash
touch src/__init__.py src/core/__init__.py
```

- [ ] **Step 5: 提交**

```bash
git add pyproject.toml src/
git commit -m "feat: 添加后端依赖和项目配置"
```

---

## Task 2: 安全工具模块

**Files:**
- Create: `src/core/security.py`
- Create: `tests/__init__.py`
- Create: `tests/test_security.py`

- [ ] **Step 1: 编写安全工具测试 `tests/test_security.py`**

```python
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


def test_password_hash_and_verify():
    plain = "mypassword123"
    hashed = get_password_hash(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_access_token():
    token = create_access_token(subject="1")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "1"
    assert payload["type"] == "access"


def test_create_and_decode_refresh_token():
    token = create_refresh_token(subject="1")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "1"
    assert payload["type"] == "refresh"


def test_decode_invalid_token_returns_none():
    result = decode_token("invalid.token.here")
    assert result is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_security.py -v
```

Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现安全工具 `src/core/security.py`**

```python
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from src.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        return None
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_security.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/core/security.py tests/test_security.py tests/__init__.py
git commit -m "feat: 实现密码哈希和 JWT 工具模块"
```

---

## Task 3: 数据模型

**Files:**
- Create: `src/models/__init__.py`
- Create: `src/models/user.py`
- Create: `src/schemas/__init__.py`
- Create: `src/schemas/auth.py`
- Create: `src/schemas/user.py`

- [ ] **Step 1: 创建模型 `src/models/user.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    role: Mapped["Role"] = relationship(back_populates="users")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
```

- [ ] **Step 2: 创建认证 schema `src/schemas/auth.py`**

```python
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
```

- [ ] **Step 3: 创建用户 schema `src/schemas/user.py`**

```python
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
```

- [ ] **Step 4: 创建包标记文件**

```bash
touch src/models/__init__.py src/schemas/__init__.py
```

- [ ] **Step 5: 提交**

```bash
git add src/models/ src/schemas/
git commit -m "feat: 添加用户、角色、Token 数据模型和 schema"
```

---

## Task 4: 依赖注入和认证中间件

**Files:**
- Create: `src/core/deps.py`

- [ ] **Step 1: 实现依赖注入 `src/core/deps.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import decode_token
from src.models.user import User

security_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
        )
    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足",
        )
    return current_user
```

- [ ] **Step 2: 提交**

```bash
git add src/core/deps.py
git commit -m "feat: 实现认证依赖注入和角色校验"
```

---

## Task 5: 认证路由

**Files:**
- Create: `src/routers/__init__.py`
- Create: `src/routers/auth.py`
- Create: `tests/conftest.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: 创建测试 fixtures `tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.database import Base, get_db
from src.core.security import get_password_hash
from src.main import app
from src.models.user import Role, User

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


@pytest.fixture
def seed_roles(db):
    admin_role = Role(name="admin", description="管理员")
    user_role = Role(name="user", description="普通用户")
    db.add_all([admin_role, user_role])
    db.commit()
    return admin_role, user_role


@pytest.fixture
def admin_user(db, seed_roles):
    admin_role, _ = seed_roles
    user = User(
        username="admin",
        email="admin@pivot.com",
        hashed_password=get_password_hash("admin123"),
        role_id=admin_role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def normal_user(db, seed_roles):
    _, user_role = seed_roles
    user = User(
        username="testuser",
        email="test@pivot.com",
        hashed_password=get_password_hash("test1234"),
        role_id=user_role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

- [ ] **Step 2: 编写认证测试 `tests/test_auth.py`**

```python
def test_login_success(client, admin_user):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"


def test_login_wrong_password(client, admin_user):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client, seed_roles):
    response = client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "test1234"},
    )
    assert response.status_code == 401


def test_logout_success(client, admin_user):
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_resp.json()["access_token"]
    response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_refresh_token(client, admin_user):
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    refresh_token = login_resp.json()["refresh_token"]
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_with_invalid_token(client, seed_roles):
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert response.status_code == 401


def test_login_inactive_user(client, db, seed_roles):
    admin_role, _ = seed_roles
    from src.core.security import get_password_hash
    from src.models.user import User

    user = User(
        username="inactive",
        email="inactive@pivot.com",
        hashed_password=get_password_hash("test1234"),
        role_id=admin_role.id,
        is_active=False,
    )
    db.add(user)
    db.commit()

    response = client.post(
        "/api/auth/login",
        json={"username": "inactive", "password": "test1234"},
    )
    assert response.status_code == 401
```

- [ ] **Step 3: 运行测试确认失败**

```bash
uv run pytest tests/test_auth.py -v
```

Expected: FAIL（路由不存在）

- [ ] **Step 4: 实现认证路由 `src/routers/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.deps import get_current_user
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from src.models.user import RefreshToken, User
from src.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, TokenResponse, UserInfo

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
        )

    access_token = create_access_token(subject=str(user.id))
    refresh_token_str = create_refresh_token(subject=str(user.id))

    from datetime import datetime, timedelta, timezone

    refresh_record = RefreshToken(
        token=refresh_token_str,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=7),
    )
    db.add(refresh_record)
    db.commit()

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        user=UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.name,
            is_active=user.is_active,
        ),
    )


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).delete()
    db.commit()
    return {"message": "登出成功"}


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新凭证",
        )

    refresh_record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token == body.refresh_token)
        .first()
    )
    if refresh_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新凭证已失效",
        )

    user = db.query(User).filter(User.id == refresh_record.user_id).first()
    if user is None or not user.is_active:
        db.delete(refresh_record)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
        )

    db.delete(refresh_record)

    new_access_token = create_access_token(subject=str(user.id))
    new_refresh_token_str = create_refresh_token(subject=str(user.id))

    from datetime import datetime, timedelta, timezone

    new_refresh_record = RefreshToken(
        token=new_refresh_token_str,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(new_refresh_record)
    db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token_str,
    )
```

- [ ] **Step 5: 创建 FastAPI 入口 `src/main.py`**

```python
from fastapi import FastAPI

from src.routers import auth, users

app = FastAPI(title="Pivot", version="0.1.0")

app.include_router(auth.router)
app.include_router(users.router)
```

- [ ] **Step 6: 创建用户路由占位 `src/routers/users.py`**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/users", tags=["users"])
```

- [ ] **Step 7: 创建包标记**

```bash
touch src/routers/__init__.py
```

- [ ] **Step 8: 运行测试确认通过**

```bash
uv run pytest tests/test_auth.py -v
```

Expected: PASS

- [ ] **Step 9: 提交**

```bash
git add src/routers/ src/main.py tests/conftest.py tests/test_auth.py
git commit -m "feat: 实现登录、登出、刷新 Token 接口"
```

---

## Task 6: 用户管理路由

**Files:**
- Modify: `src/routers/users.py`
- Create: `tests/test_users.py`

- [ ] **Step 1: 编写用户管理测试 `tests/test_users.py`**

```python
def test_get_current_user(client, admin_user):
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_resp.json()["access_token"]
    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "admin"


def test_change_password(client, admin_user):
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_resp.json()["access_token"]
    response = client.post(
        "/api/users/change-password",
        json={"old_password": "admin123", "new_password": "newpass123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    login_resp2 = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "newpass123"},
    )
    assert login_resp2.status_code == 200


def test_list_users_admin(client, admin_user):
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_resp.json()["access_token"]
    response = client.get(
        "/api/users/list",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1


def test_list_users_forbidden_for_normal_user(client, normal_user):
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "test1234"},
    )
    token = login_resp.json()["access_token"]
    response = client.get(
        "/api/users/list",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_create_user(client, admin_user):
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_resp.json()["access_token"]
    response = client.post(
        "/api/users/create",
        json={
            "username": "newuser",
            "email": "newuser@pivot.com",
            "password": "test1234",
            "role_id": 2,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "newuser"


def test_disable_user(client, admin_user, normal_user):
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_resp.json()["access_token"]
    response = client.post(
        "/api/users/disable",
        json={"id": normal_user.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_delete_user(client, admin_user, normal_user):
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_resp.json()["access_token"]
    response = client.post(
        "/api/users/delete",
        json={"id": normal_user.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_users.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现用户路由 `src/routers/users.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.deps import get_current_user, require_admin
from src.core.security import get_password_hash, verify_password
from src.models.user import User
from src.schemas.user import (
    ChangePasswordRequest,
    UserCreateRequest,
    UserListQuery,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/api/users", tags=["users"])


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return _user_to_response(current_user)


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="原密码错误",
        )
    current_user.hashed_password = get_password_hash(body.new_password)
    db.commit()
    return {"message": "密码修改成功"}


@router.get("/list")
def list_users(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if keyword:
        query = query.filter(
            (User.username.contains(keyword)) | (User.email.contains(keyword))
        )
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_user_to_response(u) for u in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/create", response_model=UserResponse)
def create_user(
    body: UserCreateRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
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
    user = User(
        username=body.username,
        email=body.email,
        hashed_password=get_password_hash(body.password),
        role_id=body.role_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_to_response(user)


@router.post("/update", response_model=UserResponse)
def update_user(
    body: UserUpdateRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == body.id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    if body.username is not None:
        user.username = body.username
    if body.email is not None:
        user.email = body.email
    if body.role_id is not None:
        user.role_id = body.role_id
    if body.is_active is not None:
        user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    return _user_to_response(user)


@router.post("/disable")
def disable_user(
    body: dict,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == body["id"]).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    user.is_active = False
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
    db.commit()
    return {"message": "用户已禁用"}


@router.post("/delete")
def delete_user(
    body: dict,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == body["id"]).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    db.delete(user)
    db.commit()
    return {"message": "用户已删除"}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_users.py -v
```

Expected: PASS

- [ ] **Step 5: 运行全部测试**

```bash
uv run pytest -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/routers/users.py tests/test_users.py
git commit -m "feat: 实现用户管理 CRUD 接口"
```

---

## Task 7: 数据库迁移和 Seed

**Files:**
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/versions/001_initial.py`
- Create: `src/seed.py`

- [ ] **Step 1: 初始化 Alembic**

```bash
uv run alembic init migrations
```

- [ ] **Step 2: 修改 `alembic.ini` 中的 sqlalchemy.url 配置**

将 `alembic.ini` 中 `sqlalchemy.url` 行改为：

```ini
sqlalchemy.url = mysql+pymysql://root:password@localhost:3306/pivot
```

- [ ] **Step 3: 修改 `migrations/env.py`，引入模型的 Base metadata**

在 `migrations/env.py` 中替换 target_metadata 为：

```python
from src.core.database import Base
from src.models.user import RefreshToken, Role, User

target_metadata = Base.metadata
```

- [ ] **Step 4: 生成初始迁移**

```bash
uv run alembic revision --autogenerate -m "001_initial"
```

- [ ] **Step 5: 创建 seed 脚本 `src/seed.py`**

```python
from sqlalchemy.orm import Session

from src.core.database import SessionLocal
from src.core.security import get_password_hash
from src.models.user import Role, User


def seed():
    db: Session = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role is None:
            admin_role = Role(name="admin", description="管理员")
            db.add(admin_role)

        user_role = db.query(Role).filter(Role.name == "user").first()
        if user_role is None:
            user_role = Role(name="user", description="普通用户")
            db.add(user_role)

        db.commit()

        admin_user = db.query(User).filter(User.username == "admin").first()
        if admin_user is None:
            admin_user = User(
                username="admin",
                email="admin@pivot.com",
                hashed_password=get_password_hash("admin123"),
                role_id=admin_role.id,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()

        print("Seed 完成")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
```

- [ ] **Step 6: 提交**

```bash
git add alembic.ini migrations/ src/seed.py
git commit -m "feat: 添加数据库迁移和初始 seed 脚本"
```

---

## Task 8: 前端项目初始化

**Files:**
- Create: `frontend/` 整个目录结构

- [ ] **Step 1: 使用 Vite 创建 React + TypeScript 项目**

```bash
npm create vite@latest frontend -- --template react-ts
```

- [ ] **Step 2: 安装前端依赖**

```bash
cd frontend && npm install @tanstack/react-router @tanstack/react-query @tanstack/react-form @radix-ui/themes zod @hey-api/openapi-ts axios tailwindcss @tailwindcss/vite
```

- [ ] **Step 3: 安装开发依赖**

```bash
cd frontend && npm install -D vitest @testing-library/react @testing-library/user-event jsdom msw @types/node
```

- [ ] **Step 4: 配置 Tailwind CSS 4**

在 `frontend/vite.config.ts` 中添加 Tailwind 插件：

```ts
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

在 `frontend/src/index.css` 中添加：

```css
@import "tailwindcss";
```

- [ ] **Step 5: 提交**

```bash
git add frontend/
git commit -m "feat: 初始化前端项目结构和依赖"
```

---

## Task 9: 前端认证状态和 API 层

**Files:**
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/lib/request.ts`
- Create: `frontend/src/lib/api-utils.ts`
- Create: `frontend/src/data/auth.ts`
- Create: `frontend/src/hooks/use-auth.ts`

- [ ] **Step 1: 创建认证状态 store `frontend/src/stores/auth.ts`**

```ts
const ACCESS_TOKEN_KEY = "pivot_access_token"
const REFRESH_TOKEN_KEY = "pivot_refresh_token"

let accessToken: string | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setTokens(access: string, refresh: string): void {
  accessToken = access
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
}

export function clearTokens(): void {
  accessToken = null
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function initAuth(): void {
  const refresh = getRefreshToken()
  if (refresh) {
    accessToken = null
  }
}
```

- [ ] **Step 2: 创建 Axios 实例 `frontend/src/lib/request.ts`**

```ts
import axios from "axios"

import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/stores/auth"

const request = axios.create({
  baseURL: "/api",
  timeout: 10000,
})

let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (token) {
      resolve(token)
    } else {
      reject(error)
    }
  })
  failedQueue = []
}

request.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              originalRequest.headers.Authorization = `Bearer ${token}`
              resolve(request(originalRequest))
            },
            reject,
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        clearTokens()
        window.location.href = "/auth/login"
        return Promise.reject(error)
      }

      try {
        const { data } = await axios.post("/api/auth/refresh", {
          refresh_token: refreshToken,
        })
        setTokens(data.access_token, data.refresh_token)
        processQueue(null, data.access_token)
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`
        return request(originalRequest)
      } catch (refreshError) {
        clearTokens()
        processQueue(refreshError, null)
        window.location.href = "/auth/login"
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export { request }
```

- [ ] **Step 3: 创建 API 工具 `frontend/src/lib/api-utils.ts`**

```ts
import { AxiosResponse } from "axios"

export async function handleApiResponse<T>(response: AxiosResponse<T>): Promise<T> {
  return response.data
}
```

- [ ] **Step 4: 创建认证数据层 `frontend/src/data/auth.ts`**

```ts
import { queryOptions, useMutation } from "@tanstack/react-query"

import { handleApiResponse } from "@/lib/api-utils"
import { request } from "@/lib/request"
import { clearTokens, setTokens } from "@/stores/auth"

interface LoginRequest {
  username: string
  password: string
}

interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: {
    id: number
    username: string
    email: string
    role: string
    is_active: boolean
  }
}

interface UserInfo {
  id: number
  username: string
  email: string
  role: string
  is_active: boolean
}

export function useLoginMutation() {
  return useMutation({
    mutationFn: async (body: LoginRequest) => {
      return handleApiResponse(await request.post<LoginResponse>("/auth/login", body))
    },
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token)
    },
  })
}

export function useLogoutMutation() {
  return useMutation({
    mutationFn: async () => {
      return handleApiResponse(await request.post("/auth/logout"))
    },
    onSuccess: () => {
      clearTokens()
    },
  })
}

export function currentUserOptions() {
  return queryOptions({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      return handleApiResponse(await request.get<UserInfo>("/users/me"))
    },
    retry: false,
  })
}
```

- [ ] **Step 5: 创建认证 Hook `frontend/src/hooks/use-auth.ts`**

```ts
import { useQuery } from "@tanstack/react-query"

import { currentUserOptions } from "@/data/auth"
import { getRefreshToken } from "@/stores/auth"

export function useAuth() {
  const hasToken = !!getRefreshToken()
  const { data: user, isLoading } = useQuery({
    ...currentUserOptions(),
    enabled: hasToken,
  })

  return {
    user,
    isLoading: hasToken && isLoading,
    isAuthenticated: !!user,
    isAdmin: user?.role === "admin",
  }
}
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/stores/ frontend/src/lib/ frontend/src/data/ frontend/src/hooks/
git commit -m "feat: 实现前端认证状态、API 请求层和 Token 管理"
```

---

## Task 10: 登录页面

**Files:**
- Create: `frontend/src/routes/__root.tsx`
- Create: `frontend/src/routes/auth/login.tsx`
- Create: `frontend/src/components/auth/login-form.tsx`

- [ ] **Step 1: 创建根路由布局 `frontend/src/routes/__root.tsx`**

```tsx
import { createRootRoute, Outlet } from "@tanstack/react-router"

export const Route = createRootRoute({
  component: () => (
    <Outlet />
  ),
})
```

- [ ] **Step 2: 创建登录表单组件 `frontend/src/components/auth/login-form.tsx`**

```tsx
import { useState } from "react"

import { useLoginMutation } from "@/data/auth"

export function LoginForm() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const loginMutation = useLoginMutation()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    try {
      await loginMutation.mutateAsync({ username, password })
      window.location.href = "/"
    } catch {
      setError("用户名或密码错误")
    }
  }

  return (
    <form onSubmit={handleSubmit} data-testid="login-form">
      <h3 className="mb-2 text-xl font-semibold">欢迎回来</h3>
      <p className="mb-6 text-sm text-gray-500">请登录你的账号</p>

      {error && (
        <div data-testid="error-message" className="mb-4 rounded bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      <div className="mb-4">
        <label className="mb-1 block text-sm text-gray-600">用户名</label>
        <input
          data-testid="username-input"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="请输入用户名"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          required
        />
      </div>

      <div className="mb-6">
        <label className="mb-1 block text-sm text-gray-600">密码</label>
        <input
          data-testid="password-input"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="请输入密码"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          required
        />
      </div>

      <button
        data-testid="submit-button"
        type="submit"
        disabled={loginMutation.isPending}
        className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {loginMutation.isPending ? "登录中..." : "登 录"}
      </button>
    </form>
  )
}
```

- [ ] **Step 3: 创建登录页面 `frontend/src/routes/auth/login.tsx`**

```tsx
import { createFileRoute, redirect } from "@tanstack/react-router"

import { LoginForm } from "@/components/auth/login-form"
import { getRefreshToken } from "@/stores/auth"

export const Route = createFileRoute("/auth/login")({
  beforeLoad: () => {
    if (getRefreshToken()) {
      throw redirect({ to: "/" })
    }
  },
  component: LoginPage,
})

function LoginPage() {
  return (
    <div className="flex min-h-screen">
      <div className="flex flex-1 items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600 p-10 text-white">
        <div className="text-center">
          <h2 className="mb-3 text-3xl font-bold text-white">Pivot</h2>
          <p className="text-sm opacity-80">智能数据管理平台</p>
        </div>
      </div>
      <div className="flex flex-1 items-center justify-center bg-white p-10">
        <div className="w-full max-w-sm">
          <LoginForm />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/routes/ frontend/src/components/auth/
git commit -m "feat: 实现登录页面和登录表单组件"
```

---

## Task 11: 认证路由守卫和首页

**Files:**
- Create: `frontend/src/routes/_authenticated/route.tsx`
- Create: `frontend/src/routes/_authenticated/index.tsx`
- Create: `frontend/src/routes/_authenticated/manage/users.tsx`
- Create: `frontend/src/components/auth/admin-route.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: 创建认证布局 `frontend/src/routes/_authenticated/route.tsx`**

```tsx
import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"

import { useLogoutMutation } from "@/data/auth"
import { getRefreshToken } from "@/stores/auth"

export const Route = createFileRoute("/_authenticated")({
  beforeLoad: () => {
    if (!getRefreshToken()) {
      throw redirect({ to: "/auth/login" })
    }
  },
  component: AuthenticatedLayout,
})

function AuthenticatedLayout() {
  const logoutMutation = useLogoutMutation()

  function handleLogout() {
    logoutMutation.mutate(undefined, {
      onSuccess: () => {
        window.location.href = "/auth/login"
      },
    })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="flex items-center justify-between border-b bg-white px-6 py-3">
        <span className="text-lg font-semibold">Pivot</span>
        <button
          data-testid="logout-button"
          onClick={handleLogout}
          className="rounded-md px-3 py-1 text-sm text-gray-600 hover:bg-gray-100"
        >
          登出
        </button>
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  )
}
```

- [ ] **Step 2: 创建首页 `frontend/src/routes/_authenticated/index.tsx`**

```tsx
import { createFileRoute } from "@tanstack/react-router"

import { useAuth } from "@/hooks/use-auth"

export const Route = createFileRoute("/_authenticated/")({
  component: HomePage,
})

function HomePage() {
  const { user } = useAuth()

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold">
        你好，{user?.username}
      </h2>
      <p className="text-gray-500">欢迎回到 Pivot 管理平台</p>
    </div>
  )
}
```

- [ ] **Step 3: 创建管理员路由守卫 `frontend/src/components/auth/admin-route.tsx`**

```tsx
import { ReactNode } from "react"

import { useAuth } from "@/hooks/use-auth"

interface AdminRouteProps {
  children: ReactNode
}

export function AdminRoute({ children }: AdminRouteProps) {
  const { isAdmin, isLoading } = useAuth()

  if (isLoading) {
    return <div className="p-6 text-gray-500">加载中...</div>
  }

  if (!isAdmin) {
    return (
      <div className="p-6">
        <h2 className="text-xl font-semibold text-red-600">403</h2>
        <p className="mt-2 text-gray-500">权限不足</p>
      </div>
    )
  }

  return <>{children}</>
}
```

- [ ] **Step 4: 创建用户管理页 `frontend/src/routes/_authenticated/manage/users.tsx`**

```tsx
import { createFileRoute } from "@tanstack/react-router"

import { AdminRoute } from "@/components/auth/admin-route"

export const Route = createFileRoute("/_authenticated/manage/users")({
  component: UsersPage,
})

function UsersPage() {
  return (
    <AdminRoute>
      <div>
        <h2 className="mb-4 text-xl font-semibold">用户管理</h2>
        <p className="text-gray-500">用户管理页面（待实现）</p>
      </div>
    </AdminRoute>
  )
}
```

- [ ] **Step 5: 更新应用入口 `frontend/src/main.tsx`**

```tsx
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"

import { routeTree } from "./routeTree.gen"

const queryClient = new QueryClient()

const router = createRouter({ routeTree })

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>
)
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/routes/ frontend/src/components/auth/ frontend/src/main.tsx
git commit -m "feat: 实现路由守卫、首页和用户管理页骨架"
```

---

## Task 12: 端到端验证

**Files:**
- 无新文件

- [ ] **Step 1: 运行后端全部测试**

```bash
uv run pytest -v
```

Expected: 全部 PASS

- [ ] **Step 2: 运行前端类型检查**

```bash
cd frontend && npm run type-check
```

Expected: 0 errors

- [ ] **Step 3: 运行前端构建**

```bash
cd frontend && npm run build
```

Expected: 构建成功

- [ ] **Step 4: 手动启动验证**

```bash
uv run uvicorn src.main:app --reload
```

在浏览器中打开 `http://localhost:8000/docs`，确认 OpenAPI 文档正常显示所有接口。

- [ ] **Step 5: 最终提交**

```bash
git add -A
git commit -m "feat: 完成登录登出功能"
```

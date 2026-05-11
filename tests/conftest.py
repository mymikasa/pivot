import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.database import Base, get_db
from src.core.security import get_password_hash
from src.main import app
from src.models.user import Role, User

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
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
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
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

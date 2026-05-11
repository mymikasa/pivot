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
    from src.core.security import get_password_hash
    from src.models.user import User

    admin_role, _ = seed_roles
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

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

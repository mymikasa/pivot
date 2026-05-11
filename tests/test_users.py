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

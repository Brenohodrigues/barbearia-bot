def test_login_success(client, admin_user):
    response = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "senha12345"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(client, admin_user):
    response = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "errada"})
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post("/api/v1/auth/login", json={"email": "ninguem@test.com", "password": "qualquer"})
    assert response.status_code == 401


def test_protected_route_requires_token(client):
    response = client.get("/api/v1/services")
    assert response.status_code == 401


def test_protected_route_with_valid_token(client, auth_headers):
    response = client.get("/api/v1/services", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_change_password_wrong_current(client, auth_headers):
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"current_password": "errada", "new_password": "novaSenha123"},
    )
    assert response.status_code == 400


def test_change_password_success(client, auth_headers):
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"current_password": "senha12345", "new_password": "novaSenha123"},
    )
    assert response.status_code == 204

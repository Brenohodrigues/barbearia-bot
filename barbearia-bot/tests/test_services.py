def test_create_service(client, auth_headers):
    payload = {"name": "Corte", "price": 35.0, "duration_minutes": 45}
    response = client.post("/api/v1/services", json=payload, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Corte"
    assert body["is_active"] is True


def test_create_service_invalid_price(client, auth_headers):
    payload = {"name": "Corte", "price": -5, "duration_minutes": 45}
    response = client.post("/api/v1/services", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_list_services_excludes_inactive_by_default(client, auth_headers, db_session, barbershop):
    from app.models.service import Service

    active = Service(barbershop_id=barbershop.id, name="Corte", price=35, duration_minutes=45)
    inactive = Service(barbershop_id=barbershop.id, name="Antigo", price=10, duration_minutes=20, is_active=False)
    db_session.add_all([active, inactive])
    db_session.commit()

    response = client.get("/api/v1/services", headers=auth_headers)
    names = [s["name"] for s in response.json()]
    assert "Corte" in names
    assert "Antigo" not in names


def test_update_service(client, auth_headers, service):
    response = client.put(f"/api/v1/services/{service.id}", json={"price": 40.0}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["price"] == 40.0


def test_deactivate_service(client, auth_headers, service):
    response = client.delete(f"/api/v1/services/{service.id}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get("/api/v1/services", headers=auth_headers)
    assert response.json() == []


def test_service_not_found(client, auth_headers):
    response = client.put("/api/v1/services/nao-existe", json={"price": 10}, headers=auth_headers)
    assert response.status_code == 404

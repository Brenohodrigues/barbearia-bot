def test_create_barber_with_services(client, auth_headers, service):
    payload = {"name": "Carlos", "service_ids": [service.id], "working_hours": []}
    response = client.post("/api/v1/barbers", json=payload, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Carlos"
    assert len(body["services"]) == 1


def test_create_barber_with_working_hours(client, auth_headers):
    payload = {
        "name": "Pedro",
        "service_ids": [],
        "working_hours": [{"weekday": 0, "starts_at": "09:00", "ends_at": "18:00"}],
    }
    response = client.post("/api/v1/barbers", json=payload, headers=auth_headers)
    assert response.status_code == 201


def test_update_barber_services(client, auth_headers, barber, db_session, barbershop):
    from app.models.service import Service

    new_service = Service(barbershop_id=barbershop.id, name="Barba", price=25, duration_minutes=30)
    db_session.add(new_service)
    db_session.commit()

    response = client.put(
        f"/api/v1/barbers/{barber.id}",
        json={"service_ids": [new_service.id]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert [s["name"] for s in response.json()["services"]] == ["Barba"]


def test_deactivate_barber(client, auth_headers, barber):
    response = client.delete(f"/api/v1/barbers/{barber.id}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get("/api/v1/barbers", headers=auth_headers)
    assert response.json() == []


def test_barber_not_found(client, auth_headers):
    response = client.put("/api/v1/barbers/inexistente", json={"name": "X"}, headers=auth_headers)
    assert response.status_code == 404

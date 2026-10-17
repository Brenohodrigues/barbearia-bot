from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.blocked_time import BlockedTime
from app.services.conversation_engine import get_or_create_customer

TZ = ZoneInfo("America/Sao_Paulo")


def _next_monday_at(hour: int, minute: int = 0):
    today = datetime.now(TZ).date()
    days_ahead = (0 - today.weekday()) % 7
    days_ahead = days_ahead or 7  # sempre uma segunda-feira futura, nunca hoje
    day = today + timedelta(days=days_ahead)
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ)


def _customer(db_session, barbershop, phone="5519999990000"):
    c = get_or_create_customer(db_session, barbershop, phone, "Cliente Teste")
    db_session.commit()
    return c


def test_create_appointment_success(client, auth_headers, db_session, barbershop, barber, service):
    customer = _customer(db_session, barbershop)
    starts_at = _next_monday_at(10)

    response = client.post(
        "/api/v1/appointments",
        json={
            "customer_id": customer.id,
            "barber_id": barber.id,
            "service_id": service.id,
            "starts_at": starts_at.isoformat(),
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["duration_minutes"] == service.duration_minutes


def test_conflict_same_barber_overlapping(client, auth_headers, db_session, barbershop, barber, service):
    customer = _customer(db_session, barbershop)
    starts_at = _next_monday_at(14)

    first = client.post(
        "/api/v1/appointments",
        json={"customer_id": customer.id, "barber_id": barber.id, "service_id": service.id,
              "starts_at": starts_at.isoformat()},
        headers=auth_headers,
    )
    assert first.status_code == 201

    # Serviço dura 45min (14:00-14:45); 14:30 conflita.
    overlapping = starts_at + timedelta(minutes=30)
    second = client.post(
        "/api/v1/appointments",
        json={"customer_id": customer.id, "barber_id": barber.id, "service_id": service.id,
              "starts_at": overlapping.isoformat()},
        headers=auth_headers,
    )
    assert second.status_code == 409


def test_no_conflict_after_service_duration_ends(client, auth_headers, db_session, barbershop, barber, service):
    customer = _customer(db_session, barbershop)
    starts_at = _next_monday_at(14)

    client.post(
        "/api/v1/appointments",
        json={"customer_id": customer.id, "barber_id": barber.id, "service_id": service.id,
              "starts_at": starts_at.isoformat()},
        headers=auth_headers,
    )
    # Serviço termina às 14:45 - agendar às 14:45 deve funcionar.
    right_after = starts_at + timedelta(minutes=45)
    response = client.post(
        "/api/v1/appointments",
        json={"customer_id": customer.id, "barber_id": barber.id, "service_id": service.id,
              "starts_at": right_after.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == 201


def test_appointment_blocked_time(client, auth_headers, db_session, barbershop, barber, service):
    customer = _customer(db_session, barbershop)
    starts_at = _next_monday_at(11)

    db_session.add(BlockedTime(
        barbershop_id=barbershop.id, barber_id=barber.id,
        starts_at=starts_at - timedelta(minutes=15),
        ends_at=starts_at + timedelta(minutes=60),
        reason="Folga",
    ))
    db_session.commit()

    response = client.post(
        "/api/v1/appointments",
        json={"customer_id": customer.id, "barber_id": barber.id, "service_id": service.id,
              "starts_at": starts_at.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_appointment_closed_day(client, auth_headers, db_session, barbershop, barber, service):
    customer = _customer(db_session, barbershop)
    today = datetime.now(TZ).date()
    days_ahead = (6 - today.weekday()) % 7 or 7  # próximo domingo (fechado no fixture)
    sunday = today + timedelta(days=days_ahead)
    starts_at = datetime(sunday.year, sunday.month, sunday.day, 10, 0, tzinfo=TZ)

    response = client.post(
        "/api/v1/appointments",
        json={"customer_id": customer.id, "barber_id": barber.id, "service_id": service.id,
              "starts_at": starts_at.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_cancel_appointment(client, auth_headers, db_session, barbershop, barber, service):
    customer = _customer(db_session, barbershop)
    starts_at = _next_monday_at(9)

    created = client.post(
        "/api/v1/appointments",
        json={"customer_id": customer.id, "barber_id": barber.id, "service_id": service.id,
              "starts_at": starts_at.isoformat()},
        headers=auth_headers,
    ).json()

    response = client.delete(f"/api/v1/appointments/{created['id']}?reason=Imprevisto", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    # Horário liberado - novo agendamento no mesmo slot deve funcionar.
    reused = client.post(
        "/api/v1/appointments",
        json={"customer_id": customer.id, "barber_id": barber.id, "service_id": service.id,
              "starts_at": starts_at.isoformat()},
        headers=auth_headers,
    )
    assert reused.status_code == 201


def test_reschedule_appointment(client, auth_headers, db_session, barbershop, barber, service):
    customer = _customer(db_session, barbershop)
    starts_at = _next_monday_at(9)

    created = client.post(
        "/api/v1/appointments",
        json={"customer_id": customer.id, "barber_id": barber.id, "service_id": service.id,
              "starts_at": starts_at.isoformat()},
        headers=auth_headers,
    ).json()

    new_time = starts_at + timedelta(hours=2)
    response = client.put(
        f"/api/v1/appointments/{created['id']}",
        json={"starts_at": new_time.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["starts_at"].startswith(new_time.isoformat()[:16])


def test_availability_endpoint_returns_slots(client, auth_headers, barber, service):
    monday = _next_monday_at(0).date()
    response = client.get(
        f"/api/v1/appointments/availability/slots?service_id={service.id}&date={monday.isoformat()}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    slots = response.json()
    assert len(slots) > 0
    assert all(s["barber_id"] == barber.id for s in slots)

from app.services.conversation_engine import get_or_create_customer


def test_get_or_create_customer_creates_new(db_session, barbershop):
    customer = get_or_create_customer(db_session, barbershop, "5519999990000", "Fulano")
    db_session.commit()
    assert customer.id is not None
    assert customer.phone == "5519999990000"
    assert customer.name == "Fulano"


def test_get_or_create_customer_reuses_existing(db_session, barbershop):
    first = get_or_create_customer(db_session, barbershop, "5519999990000", "Fulano")
    db_session.commit()
    second = get_or_create_customer(db_session, barbershop, "5519999990000", None)
    db_session.commit()
    assert first.id == second.id


def test_list_customers_via_api(client, auth_headers, db_session, barbershop):
    get_or_create_customer(db_session, barbershop, "5519999990000", "Fulano")
    db_session.commit()

    response = client.get("/api/v1/customers", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["phone"] == "5519999990000"


def test_search_customers_by_name(client, auth_headers, db_session, barbershop):
    get_or_create_customer(db_session, barbershop, "5519999990000", "Ana Silva")
    get_or_create_customer(db_session, barbershop, "5519999990001", "Bruno Costa")
    db_session.commit()

    response = client.get("/api/v1/customers?search=Ana", headers=auth_headers)
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Ana Silva"

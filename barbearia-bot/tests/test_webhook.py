import pytest


def test_webhook_verification_success(client):
    response = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "test-verify-token", "hub.challenge": "12345"},
    )
    assert response.status_code == 200
    assert response.text == "12345"


def test_webhook_verification_wrong_token(client):
    response = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "errado", "hub.challenge": "12345"},
    )
    assert response.status_code == 403


def test_webhook_receives_and_never_crashes_on_malformed_payload(client):
    response = client.post("/api/v1/whatsapp/webhook", json={"entry": [{"changes": [{"value": {}}]}]})
    assert response.status_code == 200
    assert response.json() == {"status": "received"}


def test_webhook_unknown_phone_number_id_is_ignored_gracefully(client):
    payload = {
        "entry": [{"changes": [{"value": {
            "metadata": {"phone_number_id": "nao-configurado"},
            "messages": [{"from": "5519999999999", "type": "text", "text": {"body": "Olá"}}],
        }}]}]
    }
    response = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_full_conversation_creates_customer_and_advances_state(db_session, barbershop, barber, service):
    from app.models.conversation import ConversationState
    from app.services.conversation_engine import handle_incoming_message

    await handle_incoming_message(db_session, barbershop, "5519999990000", "Olá", profile_name="Cliente")
    from app.models.conversation import Conversation
    from app.models.customer import Customer

    customer = db_session.query(Customer).filter_by(phone="5519999990000").first()
    assert customer is not None
    assert customer.name == "Cliente"

    conversation = db_session.query(Conversation).filter_by(customer_id=customer.id).first()
    assert conversation.state == ConversationState.MENU

    await handle_incoming_message(db_session, barbershop, "5519999990000", "1")
    db_session.refresh(conversation)
    assert conversation.state == ConversationState.CHOOSING_SERVICE


@pytest.mark.asyncio
async def test_human_handoff_stops_bot_replies(db_session, barbershop):
    from app.models.conversation import Conversation
    from app.services.conversation_engine import handle_incoming_message

    await handle_incoming_message(db_session, barbershop, "5519999990000", "atendente")
    conversation = db_session.query(Conversation).first()
    assert conversation.is_human_handled is True

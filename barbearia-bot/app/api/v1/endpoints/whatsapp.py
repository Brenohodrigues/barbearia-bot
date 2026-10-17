"""
Webhook da WhatsApp Business Platform (Cloud API).

- GET  /api/v1/whatsapp/webhook  -> handshake de verificação da Meta
- POST /api/v1/whatsapp/webhook  -> eventos (mensagens recebidas, status)

O endpoint em si fica bem enxuto: toda a lógica de negócio é delegada a
`app.services.conversation_engine`, conforme pedido no briefing (seção 20 -
"o processamento deverá ser organizado e não ficar todo dentro do endpoint
do webhook").
"""
import hashlib
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.deps import get_db
from app.models.barbershop import Barbershop
from app.services.conversation_engine import handle_incoming_message

router = APIRouter()


@router.get("/webhook")
async def verify_webhook(request: Request):
    """Handshake de verificação exigido pela Meta ao configurar o webhook.
    Documentação: https://developers.facebook.com/docs/graph-api/webhooks/getting-started

    Os parâmetros reais enviados pela Meta usam ponto no nome
    (hub.mode, hub.verify_token, hub.challenge), por isso são lidos
    diretamente de `request.query_params` em vez de parâmetros de rota do
    FastAPI (que não aceitam "." no nome).
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if not settings.WHATSAPP_VERIFY_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WHATSAPP_VERIFY_TOKEN não configurado no .env.",
        )

    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token de verificação inválido.")


def _valid_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Valida a assinatura X-Hub-Signature-256 enviada pela Meta, usando o
    App Secret do aplicativo. Protege contra requisições forjadas.
    Se WHATSAPP_APP_SECRET não estiver configurado, a validação é pulada
    (apenas recomendado para testes locais - configure em produção)."""
    if not settings.WHATSAPP_APP_SECRET:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.WHATSAPP_APP_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    received = signature_header.split("sha256=", 1)[1]
    return hmac.compare_digest(expected, received)


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: str | None = Header(default=None),
):
    raw_body = await request.body()

    if not _valid_signature(raw_body, x_hub_signature_256):
        logger.warning("Webhook do WhatsApp recebido com assinatura inválida - descartado.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Assinatura inválida.")

    payload = await request.json()

    try:
        await _process_payload(db, payload)
    except Exception:  # pragma: no cover - nunca deixamos o webhook cair
        logger.exception("Erro ao processar evento do webhook do WhatsApp.")
        db.rollback()

    # A Meta espera sempre um 200 rápido, mesmo que haja erro interno,
    # para não reenviar o mesmo evento repetidamente.
    return {"status": "received"}


async def _process_payload(db: Session, payload: dict) -> None:
    """Percorre a estrutura de eventos da Cloud API e delega cada mensagem
    recebida ao motor de conversação."""
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id")

            barbershop = _resolve_barbershop(db, phone_number_id)
            if not barbershop:
                logger.warning("Webhook recebido para phone_number_id desconhecido: %s", phone_number_id)
                continue

            contacts = {c["wa_id"]: c.get("profile", {}).get("name") for c in value.get("contacts", [])}

            for message in value.get("messages", []):
                from_phone = message.get("from")
                profile_name = contacts.get(from_phone)
                text, button_id = _extract_text_and_button(message)
                await handle_incoming_message(
                    db, barbershop, from_phone, text,
                    profile_name=profile_name, button_id=button_id,
                )


def _resolve_barbershop(db: Session, phone_number_id: str | None) -> Barbershop | None:
    """Em um cenário single-tenant, retorna a única barbearia ativa. Em
    multi-tenant, o ideal é guardar o `phone_number_id` de cada barbearia
    em uma coluna própria e buscar por ele - deixamos o ponto de extensão
    pronto aqui."""
    if not phone_number_id:
        return None
    query = db.query(Barbershop).filter(Barbershop.is_active.is_(True))
    if phone_number_id == settings.WHATSAPP_PHONE_NUMBER_ID:
        return query.first()
    return None


def _extract_text_and_button(message: dict) -> tuple[str, str | None]:
    msg_type = message.get("type")
    if msg_type == "text":
        return message.get("text", {}).get("body", ""), None
    if msg_type == "interactive":
        interactive = message.get("interactive", {})
        if interactive.get("type") == "button_reply":
            reply = interactive["button_reply"]
            return reply.get("title", ""), reply.get("id")
        if interactive.get("type") == "list_reply":
            reply = interactive["list_reply"]
            return reply.get("title", ""), reply.get("id")
    if msg_type == "button":
        return message.get("button", {}).get("text", ""), None
    return "", None

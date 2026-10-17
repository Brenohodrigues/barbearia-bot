"""
Cliente HTTP para a WhatsApp Business Platform (Cloud API oficial da Meta).

Referência oficial: https://developers.facebook.com/docs/whatsapp/cloud-api
Todas as mensagens (texto, botões, listas, templates) são enviadas para o
mesmo endpoint:

    POST https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages

Este módulo NUNCA deve conter tokens reais - eles vêm de `app.core.config`,
que por sua vez lê do `.env` (não versionado).
"""
from __future__ import annotations

from typing import Any, Optional

import httpx

from app.core.config import settings
from app.core.logging import logger


class WhatsAppNotConfiguredError(Exception):
    """As credenciais do WhatsApp ainda não foram configuradas no .env."""


class WhatsAppClient:
    def __init__(self) -> None:
        self._base_url = settings.WHATSAPP_GRAPH_BASE_URL
        self._version = settings.WHATSAPP_API_VERSION
        self._phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self._token = settings.WHATSAPP_ACCESS_TOKEN

    @property
    def _messages_url(self) -> str:
        return f"{self._base_url}/{self._version}/{self._phone_number_id}/messages"

    def _require_configured(self) -> None:
        if not settings.whatsapp_configured:
            raise WhatsAppNotConfiguredError(
                "Credenciais do WhatsApp não configuradas. Preencha "
                "WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID e "
                "WHATSAPP_VERIFY_TOKEN no arquivo .env (veja DOCUMENTACAO.md, seção 15)."
            )

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _post(self, payload: dict) -> Optional[dict]:
        self._require_configured()
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(self._messages_url, headers=self._headers(), json=payload)
            if response.status_code >= 400:
                logger.error(
                    "Falha ao enviar mensagem WhatsApp: status=%s body=%s",
                    response.status_code,
                    response.text,
                )
                return None
            return response.json()

    async def send_text(self, to_phone: str, body: str, preview_url: bool = False) -> Optional[dict]:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {"body": body, "preview_url": preview_url},
        }
        return await self._post(payload)

    async def send_buttons(self, to_phone: str, body: str, buttons: list[tuple[str, str]]) -> Optional[dict]:
        """Envia mensagem interativa com até 3 botões de resposta rápida.
        `buttons` é uma lista de tuplas (id, título)."""
        if len(buttons) > 3:
            raise ValueError("WhatsApp permite no máximo 3 botões de resposta rápida.")
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": bid, "title": title[:20]}}
                        for bid, title in buttons
                    ]
                },
            },
        }
        return await self._post(payload)

    async def send_list(
        self,
        to_phone: str,
        body: str,
        button_text: str,
        sections: list[dict[str, Any]],
    ) -> Optional[dict]:
        """Envia uma mensagem de lista interativa (até 10 opções no total).
        `sections` segue o formato exigido pela Graph API, por exemplo:
        [{"title": "Serviços", "rows": [{"id": "svc_1", "title": "Corte", "description": "R$ 35,00"}]}]
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body},
                "action": {"button": button_text[:20], "sections": sections},
            },
        }
        return await self._post(payload)

    async def send_template(self, to_phone: str, template_name: str, language_code: str,
                             components: Optional[list] = None) -> Optional[dict]:
        """Envia uma mensagem de template pré-aprovada pela Meta (obrigatório
        fora da janela de 24h de atendimento). Veja DOCUMENTACAO.md seção 18."""
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                **({"components": components} if components else {}),
            },
        }
        return await self._post(payload)

    async def mark_as_read(self, message_id: str) -> Optional[dict]:
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        return await self._post(payload)


whatsapp_client = WhatsAppClient()

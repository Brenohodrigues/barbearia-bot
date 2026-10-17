"""
Configuração central da aplicação.

Todos os valores sensíveis (tokens, senhas, chaves) vêm EXCLUSIVAMENTE de
variáveis de ambiente / arquivo `.env`. Nada disso é gravado no código-fonte.

Veja `.env.example` para a lista completa de variáveis e `DOCUMENTACAO.md`
(seção 10) para a explicação de cada uma.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ------------------------------------------------------------------ #
    # Aplicação
    # ------------------------------------------------------------------ #
    APP_NAME: str = "Barbearia Bot"
    APP_ENV: str = "development"  # development | staging | production
    APP_DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ------------------------------------------------------------------ #
    # Segurança / Autenticação
    # ------------------------------------------------------------------ #
    SECRET_KEY: str  # obrigatório - gere com: openssl rand -hex 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 horas

    # ------------------------------------------------------------------ #
    # Banco de dados
    # ------------------------------------------------------------------ #
    # Produção: postgresql+psycopg://usuario:senha@host:5432/barbearia
    # Desenvolvimento: sqlite:///./dev.db
    DATABASE_URL: str = "sqlite:///./dev.db"

    # ------------------------------------------------------------------ #
    # CORS (origens autorizadas a acessar a API, ex.: painel web)
    # ------------------------------------------------------------------ #
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:8000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ------------------------------------------------------------------ #
    # WhatsApp Business Platform (Cloud API oficial da Meta)
    # ------------------------------------------------------------------ #
    # Token permanente de acesso (System User) - NUNCA versionar.
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    # ID do número de telefone (Phone Number ID), obtido no painel da Meta.
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    # ID da conta comercial do WhatsApp (WABA ID).
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = None
    # Token que você escolhe e usa para validar o handshake do webhook (GET).
    WHATSAPP_VERIFY_TOKEN: Optional[str] = None
    # App Secret do aplicativo Meta, usado para validar a assinatura
    # X-Hub-Signature-256 das requisições recebidas no webhook.
    WHATSAPP_APP_SECRET: Optional[str] = None
    # Versão da Graph API utilizada nas chamadas (ex.: v21.0).
    WHATSAPP_API_VERSION: str = "v21.0"
    # Base da Graph API - normalmente não precisa mudar.
    WHATSAPP_GRAPH_BASE_URL: str = "https://graph.facebook.com"

    # ------------------------------------------------------------------ #
    # Configurações gerais da barbearia (usadas como fallback / seed)
    # ------------------------------------------------------------------ #
    DEFAULT_TIMEZONE: str = "America/Sao_Paulo"

    # ------------------------------------------------------------------ #
    # Logs
    # ------------------------------------------------------------------ #
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def whatsapp_configured(self) -> bool:
        """Indica se as credenciais mínimas do WhatsApp foram preenchidas."""
        return bool(
            self.WHATSAPP_ACCESS_TOKEN
            and self.WHATSAPP_PHONE_NUMBER_ID
            and self.WHATSAPP_VERIFY_TOKEN
        )


@lru_cache
def get_settings() -> "Settings":
    return Settings()


settings = get_settings()

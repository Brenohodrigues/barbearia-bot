"""
Configuração de logging estruturado.

Registra em stdout (capturado pelo Docker/systemd/servidor) e nunca grava
tokens, senhas ou dados sensíveis nos logs.
"""
import logging
import sys

from app.core.config import settings


class SensitiveDataFilter(logging.Filter):
    """Evita vazar tokens/segredos que acidentalmente cheguem a uma mensagem de log."""

    REDACT_KEYS = ("access_token", "token", "password", "secret", "authorization")

    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage()).lower()
        for key in self.REDACT_KEYS:
            if key in msg and "***" not in msg:
                record.msg = "[mensagem de log omitida por conter possível dado sensível]"
                record.args = ()
                break
        return True


def configure_logging() -> None:
    log_format = (
        '{"time": "%(asctime)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": "%(message)s"}'
        if settings.LOG_JSON
        else "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(log_format))
    handler.addFilter(SensitiveDataFilter())

    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)
    root.handlers = [handler]

    # Reduz verbosidade de bibliotecas de terceiros
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


logger = logging.getLogger("barbearia")

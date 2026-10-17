"""
Ponto de entrada da aplicação FastAPI.

Executar localmente:
    uvicorn app.main:app --reload

Documentação interativa: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Iniciando %s (env=%s)", settings.APP_NAME, settings.APP_ENV)
    if not settings.whatsapp_configured:
        logger.warning(
            "Credenciais do WhatsApp não configuradas. O bot não conseguirá "
            "enviar mensagens até que .env seja preenchido (ver DOCUMENTACAO.md)."
        )
    yield
    logger.info("Encerrando %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description="Sistema de atendimento e agendamento para barbearia via WhatsApp.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Mensagem amigável ao cliente; detalhes completos só nos logs.
    logger.info("Erro de validação em %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Dados inválidos enviados na requisição."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Nunca expõe stack trace/erro interno ao cliente (seção 28 do briefing).
    logger.exception("Erro não tratado em %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno. Tente novamente em instantes."},
    )


app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Painel administrativo (HTML/CSS/JS estático simples)
app.mount("/painel", StaticFiles(directory="frontend", html=True), name="painel")


@app.get("/", include_in_schema=False)
def root():
    return {
        "app": settings.APP_NAME,
        "docs": "/docs",
        "painel": "/painel",
    }

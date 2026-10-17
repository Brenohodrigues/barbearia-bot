from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("")
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "whatsapp_configured": settings.whatsapp_configured,
    }

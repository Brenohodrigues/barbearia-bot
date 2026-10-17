from fastapi import APIRouter

from app.api.v1.endpoints import appointments, auth, barbers, customers, health, services, whatsapp

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(services.router, prefix="/services", tags=["services"])
api_router.include_router(barbers.router, prefix="/barbers", tags=["barbers"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])

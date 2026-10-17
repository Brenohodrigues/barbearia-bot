"""
Configuração comum dos testes (fixtures).

Cada teste roda contra um banco SQLite em memória isolado, para não
interferir com o banco de desenvolvimento (`dev.db`) nem com outros testes.
"""
import os
from datetime import time

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "test-verify-token")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base_class import Base
from app.deps import get_db
from app.main import app
from app.models.barber import Barber
from app.models.barbershop import Barbershop
from app.models.business_hours import BusinessHours
from app.models.service import Service
from app.models.user import User, UserRole

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=TEST_ENGINE, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def _fresh_schema():
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def barbershop(db_session):
    shop = Barbershop(name="Barbearia Teste", slug="barbearia-teste", timezone="America/Sao_Paulo")
    db_session.add(shop)
    db_session.flush()
    for weekday in range(0, 6):
        db_session.add(BusinessHours(barbershop_id=shop.id, weekday=weekday,
                                      opens_at=time(9, 0), closes_at=time(18, 0)))
    db_session.add(BusinessHours(barbershop_id=shop.id, weekday=6, is_closed=True))
    db_session.commit()
    return shop


@pytest.fixture
def admin_user(db_session, barbershop):
    user = User(
        barbershop_id=barbershop.id,
        name="Admin",
        email="admin@test.com",
        hashed_password=hash_password("senha12345"),
        role=UserRole.OWNER,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth_headers(client, admin_user):
    response = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "senha12345"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def service(db_session, barbershop):
    svc = Service(barbershop_id=barbershop.id, name="Corte", price=35.0, duration_minutes=45)
    db_session.add(svc)
    db_session.commit()
    return svc


@pytest.fixture
def barber(db_session, barbershop, service):
    b = Barber(barbershop_id=barbershop.id, name="João")
    b.services = [service]
    db_session.add(b)
    db_session.commit()
    return b

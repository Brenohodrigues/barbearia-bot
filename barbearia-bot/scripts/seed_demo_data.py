"""
Cria dados de demonstração: uma barbearia, um usuário administrador, dois
barbeiros, três serviços e horário de funcionamento padrão.

ATENÇÃO: isto é apenas para desenvolvimento/teste. Não rode em produção com
dados reais, e troque a senha do usuário administrativo assim que possível
(o campo `must_change_password` já vem marcado como True).

Uso:
    python -m scripts.seed_demo_data
"""
import sys
from datetime import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.barber import Barber  # noqa: E402
from app.models.barbershop import Barbershop  # noqa: E402
from app.models.business_hours import BusinessHours  # noqa: E402
from app.models.service import Service  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

DEMO_ADMIN_EMAIL = "admin@barbearia.demo"
DEMO_ADMIN_PASSWORD = "TrocarSenha123!"  # troque no primeiro login


def run():
    db = SessionLocal()
    try:
        existing = db.query(Barbershop).filter(Barbershop.slug == "barbearia-demo").first()
        if existing:
            print("Dados de demonstração já existem. Nada a fazer.")
            return

        shop = Barbershop(
            name="Barbearia Demo",
            slug="barbearia-demo",
            phone="5519999990000",
            address="Rua Exemplo, 123 - Centro",
            instagram="@barbeariademo",
            welcome_message="Olá! 👋 Seja bem-vindo à Barbearia Demo.",
        )
        db.add(shop)
        db.flush()

        admin = User(
            barbershop_id=shop.id,
            name="Administrador",
            email=DEMO_ADMIN_EMAIL,
            hashed_password=hash_password(DEMO_ADMIN_PASSWORD),
            role=UserRole.OWNER,
            must_change_password=True,
        )
        db.add(admin)

        corte = Service(barbershop_id=shop.id, name="Corte", price=35.00, duration_minutes=45,
                         description="Corte de cabelo tradicional.")
        barba = Service(barbershop_id=shop.id, name="Barba", price=25.00, duration_minutes=30,
                         description="Aparar e desenhar a barba.")
        combo = Service(barbershop_id=shop.id, name="Corte + Barba", price=55.00, duration_minutes=75,
                         description="Corte completo com barba.")
        db.add_all([corte, barba, combo])
        db.flush()

        joao = Barber(barbershop_id=shop.id, name="João", bio="Especialista em cortes clássicos.")
        carlos = Barber(barbershop_id=shop.id, name="Carlos", bio="Especialista em barba e navalha.")
        joao.services = [corte, barba, combo]
        carlos.services = [corte, barba, combo]
        db.add_all([joao, carlos])

        # Segunda a sexta 09h-19h, sábado 09h-17h, domingo fechado
        for weekday in range(0, 5):
            db.add(BusinessHours(barbershop_id=shop.id, weekday=weekday,
                                  opens_at=time(9, 0), closes_at=time(19, 0)))
        db.add(BusinessHours(barbershop_id=shop.id, weekday=5, opens_at=time(9, 0), closes_at=time(17, 0)))
        db.add(BusinessHours(barbershop_id=shop.id, weekday=6, is_closed=True))

        db.commit()

        print("Dados de demonstração criados com sucesso!")
        print(f"  Login do painel: {DEMO_ADMIN_EMAIL}")
        print(f"  Senha temporária: {DEMO_ADMIN_PASSWORD}")
        print("  (troque a senha assim que fizer login)")
    finally:
        db.close()


if __name__ == "__main__":
    run()

"""
Importa todos os modelos para que `Base.metadata` os conheça (necessário
para o Alembic detectar as tabelas corretamente ao gerar migrations).
"""
from app.models.barbershop import Barbershop  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
from app.models.barber import Barber, barber_services  # noqa: F401
from app.models.customer import Customer  # noqa: F401
from app.models.service import Service  # noqa: F401
from app.models.appointment import Appointment, AppointmentStatus  # noqa: F401
from app.models.business_hours import BusinessHours, BarberHours  # noqa: F401
from app.models.blocked_time import BlockedTime  # noqa: F401
from app.models.conversation import Conversation, ConversationState  # noqa: F401
from app.models.message import Message, MessageDirection  # noqa: F401
from app.models.settings import Setting  # noqa: F401

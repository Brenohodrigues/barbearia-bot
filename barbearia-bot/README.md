# Barbearia Bot 💈

Sistema completo de atendimento e agendamento para barbearia via **WhatsApp Business Platform (Cloud API oficial da Meta)**, com painel administrativo web.

> 📘 Documentação completa e detalhada (para iniciantes): [`DOCUMENTACAO.md`](./DOCUMENTACAO.md)

## Descrição

- Bot de atendimento automático pelo WhatsApp (menu, agendamento, cancelamento, reagendamento, consulta de agendamentos, handoff para atendimento humano).
- Painel administrativo web (dashboard, agenda, clientes, serviços, barbeiros).
- API REST documentada (Swagger em `/docs`).
- Arquitetura preparada para multi-tenant (múltiplas barbearias) no futuro.

## Tecnologias

| Camada         | Tecnologia                                   |
|----------------|-----------------------------------------------|
| Backend        | Python 3.12 + FastAPI                         |
| Banco de dados | PostgreSQL (produção) / SQLite (dev)          |
| ORM            | SQLAlchemy 2.0 + Alembic (migrations)         |
| Autenticação   | JWT (python-jose) + bcrypt (passlib)          |
| Frontend       | HTML + CSS + JavaScript puro (sem build step) |
| WhatsApp       | WhatsApp Cloud API (Graph API da Meta)        |
| Testes         | pytest                                        |
| Deploy         | Docker + docker-compose                       |

## Requisitos

- Python 3.12+
- Git
- Docker e Docker Compose (opcional, recomendado para produção)
- Conta de desenvolvedor Meta com WhatsApp Business Platform configurado (ver `DOCUMENTACAO.md`)

## Instalação rápida (desenvolvimento)

```bash
git clone <url-do-seu-repositorio>
cd barbearia-bot

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# edite o .env e defina ao menos SECRET_KEY (openssl rand -hex 32)

alembic upgrade head
python -m scripts.seed_demo_data   # opcional: cria dados de demonstração

uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Painel: http://localhost:8000/painel/login.html
  - Login de demonstração (se você rodou o seed): `admin@barbearia.demo` / `TrocarSenha123!`

## Configuração do WhatsApp

O bot não envia mensagens de verdade até que `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` e `WHATSAPP_VERIFY_TOKEN` estejam preenchidos no `.env`. Sem isso, o sistema continua funcionando normalmente (útil para testar a lógica de agendamento e o painel), apenas registra nos logs que a mensagem "seria enviada". Veja o passo a passo completo na seção 15-18 de `DOCUMENTACAO.md`.

## Testes

```bash
pytest
```

## Estrutura do projeto

```text
barbearia-bot/
├── app/
│   ├── api/v1/endpoints/   # rotas da API (auth, services, barbers, customers, appointments, whatsapp)
│   ├── core/               # configuração, segurança, logging
│   ├── db/                 # engine/sessão do banco
│   ├── models/             # modelos SQLAlchemy
│   ├── schemas/            # schemas Pydantic
│   ├── services/           # regras de negócio (agenda, WhatsApp, motor de conversação)
│   ├── deps.py             # dependências do FastAPI (auth, tenant)
│   └── main.py             # ponto de entrada
├── frontend/               # painel administrativo (HTML/CSS/JS)
├── migrations/             # migrations do Alembic
├── scripts/seed_demo_data.py
├── tests/                  # testes automatizados (pytest)
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
└── DOCUMENTACAO.md
```

## Documentação

Veja [`DOCUMENTACAO.md`](./DOCUMENTACAO.md) para: instalação passo a passo para iniciantes, configuração completa do WhatsApp Business Platform, deploy em produção, backup, segurança, LGPD e solução de problemas.

## Licença

Projeto de uso privado/comercial conforme definido pelo contratante. Adapte esta seção conforme sua necessidade.

# DOCUMENTAÇÃO COMPLETA — Barbearia Bot

Este documento explica em detalhes o que é o sistema, como ele funciona, como instalá-lo do zero (mesmo sem experiência profissional) e como colocá-lo em produção. Leia com calma e siga os passos na ordem.

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Arquitetura](#2-arquitetura)
3. [Tecnologias e por que foram escolhidas](#3-tecnologias-e-por-que-foram-escolhidas)
4. [Estrutura de pastas](#4-estrutura-de-pastas)
5. [Instalação — passo a passo desde um computador limpo](#5-instalação--passo-a-passo-desde-um-computador-limpo)
6. [Python](#6-python)
7. [Ambiente virtual](#7-ambiente-virtual)
8. [Dependências](#8-dependências)
9. [Banco de dados](#9-banco-de-dados)
10. [Variáveis de ambiente](#10-variáveis-de-ambiente)
11. [Executar localmente](#11-executar-localmente)
12. [API](#12-api)
13. [Swagger (documentação interativa)](#13-swagger-documentação-interativa)
14. [Painel administrativo](#14-painel-administrativo)
15. [WhatsApp — visão geral da integração](#15-whatsapp--visão-geral-da-integração)
16. [Webhook](#16-webhook)
17. [Configuração na Meta (passo a passo)](#17-configuração-na-meta-passo-a-passo)
18. [Templates de mensagem](#18-templates-de-mensagem)
19. [Testes](#19-testes)
20. [Git e GitHub](#20-git-e-github)
21. [Deploy em produção](#21-deploy-em-produção)
22. [HTTPS](#22-https)
23. [Banco de dados em produção](#23-banco-de-dados-em-produção)
24. [Backup](#24-backup)
25. [Logs](#25-logs)
26. [Solução de problemas comuns](#26-solução-de-problemas-comuns)
27. [Segurança](#27-segurança)
28. [LGPD](#28-lgpd)
29. [Manutenção](#29-manutenção)
30. [Expansão para SaaS (multi-tenant)](#30-expansão-para-saas-multi-tenant)

---

## 1. Visão geral

O **Barbearia Bot** é um sistema que permite que uma barbearia atenda seus clientes automaticamente pelo WhatsApp: o cliente manda mensagem, o bot mostra um menu, ajuda a escolher serviço, barbeiro, data e horário, confirma o agendamento e cria tudo no banco de dados — sem a barbearia precisar digitar nada. Além disso, o sistema tem um **painel administrativo web** onde o dono/gerente da barbearia gerencia clientes, serviços, barbeiros, agenda e configurações.

O sistema é composto por três grandes partes:

1. **Backend (API)** — em Python/FastAPI, é o "cérebro" do sistema: guarda os dados, aplica as regras de negócio (ex.: não deixar dois clientes agendarem o mesmo horário com o mesmo barbeiro) e conversa com o WhatsApp.
2. **Bot do WhatsApp** — um conjunto de rotinas dentro do backend que interpreta as mensagens recebidas e responde de forma automática, seguindo um fluxo de conversa (máquina de estados).
3. **Painel administrativo** — uma página web simples (HTML/CSS/JavaScript) para o dono da barbearia gerenciar tudo visualmente.

---

## 2. Arquitetura

```text
                    CLIENTE
                       │
                       ▼
                  WHATSAPP
                       │
                       ▼
          WhatsApp Business Platform (Meta)
                       │
                       ▼
             WEBHOOK (POST /api/v1/whatsapp/webhook)
                       │
                       ▼
                  FASTAPI (app/main.py)
                       │
          ┌────────────┼─────────────────┐
          ▼            ▼                 ▼
   Motor de conversa   Agenda        Cadastros
 (conversation_engine)(scheduling) (clientes/serviços/barbeiros)
          │            │                 │
          └────────────┼─────────────────┘
                       ▼
                   PostgreSQL / SQLite
                       ▲
                       │
                 Painel Web (frontend/)
                       │
                       ▼
                  DONO DA BARBEARIA
```

**Como uma mensagem percorre o sistema:**

1. O cliente manda uma mensagem no WhatsApp da barbearia.
2. A Meta (dona da API do WhatsApp) recebe essa mensagem e a repassa, via HTTP POST, para o **webhook** do nosso backend (`/api/v1/whatsapp/webhook`).
3. O endpoint do webhook (`app/api/v1/endpoints/whatsapp.py`) apenas valida a requisição e repassa para o **motor de conversação** (`app/services/conversation_engine.py`).
4. O motor de conversação decide o que fazer com base no estado atual da conversa daquele cliente (guardado na tabela `conversations`) e, quando precisa checar horários, chama o módulo de **agenda** (`app/services/scheduling.py`), que é o único responsável por decidir se um horário está disponível.
5. A resposta é enviada de volta ao cliente através do **cliente HTTP do WhatsApp** (`app/services/whatsapp_client.py`), que fala com a Graph API da Meta.
6. Tudo o que acontece (mensagens, agendamentos, cancelamentos) fica salvo no banco de dados e pode ser visto no **painel administrativo**.

---

## 3. Tecnologias e por que foram escolhidas

| Escolha | Motivo |
|---|---|
| **Python + FastAPI** | Framework moderno, rápido, com documentação automática (Swagger) e tipagem, o que ajuda muito quem está começando a entender o código. |
| **SQLAlchemy 2.0 (ORM)** | É o ORM mais maduro do ecossistema Python, com excelente suporte a PostgreSQL e SQLite, e integra bem com Alembic para migrations. |
| **Alembic** | Ferramenta padrão de migrations para SQLAlchemy — permite versionar mudanças no banco de dados. |
| **PostgreSQL** | Banco de dados robusto, gratuito e o mais recomendado para aplicações em produção com FastAPI/SQLAlchemy. |
| **SQLite** | Usado apenas em desenvolvimento local, pois não exige instalar nada — o "banco" é um único arquivo. |
| **JWT (python-jose) + bcrypt (passlib)** | Padrão de mercado para autenticação stateless de APIs e hash seguro de senha. |
| **HTML/CSS/JS puro no painel** | Evita a complexidade de configurar um projeto React/Vue (build step, node_modules, etc.) para um painel relativamente simples — mais fácil de entender e modificar para quem está começando. |
| **WhatsApp Cloud API (oficial da Meta)** | É a única forma de integração com o WhatsApp suportada oficialmente, estável e sem risco de bloqueio do número, ao contrário de soluções não oficiais (Selenium, WhatsApp Web, bibliotecas não oficiais). |
| **Docker + docker-compose** | Facilita rodar o backend e o PostgreSQL juntos, tanto em desenvolvimento quanto em produção, com um único comando. |

---

## 4. Estrutura de pastas

```text
barbearia-bot/
│
├── app/
│   ├── main.py                  # cria a aplicação FastAPI, monta rotas e o painel
│   ├── deps.py                  # dependências reutilizáveis (sessão de banco, usuário logado)
│   │
│   ├── core/
│   │   ├── config.py            # lê as variáveis de ambiente (.env)
│   │   ├── security.py          # hash de senha e tokens JWT
│   │   └── logging.py           # configuração de logs
│   │
│   ├── db/
│   │   ├── base_class.py        # classe base do SQLAlchemy (id, created_at, updated_at)
│   │   └── session.py           # engine e sessão do banco
│   │
│   ├── models/                  # um arquivo por tabela do banco (SQLAlchemy)
│   │   ├── barbershop.py        # a barbearia (tenant)
│   │   ├── user.py              # usuário do painel administrativo
│   │   ├── barber.py            # barbeiro
│   │   ├── customer.py          # cliente
│   │   ├── service.py           # serviço (corte, barba, etc.)
│   │   ├── appointment.py       # agendamento
│   │   ├── business_hours.py    # horário de funcionamento (barbearia e barbeiro)
│   │   ├── blocked_time.py      # bloqueios pontuais (folgas, feriados)
│   │   ├── conversation.py      # estado da conversa do bot com cada cliente
│   │   ├── message.py           # histórico de mensagens
│   │   └── settings.py          # configurações extras chave-valor
│   │
│   ├── schemas/                 # validação de entrada/saída da API (Pydantic)
│   │
│   ├── services/
│   │   ├── scheduling.py        # regras de disponibilidade e conflito de horário
│   │   ├── whatsapp_client.py   # chamadas HTTP para a Graph API da Meta
│   │   └── conversation_engine.py  # máquina de estados do bot
│   │
│   └── api/v1/
│       ├── router.py             # agrega todas as rotas
│       └── endpoints/            # um arquivo por grupo de rotas (auth, services, barbers...)
│
├── frontend/                     # painel administrativo (HTML puro, sem build)
│   ├── login.html
│   ├── index.html
│   ├── css/style.css
│   └── js/{api.js, app.js}
│
├── migrations/                   # migrations do Alembic (versionamento do banco)
│   ├── env.py
│   └── versions/
│
├── scripts/
│   └── seed_demo_data.py         # cria dados de demonstração
│
├── tests/                        # testes automatizados (pytest)
│
├── .env.example                  # modelo de variáveis de ambiente (sem segredos reais)
├── .gitignore
├── .dockerignore
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
├── README.md
└── DOCUMENTACAO.md               # este arquivo
```

---

## 5. Instalação — passo a passo desde um computador limpo

Estes passos assumem que você está começando do zero, sem nada instalado.

1. **Instale o Git**: baixe em https://git-scm.com/downloads e siga o instalador padrão.
2. **Instale o Python 3.12 ou superior**: veja a seção [6. Python](#6-python).
3. **Baixe o projeto**: se você recebeu um `.zip`, extraia-o em uma pasta. Se estiver usando Git:
   ```bash
   git clone <url-do-seu-repositorio>
   cd barbearia-bot
   ```
4. **Crie o ambiente virtual** — veja a seção [7. Ambiente virtual](#7-ambiente-virtual).
5. **Instale as dependências** — veja a seção [8. Dependências](#8-dependências).
6. **Configure o `.env`** — veja a seção [10. Variáveis de ambiente](#10-variáveis-de-ambiente).
7. **Crie o banco de dados (rode as migrations)** — veja a seção [9. Banco de dados](#9-banco-de-dados).
8. **(Opcional) Crie dados de demonstração** para testar sem precisar cadastrar tudo manualmente:
   ```bash
   python -m scripts.seed_demo_data
   ```
9. **Rode o servidor** — veja a seção [11. Executar localmente](#11-executar-localmente).
10. **Acesse** `http://localhost:8000/docs` (API) e `http://localhost:8000/painel/login.html` (painel).

Nesse ponto o sistema já funciona **localmente**, sem WhatsApp real ainda (o bot "finge" que enviou a mensagem e registra isso nos logs, para você poder testar toda a lógica de agendamento antes de configurar a integração de verdade). Quando estiver pronto, siga a seção [17. Configuração na Meta](#17-configuração-na-meta-passo-a-passo) para ligar o WhatsApp de verdade.

---

## 6. Python

Baixe o instalador em https://www.python.org/downloads/ (versão 3.12 ou mais recente) e instale.

- **Windows**: marque a opção "Add Python to PATH" durante a instalação.
- **macOS**: você pode usar o instalador oficial ou `brew install python@3.12` (se tiver o Homebrew).
- **Linux**: normalmente já vem instalado; se não, use o gerenciador de pacotes da sua distribuição (ex.: `sudo apt install python3.12 python3.12-venv`).

Verifique a instalação:

```bash
python3 --version
```

---

## 7. Ambiente virtual

Um ambiente virtual isola as dependências deste projeto do resto do seu computador, evitando conflitos.

```bash
# dentro da pasta barbearia-bot
python3 -m venv .venv

# ativar (Linux/macOS)
source .venv/bin/activate

# ativar (Windows - PowerShell)
.venv\Scripts\Activate.ps1

# ativar (Windows - CMD)
.venv\Scripts\activate.bat
```

Quando o ambiente estiver ativo, o terminal mostrará `(.venv)` no início da linha. A partir daqui, todo `pip install` e `python` usado será isolado deste projeto. Para sair do ambiente, digite `deactivate`.

---

## 8. Dependências

Com o ambiente virtual ativo:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Isso instala o FastAPI, SQLAlchemy, Alembic, bibliotecas de autenticação, o driver do PostgreSQL, etc. — tudo o que está listado em `requirements.txt`.

---

## 9. Banco de dados

### Desenvolvimento (SQLite - recomendado para começar)

Não é necessário instalar nada: o `.env.example` já vem configurado com:

```
DATABASE_URL=sqlite:///./dev.db
```

O arquivo `dev.db` será criado automaticamente na primeira migration.

### Produção (PostgreSQL - recomendado)

1. Instale o PostgreSQL (https://www.postgresql.org/download/) ou use um serviço gerenciado (ex.: um provedor de nuvem com PostgreSQL como serviço).
2. Crie um banco e um usuário, por exemplo:
   ```sql
   CREATE DATABASE barbearia;
   CREATE USER barbearia WITH PASSWORD 'uma-senha-forte';
   GRANT ALL PRIVILEGES ON DATABASE barbearia TO barbearia;
   ```
3. Configure no `.env`:
   ```
   DATABASE_URL=postgresql+psycopg://barbearia:uma-senha-forte@localhost:5432/barbearia
   ```

### Criando/atualizando as tabelas (migrations com Alembic)

O projeto já vem com uma migration inicial pronta (`migrations/versions/`). Para aplicá-la:

```bash
alembic upgrade head
```

Sempre que você alterar um modelo em `app/models/`, gere uma nova migration e aplique:

```bash
alembic revision --autogenerate -m "descreva a mudança aqui"
alembic upgrade head
```

Para desfazer a última migration (rollback):

```bash
alembic downgrade -1
```

---

## 10. Variáveis de ambiente

Copie o modelo e edite:

```bash
cp .env.example .env
```

| Variável | Obrigatória? | Explicação |
|---|---|---|
| `APP_NAME` | Não | Nome exibido nos logs e na documentação da API. |
| `APP_ENV` | Não | `development`, `staging` ou `production` (apenas informativo/organizacional). |
| `APP_DEBUG` | Não | Liga/desliga detalhes extras de depuração. |
| `SECRET_KEY` | **Sim** | Chave usada para assinar os tokens JWT. Gere uma forte com `openssl rand -hex 32`. Nunca compartilhe nem reutilize entre ambientes. |
| `DATABASE_URL` | **Sim** | String de conexão do banco. Veja a seção 9. |
| `CORS_ORIGINS` | Não | Lista (separada por vírgula) de origens que podem chamar a API a partir do navegador. |
| `WHATSAPP_ACCESS_TOKEN` | Só para usar o WhatsApp de verdade | Token de acesso (System User) obtido no painel da Meta. |
| `WHATSAPP_PHONE_NUMBER_ID` | Só para usar o WhatsApp de verdade | ID do número de telefone cadastrado na Meta. |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | Só para usar o WhatsApp de verdade | ID da conta comercial do WhatsApp (WABA). |
| `WHATSAPP_VERIFY_TOKEN` | Só para usar o WhatsApp de verdade | Um valor que **você mesmo escolhe** (qualquer string forte) e usa para validar o webhook na Meta. |
| `WHATSAPP_APP_SECRET` | Recomendado | App Secret do app da Meta, usado para validar a assinatura das requisições do webhook. |
| `WHATSAPP_API_VERSION` | Não | Versão da Graph API (ex.: `v21.0`). Consulte a documentação oficial para saber a versão vigente. |
| `DEFAULT_TIMEZONE` | Não | Fuso horário padrão usado nos cálculos de agenda. |
| `LOG_LEVEL` / `LOG_JSON` | Não | Controlam o nível e o formato dos logs. |

**Nenhuma dessas variáveis deve ser colocada diretamente no código.** O arquivo `.env` nunca deve ser commitado no Git (ele já está no `.gitignore`).

---

## 11. Executar localmente

Com o ambiente virtual ativo, dependências instaladas, `.env` configurado e migrations aplicadas:

```bash
uvicorn app.main:app --reload
```

- `--reload` reinicia o servidor automaticamente a cada alteração de código (útil em desenvolvimento; **não use em produção**).
- Por padrão, a API sobe em `http://localhost:8000`.

Para rodar em outra porta:

```bash
uvicorn app.main:app --reload --port 8080
```

---

## 12. API

Todos os endpoints ficam sob o prefixo `/api/v1`. Principais grupos:

```text
GET    /api/v1/health                        Verifica se a API está no ar
POST   /api/v1/auth/login                    Login do painel (retorna token JWT)
POST   /api/v1/auth/change-password          Troca a senha do usuário logado

GET    /api/v1/customers                     Lista clientes (parâmetro ?search=)
GET    /api/v1/customers/{id}
PUT    /api/v1/customers/{id}
DELETE /api/v1/customers/{id}                Exclusão de dados (LGPD)

GET    /api/v1/services                      Lista serviços
POST   /api/v1/services
PUT    /api/v1/services/{id}
DELETE /api/v1/services/{id}                 Desativa (não apaga o histórico)

GET    /api/v1/barbers
POST   /api/v1/barbers
PUT    /api/v1/barbers/{id}
DELETE /api/v1/barbers/{id}

GET    /api/v1/appointments                  Lista agendamentos (filtros de data/status/barbeiro)
POST   /api/v1/appointments
PUT    /api/v1/appointments/{id}             Editar, reagendar ou mudar status
DELETE /api/v1/appointments/{id}             Cancela (parâmetro opcional ?reason=)
GET    /api/v1/appointments/availability/slots  Lista horários disponíveis

GET    /api/v1/whatsapp/webhook              Verificação do webhook (usado pela Meta)
POST   /api/v1/whatsapp/webhook              Recebe mensagens/eventos do WhatsApp
```

Todos os endpoints (exceto `health`, `auth/login` e o webhook) exigem um token JWT no cabeçalho:

```
Authorization: Bearer <seu-token>
```

---

## 13. Swagger (documentação interativa)

Com o servidor rodando, acesse:

```
http://localhost:8000/docs
```

Lá você pode ver todos os endpoints, seus parâmetros, e até testá-los diretamente pelo navegador (clique em "Authorize" e cole o token JWT obtido no login para testar rotas protegidas). Também existe uma versão alternativa em `/redoc`.

---

## 14. Painel administrativo

Acesse:

```
http://localhost:8000/painel/login.html
```

Se você rodou o script de dados de demonstração (`python -m scripts.seed_demo_data`), use:

- **E-mail**: `admin@barbearia.demo`
- **Senha**: `TrocarSenha123!`

⚠️ Essa senha é temporária e serve apenas para teste local. Troque-a assim que possível e nunca use esses dados em um ambiente de produção com clientes reais.

O painel possui as seções:

- **Dashboard**: resumo do dia (agendamentos, confirmados, cancelados, total de clientes).
- **Agenda**: lista os agendamentos por data, permitindo alterar o status (confirmar, concluir, cancelar, marcar não comparecimento).
- **Clientes**: lista e busca de clientes cadastrados.
- **Serviços**: criar, editar e desativar serviços.
- **Barbeiros**: criar, editar e desativar barbeiros, e escolher quais serviços cada um realiza.

---

## 15. WhatsApp — visão geral da integração

Este sistema usa exclusivamente a **WhatsApp Business Platform / Cloud API**, a solução oficial da Meta. Isso significa:

- Não há uso de WhatsApp Web, QR Code, Selenium, Puppeteer ou bibliotecas não oficiais.
- O envio de mensagens é feito via chamadas HTTPS para a **Graph API** da Meta (`https://graph.facebook.com/{versão}/{phone_number_id}/messages`).
- O recebimento de mensagens é feito via **webhook**: a Meta envia um `POST` para uma URL pública sua sempre que um cliente manda uma mensagem.

**Enquanto você não configurar as credenciais**, o sistema continua funcionando normalmente: o bot processa a lógica da conversa e "tentaria" enviar a resposta, mas como não há token configurado, ele apenas registra um aviso no log (`WhatsApp não configurado - mensagem NÃO enviada de verdade`) e a mensagem outbound fica salva no histórico (tabela `messages`), visível para fins de teste e depuração. Isso permite testar toda a lógica de agendamento antes de mexer na configuração da Meta.

### Limitações e custos (verifique sempre a documentação oficial, pois isso muda com frequência)

- A Meta cobra por conversa iniciada, com regras diferentes para conversas iniciadas pela empresa (marketing/utilidade/autenticação) e conversas iniciadas pelo cliente. Consulte a página oficial de preços: https://developers.facebook.com/docs/whatsapp/pricing
- Existe uma **janela de atendimento de 24 horas**: você só pode responder livremente com texto/mídia dentro de 24h a partir da última mensagem do cliente. Fora dessa janela, é obrigatório usar um **template pré-aprovado** (ver seção 18).
- Números novos passam por um processo de verificação/qualidade e têm limites de mensagens por dia que aumentam gradualmente.
- Consulte sempre a documentação oficial atualizada, pois a Meta altera essas regras com frequência: https://developers.facebook.com/docs/whatsapp

---

## 16. Webhook

O webhook é o endpoint que a Meta chama para entregar mensagens recebidas. Ele tem dois métodos:

- **`GET /api/v1/whatsapp/webhook`**: usado *apenas* durante a configuração, para a Meta verificar que a URL é sua. A Meta manda `hub.mode=subscribe`, `hub.verify_token=<seu token>` e `hub.challenge=<valor aleatório>`; o sistema confere se o `hub.verify_token` bate com `WHATSAPP_VERIFY_TOKEN` do seu `.env` e, se sim, responde com o valor de `hub.challenge`.
- **`POST /api/v1/whatsapp/webhook`**: usado para toda mensagem/evento real. O sistema valida a assinatura da requisição (cabeçalho `X-Hub-Signature-256`, calculado com o `WHATSAPP_APP_SECRET`) e repassa a mensagem para o motor de conversação.

**Importante**: para a Meta conseguir chamar seu webhook, ele precisa estar em uma **URL pública com HTTPS** (não funciona com `localhost`). Em desenvolvimento, use uma ferramenta de túnel (ex.: `ngrok http 8000`) para expor temporariamente seu servidor local com uma URL pública HTTPS, e use essa URL na configuração da Meta.

---

## 17. Configuração na Meta (passo a passo)

⚠️ As telas exatas do painel da Meta mudam com frequência — sempre confira a documentação oficial em https://developers.facebook.com/docs/whatsapp/cloud-api/get-started caso algo pareça diferente do descrito aqui.

1. **Crie uma conta de desenvolvedor Meta**: acesse https://developers.facebook.com e crie/entre com uma conta.
2. **Crie um aplicativo (App)**: no painel de apps (https://developers.facebook.com/apps), clique em "Criar app", escolha o tipo relacionado a negócios ("Business") e siga o assistente.
3. **Adicione o produto "WhatsApp"** ao seu app.
4. **Configuração inicial / número de teste**: a Meta disponibiliza um número de teste gratuito para você começar. Anote:
   - **Phone Number ID** → vai em `WHATSAPP_PHONE_NUMBER_ID`.
   - **WhatsApp Business Account ID (WABA ID)** → vai em `WHATSAPP_BUSINESS_ACCOUNT_ID`.
5. **Gere um token de acesso**:
   - Para testes rápidos, o painel oferece um token temporário (válido por 24h).
   - Para produção, crie um **System User** em Business Settings (Configurações do Negócio → Usuários do sistema), gere um **token permanente** com a permissão `whatsapp_business_messaging` (e `whatsapp_business_management` se for gerenciar templates/números por API), e use esse token → `WHATSAPP_ACCESS_TOKEN`.
6. **Encontre o App Secret**: em Configurações do App → Básico, copie a "Chave secreta do aplicativo" (App Secret) → `WHATSAPP_APP_SECRET`.
7. **Escolha um Verify Token**: invente uma string forte qualquer (ex.: gere com `openssl rand -hex 16`) e coloque em `WHATSAPP_VERIFY_TOKEN` no seu `.env`. Você vai digitar esse mesmo valor no painel da Meta no próximo passo.
8. **Configure o Webhook**:
   - No painel do produto WhatsApp do seu app, vá em "Configuration" → "Webhook".
   - Informe a **URL de callback**: `https://SEU_DOMINIO_PUBLICO/api/v1/whatsapp/webhook`.
   - Informe o **Verify Token**: o mesmo valor que você colocou em `WHATSAPP_VERIFY_TOKEN`.
   - Clique em "Verify and Save". Se tudo estiver certo, a Meta vai chamar o `GET` do seu webhook e validar.
   - Assine (subscribe) o campo **`messages`** para começar a receber mensagens.
9. **Teste o envio**: use o próprio painel da Meta (aba "API Setup"/"Test number") para mandar uma mensagem de teste para o seu número via `curl`, e confira se aparece no seu WhatsApp pessoal (número de destino precisa estar cadastrado como destinatário de teste, se você ainda estiver usando o número de teste gratuito).
10. **Teste o recebimento**: mande uma mensagem do seu celular para o número de teste. Se o webhook estiver corretamente configurado e sua aplicação estiver no ar, você verá o bot responder automaticamente.
11. **Verificação de negócio e número de produção**: para usar um número de telefone real da barbearia (em vez do número de teste) e enviar mensagens para qualquer pessoa (não só destinatários de teste cadastrados), você precisará passar pela verificação da empresa (Business Verification) e registrar/migrar o número. Siga o assistente da Meta para isso.

Depois de preencher `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN` (e idealmente `WHATSAPP_APP_SECRET`) no `.env`, reinicie a aplicação. O log de inicialização vai parar de mostrar o aviso "Credenciais do WhatsApp não configuradas".

---

## 18. Templates de mensagem

Fora da janela de 24 horas de atendimento (por exemplo, para lembretes enviados 24h antes de um agendamento, que a barbearia inicia por conta própria), a Meta **exige** o uso de um **template pré-aprovado**.

- Templates são criados e enviados para aprovação da Meta pelo **WhatsApp Manager** (https://business.facebook.com/wa/manage/) ou pela API de gerenciamento de templates.
- Cada template tem um **nome**, um **idioma** e pode ter variáveis (`{{1}}`, `{{2}}`, etc.).
- A aprovação normalmente leva de minutos a algumas horas, e pode ser recusada se o texto parecer promocional demais ou não seguir as políticas da Meta.
- No código, o envio de um template é feito pelo método `whatsapp_client.send_template(...)` (veja `app/services/whatsapp_client.py`), que já está implementado e pronto para uso assim que você tiver um template aprovado.
- **Não crie templates automaticamente pelo sistema** — isso deve ser feito manualmente no WhatsApp Manager, revisando o conteúdo antes de enviar para aprovação.

O sistema de lembretes automáticos (seção 14 do briefing original) está preparado no código (campo `reminder_sent_at` na tabela `appointments`), mas o **agendador** que dispara os lembretes periodicamente (ex.: um cron job ou tarefa agendada rodando a cada hora) precisa ser configurado por você conforme o ambiente de produção escolhido (por exemplo, `cron` do Linux chamando um script que consulta agendamentos das próximas 24h e envia o template de lembrete). Deixamos esse ponto de extensão claramente identificado em vez de simular um agendador que não estaria realmente rodando em produção.

---

## 19. Testes

O projeto usa `pytest`. Para rodar todos os testes:

```bash
pytest
```

Para rodar um arquivo específico:

```bash
pytest tests/test_appointments.py -v
```

Os testes cobrem: criação de cliente (novo e reaproveitado), criação de serviço e barbeiro, agendamento, conflito de horário, respeito à duração do serviço, cancelamento (e liberação do horário), reagendamento, dia fechado, horário bloqueado, autenticação e permissões (rotas protegidas), o handshake e o recebimento do webhook, e o fluxo completo de conversa do bot.

Os testes rodam contra um banco **SQLite em memória**, isolado do seu `dev.db` — é seguro rodá-los quantas vezes quiser.

---

## 20. Git e GitHub

Se você recebeu os arquivos fora de um repositório Git, inicialize um:

```bash
git init
git add .
git commit -m "Versão inicial do sistema"
```

Crie um repositório vazio no GitHub (via https://github.com/new) e conecte:

```bash
git remote add origin https://github.com/SEU_USUARIO/barbearia-bot.git
git branch -M main
git push -u origin main
```

O `.gitignore` já está configurado para nunca versionar o `.env`, o ambiente virtual, o banco SQLite local e outros arquivos sensíveis/temporários.

---

## 21. Deploy em produção

### Opção recomendada: Docker + docker-compose

1. Em um servidor Linux com Docker e Docker Compose instalados, copie o projeto para lá (via `git clone` ou upload).
2. Crie o arquivo `.env` de produção (não versionado) com valores reais: `SECRET_KEY` forte, `DATABASE_URL` (ou deixe o `docker-compose.yml` apontar para o serviço `db`), credenciais reais do WhatsApp, etc.
3. Suba os containers:
   ```bash
   docker compose up -d --build
   ```
   Isso sobe o PostgreSQL e a API (a API já roda `alembic upgrade head` automaticamente antes de iniciar, conforme definido no `Dockerfile`).
4. Confirme que está no ar:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```
5. Configure um **proxy reverso com HTTPS** na frente da aplicação (ver seção 22) e aponte seu domínio para o servidor.
6. Configure o webhook da Meta apontando para `https://seu-dominio.com/api/v1/whatsapp/webhook` (ver seção 17).

### Sem Docker (deploy manual)

1. Instale Python 3.12+, PostgreSQL e um servidor de aplicação (ex.: `gunicorn` com workers `uvicorn`, ou apenas `uvicorn` gerenciado por `systemd`).
2. Clone o projeto, crie o ambiente virtual, instale dependências (`pip install -r requirements.txt`), configure o `.env` e rode `alembic upgrade head`.
3. Rode a aplicação de forma persistente, por exemplo com `systemd` (crie um serviço que executa `uvicorn app.main:app --host 0.0.0.0 --port 8000`) ou com `gunicorn -k uvicorn.workers.UvicornWorker app.main:app`.
4. Configure HTTPS (seção 22) na frente do serviço.

### Reinicialização

- Com Docker: `docker compose restart api`
- Com `systemd`: `sudo systemctl restart barbearia-bot` (nome do serviço que você criar)

---

## 22. HTTPS

O webhook da Meta **exige HTTPS** — não funciona com HTTP puro nem com `localhost`. Formas comuns de obter isso em produção:

- Usar um proxy reverso como **Nginx** ou **Caddy** na frente da aplicação, com certificado gratuito via **Let's Encrypt** (o Caddy faz isso automaticamente; com Nginx, use `certbot`).
- Usar um provedor de nuvem que já oferece HTTPS gerenciado na borda (load balancer com certificado).

Exemplo simplificado de bloco Nginx (adapte ao seu domínio e caminhos de certificado):

```nginx
server {
    listen 443 ssl;
    server_name seu-dominio.com;

    ssl_certificate     /etc/letsencrypt/live/seu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Em desenvolvimento, para testar o webhook sem precisar de um domínio/certificado próprio, use um túnel como `ngrok` (`ngrok http 8000`), que já fornece uma URL HTTPS pública temporária.

---

## 23. Banco de dados em produção

- Use sempre **PostgreSQL** em produção (não SQLite, que não é adequado para múltiplos acessos simultâneos).
- Prefira um serviço gerenciado (backup automático, alta disponibilidade) quando possível.
- Nunca exponha a porta do banco (5432) publicamente na internet; mantenha-a acessível apenas pela rede interna/privada onde a aplicação roda (no `docker-compose.yml` fornecido, remova o mapeamento de porta `5432:5432` em produção se não precisar acessar o banco de fora do servidor).
- Configure `DATABASE_URL` com uma senha forte, diferente da usada em desenvolvimento.

---

## 24. Backup

- **PostgreSQL**: use `pg_dump` periodicamente:
  ```bash
  pg_dump -U barbearia -h localhost barbearia > backup_$(date +%Y%m%d_%H%M%S).sql
  ```
  Automatize isso com uma tarefa agendada (`cron`) e armazene os backups em um local separado do servidor de produção (ex.: outro servidor, um serviço de armazenamento em nuvem).
- **Restauração**:
  ```bash
  psql -U barbearia -h localhost barbearia < backup_20260101_030000.sql
  ```
- Teste periodicamente se seus backups realmente restauram corretamente — um backup nunca testado não é confiável.
- Com Docker, você também pode fazer backup do volume nomeado `barbearia_pgdata` diretamente, mas o `pg_dump` lógico é mais portável entre versões do PostgreSQL.

---

## 25. Logs

Os logs são escritos em **stdout** (saída padrão do processo), seguindo o formato configurado em `app/core/logging.py`. Isso significa:

- **Localmente**: aparecem diretamente no terminal onde você rodou `uvicorn`.
- **Com Docker**: veja com `docker compose logs -f api`.
- **Com systemd**: veja com `journalctl -u barbearia-bot -f`.

Informações importantes registradas: inicialização da aplicação, se o WhatsApp está configurado, cada requisição HTTP, erros não tratados, eventos de webhook mal formados ou com assinatura inválida, e falhas ao enviar mensagens. Um filtro (`SensitiveDataFilter`) evita vazar tokens/senhas nos logs, mas ainda assim evite logar dados sensíveis manualmente ao modificar o código.

---

## 26. Solução de problemas comuns

| Sintoma | Possível causa / solução |
|---|---|
| `ModuleNotFoundError` ao rodar `uvicorn` | Ambiente virtual não está ativado, ou `pip install -r requirements.txt` não foi executado. |
| Erro `SECRET_KEY` obrigatório / aplicação não sobe | Falta configurar `SECRET_KEY` no `.env`. |
| Login sempre retorna 401 | Confira se o usuário existe no banco (rode o seed ou crie um usuário manualmente) e se a senha está correta. |
| Webhook da Meta não verifica (`Verify and Save` falha) | Confirme que `WHATSAPP_VERIFY_TOKEN` no `.env` é **exatamente** igual ao valor digitado no painel da Meta, e que a URL está acessível publicamente via HTTPS (teste com `curl` de outra máquina). |
| Mensagens não chegam no bot | Verifique se você assinou o campo `messages` no webhook, se a URL de callback está correta e se o servidor está de fato no ar e acessível externamente. |
| Bot não envia respostas de verdade | Verifique se `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` e `WHATSAPP_VERIFY_TOKEN` estão preenchidos; sem eles, o sistema roda em "modo simulado" (ver seção 15). |
| Erro 403 no webhook em produção | Provavelmente a assinatura `X-Hub-Signature-256` não bateu — confirme que `WHATSAPP_APP_SECRET` está correto. |
| `alembic revision --autogenerate` não detecta mudanças | Confirme que o novo modelo está importado em `app/models/__init__.py`. |
| Erro de conexão com PostgreSQL | Confira usuário/senha/host/porta em `DATABASE_URL` e se o serviço do PostgreSQL está no ar (`docker compose ps`). |
| Horários não aparecem na consulta de disponibilidade | Confirme se há `BusinessHours`/`BarberHours` cadastrados para aquele dia da semana e se o barbeiro está vinculado ao serviço escolhido. |

---

## 27. Segurança

Práticas já implementadas no projeto:

- Segredos exclusivamente via variáveis de ambiente (`.env`), nunca no código.
- Senhas de usuários do painel armazenadas com hash **bcrypt** (nunca em texto puro).
- Autenticação via **JWT** com expiração configurável, exigida em todas as rotas administrativas.
- Validação de assinatura (`X-Hub-Signature-256`) das requisições recebidas no webhook do WhatsApp.
- Validação de todos os dados de entrada da API via Pydantic (schemas).
- CORS restrito às origens configuradas em `CORS_ORIGINS`.
- Tratamento de erros que nunca expõe stack trace, mensagens de erro do banco, tokens ou detalhes internos ao cliente final — apenas mensagens genéricas amigáveis (os detalhes completos vão para o log do servidor).
- `.gitignore` e `.dockerignore` configurados para nunca incluir segredos, banco local ou ambiente virtual no controle de versão / imagem Docker.

Recomendações adicionais para produção:

- Use HTTPS em todo o tráfego (seção 22).
- Troque a senha do usuário administrativo de demonstração assim que possível.
- Considere adicionar *rate limiting* (ex.: via proxy reverso ou um middleware dedicado) em rotas sensíveis como `/auth/login`, para dificultar ataques de força bruta.
- Restrinja o acesso à porta do banco de dados apenas à rede interna (seção 23).
- Mantenha as dependências atualizadas (`pip list --outdated`) e acompanhe avisos de segurança do FastAPI/SQLAlchemy/Alembic.
- Faça backups regulares e teste a restauração (seção 24).

---

## 28. LGPD

O sistema armazena dados pessoais de clientes (nome e telefone) e mensagens trocadas via WhatsApp. Alguns cuidados já incorporados:

- **Minimização de dados**: o sistema não pede informações que a própria API do WhatsApp já fornece (como nome de perfil e telefone) e não coleta dados desnecessários (ex.: não pede CPF, e-mail, endereço do cliente).
- **Consulta**: o painel permite consultar todo o histórico de um cliente (agendamentos, mensagens) — ponto de partida para atender pedidos de acesso aos dados.
- **Exclusão**: o endpoint `DELETE /api/v1/customers/{id}` remove o cadastro do cliente e seu histórico de mensagens, atendendo a pedidos de exclusão. Agendamentos já registrados são mantidos para fins contábeis/fiscais/históricos da barbearia, mas o vínculo direto pode ser revisado conforme a política de retenção que a barbearia definir.
- **Controle de acesso**: apenas usuários autenticados do painel (donos/gerentes/atendentes) acessam os dados de clientes; o cliente final só interage via WhatsApp, sem acesso direto ao banco.
- **Consentimento**: existe um campo `consent_given` na tabela de clientes, pensado para registrar consentimento explícito caso a barbearia deseje implementar uma etapa de aceite (por exemplo, uma mensagem inicial perguntando se o cliente concorda com o uso do WhatsApp para agendamentos e lembretes).

**Importante**: este documento não constitui aconselhamento jurídico. Consulte um profissional especializado em LGPD para revisar a política de privacidade e o tratamento de dados adequado ao seu caso específico, especialmente antes de operar com dados reais de clientes em produção.

---

## 29. Manutenção

- **Atualizando dependências**: revise `requirements.txt` periodicamente (`pip list --outdated`), atualize com cuidado (uma dependência por vez, rodando os testes depois) e sempre rode `pytest` após qualquer atualização.
- **Aplicando mudanças no banco**: sempre que alterar um modelo, gere e aplique uma migration (`alembic revision --autogenerate` + `alembic upgrade head`) em vez de editar o banco manualmente.
- **Monitorando o WhatsApp**: fique de olho no painel de qualidade do número (WhatsApp Manager) — mensagens muito reportadas como spam podem reduzir seus limites de envio.
- **Rotina recomendada**: antes de subir uma nova versão em produção, rode os testes automatizados (`pytest`), teste manualmente o fluxo principal (agendar, cancelar, reagendar) em um ambiente de homologação, e só depois faça o deploy.

---

## 30. Expansão para SaaS (multi-tenant)

O modelo de dados já foi desenhado para suportar múltiplas barbearias (tabela `barbershops` como "tenant raiz", e toda entidade de negócio — clientes, barbeiros, serviços, agendamentos, horários — referenciando `barbershop_id`). Para transformar isso em um produto SaaS completo, os principais passos seriam:

1. **Cadastro de novas barbearias**: criar um fluxo (via painel ou API) para criar uma nova `Barbershop` e seu primeiro usuário administrador (hoje isso é feito via `scripts/seed_demo_data.py`, pensado apenas para demonstração).
2. **Vincular cada barbearia a um número de WhatsApp próprio**: hoje o sistema assume um único número de WhatsApp (via `WHATSAPP_PHONE_NUMBER_ID` no `.env`). Para múltiplas barbearias com números diferentes, adicione uma coluna `whatsapp_phone_number_id` (e, se necessário, um token próprio) na tabela `barbershops`, e ajuste `app/api/v1/endpoints/whatsapp.py` (função `_resolve_barbershop`) para buscar a barbearia certa a partir do `phone_number_id` recebido no webhook, em vez de assumir uma única barbearia ativa.
3. **Cobrança/planos**: adicionar um módulo de assinatura (ex.: integração com um gateway de pagamento) e regras de limite por plano.
4. **Isolamento e testes de segurança entre tenants**: garantir, com testes automatizados, que nenhuma consulta da API retorne dados de uma barbearia diferente da do usuário autenticado (o padrão atual já filtra tudo por `barbershop_id` a partir do usuário logado, via `get_current_barbershop` em `app/deps.py` — mantenha esse padrão em qualquer novo endpoint).
5. **Onboarding**: um fluxo guiado para o dono de uma nova barbearia cadastrar serviços, barbeiros e horários de funcionamento pela primeira vez.

O objetivo desta primeira versão foi manter a base **correta e simples** (uma barbearia por instalação, mas com a coluna `barbershop_id` em tudo desde o início) para que essa evolução para múltiplos tenants não exija reescrever o modelo de dados — apenas adicionar as camadas de cadastro, roteamento por número e cobrança acima do que já existe.

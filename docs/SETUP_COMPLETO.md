# ✅ Setup Completo - Starke

## 🎉 Sistema Implementado com Sucesso!

Todas as melhorias foram implementadas e o sistema está pronto para uso.

---

## 📊 **Status Atual**

### ✅ Concluído

1. **Banco de Dados PostgreSQL** - Inicializado e funcionando
2. **Tabelas Criadas:**
   - `users` - Usuários do sistema
   - `email_recipients` - Destinatários de email
   - (Todas as tabelas anteriores: runs, raw_payloads, cash_in, cash_out, balance, portfolio_stats)

3. **Usuário Admin Criado:**
   - Email: `admin@starke.com`
   - Senha: `admin123`
   - ID: 2
   - Tipo: Superusuário (Admin)

4. **JWT Secret Configurado:**
   - Chave segura gerada e adicionada ao `.env`

5. **Google Sheets Removido:**
   - Código removido
   - Dependências removidas
   - Configurações removidas

---

## 🚀 **Como Iniciar o Sistema**

### Opção 1: Via Poetry (Recomendado)

```bash
# Instalar dependências
poetry install

# Iniciar servidor web
poetry run starke serve --reload
```

### Opção 2: Via Python Direto

```bash
# Definir PYTHONPATH
export PYTHONPATH=/Users/fernandoferreira/Documents/projetos/atlas/starke/src:$PYTHONPATH

# Iniciar servidor
python3 -m uvicorn starke.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Opção 3: Via CLI Starke

```bash
# Configurar PYTHONPATH
export PYTHONPATH=/Users/fernandoferreira/Documents/projetos/atlas/starke/src:$PYTHONPATH

# Iniciar via CLI
python3 -m starke.cli serve --reload
```

---

## 🌐 **Acessar Interface Web**

Depois de iniciar o servidor:

```
🌐 Frontend: http://localhost:8000
📖 API Docs: http://localhost:8000/docs
```

---

## 🔐 **Credenciais de Acesso**

```
Email: admin@starke.com
Senha: admin123
```

⚠️ **IMPORTANTE:** Troque essa senha após o primeiro login!

---

## 📋 **Funcionalidades Disponíveis**

### Interface Web (`http://localhost:8000`)

1. **Login** (`/login`)
   - Autenticação com email/senha
   - Sessão segura

2. **Dashboard** (`/dashboard`)
   - Total de usuários
   - Total de destinatários
   - Destinatários ativos
   - Ações rápidas

3. **Gerenciar Usuários** (`/users`) - **Admin Only**
   - Criar novos usuários
   - Ver lista de usuários
   - Deletar usuários
   - Ver tipo (Admin/Usuário)

4. **Gerenciar Destinatários** (`/recipients`)
   - Criar destinatários
   - Filtrar por status (Ativo/Inativo/Todos)
   - Ativar/Desativar
   - Deletar
   - Definir empreendimento específico ou global

### API REST (`http://localhost:8000/docs`)

#### Autenticação
- `POST /api/auth/login` - Login
- `POST /api/auth/users` - Criar usuário (admin)
- `GET /api/auth/users` - Listar usuários (admin)
- `GET /api/auth/users/{id}` - Ver usuário (admin)
- `PUT /api/auth/users/{id}` - Atualizar usuário (admin)
- `DELETE /api/auth/users/{id}` - Deletar usuário (admin)

#### Destinatários
- `POST /api/email-recipients` - Criar destinatário
- `GET /api/email-recipients` - Listar destinatários
- `GET /api/email-recipients/{id}` - Ver destinatário
- `PUT /api/email-recipients/{id}` - Atualizar destinatário
- `DELETE /api/email-recipients/{id}` - Deletar destinatário
- `POST /api/email-recipients/{id}/activate` - Ativar
- `POST /api/email-recipients/{id}/deactivate` - Desativar

### CLI Commands

```bash
# Usuários
python3 -m starke.cli create-user              # Criar usuário
python3 -m starke.cli create-user --superuser  # Criar admin
python3 -m starke.cli list-users               # Listar usuários

# API Server
python3 -m starke.cli serve                    # Iniciar servidor
python3 -m starke.cli serve --reload           # Modo desenvolvimento
python3 -m starke.cli serve --port 8080        # Porta customizada

# Workflow (existentes)
python3 -m starke.cli run                      # Executar relatórios
python3 -m starke.cli init                     # Inicializar DB
python3 -m starke.cli test-email               # Testar email
python3 -m starke.cli config                   # Ver configuração
```

---

## 🔧 **Configuração Atual (`.env`)**

### Banco de Dados
```
DATABASE_URL=postgresql://cxggichesjlqkw:***@66.94.104.117:5432/starke
```

### Email (SMTP)
```
EMAIL_BACKEND=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=brainitsolutionscwb@gmail.com
SMTP_PASSWORD=***
EMAIL_FROM_NAME=Relatórios Starke
EMAIL_FROM_ADDRESS=brainitsolutionscwb@gmail.com
```

### Autenticação
```
JWT_SECRET_KEY=f93be062ffc55d09442653e6ce3803def20aacb5e129b7beb1e5dd1e01282650
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Teste
```
TEST_MODE=true
TEST_EMAIL_RECIPIENT=fernando.ferreira@brainitsolutions.com.br
```

---

## 📝 **Próximos Passos**

### 1. Fazer Login

```bash
# 1. Iniciar servidor
python3 -m starke.cli serve --reload

# 2. Abrir navegador
open http://localhost:8000

# 3. Fazer login
Email: admin@starke.com
Senha: admin123
```

### 2. Adicionar Destinatários

No frontend (`/recipients`):
1. Clicar em "Novo Destinatário"
2. Preencher:
   - Nome: Ex: "João Silva"
   - Email: Ex: "joao@example.com"
   - Empreendimento ID: (deixar vazio para global ou especificar um ID)
   - Status: Marcar "Ativo"
3. Clicar em "Adicionar"

### 3. Testar Envio de Email

```bash
# Com destinatários cadastrados
python3 -m starke.cli test-email

# Executar workflow completo (modo de teste)
python3 -m starke.cli run --dry-run
```

### 4. Criar Mais Usuários (Opcional)

Via web (`/users`):
1. Fazer login como admin
2. Ir para "Usuários"
3. Clicar em "Novo Usuário"
4. Definir email, senha e tipo (Admin ou Usuário)

---

## 🗂️ **Estrutura do Projeto**

```
starke/
├── src/starke/
│   ├── api/
│   │   ├── main.py                  # FastAPI app
│   │   ├── schemas.py               # Pydantic schemas
│   │   ├── dependencies/            # Auth & DB dependencies
│   │   └── routes/
│   │       ├── auth.py              # Rotas de autenticação
│   │       ├── email_recipients.py  # Rotas de destinatários
│   │       └── web.py               # Rotas web (HTML)
│   │
│   ├── domain/
│   │   └── services/
│   │       ├── auth_service.py               # Serviço de autenticação
│   │       └── email_recipient_service.py    # Serviço de destinatários
│   │
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── models.py            # Models SQLAlchemy
│   │   │   └── base.py              # DB connection
│   │   ├── email/
│   │   │   └── email_service.py     # Envio de emails
│   │   └── external_apis/
│   │       └── mega_client.py       # Cliente Mega API
│   │
│   ├── presentation/
│   │   └── web/
│   │       └── templates/
│   │           ├── base.html         # Layout base
│   │           ├── login.html        # Login
│   │           ├── dashboard.html    # Dashboard
│   │           ├── users.html        # Gerenciar usuários
│   │           ├── recipients.html   # Gerenciar destinatários
│   │           └── partials/         # Fragmentos HTML
│   │
│   ├── core/
│   │   ├── config.py                # Configurações
│   │   ├── logging.py               # Logging
│   │   └── orchestrator.py          # Orquestrador principal
│   │
│   └── cli.py                       # CLI commands
│
├── alembic/                         # Migrations
├── .env                             # Configuração
├── pyproject.toml                   # Dependências
├── AUTHENTICATION_GUIDE.md          # Guia de autenticação
├── FRONTEND_GUIDE.md                # Guia do frontend
└── SETUP_COMPLETO.md                # Este arquivo
```

---

## 🛠️ **Solução de Problemas**

### Erro: "Module not found"

```bash
# Configurar PYTHONPATH
export PYTHONPATH=/Users/fernandoferreira/Documents/projetos/atlas/starke/src:$PYTHONPATH
```

### Erro: "Database connection failed"

Verifique se o PostgreSQL está acessível:
```bash
psql postgresql://cxggichesjlqkw:***@66.94.104.117:5432/starke
```

### Erro: "Session expired"

Faça login novamente. A sessão expira após 30 minutos.

### Erro ao criar usuário via CLI

Use o script Python direto ou crie via interface web.

---

## 📦 **Dependências Principais**

```toml
# Backend
fastapi = "^0.115"
uvicorn = "^0.32"
sqlalchemy = "^2.0"
alembic = "^1.13"
psycopg2-binary = "^2.9"

# Autenticação
python-jose = "^3.3"         # JWT
passlib = "^1.7"             # Password hashing
itsdangerous = "^2.1"        # Session tokens

# Email
aiosmtplib = "^3.0"

# API & HTTP
httpx = "^0.27"
python-multipart = "^0.0.9"

# Frontend
jinja2 = "^3.1"              # Templates

# Configuração
pydantic = "^2.0"
pydantic-settings = "^2.0"
```

---

## 📚 **Documentação**

1. **`AUTHENTICATION_GUIDE.md`** - Guia completo de autenticação e API REST
2. **`FRONTEND_GUIDE.md`** - Guia do frontend web (templates, rotas, HTMX)
3. **`SETUP_COMPLETO.md`** - Este arquivo (setup e credenciais)

---

## 🎯 **Resumo**

✅ **Banco de dados:** PostgreSQL configurado e inicializado
✅ **Usuário admin:** `admin@starke.com` / `admin123`
✅ **Frontend web:** Completo com login, dashboard, CRUD
✅ **API REST:** Documentada em `/docs`
✅ **Google Sheets:** Removido completamente
✅ **Autenticação:** JWT + Sessions implementado
✅ **Destinatários:** Gerenciados via banco de dados

---

## 🚀 **Comando Rápido para Iniciar**

```bash
# Configurar PYTHONPATH
export PYTHONPATH=/Users/fernandoferreira/Documents/projetos/atlas/starke/src:$PYTHONPATH

# Iniciar servidor
python3 -m starke.cli serve --reload

# Acessar
open http://localhost:8000
```

**Login:** `admin@starke.com` / `admin123`

---

🎉 **Pronto para usar!**

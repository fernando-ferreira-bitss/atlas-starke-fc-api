# DOCUMENTAÇÃO TÉCNICA - SISTEMA STARKE CONSOLID
## Especificação para Desenvolvimento

---

## 📋 ÍNDICE

1. [Visão Geral do Projeto](#1-visão-geral-do-projeto)
2. [Arquitetura do Sistema](#2-arquitetura-do-sistema)
3. [Stack Tecnológico](#3-stack-tecnológico)
4. [Estrutura de Banco de Dados](#4-estrutura-de-banco-de-dados)
5. [Módulos Backend](#5-módulos-backend)
6. [Módulos Frontend](#6-módulos-frontend)
7. [Autenticação e Segurança](#7-autenticação-e-segurança)
8. [Integrações](#8-integrações)
9. [Tarefas de Desenvolvimento](#9-tarefas-de-desenvolvimento)
10. [Testes e Qualidade](#10-testes-e-qualidade)
11. [Deploy e Infraestrutura](#11-deploy-e-infraestrutura)

---

## 1. VISÃO GERAL DO PROJETO

### 1.1 Objetivo
Desenvolver plataforma web para gestão e controle patrimonial de clientes (PF, PJ, Família, Empresa) com conformidade LGPD, integrada ao sistema de fluxo de caixa existente.

### 1.2 Perfis de Usuário
- **Admin**: Acesso total ao sistema
- **RM (Relationship Manager)**: Gestão dos clientes atribuídos
- **Analista**: Acesso de leitura
- **Cliente**: Visualização do próprio patrimônio

### 1.3 Funcionalidades Principais
- Gestão de clientes, ativos e passivos
- Importação de planilhas com posições mensais
- Visualização de dashboards e relatórios
- Geração de PDF
- Upload e gestão de documentos
- Integração com sistema de fluxo de caixa

---

## 2. ARQUITETURA DO SISTEMA

### 2.1 Arquitetura Geral
```
┌─────────────────┐
│   React App     │ (Frontend - PWA)
│   (TypeScript)  │
└────────┬────────┘
         │ HTTP/HTTPS
         │ REST API
┌────────▼────────┐
│   FastAPI       │ (Backend - Python)
│   Application   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──┐
│ PostgreSQL│ │Redis│
│  Database │ │Cache│
└───────────┘ └─────┘
         │
    ┌────▼────┐
    │  AWS S3 │ (Armazenamento de arquivos)
    └─────────┘
```

### 2.2 Padrões Arquiteturais
- **Backend**: Clean Architecture com camadas (API → Service → Repository)
- **Frontend**: Component-based architecture com React
- **API**: RESTful com versionamento (v1)
- **State Management**: Context API ou Zustand

---

## 3. STACK TECNOLÓGICO

### 3.1 Backend
```yaml
Linguagem: Python 3.11+
Framework: FastAPI
ORM: SQLAlchemy
Validação: Pydantic
Autenticação: JWT (python-jose)
Criptografia: cryptography, passlib
Migrações: Alembic
Task Queue: Celery (opcional para processamento assíncrono)
```

**Bibliotecas Principais:**
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
pydantic==2.5.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pandas==2.1.4
openpyxl==3.1.2
boto3==1.34.18
redis==5.0.1
```

### 3.2 Frontend
```yaml
Linguagem: TypeScript
Framework: React 18+
Build Tool: Vite
UI Library: Material-UI (MUI) v5
Charts: Recharts
HTTP Client: Axios
State Management: Zustand ou Context API
Forms: React Hook Form + Zod
Routing: React Router v6
```

**Bibliotecas Principais:**
```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "typescript": "^5.3.3",
  "@mui/material": "^5.15.0",
  "@mui/icons-material": "^5.15.0",
  "recharts": "^2.10.3",
  "axios": "^1.6.5",
  "react-router-dom": "^6.21.1",
  "react-hook-form": "^7.49.3",
  "zod": "^3.22.4",
  "zustand": "^4.4.7",
  "date-fns": "^3.0.6"
}
```

### 3.3 Banco de Dados
- **Principal**: PostgreSQL 15+
- **Cache**: Redis 7+
- **Storage**: AWS S3 (documentos e arquivos)

### 3.4 DevOps
- **Containerização**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoramento**: Sentry (erros) + CloudWatch (logs)

---

## 4. ESTRUTURA DE BANCO DE DADOS

### 4.1 Diagrama ER (Simplificado)

```
┌──────────────┐       ┌──────────────┐
│    users     │──────┐│   clients    │
├──────────────┤      │├──────────────┤
│ id (PK)      │      ││ id (PK)      │
│ email        │      ││ name         │
│ password_hash│      ││ type         │◄──┐
│ role         │      ││ cpf_cnpj     │   │
│ created_at   │      ││ user_id (FK) │   │
└──────────────┘      │└──────────────┘   │
                      │        │           │
                      │   ┌────┴────┐      │
                      │   │         │      │
                      │┌──▼───────┐ │      │
                      ││accounts  │ │      │
                      │├──────────┤ │      │
                      ││id (PK)   │ │      │
                      ││client_id │ │      │
                      ││institution│ │     │
                      ││type      │ │      │
                      │└──────────┘ │      │
                      │             │      │
                      │ ┌───────────▼──┐   │
                      │ │   assets     │   │
                      │ ├──────────────┤   │
                      │ │ id (PK)      │   │
                      │ │ client_id(FK)│───┘
                      │ │ category     │
                      │ │ name         │
                      │ │ base_value   │
                      │ │ current_value│
                      │ │ base_date    │
                      │ └──────────────┘
                      │
                      │ ┌──────────────┐
                      │ │ liabilities  │
                      │ ├──────────────┤
                      │ │ id (PK)      │
                      └─┤ client_id(FK)│
                        │ description  │
                        │ institution  │
                        │ amount       │
                        └──────────────┘
```

### 4.2 Tabelas Principais

#### **users**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'admin', 'rm', 'analyst', 'client'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

#### **clients**
```sql
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'pf', 'pj', 'family', 'company'
    cpf_cnpj VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    rm_user_id UUID REFERENCES users(id), -- Relationship Manager
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'pending'
    base_currency VARCHAR(3) DEFAULT 'BRL',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_clients_cpf_cnpj ON clients(cpf_cnpj);
CREATE INDEX idx_clients_rm_user_id ON clients(rm_user_id);
CREATE INDEX idx_clients_status ON clients(status);
```

#### **institutions**
```sql
CREATE TABLE institutions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    type VARCHAR(50), -- 'bank', 'broker', 'insurance', 'other'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_institutions_name ON institutions(name);
```

#### **accounts**
```sql
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    institution_id UUID REFERENCES institutions(id),
    account_type VARCHAR(50), -- 'checking', 'savings', 'investment', 'brokerage'
    account_number VARCHAR(50),
    currency VARCHAR(3) DEFAULT 'BRL',
    base_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_accounts_client_id ON accounts(client_id);
CREATE INDEX idx_accounts_institution_id ON accounts(institution_id);
```

#### **assets**
```sql
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    category VARCHAR(50) NOT NULL, -- 'fixed_income', 'variable_income', 'real_estate', 'participations', 'alternatives', 'cash'
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_value DECIMAL(18, 2),
    current_value DECIMAL(18, 2),
    base_date DATE,
    base_year INTEGER,
    currency VARCHAR(3) DEFAULT 'BRL',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_assets_client_id ON assets(client_id);
CREATE INDEX idx_assets_category ON assets(category);
CREATE INDEX idx_assets_account_id ON assets(account_id);
```

#### **liabilities**
```sql
CREATE TABLE liabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    description VARCHAR(255) NOT NULL,
    institution_id UUID REFERENCES institutions(id),
    amount DECIMAL(18, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'BRL',
    liability_type VARCHAR(50), -- 'mortgage', 'credit_card', 'loan', 'other'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_liabilities_client_id ON liabilities(client_id);
```

#### **monthly_positions**
```sql
CREATE TABLE monthly_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    reference_date DATE NOT NULL,
    value DECIMAL(18, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'BRL',
    source VARCHAR(50) DEFAULT 'manual', -- 'manual', 'spreadsheet', 'api'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_monthly_positions_client_id ON monthly_positions(client_id);
CREATE INDEX idx_monthly_positions_asset_id ON monthly_positions(asset_id);
CREATE INDEX idx_monthly_positions_reference_date ON monthly_positions(reference_date);
CREATE UNIQUE INDEX idx_monthly_positions_unique ON monthly_positions(asset_id, reference_date);
```

#### **documents**
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    asset_id UUID REFERENCES assets(id) ON DELETE SET NULL,
    document_type VARCHAR(50), -- 'contract', 'report', 'statement', 'certificate', 'other'
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL, -- S3 path
    file_size INTEGER,
    mime_type VARCHAR(100),
    uploaded_by UUID REFERENCES users(id),
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_client_id ON documents(client_id);
CREATE INDEX idx_documents_document_type ON documents(document_type);
```

#### **import_logs**
```sql
CREATE TABLE import_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    file_name VARCHAR(255),
    file_path VARCHAR(500),
    status VARCHAR(50), -- 'pending', 'processing', 'success', 'failed'
    records_processed INTEGER DEFAULT 0,
    records_success INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_log TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_import_logs_user_id ON import_logs(user_id);
CREATE INDEX idx_import_logs_status ON import_logs(status);
```

#### **audit_logs**
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL, -- 'create', 'read', 'update', 'delete', 'login', 'logout'
    entity_type VARCHAR(100), -- 'client', 'asset', 'document', etc.
    entity_id UUID,
    ip_address VARCHAR(50),
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_entity_type ON audit_logs(entity_type);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

---

## 5. MÓDULOS BACKEND

### 5.1 Estrutura de Diretórios
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Configurações
│   ├── database.py             # Database connection
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── client.py
│   │   ├── asset.py
│   │   ├── liability.py
│   │   ├── account.py
│   │   ├── document.py
│   │   └── audit.py
│   │
│   ├── schemas/                # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── client.py
│   │   ├── asset.py
│   │   ├── liability.py
│   │   └── common.py
│   │
│   ├── api/                    # API routes
│   │   ├── __init__.py
│   │   ├── deps.py            # Dependencies
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── clients.py
│   │   │   ├── assets.py
│   │   │   ├── liabilities.py
│   │   │   ├── accounts.py
│   │   │   ├── documents.py
│   │   │   ├── positions.py
│   │   │   ├── dashboard.py
│   │   │   └── reports.py
│   │
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── client_service.py
│   │   ├── asset_service.py
│   │   ├── import_service.py
│   │   ├── document_service.py
│   │   ├── pdf_service.py
│   │   └── calculation_service.py
│   │
│   ├── repositories/          # Data access
│   │   ├── __init__.py
│   │   ├── user_repository.py
│   │   ├── client_repository.py
│   │   ├── asset_repository.py
│   │   └── document_repository.py
│   │
│   ├── core/                  # Core utilities
│   │   ├── __init__.py
│   │   ├── security.py       # Auth & encryption
│   │   ├── config.py         # Settings
│   │   └── exceptions.py     # Custom exceptions
│   │
│   └── utils/                 # Utilities
│       ├── __init__.py
│       ├── validators.py
│       ├── formatters.py
│       └── s3.py
│
├── alembic/                   # Database migrations
│   ├── versions/
│   └── env.py
│
├── tests/                     # Unit tests
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### 5.2 Endpoints da API

#### **Autenticação**
```
POST   /api/v1/auth/login          # Login
POST   /api/v1/auth/logout         # Logout
POST   /api/v1/auth/refresh        # Refresh token
POST   /api/v1/auth/reset-password # Solicitar reset
POST   /api/v1/auth/change-password # Alterar senha
```

#### **Usuários**
```
GET    /api/v1/users              # Listar usuários
POST   /api/v1/users              # Criar usuário
GET    /api/v1/users/{id}         # Obter usuário
PUT    /api/v1/users/{id}         # Atualizar usuário
DELETE /api/v1/users/{id}         # Deletar usuário
GET    /api/v1/users/me           # Usuário logado
```

#### **Clientes**
```
GET    /api/v1/clients            # Listar clientes
POST   /api/v1/clients            # Criar cliente
GET    /api/v1/clients/{id}       # Obter cliente
PUT    /api/v1/clients/{id}       # Atualizar cliente
DELETE /api/v1/clients/{id}       # Deletar cliente
GET    /api/v1/clients/{id}/summary # Dashboard do cliente
```

#### **Ativos**
```
GET    /api/v1/assets             # Listar ativos
POST   /api/v1/assets             # Criar ativo
GET    /api/v1/assets/{id}        # Obter ativo
PUT    /api/v1/assets/{id}        # Atualizar ativo
DELETE /api/v1/assets/{id}        # Deletar ativo
GET    /api/v1/assets/by-client/{client_id} # Ativos por cliente
```

#### **Passivos**
```
GET    /api/v1/liabilities        # Listar passivos
POST   /api/v1/liabilities        # Criar passivo
GET    /api/v1/liabilities/{id}   # Obter passivo
PUT    /api/v1/liabilities/{id}   # Atualizar passivo
DELETE /api/v1/liabilities/{id}   # Deletar passivo
```

#### **Contas**
```
GET    /api/v1/accounts           # Listar contas
POST   /api/v1/accounts           # Criar conta
GET    /api/v1/accounts/{id}      # Obter conta
PUT    /api/v1/accounts/{id}      # Atualizar conta
DELETE /api/v1/accounts/{id}      # Deletar conta
```

#### **Posições Mensais**
```
GET    /api/v1/positions          # Listar posições
POST   /api/v1/positions/import   # Importar planilha
GET    /api/v1/positions/history  # Histórico de importações
GET    /api/v1/positions/validate # Validar antes de importar
```

#### **Documentos**
```
GET    /api/v1/documents          # Listar documentos
POST   /api/v1/documents          # Upload documento
GET    /api/v1/documents/{id}     # Obter documento
DELETE /api/v1/documents/{id}     # Deletar documento
GET    /api/v1/documents/{id}/download # Download
```

#### **Dashboard & Relatórios**
```
GET    /api/v1/dashboard/client/{id}        # Dashboard do cliente
GET    /api/v1/dashboard/evolution          # Evolução patrimonial
GET    /api/v1/dashboard/composition        # Composição de ativos
GET    /api/v1/reports/pdf/{client_id}      # Gerar PDF
```

---

## 6. MÓDULOS FRONTEND

### 6.1 Estrutura de Diretórios
```
frontend/
├── public/
│   └── index.html
│
├── src/
│   ├── main.tsx               # Entry point
│   ├── App.tsx                # Root component
│   ├── vite-env.d.ts
│   │
│   ├── assets/                # Imagens, ícones
│   │   └── logo.png
│   │
│   ├── components/            # Componentes reutilizáveis
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Table.tsx
│   │   │   ├── Modal.tsx
│   │   │   └── Loading.tsx
│   │   │
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── Layout.tsx
│   │   │
│   │   └── charts/
│   │       ├── PieChart.tsx
│   │       ├── LineChart.tsx
│   │       └── BarChart.tsx
│   │
│   ├── pages/                 # Páginas da aplicação
│   │   ├── auth/
│   │   │   ├── Login.tsx
│   │   │   └── ForgotPassword.tsx
│   │   │
│   │   ├── client/           # Área do cliente
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Assets.tsx
│   │   │   ├── Liabilities.tsx
│   │   │   ├── Evolution.tsx
│   │   │   ├── Documents.tsx
│   │   │   └── Settings.tsx
│   │   │
│   │   └── admin/            # Área administrativa
│   │       ├── Clients.tsx
│   │       ├── ClientForm.tsx
│   │       ├── Assets.tsx
│   │       ├── AssetForm.tsx
│   │       ├── Accounts.tsx
│   │       ├── Positions.tsx
│   │       ├── PositionImport.tsx
│   │       ├── Documents.tsx
│   │       └── Users.tsx
│   │
│   ├── services/             # API calls
│   │   ├── api.ts           # Axios config
│   │   ├── authService.ts
│   │   ├── clientService.ts
│   │   ├── assetService.ts
│   │   ├── documentService.ts
│   │   └── dashboardService.ts
│   │
│   ├── store/               # State management
│   │   ├── authStore.ts
│   │   ├── clientStore.ts
│   │   └── uiStore.ts
│   │
│   ├── hooks/               # Custom hooks
│   │   ├── useAuth.ts
│   │   ├── useClients.ts
│   │   └── useDebounce.ts
│   │
│   ├── types/               # TypeScript types
│   │   ├── auth.ts
│   │   ├── client.ts
│   │   ├── asset.ts
│   │   └── common.ts
│   │
│   ├── utils/               # Utilities
│   │   ├── formatters.ts    # Formatação de datas, moedas
│   │   ├── validators.ts    # Validações CPF/CNPJ
│   │   └── constants.ts     # Constantes
│   │
│   ├── styles/              # Estilos globais
│   │   └── theme.ts         # Tema MUI
│   │
│   └── routes/              # Configuração de rotas
│       ├── index.tsx
│       ├── PrivateRoute.tsx
│       └── PublicRoute.tsx
│
├── package.json
├── tsconfig.json
├── vite.config.ts
└── Dockerfile
```

### 6.2 Principais Componentes

#### **Área do Cliente**

**Dashboard.tsx**
```typescript
// Exibe:
// - Patrimônio líquido total + variação
// - Cards: Ativos, Passivos, Moeda Base, Entidades
// - Gráfico de composição (pizza)
// - Tabela de ativos por categoria
```

**Evolution.tsx**
```typescript
// Exibe:
// - Gráfico de linha com evolução temporal
// - Filtros: 3M, 6M, 12M, 24M
// - Tabela de variação mensal com %
```

**Assets.tsx**
```typescript
// Exibe:
// - Listagem de ativos do cliente
// - Filtros por categoria
// - Detalhes com documentos vinculados
```

**Liabilities.tsx**
```typescript
// Exibe:
// - Total de passivos
// - Lista detalhada por tipo
// - Instituição credora
```

**Documents.tsx**
```typescript
// Exibe:
// - Listagem de documentos
// - Filtros por tipo e data
// - Download de documentos
```

#### **Área Administrativa**

**Clients.tsx**
```typescript
// Exibe:
// - Tabela de clientes com filtros
// - Ações: editar, visualizar como cliente, excluir
// - Botão: Adicionar Cliente
```

**ClientForm.tsx**
```typescript
// Formulário com:
// - Tipo (PF/PJ/Família/Empresa)
// - Nome/Razão Social
// - CPF/CNPJ
// - E-mail, telefone
// - RM Responsável
// - Status
```

**AssetForm.tsx**
```typescript
// Formulário com:
// - Cliente/Entidade
// - Categoria (select)
// - Nome do ativo
// - Valor base e atual
// - Data base
// - Upload de documento
```

**PositionImport.tsx**
```typescript
// Interface de importação:
// - Drag & drop para planilha
// - Preview dos dados
// - Validação prévia
// - Log de erros
// - Histórico de importações
```

---

## 7. AUTENTICAÇÃO E SEGURANÇA

### 7.1 Fluxo de Autenticação

```
1. Login
   ├─ POST /api/v1/auth/login
   │  └─ Body: { email, password }
   │
   ├─ Backend valida credenciais
   │  └─ Verifica hash da senha
   │
   ├─ Gera tokens JWT
   │  ├─ access_token (exp: 30 min)
   │  └─ refresh_token (exp: 7 dias)
   │
   └─ Retorna: { access_token, refresh_token, user }

2. Requisições Autenticadas
   ├─ Header: Authorization: Bearer {access_token}
   │
   ├─ Backend valida token
   │  ├─ Verifica assinatura
   │  └─ Verifica expiração
   │
   └─ Extrai user_id e role do token

3. Refresh Token
   ├─ POST /api/v1/auth/refresh
   │  └─ Body: { refresh_token }
   │
   └─ Gera novo access_token
```

### 7.2 Permissões por Role

```python
PERMISSIONS = {
    "admin": ["*"],  # Acesso total
    "rm": [
        "read:clients",
        "write:clients",  # Apenas seus clientes
        "read:assets",
        "write:assets",
        "read:documents",
        "write:documents",
        "import:positions"
    ],
    "analyst": [
        "read:clients",
        "read:assets",
        "read:documents"
    ],
    "client": [
        "read:own_data"  # Apenas seus próprios dados
    ]
}
```

### 7.3 Criptografia de Dados Sensíveis

```python
# Campos a serem criptografados:
# - CPF/CNPJ
# - Documentos sensíveis
# - Informações bancárias

from cryptography.fernet import Fernet

def encrypt_field(value: str, key: bytes) -> str:
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()

def decrypt_field(encrypted_value: str, key: bytes) -> str:
    f = Fernet(key)
    return f.decrypt(encrypted_value.encode()).decode()
```

### 7.4 Auditoria LGPD

**Registrar todas as ações:**
```python
# Ações a serem logadas:
# - Login/Logout
# - Criação/Edição/Exclusão de dados
# - Acesso a documentos
# - Exportação de dados (PDF)

async def log_audit(
    user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID,
    ip_address: str,
    details: dict = None
):
    # Salvar em audit_logs
    pass
```

---

## 8. INTEGRAÇÕES

### 8.1 Integração com Sistema de Fluxo de Caixa

**Requisitos:**
- O sistema de fluxo de caixa já existe
- Deve ser acessível pelo mesmo menu/layout
- Autenticação compartilhada (SSO)

**Abordagens possíveis:**

**Opção 1: Iframe**
```typescript
// Incorporar o sistema existente via iframe
<iframe 
  src="https://fluxo-caixa.starke.com" 
  style={{ width: '100%', height: '100vh' }}
/>
```

**Opção 2: Proxy Reverso**
```
# Configurar no backend/proxy para rotear
/fluxo-caixa/* → Sistema existente
/patrimonio/* → Novo sistema
```

**Opção 3: Menu Unificado**
```typescript
// Sidebar com links para ambos os sistemas
<MenuItem onClick={() => window.open('/fluxo-caixa', '_blank')}>
  Fluxo de Caixa
</MenuItem>
<MenuItem href="/patrimonio">
  Controle Patrimonial
</MenuItem>
```

### 8.2 AWS S3 para Documentos

```python
import boto3
from app.core.config import settings

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION
)

async def upload_file_to_s3(
    file: UploadFile,
    client_id: UUID,
    document_type: str
) -> str:
    """Upload file to S3 and return path"""
    file_key = f"documents/{client_id}/{document_type}/{file.filename}"
    
    s3_client.upload_fileobj(
        file.file,
        settings.S3_BUCKET_NAME,
        file_key,
        ExtraArgs={'ContentType': file.content_type}
    )
    
    return file_key

async def generate_presigned_url(file_key: str) -> str:
    """Generate temporary download URL"""
    return s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': settings.S3_BUCKET_NAME,
            'Key': file_key
        },
        ExpiresIn=3600  # 1 hour
    )
```

---

## 9. TAREFAS DE DESENVOLVIMENTO

### 9.1 Sprint 1-2: Setup e Autenticação (Semanas 1-2)

#### Backend
- [ ] Setup do projeto FastAPI
- [ ] Configurar SQLAlchemy + Alembic
- [ ] Criar modelos: User, Client (básico)
- [ ] Implementar autenticação JWT
- [ ] Endpoints: login, logout, refresh, me
- [ ] Middleware de autenticação
- [ ] Sistema de permissões por role
- [ ] Testes unitários de autenticação

#### Frontend
- [ ] Setup do projeto React + TypeScript + Vite
- [ ] Configurar Material-UI
- [ ] Criar layout base (Sidebar, Header)
- [ ] Página de login
- [ ] Configurar Axios com interceptors
- [ ] Store de autenticação (Zustand)
- [ ] Rotas privadas e públicas
- [ ] Logout e refresh token automático

#### DevOps
- [ ] Docker Compose (backend, frontend, postgres, redis)
- [ ] Configurar variáveis de ambiente
- [ ] README com instruções de setup

---

### 9.2 Sprint 3-4: Painel do Cliente - Dashboard (Semanas 3-4)

#### Backend
- [ ] Completar modelos: Asset, Liability, Account, Institution
- [ ] Migrations do banco de dados
- [ ] Repository: ClientRepository
- [ ] Service: CalculationService (patrimônio líquido, variações)
- [ ] Endpoints:
  - [ ] GET /clients/{id}/summary (dashboard completo)
  - [ ] GET /clients/{id}/assets (lista de ativos)
  - [ ] GET /clients/{id}/liabilities (lista de passivos)
- [ ] Cálculos:
  - [ ] Total de ativos
  - [ ] Total de passivos
  - [ ] Patrimônio líquido
  - [ ] Variação percentual
  - [ ] Composição por categoria
- [ ] Testes unitários

#### Frontend
- [ ] Página: Dashboard do cliente
- [ ] Componente: SummaryCards (patrimônio, ativos, passivos, moeda, entidades)
- [ ] Componente: CompositionPieChart (Recharts)
- [ ] Componente: AssetsTable (por categoria)
- [ ] Service: dashboardService
- [ ] Formatadores: moeda, percentual, data
- [ ] Loading states e error handling

---

### 9.3 Sprint 5: Evolução Patrimonial (Semana 5)

#### Backend
- [ ] Modelo: MonthlyPosition
- [ ] Service: EvolutionService
- [ ] Endpoint: GET /dashboard/evolution?period=12M
- [ ] Cálculos:
  - [ ] Agregação por mês
  - [ ] Variação mensal (%)
  - [ ] Filtros de período (3M, 6M, 12M, 24M)
- [ ] Testes

#### Frontend
- [ ] Página: Evolution
- [ ] Componente: EvolutionLineChart
- [ ] Componente: MonthlyVariationTable
- [ ] Filtros de período (botões)
- [ ] Indicadores de alta/baixa (cores)

---

### 9.4 Sprint 6: Documentos e Configurações (Semana 6)

#### Backend
- [ ] Modelo: Document
- [ ] Service: DocumentService (S3 integration)
- [ ] Endpoints:
  - [ ] GET /documents (listar)
  - [ ] POST /documents (upload)
  - [ ] GET /documents/{id}/download (presigned URL)
  - [ ] DELETE /documents/{id}
- [ ] Validação de tipos de arquivo
- [ ] Limite de tamanho (10MB)
- [ ] Testes

#### Frontend - Documentos
- [ ] Página: Documents
- [ ] Componente: DocumentList
- [ ] Filtros: tipo, data
- [ ] Download de documentos

#### Frontend - Configurações
- [ ] Página: Settings
- [ ] Formulário: dados pessoais
- [ ] Seletores: moeda, idioma
- [ ] Toggle: tema claro/escuro
- [ ] Formulário: mudança de senha

---

### 9.5 Sprint 7-8: Painel Admin - CRUD (Semanas 7-8)

#### Backend
- [ ] Endpoints CRUD completos:
  - [ ] Clients (com validação CPF/CNPJ)
  - [ ] Assets
  - [ ] Liabilities
  - [ ] Accounts
  - [ ] Institutions
- [ ] Filtros e paginação
- [ ] Validações de negócio
- [ ] Verificação de duplicidade (CPF/CNPJ)
- [ ] Testes

#### Frontend - Gestão de Clientes
- [ ] Página: Clients (listagem)
- [ ] Componente: ClientTable
- [ ] Filtros: tipo, status, RM
- [ ] Busca por nome/CPF
- [ ] Página: ClientForm
- [ ] Validação: CPF/CNPJ
- [ ] Select: RM responsável

#### Frontend - Gestão de Ativos
- [ ] Página: Assets (admin)
- [ ] Página: AssetForm
- [ ] Select: cliente, categoria, instituição
- [ ] Upload de documento comprovante

#### Frontend - Gestão de Contas
- [ ] Página: Accounts
- [ ] Formulário: cadastro de conta
- [ ] Vínculo com instituição

---

### 9.6 Sprint 9: Importação de Planilhas (Semana 9)

#### Backend
- [ ] Service: ImportService
- [ ] Parser de Excel (openpyxl)
- [ ] Parser de CSV (pandas)
- [ ] Validações:
  - [ ] Formato de arquivo
  - [ ] Colunas obrigatórias
  - [ ] Tipos de dados
  - [ ] Cliente/Ativo existe
  - [ ] Valores válidos
- [ ] Modelo: ImportLog
- [ ] Endpoint: POST /positions/import
- [ ] Endpoint: GET /positions/history
- [ ] Processamento em lote (bulk insert)
- [ ] Rollback em caso de erro
- [ ] Testes com arquivos de exemplo

#### Frontend
- [ ] Página: PositionImport
- [ ] Componente: FileUploader (drag & drop)
- [ ] Template de planilha para download
- [ ] Preview de dados antes de importar
- [ ] Validação no frontend
- [ ] Barra de progresso
- [ ] Relatório de erros
- [ ] Histórico de importações

---

### 9.7 Sprint 10: Upload de Documentos (Admin) (Semana 10)

#### Backend
- [ ] Endpoint: POST /documents/bulk (múltiplos arquivos)
- [ ] Service: BulkDocumentService
- [ ] Scan de vírus (opcional - ClamAV)
- [ ] Compressão de imagens (Pillow)
- [ ] Nomenclatura padronizada

#### Frontend
- [ ] Página: DocumentUpload (admin)
- [ ] Upload múltiplo
- [ ] Select: cliente, tipo
- [ ] Preview de arquivos
- [ ] Lista de uploads recentes
- [ ] Status: validado/pendente

---

### 9.8 Sprint 11: Geração de PDF (Semana 11)

#### Backend
- [ ] Service: PDFService
- [ ] Biblioteca: ReportLab ou WeasyPrint
- [ ] Template de relatório:
  - [ ] Cabeçalho com logo
  - [ ] Dados do cliente
  - [ ] Patrimônio líquido
  - [ ] Composição de ativos (gráfico)
  - [ ] Tabelas detalhadas
  - [ ] Rodapé com data de geração
- [ ] Endpoint: GET /reports/pdf/{client_id}
- [ ] Testes

#### Frontend
- [ ] Botão "Baixar PDF" no dashboard
- [ ] Loading durante geração
- [ ] Download automático

---

### 9.9 Sprint 12: Gestão de Usuários (Admin) (Semana 12)

#### Backend
- [ ] Endpoints CRUD: Users
- [ ] Validação de permissões (admin only)
- [ ] Desativação de usuário (soft delete)
- [ ] Endpoint: POST /users/{id}/reset-password (força reset)

#### Frontend
- [ ] Página: Users
- [ ] Listagem de usuários
- [ ] Filtros: role, status
- [ ] Formulário: criar/editar usuário
- [ ] Select: perfil (Admin/RM/Analista)
- [ ] Ativar/desativar usuário

---

### 9.10 Sprint 13: LGPD e Auditoria (Semana 13)

#### Backend
- [ ] Modelo: AuditLog
- [ ] Middleware de auditoria (decorator)
- [ ] Log de todas as ações sensíveis
- [ ] Criptografia de campos sensíveis (CPF/CNPJ)
- [ ] Endpoints:
  - [ ] GET /lgpd/my-data (portabilidade)
  - [ ] POST /lgpd/request-deletion (solicitar exclusão)
- [ ] Service: AnonymizationService
- [ ] Testes de compliance

#### Frontend
- [ ] Política de Privacidade (página)
- [ ] Termos de Uso (página)
- [ ] Aceite inicial (modal)
- [ ] Página: Meus Dados (portabilidade)
- [ ] Botão: Solicitar Exclusão de Dados

---

### 9.11 Sprint 14: Integração com Fluxo de Caixa (Semana 14)

#### Backend
- [ ] Configurar proxy/routing para sistema existente
- [ ] SSO (Single Sign-On) se necessário
- [ ] Compartilhar sessão/token

#### Frontend
- [ ] Menu unificado (Sidebar)
- [ ] Link para Fluxo de Caixa
- [ ] Integração via iframe ou redirecionamento
- [ ] Testes de navegação

---

### 9.12 Sprint 15-16: Testes e Refinamentos (Semanas 15-16)

#### Backend
- [ ] Testes de integração (pytest)
- [ ] Testes de segurança (OWASP)
- [ ] Testes de performance (carga)
- [ ] Code coverage > 80%
- [ ] Correção de bugs

#### Frontend
- [ ] Testes de componentes (Vitest + Testing Library)
- [ ] Testes E2E (Playwright)
- [ ] Testes de responsividade (mobile)
- [ ] Testes em diferentes navegadores
- [ ] Ajustes de UX
- [ ] Correção de bugs

#### DevOps
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Build e deploy automatizado
- [ ] Health checks
- [ ] Monitoramento (Sentry)

---

## 10. TESTES E QUALIDADE

### 10.1 Backend - Testes Unitários (pytest)

```python
# tests/test_auth.py
def test_login_success(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

# tests/test_clients.py
def test_create_client(client, admin_token):
    response = client.post(
        "/api/v1/clients",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "João Silva",
            "type": "pf",
            "cpf_cnpj": "12345678901"
        }
    )
    assert response.status_code == 201
```

### 10.2 Frontend - Testes de Componentes (Vitest)

```typescript
// Dashboard.test.tsx
import { render, screen } from '@testing-library/react';
import Dashboard from './Dashboard';

test('renders dashboard with summary cards', () => {
  render(<Dashboard />);
  expect(screen.getByText(/patrimônio líquido/i)).toBeInTheDocument();
});
```

### 10.3 Testes E2E (Playwright)

```typescript
// e2e/login.spec.ts
import { test, expect } from '@playwright/test';

test('admin can login and access clients page', async ({ page }) => {
  await page.goto('http://localhost:3000/login');
  await page.fill('input[name="email"]', 'admin@example.com');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');
  
  await expect(page).toHaveURL('/admin/clients');
});
```

---

## 11. DEPLOY E INFRAESTRUTURA

### 11.1 Docker Compose (Desenvolvimento)

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/starke_db
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=your-secret-key
      - AWS_ACCESS_KEY_ID=your-key
      - AWS_SECRET_ACCESS_KEY=your-secret
      - AWS_REGION=us-east-1
      - S3_BUCKET_NAME=starke-documents
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000/api/v1
    volumes:
      - ./frontend:/app
      - /app/node_modules

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=starke_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 11.2 GitHub Actions (CI/CD)

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Backend Tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest
      
      - name: Run Frontend Tests
        run: |
          cd frontend
          npm install
          npm test

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to AWS
        # Configurar deploy específico
        run: echo "Deploy to production"
```

### 11.3 Variáveis de Ambiente

**.env.example (Backend)**
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/starke_db

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# AWS S3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=starke-documents

# Encryption
ENCRYPTION_KEY=your-encryption-key-for-sensitive-data

# CORS
ALLOWED_ORIGINS=http://localhost:3000,https://app.starke.com

# Environment
ENVIRONMENT=production
DEBUG=False
```

**.env.example (Frontend)**
```bash
VITE_API_URL=http://localhost:8000/api/v1
VITE_APP_NAME=Starke Consolid
VITE_ENABLE_ANALYTICS=true
```

---

## 12. OBSERVAÇÕES FINAIS

### 12.1 Prioridades
1. **Segurança**: Autenticação, autorização, criptografia, LGPD
2. **Funcionalidade Core**: CRUD de clientes, ativos, passivos
3. **Importação**: Sistema robusto de importação de planilhas
4. **UX**: Interface intuitiva e responsiva
5. **Performance**: Consultas otimizadas, cache

### 12.2 Boas Práticas
- **Código limpo**: Seguir PEP 8 (Python) e ESLint (TypeScript)
- **Commits semânticos**: `feat:`, `fix:`, `docs:`, `refactor:`
- **Code review**: Todo PR deve ser revisado
- **Documentação inline**: Docstrings (Python) e JSDoc (TypeScript)
- **Error handling**: Tratar todos os erros adequadamente
- **Logging**: Usar logger estruturado (não prints)

### 12.3 Pontos de Atenção
- **Validação de CPF/CNPJ**: Implementar validação rigorosa
- **Importação de planilhas**: Validar dados antes de salvar
- **Performance em gráficos**: Otimizar queries para grandes volumes
- **Documentos S3**: Sempre usar URLs assinadas (presigned)
- **LGPD**: Auditar todas as ações sensíveis

---

## 13. GLOSSÁRIO

- **PF**: Pessoa Física
- **PJ**: Pessoa Jurídica
- **RM**: Relationship Manager (Gerente de Relacionamento)
- **CRUD**: Create, Read, Update, Delete
- **JWT**: JSON Web Token
- **SSO**: Single Sign-On
- **PWA**: Progressive Web App
- **ORM**: Object-Relational Mapping
- **S3**: Amazon Simple Storage Service
- **LGPD**: Lei Geral de Proteção de Dados

---

**Documento criado em:** 19 de novembro de 2025  
**Versão:** 1.0  
**Responsável:** Brain IT Solutions  
**Cliente:** Starke Capital

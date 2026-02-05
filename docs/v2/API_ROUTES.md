# Starke API v2 - Documentação de Rotas

Documentação completa das rotas da API v2 para integração com o frontend.

**Base URL:** `/api/v1`

---

## Índice

1. [Autenticação](#1-autenticação)
2. [Usuários](#2-usuários)
3. [Instituições](#3-instituições)
4. [Clientes](#4-clientes)
5. [Contas](#5-contas)
6. [Ativos](#6-ativos)
7. [Passivos](#7-passivos)
8. [Documentos](#8-documentos)
9. [Posições Mensais](#9-posições-mensais)
10. [Self-Service (Portal do Cliente)](#10-self-service-portal-do-cliente)
11. [Controle de Acesso](#11-controle-de-acesso)
12. [Códigos de Erro](#12-códigos-de-erro)

---

## 1. Autenticação

### POST `/auth/login`

Autentica usuário e retorna token JWT.

**Content-Type:** `application/x-www-form-urlencoded`

**Request Body:**
| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| username | string | Sim | Email do usuário |
| password | string | Sim | Senha do usuário |

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Response 401:**
```json
{
  "detail": "Incorrect email or password"
}
```

---

### GET `/auth/me`

Retorna informações do usuário autenticado.

**Headers:** `Authorization: Bearer {token}`

**Response 200:**
```json
{
  "id": 1,
  "email": "usuario@email.com",
  "full_name": "Nome Completo",
  "role": "admin",
  "is_active": true,
  "permissions": ["CLIENTS", "ASSETS", "LIABILITIES", "ACCOUNTS", "INSTITUTIONS", "USERS"]
}
```

---

### POST `/auth/change-password`

Altera senha do usuário autenticado.

**Headers:** `Authorization: Bearer {token}`

**Request Body:**
```json
{
  "current_password": "senha_atual",
  "new_password": "nova_senha"
}
```

**Response 204:** No Content (sucesso)

**Response 400:**
```json
{
  "detail": "Current password is incorrect"
}
```

---

### POST `/auth/logout`

Logout do usuário (invalidação client-side).

**Headers:** `Authorization: Bearer {token}`

**Response 204:** No Content

---

## 2. Usuários

> **Permissão necessária:** `USERS` (somente Admin)

### GET `/users`

Lista todos os usuários.

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| skip | int | 0 | Offset para paginação |
| limit | int | 100 | Limite de registros (max: 1000) |
| role | string | - | Filtrar por role: `admin`, `rm`, `analyst`, `client` |
| is_active | bool | - | Filtrar por ativo/inativo |

**Response 200:**
```json
[
  {
    "id": 1,
    "email": "admin@empresa.com",
    "full_name": "Administrador",
    "role": "admin",
    "is_active": true,
    "is_superuser": true,
    "created_at": "2025-01-01T10:00:00",
    "updated_at": null
  }
]
```

---

### POST `/users`

Cria novo usuário.

**Headers:** `Authorization: Bearer {token}`

**Request Body:**
```json
{
  "email": "novo@email.com",
  "password": "Senha@123",
  "full_name": "Nome Completo",
  "role": "analyst"
}
```

| Campo | Tipo | Obrigatório | Valores |
|-------|------|-------------|---------|
| email | string | Sim | Email válido único |
| password | string | Sim | Mínimo 8 caracteres |
| full_name | string | Sim | Nome completo |
| role | string | Sim | `admin`, `rm`, `analyst`, `client` |

**Response 201:**
```json
{
  "id": 2,
  "email": "novo@email.com",
  "full_name": "Nome Completo",
  "role": "analyst",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-01-01T10:00:00",
  "updated_at": null
}
```

---

### GET `/users/{user_id}`

Busca usuário por ID.

**Response 200:** Objeto de usuário

**Response 404:**
```json
{
  "detail": "User not found"
}
```

---

### PUT `/users/{user_id}`

Atualiza usuário.

**Request Body:**
```json
{
  "email": "novo@email.com",
  "full_name": "Nome Atualizado",
  "role": "rm",
  "is_active": true
}
```

> Todos os campos são opcionais. Apenas campos enviados serão atualizados.

**Response 200:** Objeto de usuário atualizado

---

### DELETE `/users/{user_id}`

Desativa usuário (soft delete).

**Response 204:** No Content

---

## 3. Instituições

> **Permissão necessária:** `INSTITUTIONS`

### GET `/institutions`

Lista instituições financeiras.

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| page | int | 1 | Página |
| per_page | int | 20 | Itens por página (max: 100) |
| is_active | bool | - | Filtrar por ativo/inativo |
| institution_type | string | - | Filtrar por tipo |
| search | string | - | Buscar por nome |

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid-da-instituicao",
      "name": "Banco do Brasil",
      "code": "001",
      "institution_type": "bank",
      "is_active": true,
      "created_at": "2025-01-01T10:00:00",
      "updated_at": null
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

---

### POST `/institutions`

Cria nova instituição.

**Request Body:**
```json
{
  "name": "Banco XYZ",
  "code": "999",
  "institution_type": "bank"
}
```

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| name | string | Sim | Nome da instituição |
| code | string | Não | Código BACEN |
| institution_type | string | Não | Tipo: `bank`, `broker`, `insurance`, `other` |

**Response 201:** Objeto da instituição criada

---

### GET `/institutions/{institution_id}`

Busca instituição por ID.

**Response 200:** Objeto da instituição

---

### PUT `/institutions/{institution_id}`

Atualiza instituição.

**Request Body:**
```json
{
  "name": "Novo Nome",
  "code": "123",
  "institution_type": "broker",
  "is_active": false
}
```

**Response 200:** Objeto atualizado

---

### DELETE `/institutions/{institution_id}`

Desativa instituição (soft delete).

**Response 204:** No Content

---

## 4. Clientes

> **Permissão necessária:** `CLIENTS`

### Controle de Acesso por Role

| Role | Acesso |
|------|--------|
| Admin | Todos os clientes |
| RM | Apenas clientes atribuídos a ele |
| Analyst | Todos os clientes (leitura) |
| Client | Apenas seus próprios dados |

---

### GET `/clients`

Lista clientes com paginação.

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| page | int | 1 | Página |
| per_page | int | 20 | Itens por página (max: 100) |
| status | string | - | Filtrar: `active`, `inactive` |
| client_type | string | - | Filtrar: `pf` (pessoa física), `pj` (jurídica) |
| search | string | - | Buscar por nome |
| rm_user_id | int | - | Filtrar por RM (apenas admin) |

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid-do-cliente",
      "name": "João da Silva",
      "client_type": "pf",
      "email": "joao@email.com",
      "phone": "(11) 99999-9999",
      "base_currency": "BRL",
      "notes": "Cliente VIP",
      "status": "active",
      "rm_user_id": 5,
      "rm_user_name": "Maria RM",
      "user_id": null,
      "has_login": false,
      "created_at": "2025-01-01T10:00:00",
      "updated_at": null
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 20,
  "pages": 8
}
```

---

### GET `/clients/{client_id}`

Busca cliente por ID com resumo patrimonial.

**Response 200:**
```json
{
  "id": "uuid-do-cliente",
  "name": "João da Silva",
  "client_type": "pf",
  "email": "joao@email.com",
  "phone": "(11) 99999-9999",
  "base_currency": "BRL",
  "notes": "Cliente VIP",
  "status": "active",
  "rm_user_id": 5,
  "rm_user_name": "Maria RM",
  "user_id": null,
  "has_login": false,
  "created_at": "2025-01-01T10:00:00",
  "updated_at": null,
  "cpf_cnpj_masked": "***.***123.-**",
  "total_assets": "1500000.00",
  "total_liabilities": "350000.00",
  "net_worth": "1150000.00",
  "accounts_count": 3,
  "assets_count": 15,
  "liabilities_count": 2
}
```

---

### POST `/clients`

Cria novo cliente.

**Request Body:**
```json
{
  "name": "Maria Santos",
  "client_type": "pf",
  "cpf_cnpj": "12345678909",
  "email": "maria@email.com",
  "phone": "(11) 98888-8888",
  "base_currency": "BRL",
  "notes": "Nova cliente",
  "rm_user_id": 5
}
```

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| name | string | Sim | Nome completo |
| client_type | string | Sim | `pf` ou `pj` |
| cpf_cnpj | string | Sim | CPF (11 dígitos) ou CNPJ (14 dígitos) |
| email | string | Não | Email de contato |
| phone | string | Não | Telefone |
| base_currency | string | Não | Moeda base (default: BRL) |
| notes | string | Não | Observações |
| rm_user_id | int | Não | ID do RM responsável |

> **Nota:** Se o usuário logado for RM, o cliente é automaticamente atribuído a ele.

**Response 201:** Objeto do cliente criado

**Response 400:**
```json
{
  "detail": "CPF/CNPJ já cadastrado"
}
```

**Response 422:**
```json
{
  "detail": [{"loc": ["body", "cpf_cnpj"], "msg": "CPF inválido"}]
}
```

---

### PUT `/clients/{client_id}`

Atualiza cliente.

**Request Body:**
```json
{
  "name": "Maria Santos Atualizado",
  "email": "novo@email.com",
  "status": "inactive"
}
```

> RM não pode alterar `rm_user_id` (atribuição).

**Response 200:** Objeto atualizado

---

### DELETE `/clients/{client_id}`

Desativa cliente (status = inactive).

**Response 204:** No Content

---

### GET `/clients/{client_id}/summary`

Retorna resumo patrimonial detalhado do cliente.

**Response 200:**
```json
{
  "client_id": "uuid",
  "client_name": "João da Silva",
  "total_assets": "1500000.00",
  "total_liabilities": "350000.00",
  "net_worth": "1150000.00",
  "assets_by_category": {
    "renda_fixa": "500000.00",
    "renda_variavel": "800000.00",
    "imoveis": "200000.00"
  },
  "liabilities_by_type": {
    "mortgage": "300000.00",
    "personal_loan": "50000.00"
  },
  "accounts_count": 3,
  "assets_count": 15,
  "liabilities_count": 2
}
```

---

### GET `/clients/{client_id}/evolution`

Retorna evolução patrimonial mensal do cliente.

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| months | int | 12 | Número de meses (1-60) |

**Response 200:**
```json
{
  "client_id": "uuid",
  "client_name": "João da Silva",
  "period_months": 12,
  "data_points": 12,
  "variation": 150000.00,
  "variation_pct": 15.0,
  "evolution": [
    {
      "date": "2025-01-31",
      "total_assets": 1000000.00,
      "total_liabilities": 350000.00,
      "net_worth": 650000.00
    },
    {
      "date": "2025-02-28",
      "total_assets": 1050000.00,
      "total_liabilities": 340000.00,
      "net_worth": 710000.00
    }
  ]
}
```

---

### GET `/clients/{client_id}/report/pdf`

Gera relatório PDF do patrimônio do cliente.

**Response 200:** Arquivo PDF para download

**Headers de Resposta:**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename=relatorio_{client_id}_{data}.pdf
```

> **Nota:** Se a biblioteca `weasyprint` não estiver disponível, retorna HTML.

---

## 5. Contas

> **Permissão necessária:** `ACCOUNTS`

### GET `/accounts`

Lista contas com paginação.

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| page | int | 1 | Página |
| per_page | int | 20 | Itens por página |
| client_id | string | - | Filtrar por cliente |
| institution_id | string | - | Filtrar por instituição |
| account_type | string | - | Filtrar por tipo |
| is_active | bool | - | Filtrar por ativo/inativo |

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid-da-conta",
      "client_id": "uuid-do-cliente",
      "institution_id": "uuid-da-instituicao",
      "institution": {
        "id": "uuid",
        "name": "Banco do Brasil",
        "code": "001"
      },
      "account_type": "checking",
      "account_number": "12345-6",
      "agency": "0001",
      "currency": "BRL",
      "base_date": "2025-01-01",
      "notes": null,
      "is_active": true,
      "created_at": "2025-01-01T10:00:00",
      "updated_at": null
    }
  ],
  "total": 25,
  "page": 1,
  "per_page": 20,
  "pages": 2
}
```

---

### GET `/accounts/by-client/{client_id}`

Lista todas as contas de um cliente.

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| is_active | bool | true | Filtrar por ativo/inativo |

**Response 200:** Array de contas

---

### POST `/accounts`

Cria nova conta.

**Request Body:**
```json
{
  "client_id": "uuid-do-cliente",
  "institution_id": "uuid-da-instituicao",
  "account_type": "investment",
  "account_number": "98765-4",
  "agency": "0002",
  "currency": "BRL",
  "base_date": "2025-01-01",
  "notes": "Conta de investimentos"
}
```

| Campo | Tipo | Obrigatório | Valores |
|-------|------|-------------|---------|
| client_id | string | Sim | UUID do cliente |
| institution_id | string | Não | UUID da instituição |
| account_type | string | Sim | `checking`, `savings`, `investment`, `other` |
| account_number | string | Não | Número da conta |
| agency | string | Não | Agência |
| currency | string | Não | Moeda (default: BRL) |
| base_date | date | Não | Data base |
| notes | string | Não | Observações |

**Response 201:** Objeto da conta criada

---

### GET `/accounts/{account_id}`

Busca conta por ID.

**Response 200:** Objeto da conta

---

### PUT `/accounts/{account_id}`

Atualiza conta.

**Response 200:** Objeto atualizado

---

### DELETE `/accounts/{account_id}`

Desativa conta (soft delete).

**Response 204:** No Content

---

## 6. Ativos

> **Permissão necessária:** `ASSETS`

### GET `/assets`

Lista ativos com paginação.

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| page | int | 1 | Página |
| per_page | int | 20 | Itens por página |
| client_id | string | - | Filtrar por cliente |
| account_id | string | - | Filtrar por conta |
| category | string | - | Filtrar por categoria |
| is_active | bool | - | Filtrar por ativo/inativo |

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid-do-ativo",
      "client_id": "uuid-do-cliente",
      "account_id": "uuid-da-conta",
      "account": {
        "id": "uuid",
        "account_type": "investment",
        "institution_name": "XP Investimentos"
      },
      "category": "renda_variavel",
      "subcategory": "acoes",
      "name": "PETR4",
      "description": "Petrobrás PN",
      "ticker": "PETR4",
      "base_value": "10000.00",
      "current_value": "12500.00",
      "quantity": "100",
      "base_date": "2024-06-01",
      "base_year": 2024,
      "maturity_date": null,
      "currency": "BRL",
      "is_active": true,
      "created_at": "2025-01-01T10:00:00",
      "updated_at": null,
      "gain_loss": "2500.00",
      "gain_loss_percent": 25.0
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```

---

### GET `/assets/by-client/{client_id}`

Lista todos os ativos de um cliente.

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| category | string | - | Filtrar por categoria |
| is_active | bool | true | Filtrar por ativo/inativo |

**Response 200:** Array de ativos

---

### GET `/assets/by-client/{client_id}/grouped`

Lista ativos agrupados por categoria.

**Response 200:**
```json
[
  {
    "category": "renda_variavel",
    "total_value": "800000.00",
    "count": 10,
    "percentage": 53.33,
    "assets": [...]
  },
  {
    "category": "renda_fixa",
    "total_value": "500000.00",
    "count": 5,
    "percentage": 33.33,
    "assets": [...]
  },
  {
    "category": "imoveis",
    "total_value": "200000.00",
    "count": 1,
    "percentage": 13.33,
    "assets": [...]
  }
]
```

---

### POST `/assets`

Cria novo ativo.

**Request Body:**
```json
{
  "client_id": "uuid-do-cliente",
  "account_id": "uuid-da-conta",
  "category": "renda_variavel",
  "subcategory": "acoes",
  "name": "PETR4",
  "description": "Petrobrás PN",
  "ticker": "PETR4",
  "base_value": "10000.00",
  "current_value": "10000.00",
  "quantity": "100",
  "base_date": "2025-01-01",
  "base_year": 2025,
  "maturity_date": null,
  "currency": "BRL"
}
```

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| client_id | string | Sim | UUID do cliente |
| account_id | string | Não | UUID da conta |
| category | string | Sim | Ver tabela de categorias |
| subcategory | string | Não | Subcategoria |
| name | string | Sim | Nome do ativo |
| description | string | Não | Descrição |
| ticker | string | Não | Ticker (para ações/fundos) |
| base_value | decimal | Não | Valor de custo |
| current_value | decimal | Não | Valor atual |
| quantity | decimal | Não | Quantidade |
| base_date | date | Não | Data de aquisição |
| base_year | int | Não | Ano de referência |
| maturity_date | date | Não | Data de vencimento |
| currency | string | Não | Moeda (default: BRL) |

**Categorias de Ativos:**
- `renda_fixa` - Renda Fixa (CDB, LCI, LCA, Tesouro)
- `renda_variavel` - Renda Variável (Ações, ETFs)
- `fundos` - Fundos de Investimento
- `imoveis` - Imóveis
- `previdencia` - Previdência Privada
- `internacional` - Ativos Internacionais
- `criptomoedas` - Criptomoedas
- `outros` - Outros

**Response 201:** Objeto do ativo criado

---

### GET `/assets/{asset_id}`

Busca ativo por ID (inclui cálculo de gain/loss).

**Response 200:** Objeto do ativo com campos calculados

---

### PUT `/assets/{asset_id}`

Atualiza ativo.

**Response 200:** Objeto atualizado

---

### DELETE `/assets/{asset_id}`

Desativa ativo (soft delete).

**Response 204:** No Content

---

## 7. Passivos

> **Permissão necessária:** `LIABILITIES`

### GET `/liabilities`

Lista passivos com paginação (ordenado por saldo decrescente).

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| page | int | 1 | Página |
| per_page | int | 20 | Itens por página |
| client_id | string | - | Filtrar por cliente |
| institution_id | string | - | Filtrar por instituição |
| liability_type | string | - | Filtrar por tipo |
| is_active | bool | - | Filtrar por ativo/inativo |

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid-do-passivo",
      "client_id": "uuid-do-cliente",
      "institution_id": "uuid-da-instituicao",
      "institution": {
        "id": "uuid",
        "name": "Banco Itaú",
        "code": "341"
      },
      "liability_type": "mortgage",
      "description": "Financiamento Imobiliário",
      "notes": "Apartamento Centro",
      "original_amount": "500000.00",
      "current_balance": "450000.00",
      "monthly_payment": "5000.00",
      "interest_rate": "0.8",
      "start_date": "2020-01-01",
      "end_date": "2035-01-01",
      "last_payment_date": "2025-01-05",
      "currency": "BRL",
      "is_active": true,
      "is_paid_off": false,
      "created_at": "2025-01-01T10:00:00",
      "updated_at": null,
      "remaining_payments": 91,
      "total_to_pay": "450000.00"
    }
  ],
  "total": 10,
  "page": 1,
  "per_page": 20,
  "pages": 1
}
```

---

### GET `/liabilities/by-client/{client_id}`

Lista todos os passivos de um cliente.

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| liability_type | string | - | Filtrar por tipo |
| is_active | bool | true | Filtrar por ativo/inativo |

**Response 200:** Array de passivos

---

### GET `/liabilities/by-client/{client_id}/grouped`

Lista passivos agrupados por tipo.

**Response 200:**
```json
[
  {
    "liability_type": "mortgage",
    "total_balance": "450000.00",
    "total_monthly_payment": "5000.00",
    "count": 1,
    "percentage": 90.0,
    "liabilities": [...]
  },
  {
    "liability_type": "personal_loan",
    "total_balance": "50000.00",
    "total_monthly_payment": "2500.00",
    "count": 1,
    "percentage": 10.0,
    "liabilities": [...]
  }
]
```

---

### POST `/liabilities`

Cria novo passivo.

**Request Body:**
```json
{
  "client_id": "uuid-do-cliente",
  "institution_id": "uuid-da-instituicao",
  "liability_type": "personal_loan",
  "description": "Empréstimo Pessoal",
  "notes": "Para reforma",
  "original_amount": "50000.00",
  "current_balance": "45000.00",
  "monthly_payment": "2500.00",
  "interest_rate": "1.5",
  "start_date": "2024-06-01",
  "end_date": "2026-06-01",
  "currency": "BRL"
}
```

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| client_id | string | Sim | UUID do cliente |
| institution_id | string | Não | UUID da instituição |
| liability_type | string | Sim | Ver tipos abaixo |
| description | string | Não | Descrição |
| notes | string | Não | Observações |
| original_amount | decimal | Não | Valor original |
| current_balance | decimal | Não | Saldo atual |
| monthly_payment | decimal | Não | Parcela mensal |
| interest_rate | decimal | Não | Taxa de juros (% a.m.) |
| start_date | date | Não | Data de início |
| end_date | date | Não | Data de término |
| currency | string | Não | Moeda (default: BRL) |

**Tipos de Passivo:**
- `mortgage` - Financiamento Imobiliário
- `vehicle_loan` - Financiamento de Veículo
- `personal_loan` - Empréstimo Pessoal
- `credit_card` - Cartão de Crédito
- `overdraft` - Cheque Especial
- `consignado` - Crédito Consignado
- `other` - Outros

**Response 201:** Objeto do passivo criado

---

### GET `/liabilities/{liability_id}`

Busca passivo por ID (inclui cálculo de parcelas restantes).

**Response 200:** Objeto do passivo com campos calculados

---

### PUT `/liabilities/{liability_id}`

Atualiza passivo.

**Response 200:** Objeto atualizado

---

### DELETE `/liabilities/{liability_id}`

Desativa passivo (soft delete).

**Response 204:** No Content

---

## 8. Documentos

> **Permissão necessária:** `DOCUMENTS`

### POST `/documents/upload`

Faz upload de um documento para um cliente.

**Content-Type:** `multipart/form-data`

**Request Body:**
| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| file | file | Sim | Arquivo a ser enviado |
| client_id | string | Sim | UUID do cliente |
| document_type | string | Sim | `contract`, `report`, `statement`, `certificate`, `proof`, `other` |
| title | string | Sim | Título do documento |
| description | string | Não | Descrição |
| reference_date | string | Não | Data de referência (ISO 8601) |
| account_id | string | Não | UUID da conta relacionada |
| asset_id | string | Não | UUID do ativo relacionado |

**Limites:**
- Tamanho máximo: 10MB
- Extensões permitidas: PDF, PNG, JPG, JPEG, XLS, XLSX, CSV, DOC, DOCX

**Response 201:**
```json
{
  "id": "uuid-do-documento",
  "client_id": "uuid-do-cliente",
  "client_name": "João da Silva",
  "account_id": null,
  "asset_id": null,
  "document_type": "statement",
  "title": "Extrato Dezembro 2024",
  "description": "Extrato mensal da conta corrente",
  "file_name": "extrato_dez_2024.pdf",
  "s3_key": "uploads/documents/uuid/statement/abc123.pdf",
  "file_size": 125000,
  "mime_type": "application/pdf",
  "reference_date": "2024-12-31T00:00:00",
  "uploaded_by": 5,
  "uploader_name": "Maria RM",
  "created_at": "2025-01-01T10:00:00",
  "updated_at": null
}
```

---

### GET `/documents`

Lista documentos com paginação e filtros.

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| page | int | 1 | Página |
| per_page | int | 20 | Itens por página (max: 100) |
| client_id | string | - | Filtrar por cliente |
| document_type | string | - | Filtrar por tipo |
| start_date | string | - | Data inicial (YYYY-MM-DD) |
| end_date | string | - | Data final (YYYY-MM-DD) |

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "client_id": "uuid",
      "client_name": "João da Silva",
      "document_type": "statement",
      "title": "Extrato Dezembro 2024",
      "file_name": "extrato.pdf",
      "file_size": 125000,
      "mime_type": "application/pdf",
      "created_at": "2025-01-01T10:00:00"
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

---

### GET `/documents/{document_id}`

Busca documento por ID.

**Response 200:** Objeto completo do documento

---

### GET `/documents/{document_id}/download`

Faz download do arquivo do documento.

**Response 200:** Arquivo binário para download

**Headers de Resposta:**
```
Content-Type: {mime_type}
Content-Disposition: attachment; filename={file_name}
```

---

### PUT `/documents/{document_id}`

Atualiza metadados do documento.

**Request Body:**
```json
{
  "title": "Novo Título",
  "description": "Nova descrição",
  "document_type": "contract",
  "reference_date": "2025-01-01T00:00:00"
}
```

**Response 200:** Objeto atualizado

---

### DELETE `/documents/{document_id}`

Remove documento e arquivo.

**Response 204:** No Content

---

## 9. Posições Mensais

> **Permissão necessária:** `POSITIONS`

Snapshots mensais do patrimônio para evolução histórica.

### GET `/positions`

Lista posições mensais com paginação.

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| page | int | 1 | Página |
| per_page | int | 20 | Itens por página (max: 100) |
| client_id | string | - | Filtrar por cliente |
| year | int | - | Filtrar por ano |
| month | int | - | Filtrar por mês (1-12) |

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid_2025-01-31",
      "client_id": "uuid",
      "client_name": "João da Silva",
      "reference_date": "2025-01-31",
      "total_assets": "1500000.00",
      "total_liabilities": "350000.00",
      "net_worth": "1150000.00",
      "status": "processed",
      "created_at": "2025-02-01T00:00:00"
    }
  ],
  "total": 24,
  "page": 1,
  "per_page": 20,
  "pages": 2
}
```

---

### GET `/positions/{position_id}`

Busca posição por ID com snapshot completo.

**Formato do ID:** `{client_id}_{reference_date}` (ex: `uuid_2025-01-31`)

**Response 200:**
```json
{
  "id": "uuid_2025-01-31",
  "client_id": "uuid",
  "client_name": "João da Silva",
  "reference_date": "2025-01-31",
  "total_assets": "1500000.00",
  "total_liabilities": "350000.00",
  "net_worth": "1150000.00",
  "status": "processed",
  "snapshot": {
    "assets_by_category": {
      "renda_variavel": {
        "total": 800000.00,
        "items": [
          {
            "asset_id": "uuid",
            "name": "PETR4",
            "category": "renda_variavel",
            "value": 125000.00,
            "quantity": 1000,
            "currency": "BRL"
          }
        ]
      },
      "renda_fixa": {
        "total": 500000.00,
        "items": [...]
      }
    },
    "liabilities": {
      "total": 350000.00,
      "items": [
        {
          "liability_id": "uuid",
          "description": "Financiamento Imobiliário",
          "value": 300000.00,
          "currency": "BRL"
        }
      ]
    }
  },
  "created_at": "2025-02-01T00:00:00"
}
```

---

### POST `/positions`

Cria snapshot mensal para um cliente.

**Request Body:**
```json
{
  "client_id": "uuid-do-cliente",
  "reference_date": "2025-01-31"
}
```

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| client_id | string | Sim | UUID do cliente |
| reference_date | date | Sim | **Deve ser último dia do mês** |

**Response 201:** Objeto da posição criada com snapshot

**Response 400:**
```json
{
  "detail": "A data de referência deve ser o último dia do mês (2025-01-31)"
}
```

**Response 409:**
```json
{
  "detail": "Já existe um snapshot para este cliente/período"
}
```

---

### POST `/positions/generate-all`

Gera snapshots para todos os clientes ativos.

**Request Body:**
```json
{
  "reference_date": "2025-01-31",
  "overwrite": false
}
```

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| reference_date | date | Sim | Último dia do mês |
| overwrite | bool | Não | Se true, sobrescreve existentes |

**Response 200:**
```json
{
  "total_clients": 150,
  "total_generated": 145,
  "total_skipped": 5,
  "errors": [
    {
      "client_id": "uuid",
      "client_name": "Cliente com Erro",
      "error": "Mensagem de erro"
    }
  ]
}
```

---

### DELETE `/positions/{position_id}`

Remove posição mensal.

**Response 204:** No Content

---

## 10. Self-Service (Portal do Cliente)

> **Permissão necessária:** `MY_*` (somente role `client`)

### GET `/me/dashboard`

Dashboard do cliente com resumo patrimonial.

**Response 200:**
```json
{
  "client_id": "uuid",
  "client_name": "João da Silva",
  "data": {
    "net_worth": 1150000.00,
    "total_assets": 1500000.00,
    "total_liabilities": 350000.00,
    "composition": [
      {
        "category": "renda_variavel",
        "value": 800000.00,
        "percentage": 53.33
      },
      {
        "category": "renda_fixa",
        "value": 500000.00,
        "percentage": 33.33
      },
      {
        "category": "imoveis",
        "value": 200000.00,
        "percentage": 13.33
      }
    ]
  }
}
```

---

### GET `/me/assets`

Lista ativos do cliente logado.

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| category | string | - | Filtrar por categoria |

**Response 200:**
```json
{
  "client_id": "uuid",
  "total": 15,
  "assets": [
    {
      "id": "uuid",
      "name": "PETR4",
      "category": "renda_variavel",
      "subcategory": "acoes",
      "current_value": 125000.00,
      "base_value": 100000.00,
      "quantity": 1000,
      "currency": "BRL",
      "acquisition_date": "2024-06-01",
      "institution_name": "XP Investimentos"
    }
  ]
}
```

---

### GET `/me/liabilities`

Lista passivos do cliente logado.

**Response 200:**
```json
{
  "client_id": "uuid",
  "total": 2,
  "liabilities": [
    {
      "id": "uuid",
      "liability_type": "mortgage",
      "description": "Financiamento Imobiliário",
      "current_balance": 300000.00,
      "original_value": 500000.00,
      "monthly_payment": 5000.00,
      "interest_rate": 0.8,
      "start_date": "2020-01-01",
      "end_date": "2035-01-01",
      "institution_name": "Banco Itaú"
    }
  ]
}
```

---

### GET `/me/documents`

Lista documentos do cliente logado.

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| document_type | string | - | Filtrar por tipo |

**Response 200:**
```json
{
  "client_id": "uuid",
  "total": 10,
  "documents": [
    {
      "id": "uuid",
      "document_type": "statement",
      "title": "Extrato Dezembro 2024",
      "description": "Extrato mensal",
      "file_name": "extrato.pdf",
      "file_size": 125000,
      "mime_type": "application/pdf",
      "reference_date": "2024-12-31",
      "created_at": "2025-01-01T10:00:00"
    }
  ]
}
```

---

### GET `/me/documents/{document_id}/download`

Faz download de um documento do cliente.

**Response 200:** Arquivo binário

---

### GET `/me/evolution`

Evolução patrimonial mensal do cliente.

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| months | int | 12 | Número de meses (1-60) |

**Response 200:**
```json
{
  "client_id": "uuid",
  "period_months": 12,
  "data_points": 12,
  "variation": 150000.00,
  "variation_pct": 15.0,
  "evolution": [
    {
      "date": "2024-02-29",
      "total_assets": 1000000.00,
      "total_liabilities": 400000.00,
      "net_worth": 600000.00
    },
    {
      "date": "2024-03-31",
      "total_assets": 1050000.00,
      "total_liabilities": 390000.00,
      "net_worth": 660000.00
    }
  ]
}
```

---

### GET `/me/report/pdf`

Gera relatório PDF do patrimônio do cliente.

**Response 200:** Arquivo PDF para download

**Headers de Resposta:**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename=meu_relatorio_{data}.pdf
```

> **Nota:** Se a biblioteca `weasyprint` não estiver disponível, retorna HTML.

---

## 11. Controle de Acesso

### Roles e Permissões

| Role | Descrição | Permissões |
|------|-----------|------------|
| `admin` | Administrador | Acesso total |
| `rm` | Relationship Manager | Clientes atribuídos, ativos, passivos, contas |
| `analyst` | Analista | Leitura de todos os dados patrimoniais |
| `client` | Cliente | Apenas seus próprios dados via `/me` |

### Matriz de Acesso

| Endpoint | Admin | RM | Analyst | Client |
|----------|:-----:|:--:|:-------:|:------:|
| `/institutions` | ✅ CRUD | ✅ Read | ✅ Read | ❌ |
| `/clients` | ✅ Todos | ✅ Seus | ✅ Read | ❌ |
| `/accounts` | ✅ Todos | ✅ Seus clientes | ✅ Read | ❌ |
| `/assets` | ✅ Todos | ✅ Seus clientes | ✅ Read | ❌ |
| `/liabilities` | ✅ Todos | ✅ Seus clientes | ✅ Read | ❌ |
| `/documents` | ✅ CRUD | ✅ Upload/Read | ✅ Read | ❌ |
| `/positions` | ✅ CRUD | ✅ CRUD | ✅ Read | ❌ |
| `/users` | ✅ CRUD | ❌ | ❌ | ❌ |
| `/me/*` | ❌ | ❌ | ❌ | ✅ Seus |

---

## 12. Códigos de Erro

| Código | Descrição |
|--------|-----------|
| 200 | Sucesso |
| 201 | Criado com sucesso |
| 204 | No Content (DELETE sucesso) |
| 400 | Bad Request (dados inválidos, duplicidade) |
| 401 | Não autenticado |
| 403 | Sem permissão |
| 404 | Recurso não encontrado |
| 422 | Erro de validação (Pydantic) |
| 500 | Erro interno do servidor |

### Formato de Erro

```json
{
  "detail": "Mensagem de erro"
}
```

### Erro de Validação (422)

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "cpf_cnpj"],
      "msg": "Value error, CPF inválido",
      "input": "12345678901"
    }
  ]
}
```

---

## Headers Padrão

Todas as requisições (exceto `/auth/login`) devem incluir:

```
Authorization: Bearer {token}
Content-Type: application/json
```

---

## Notas de Implementação

1. **CPF/CNPJ:** São validados na criação/atualização de clientes e criptografados no banco (LGPD).

2. **Soft Delete:** Todas as exclusões são lógicas (marcam como inativo/inactive).

3. **Paginação:** Padrão com `page` e `per_page`. Resposta inclui `total` e `pages`.

4. **Campos Calculados:**
   - Ativos: `gain_loss`, `gain_loss_percent`
   - Passivos: `remaining_payments`, `total_to_pay`, `is_paid_off`
   - Clientes: `total_assets`, `total_liabilities`, `net_worth`

5. **Filtros por Role:**
   - RM só vê/edita clientes atribuídos a ele
   - Cliente só vê seus próprios dados
   - Admin e Analyst veem todos

---

*Última atualização: Dezembro 2025*

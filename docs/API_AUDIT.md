# API de Auditoria

Documentação do sistema de auditoria e logs para conformidade com LGPD.

---

## Visão Geral

O sistema Starke implementa auditoria automática de todas as ações sensíveis realizadas pelos usuários. Isso inclui:

- **Requisições HTTP** para endpoints sensíveis (clientes, ativos, documentos, etc.)
- **Autenticação** (login, logout, tentativas falhas)
- **Operações CRUD** em entidades do sistema
- **Exportações de dados**
- **Acessos negados**

### Conformidade LGPD

Os logs de auditoria são armazenados para atender aos requisitos da Lei Geral de Proteção de Dados:

- Registro de quem acessou dados pessoais
- Registro de quando e como os dados foram acessados
- Rastreabilidade de alterações em dados sensíveis
- Imutabilidade dos logs (não podem ser alterados ou excluídos)

---

## Arquitetura

### Middleware de Auditoria

O sistema usa um middleware que intercepta todas as requisições HTTP e registra automaticamente:

- **Request ID**: Identificador único para correlação de logs
- **Usuário**: ID e email do usuário autenticado
- **Ação**: Tipo de operação (create, read, update, delete, export)
- **Entidade**: Tipo e ID da entidade afetada
- **IP**: Endereço IP do cliente (com suporte a proxies)
- **User-Agent**: Identificação do navegador/cliente
- **Detalhes**: Query params, códigos de status, tempo de resposta

### Paths Auditados

| Tipo | Paths |
|------|-------|
| **Sempre auditados** | `/api/v1/clients`, `/api/v1/assets`, `/api/v1/liabilities`, `/api/v1/accounts`, `/api/v1/documents`, `/api/v1/positions` |
| **Operações mutáveis** | Todos os `POST`, `PUT`, `PATCH`, `DELETE` |
| **Autenticação** | Todos os paths contendo `/auth/` |

### Paths Excluídos

- `/health`
- `/docs`
- `/redoc`
- `/openapi.json`
- `/favicon.ico`

---

## Endpoints

### 1. Listar Logs de Auditoria

```http
GET /api/v1/audit/logs
Authorization: Bearer {token}
```

**Permissão:** Apenas `admin` e `analyst`

**Query Parameters:**

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `page` | int | Página (default: 1) |
| `per_page` | int | Itens por página (default: 50, max: 100) |
| `user_id` | int | Filtrar por ID do usuário |
| `action` | string | Filtrar por ação |
| `entity_type` | string | Filtrar por tipo de entidade |
| `entity_id` | string | Filtrar por ID da entidade |
| `ip_address` | string | Filtrar por endereço IP |
| `start_date` | datetime | Data inicial (ISO 8601) |
| `end_date` | datetime | Data final (ISO 8601) |

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": 1,
      "user_email": "admin@starke.com",
      "action": "read",
      "entity_type": "pat_clients",
      "entity_id": "123e4567-e89b-12d3-a456-426614174000",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0 ...",
      "details": {
        "request_id": "abc123",
        "method": "GET",
        "path": "/api/v1/clients/123e4567...",
        "status_code": 200,
        "duration_ms": 45
      },
      "created_at": "2025-12-08T10:30:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 50,
  "pages": 3
}
```

---

### 2. Buscar Log Específico

```http
GET /api/v1/audit/logs/{log_id}
Authorization: Bearer {token}
```

**Permissão:** Apenas `admin` e `analyst`

**Response (200 OK):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "user_email": "admin@starke.com",
  "action": "update",
  "entity_type": "pat_clients",
  "entity_id": "123e4567-e89b-12d3-a456-426614174000",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0 ...",
  "details": {
    "request_id": "abc123",
    "method": "PUT",
    "path": "/api/v1/clients/123e4567...",
    "status_code": 200,
    "duration_ms": 120
  },
  "created_at": "2025-12-08T10:30:00Z"
}
```

---

### 3. Estatísticas de Auditoria

```http
GET /api/v1/audit/stats
Authorization: Bearer {token}
```

**Permissão:** Apenas `admin` e `analyst`

**Query Parameters:**

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `days` | int | Número de dias para análise (default: 30, max: 365) |

**Response (200 OK):**

```json
{
  "total_actions": 5420,
  "actions_by_type": {
    "read": 4200,
    "create": 500,
    "update": 450,
    "delete": 50,
    "login": 180,
    "export": 40
  },
  "actions_by_entity": {
    "pat_clients": 2100,
    "pat_assets": 1800,
    "pat_documents": 900,
    "pat_accounts": 620
  },
  "top_users": [
    {
      "user_id": 1,
      "email": "admin@starke.com",
      "actions_count": 3200
    },
    {
      "user_id": 2,
      "email": "analyst@starke.com",
      "actions_count": 1500
    }
  ],
  "recent_logins": 45,
  "recent_failures": 3
}
```

---

### 4. Histórico de uma Entidade

```http
GET /api/v1/audit/entity/{entity_type}/{entity_id}
Authorization: Bearer {token}
```

**Permissão:** Apenas `admin` e `analyst`

**Parâmetros de Path:**

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `entity_type` | string | Tipo da entidade (ex: `pat_clients`, `pat_assets`) |
| `entity_id` | string (UUID) | ID da entidade |

**Query Parameters:**

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `page` | int | Página (default: 1) |
| `per_page` | int | Itens por página (default: 50) |

**Exemplo:**

```bash
GET /api/v1/audit/entity/pat_clients/550e8400-e29b-41d4-a716-446655440000
```

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "log-id-1",
      "user_id": 1,
      "user_email": "admin@starke.com",
      "action": "create",
      "entity_type": "pat_clients",
      "entity_id": "550e8400-e29b-41d4-a716-446655440000",
      "details": {
        "new_values": {
          "name": "João Silva",
          "email": "joao@email.com"
        }
      },
      "created_at": "2025-12-01T10:00:00Z"
    },
    {
      "id": "log-id-2",
      "user_id": 2,
      "user_email": "analyst@starke.com",
      "action": "update",
      "entity_type": "pat_clients",
      "entity_id": "550e8400-e29b-41d4-a716-446655440000",
      "details": {
        "old_values": {"phone": "11999998888"},
        "new_values": {"phone": "11999997777"}
      },
      "created_at": "2025-12-05T14:30:00Z"
    }
  ],
  "total": 2,
  "page": 1,
  "per_page": 50,
  "pages": 1
}
```

---

### 5. Atividade de um Usuário

```http
GET /api/v1/audit/user/{user_id}/activity
Authorization: Bearer {token}
```

**Permissão:** Apenas `admin` e `analyst`

**Parâmetros de Path:**

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `user_id` | int | ID do usuário |

**Query Parameters:**

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `page` | int | Página (default: 1) |
| `per_page` | int | Itens por página (default: 50) |
| `days` | int | Últimos N dias (default: 30) |

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "log-id-1",
      "user_id": 1,
      "user_email": "admin@starke.com",
      "action": "login",
      "entity_type": null,
      "entity_id": null,
      "ip_address": "192.168.1.100",
      "details": {
        "email": "admin@starke.com"
      },
      "created_at": "2025-12-08T08:00:00Z"
    },
    {
      "id": "log-id-2",
      "user_id": 1,
      "user_email": "admin@starke.com",
      "action": "read",
      "entity_type": "pat_clients",
      "entity_id": "550e8400-...",
      "ip_address": "192.168.1.100",
      "created_at": "2025-12-08T08:05:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 50,
  "pages": 3
}
```

---

## Tipos de Ações

| Ação | Descrição |
|------|-----------|
| `create` | Criação de registro |
| `read` | Leitura/visualização de registro |
| `update` | Atualização de registro |
| `delete` | Exclusão de registro |
| `export` | Exportação de dados |
| `login` | Login bem-sucedido |
| `logout` | Logout |
| `login_failed` | Tentativa de login falha |
| `password_reset` | Redefinição de senha |
| `permission_denied` | Acesso negado |

---

## Tipos de Entidades

| Tipo | Descrição |
|------|-----------|
| `pat_clients` | Clientes |
| `pat_assets` | Ativos |
| `pat_liabilities` | Passivos |
| `pat_accounts` | Contas |
| `pat_documents` | Documentos |
| `pat_institutions` | Instituições |
| `pat_monthly_positions` | Posições mensais |
| `users` | Usuários |
| `auth` | Autenticação |

---

## Exemplos de Uso

### Buscar todos os acessos a um cliente específico

```bash
curl -X GET "http://localhost:8000/api/v1/audit/entity/pat_clients/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer {token}"
```

### Buscar tentativas de login falhas nos últimos 7 dias

```bash
curl -X GET "http://localhost:8000/api/v1/audit/logs?action=login_failed&start_date=2025-12-01T00:00:00" \
  -H "Authorization: Bearer {token}"
```

### Monitorar atividade de um usuário suspeito

```bash
curl -X GET "http://localhost:8000/api/v1/audit/user/5/activity?days=7" \
  -H "Authorization: Bearer {token}"
```

### Obter estatísticas de auditoria do último mês

```bash
curl -X GET "http://localhost:8000/api/v1/audit/stats?days=30" \
  -H "Authorization: Bearer {token}"
```

---

## Considerações de Segurança

1. **Acesso Restrito**: Apenas usuários com role `admin` ou `analyst` podem acessar os logs de auditoria.

2. **Imutabilidade**: Os logs de auditoria são somente-leitura e não podem ser alterados ou excluídos.

3. **Dados Sensíveis**: Senhas e tokens não são registrados nos logs.

4. **Retenção**: Os logs devem ser retidos pelo período exigido pela LGPD (mínimo de 5 anos).

5. **IP Real**: O sistema detecta automaticamente o IP real do cliente mesmo quando atrás de proxies/load balancers (usando headers `X-Forwarded-For` e `X-Real-IP`).

---

## Integração com Frontend

### Tela de Logs de Auditoria (Admin)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Logs de Auditoria                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Filtros:                                                               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │ Usuário ▼    │ │ Ação ▼       │ │ Entidade ▼   │ │ Período ▼    │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Data/Hora    │ Usuário       │ Ação   │ Entidade │ IP          │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ 08/12 10:30  │ admin@...     │ read   │ Clientes │ 192.168.1.1 │   │
│  │ 08/12 10:25  │ analyst@...   │ update │ Ativos   │ 192.168.1.2 │   │
│  │ 08/12 10:20  │ admin@...     │ login  │ -        │ 192.168.1.1 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Mostrando 1-50 de 5420 registros                       [< 1 2 3 ... >] │
└─────────────────────────────────────────────────────────────────────────┘
```

### Dashboard de Estatísticas

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   Estatísticas de Auditoria (30 dias)                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐             │
│  │    5.420       │  │      45        │  │       3        │             │
│  │ Total Ações    │  │   Logins       │  │ Falhas Login   │             │
│  └────────────────┘  └────────────────┘  └────────────────┘             │
│                                                                          │
│  Ações por Tipo                    Entidades Mais Acessadas            │
│  ┌─────────────────────┐           ┌─────────────────────┐              │
│  │ ████████████ 78%    │ read      │ ██████████ 39%      │ Clientes    │
│  │ ██████ 9%           │ create    │ ████████ 33%        │ Ativos      │
│  │ █████ 8%            │ update    │ ████ 17%            │ Documentos  │
│  │ █ 1%                │ delete    │ ██ 11%              │ Contas      │
│  └─────────────────────┘           └─────────────────────┘              │
│                                                                          │
│  Usuários Mais Ativos                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. admin@starke.com - 3.200 ações                               │   │
│  │ 2. analyst@starke.com - 1.500 ações                             │   │
│  │ 3. manager@starke.com - 720 ações                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

*Última atualização: 2025-12-08*

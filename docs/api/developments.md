# API de Empreendimentos (Developments)

## Visão Geral

Esta API permite gerenciar empreendimentos (developments) do sistema, incluindo listagem, busca e ativação/desativação para sincronização.

**Base URL:** `/api/v1/developments`

**Autenticação:** Bearer Token (JWT) - Requer role `admin`

---

## Endpoints

### 1. Listar Empreendimentos

```
GET /api/v1/developments
```

Lista todos os empreendimentos com paginação e filtros.

#### Query Parameters

| Parâmetro | Tipo | Obrigatório | Default | Descrição |
|-----------|------|-------------|---------|-----------|
| `page` | integer | Não | 1 | Número da página (mínimo: 1) |
| `per_page` | integer | Não | 20 | Itens por página (1-100) |
| `is_active` | boolean | Não | - | Filtrar por status ativo/inativo |
| `origem` | string | Não | - | Filtrar por origem: `mega` ou `uau` |
| `search` | string | Não | - | Buscar por nome (case-insensitive) |

#### Response (200 OK)

```json
{
  "items": [
    {
      "id": 30779,
      "external_id": 2,
      "name": "JVF NEGOCIOS IMOBILIARIOS LTDA",
      "filial_id": 1010001,
      "centro_custo_id": null,
      "is_active": true,
      "origem": "uau",
      "created_at": "2026-01-10T14:30:00",
      "updated_at": "2026-01-12T16:08:37",
      "last_synced_at": "2026-01-12T15:00:00"
    }
  ],
  "total": 140,
  "page": 1,
  "per_page": 20,
  "pages": 7
}
```

#### Exemplos de Uso

```bash
# Listar todos os empreendimentos UAU
GET /api/v1/developments?origem=uau

# Listar apenas ativos
GET /api/v1/developments?is_active=true&origem=uau

# Buscar por nome
GET /api/v1/developments?search=JVF&origem=uau

# Paginação
GET /api/v1/developments?page=2&per_page=50
```

---

### 2. Buscar Empreendimento por ID

```
GET /api/v1/developments/{id}
```

Retorna os detalhes de um empreendimento específico.

#### Path Parameters

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `id` | integer | ID interno do empreendimento |

#### Response (200 OK)

```json
{
  "id": 30779,
  "external_id": 2,
  "name": "JVF NEGOCIOS IMOBILIARIOS LTDA",
  "filial_id": 1010001,
  "centro_custo_id": null,
  "is_active": true,
  "origem": "uau",
  "created_at": "2026-01-10T14:30:00",
  "updated_at": "2026-01-12T16:08:37",
  "last_synced_at": "2026-01-12T15:00:00"
}
```

#### Response (404 Not Found)

```json
{
  "detail": "Empreendimento não encontrado"
}
```

---

### 3. Ativar Empreendimento

```
PATCH /api/v1/developments/{id}/activate
```

Ativa um empreendimento para sincronização. Também ativa a filial associada.

#### Path Parameters

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `id` | integer | ID interno do empreendimento |

#### Response (200 OK)

```json
{
  "id": 30779,
  "name": "JVF NEGOCIOS IMOBILIARIOS LTDA",
  "is_active": true,
  "filial_id": 1010001,
  "filial_is_active": true,
  "message": "Empreendimento 'JVF NEGOCIOS IMOBILIARIOS LTDA' ativado com sucesso"
}
```

#### Response (400 Bad Request)

```json
{
  "detail": "Empreendimento 'JVF NEGOCIOS IMOBILIARIOS LTDA' já está ativo"
}
```

#### Response (404 Not Found)

```json
{
  "detail": "Empreendimento não encontrado"
}
```

---

### 4. Desativar Empreendimento

```
PATCH /api/v1/developments/{id}/deactivate
```

Desativa um empreendimento da sincronização. Também desativa a filial associada.

#### Path Parameters

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `id` | integer | ID interno do empreendimento |

#### Response (200 OK)

```json
{
  "id": 30779,
  "name": "JVF NEGOCIOS IMOBILIARIOS LTDA",
  "is_active": false,
  "filial_id": 1010001,
  "filial_is_active": false,
  "message": "Empreendimento 'JVF NEGOCIOS IMOBILIARIOS LTDA' desativado com sucesso"
}
```

#### Response (400 Bad Request)

```json
{
  "detail": "Empreendimento 'JVF NEGOCIOS IMOBILIARIOS LTDA' já está inativo"
}
```

---

## Schemas

### DevelopmentResponse

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | integer | ID interno do empreendimento |
| `external_id` | integer | ID original no sistema de origem (Mega ou UAU) |
| `name` | string | Nome do empreendimento |
| `filial_id` | integer \| null | ID da filial associada |
| `centro_custo_id` | integer \| null | ID do centro de custo |
| `is_active` | boolean | Se está ativo para sincronização |
| `origem` | string | Sistema de origem: `mega` ou `uau` |
| `created_at` | datetime | Data de criação |
| `updated_at` | datetime \| null | Data da última atualização |
| `last_synced_at` | datetime \| null | Data da última sincronização |

### DevelopmentListResponse

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `items` | array | Lista de empreendimentos |
| `total` | integer | Total de registros |
| `page` | integer | Página atual |
| `per_page` | integer | Itens por página |
| `pages` | integer | Total de páginas |

### DevelopmentActivateResponse

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | integer | ID do empreendimento |
| `name` | string | Nome do empreendimento |
| `is_active` | boolean | Status após a operação |
| `filial_id` | integer \| null | ID da filial |
| `filial_is_active` | boolean \| null | Status da filial após a operação |
| `message` | string | Mensagem de confirmação |

---

## Fluxo de Uso

### 1. Listar empreendimentos disponíveis para ativação

```
GET /api/v1/developments?origem=uau&is_active=false
```

### 2. Ativar um empreendimento selecionado

```
PATCH /api/v1/developments/30779/activate
```

### 3. Verificar empreendimentos ativos

```
GET /api/v1/developments?origem=uau&is_active=true
```

### 4. Desativar se necessário

```
PATCH /api/v1/developments/30779/deactivate
```

---

## Notas Importantes

1. **Sincronização:** Apenas empreendimentos com `is_active=true` serão processados durante a sincronização automática.

2. **Filial:** Ao ativar/desativar um empreendimento, a filial associada também é ativada/desativada automaticamente.

3. **Permissões:** Apenas usuários com role `admin` podem acessar esses endpoints.

4. **Origem:**
   - `mega` = Empreendimentos do sistema Mega ERP
   - `uau` = Empreendimentos do sistema UAU (Senior/Globaltec)

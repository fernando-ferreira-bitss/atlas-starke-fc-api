# API de Usuários - Documentação para Frontend

## Visão Geral

Este documento descreve as mudanças na API de usuários e o sistema de permissões por role.

---

## Roles Disponíveis

O sistema possui 4 roles estáticos:

| Role | Descrição |
|------|-----------|
| `admin` | Administrador do sistema - acesso total |
| `rm` | Relationship Manager - gerencia clientes atribuídos |
| `analyst` | Analista - acesso apenas leitura |
| `client` | Cliente - visualiza apenas seu próprio portfólio |

---

## Permissões por Role

### ADMIN
**Acesso completo ao sistema**

- Dashboard
- Relatórios (Cash Flow, Portfolio)
- Gestão de Usuários (CRUD completo)
- Scheduler
- Empreendimentos e Contratos
- Clientes (CRUD completo)
- Ativos (CRUD completo)
- Passivos (CRUD completo)
- Contas (CRUD completo)
- Instituições
- Posições (visualizar + importar)
- Documentos (CRUD completo)
- Auditoria
- Configurações

### RM (Relationship Manager)
**Gerencia clientes atribuídos a ele**

- Dashboard
- Relatórios (Cash Flow, Portfolio)
- Empreendimentos e Contratos (leitura)
- Meus Clientes (lista de clientes atribuídos)
- Clientes (criar e editar - são atribuídos automaticamente a ele)
- Ativos (criar e editar)
- Passivos (criar e editar)
- Contas (criar e editar)
- Instituições (leitura)
- Posições (visualizar + importar)
- Documentos (visualizar + upload)

### ANALYST
**Acesso somente leitura**

- Dashboard
- Relatórios (Cash Flow, Portfolio)
- Empreendimentos e Contratos (leitura)
- Clientes (leitura)
- Ativos (leitura)
- Passivos (leitura)
- Contas (leitura)
- Instituições (leitura)
- Posições (leitura)
- Documentos (leitura)

### CLIENT
**Visualiza apenas seu próprio portfólio**

- Meu Portfólio (visão consolidada)
- Meus Ativos
- Meus Passivos
- Meus Documentos
- Minha Evolução (histórico)

---

## API de Usuários

### Endpoints

| Método | Endpoint | Descrição | Permissão |
|--------|----------|-----------|-----------|
| GET | `/api/v1/users` | Lista usuários | `users` |
| POST | `/api/v1/users` | Criar usuário | `users.create` |
| GET | `/api/v1/users/{id}` | Buscar usuário | `users` |
| PUT | `/api/v1/users/{id}` | Atualizar usuário | `users.edit` |
| DELETE | `/api/v1/users/{id}` | Desativar usuário | `users.delete` |

---

## Schemas

### UserCreate (POST /api/v1/users)

```json
{
  "email": "string (required)",
  "full_name": "string (required, 1-255 chars)",
  "password": "string (required, 6-100 chars)",
  "role": "string (default: 'analyst', enum: admin|rm|analyst|client)",
  "client_id": "string (UUID, obrigatório quando role=client)"
}
```

**Regras de Validação:**
- Quando `role=client`, o campo `client_id` é **obrigatório**
- Quando `role!=client`, o campo `client_id` **não pode ser informado**
- O `client_id` deve ser um cliente existente (pat_clients.id)
- O cliente não pode estar vinculado a outro usuário

### UserUpdate (PUT /api/v1/users/{id})

```json
{
  "email": "string (optional)",
  "full_name": "string (optional, 1-255 chars)",
  "role": "string (optional, enum: admin|rm|analyst|client)",
  "is_active": "boolean (optional)",
  "client_id": "string (UUID, opcional - para vincular/trocar cliente)"
}
```

**Regras de Validação:**
- Ao mudar `role` para `client`:
  - Se não há cliente vinculado, `client_id` é **obrigatório**
  - Se já há cliente vinculado, pode omitir (mantém o atual)
  - Se informar novo `client_id`, troca o vínculo
- Ao mudar `role` de `client` para outra role:
  - O cliente é automaticamente **desvinculado**
- Apenas **admin** pode alterar roles

### UserResponse

```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "Nome Completo",
  "role": "client",
  "is_active": true,
  "is_superuser": false,
  "client_id": "uuid-do-cliente",
  "client_name": "Nome do Cliente",
  "created_at": "2025-12-08T10:00:00",
  "updated_at": "2025-12-08T12:00:00"
}
```

**Novos campos:**
- `client_id`: ID do cliente vinculado (null se não for role=client)
- `client_name`: Nome do cliente vinculado (null se não for role=client)

---

## Exemplos de Uso

### Criar usuário Admin

```json
POST /api/v1/users
{
  "email": "admin@empresa.com",
  "full_name": "Administrador",
  "password": "senha123",
  "role": "admin"
}
```

### Criar usuário Cliente (vinculado a um cliente)

```json
POST /api/v1/users
{
  "email": "joao@email.com",
  "full_name": "João Silva",
  "password": "senha123",
  "role": "client",
  "client_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Alterar usuário de Analyst para Client

```json
PUT /api/v1/users/5
{
  "role": "client",
  "client_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Alterar usuário de Client para RM

```json
PUT /api/v1/users/5
{
  "role": "rm"
}
// O cliente será automaticamente desvinculado
```

### Trocar cliente vinculado

```json
PUT /api/v1/users/5
{
  "client_id": "novo-uuid-do-cliente"
}
// Só funciona se o usuário já é role=client
```

---

## Erros Comuns

| Código | Mensagem | Causa |
|--------|----------|-------|
| 400 | `client_id é obrigatório quando role=client` | Tentou criar/atualizar para role=client sem informar client_id |
| 400 | `client_id só pode ser informado quando role=client` | Tentou informar client_id para role diferente de client |
| 400 | `Cliente não encontrado: {id}` | O client_id informado não existe |
| 400 | `Este cliente já está vinculado a outro usuário` | O cliente já tem user_id preenchido |
| 400 | `client_id é obrigatório ao alterar role para client` | Alterou role para client mas não informou client_id e não havia vínculo anterior |
| 403 | `Only admin can change user roles` | Apenas admin pode alterar roles |

---

## Fluxo Recomendado no Frontend

### Tela de Criação de Usuário

1. Exibir campo `role` como select/dropdown
2. Quando `role === 'client'`:
   - Exibir campo `client_id` (select de clientes)
   - Marcar como **obrigatório**
   - Filtrar apenas clientes sem vínculo (`has_login === false`)
3. Quando `role !== 'client'`:
   - Ocultar campo `client_id`

### Tela de Edição de Usuário

1. Exibir role atual
2. Se role atual é `client`:
   - Exibir nome do cliente vinculado
   - Permitir trocar cliente (select de clientes disponíveis)
3. Se alterando role para `client`:
   - Exibir campo para selecionar cliente
4. Se alterando role de `client` para outro:
   - Exibir aviso: "O cliente será desvinculado"

### Lista de Usuários

- Exibir coluna `Client` com nome do cliente (se houver)
- Ou "-" se não houver vínculo

---

## Relacionamento RM → Clientes

O RM (Relationship Manager) gerencia clientes atribuídos a ele através do campo `rm_user_id` na tabela de clientes.

### Estrutura

```
Tabela: pat_clients
- rm_user_id: FK → users.id (ID do RM responsável pelo cliente)
```

### Comportamento na Criação de Cliente

| Quem cria | Campo `rm_user_id` |
|-----------|-------------------|
| **Admin** | Pode informar manualmente ou deixar vazio |
| **RM** | Automaticamente atribuído ao RM que está criando |

### Comportamento na Listagem

| Role | O que vê |
|------|----------|
| **Admin** | Todos os clientes |
| **RM** | Apenas clientes onde `rm_user_id = seu_id` |
| **Analyst** | Todos os clientes (somente leitura) |
| **Client** | Apenas seu próprio registro |

### Alteração de RM Responsável

- **Admin**: Pode alterar `rm_user_id` de qualquer cliente
- **RM**: Não pode alterar (clientes ficam atribuídos a ele)

### API de Clientes

**Criar cliente (POST /api/v1/clients)**
```json
{
  "name": "Nome do Cliente",
  "client_type": "pf|pj|family|company",
  "cpf_cnpj": "12345678901",
  "email": "cliente@email.com",
  "phone": "(11) 99999-9999",
  "rm_user_id": 6  // Opcional para Admin, ignorado para RM
}
```

**Atualizar cliente (PUT /api/v1/clients/{id})**
```json
{
  "rm_user_id": 7  // Apenas Admin pode alterar
}
```

---

## Endpoints Auxiliares para o Frontend

### Listar RMs (para select de RM responsável)

```
GET /api/v1/users?role=rm
```

**Response:**
```json
{
  "items": [
    {
      "id": 6,
      "email": "rm1@starke.com.br",
      "full_name": "Carlos Silva",
      "role": "rm",
      "is_active": true
    }
  ],
  "total": 3,
  "page": 1,
  "per_page": 20,
  "pages": 1
}
```

**Uso no frontend:** Popular select de "RM Responsável" no cadastro/edição de cliente.

---

### Listar Clientes Disponíveis (sem login vinculado)

```
GET /api/v1/clients?has_login=false&status=active
```

**Response:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "João Silva",
      "client_type": "pf",
      "has_login": false,
      "user_id": null
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 20,
  "pages": 1
}
```

**Uso no frontend:** Popular select de "Cliente" no cadastro de usuário com role=client.

---

### Listar Clientes por RM

```
GET /api/v1/clients?rm_user_id=6
```

**Uso no frontend:** Listar clientes de um RM específico.

---

## Resumo dos Vínculos

| Vínculo | Campo | Tabela | Descrição |
|---------|-------|--------|-----------|
| **RM → Cliente** | `rm_user_id` | `pat_clients` | RM responsável pelo cliente |
| **Usuário → Cliente** | `user_id` | `pat_clients` | Login do cliente no sistema |

### Diagrama

```
┌─────────────┐         ┌─────────────┐
│   users     │         │ pat_clients │
├─────────────┤         ├─────────────┤
│ id          │◄────────│ rm_user_id  │  (RM gerencia o cliente)
│ email       │         │             │
│ role = 'rm' │         │             │
└─────────────┘         │             │
                        │             │
┌─────────────┐         │             │
│   users     │         │             │
├─────────────┤         │             │
│ id          │◄────────│ user_id     │  (Cliente faz login)
│ email       │         │             │
│ role='client│         │             │
└─────────────┘         └─────────────┘
```

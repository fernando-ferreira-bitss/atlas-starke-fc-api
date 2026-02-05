# API de Clientes - Vínculo com RM

Documentação para implementação do vínculo Cliente-RM no frontend.

---

## Visão Geral

Cada cliente pode ter um **RM (Relationship Manager)** responsável por gerenciá-lo. O vínculo é feito através do campo `rm_user_id` na tabela de clientes.

---

## Comportamento por Role

### Criação de Cliente

| Quem cria | Campo `rm_user_id` |
|-----------|-------------------|
| **Admin** | Opcional - pode informar manualmente ou deixar vazio |
| **RM** | **Ignorado** - sistema atribui automaticamente ao RM que está criando |
| **Analyst** | Não tem permissão para criar clientes |

### Edição de Cliente

| Quem edita | Campo `rm_user_id` |
|------------|-------------------|
| **Admin** | Pode alterar para qualquer RM ou remover (null) |
| **RM** | **Não pode alterar** - retorna erro 403 |

### Listagem de Clientes

| Role | O que vê |
|------|----------|
| **Admin** | Todos os clientes |
| **RM** | Apenas clientes onde `rm_user_id = seu_id` |
| **Analyst** | Todos os clientes (somente leitura) |
| **Client** | Apenas seu próprio registro |

---

## Endpoints

### Listar RMs Disponíveis

```http
GET /api/v1/users?role=rm&is_active=true
```

**Use para:** Popular select de "RM Responsável" no cadastro/edição de cliente.

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
    },
    {
      "id": 7,
      "email": "rm2@starke.com.br",
      "full_name": "Maria Santos",
      "role": "rm",
      "is_active": true
    }
  ],
  "total": 2,
  "page": 1,
  "per_page": 20,
  "pages": 1
}
```

### Criar Cliente

```http
POST /api/v1/clients
Content-Type: application/json
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "name": "João Silva",
  "client_type": "pf",
  "cpf_cnpj": "123.456.789-09",
  "email": "joao@email.com",
  "phone": "(11) 99999-9999",
  "rm_user_id": 6,
  "status": "active"
}
```

**Campos:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `name` | string | Sim | Nome do cliente (1-255 chars) |
| `client_type` | string | Sim | Tipo: `pf`, `pj`, `family`, `company` |
| `cpf_cnpj` | string | Sim | CPF (11 dígitos) ou CNPJ (14 dígitos) |
| `email` | string | Não* | Email do cliente (*obrigatório se `create_login` for informado) |
| `phone` | string | Não | Telefone |
| `base_currency` | string | Não | Moeda base (default: `BRL`) |
| `notes` | string | Não | Observações |
| `rm_user_id` | int | Não | ID do RM responsável |
| `status` | string | Não | Status: `active`, `inactive`, `pending` (default: `active`) |
| `create_login` | object | Não | Se informado, cria usuário junto com o cliente |
| `create_login.password` | string | Sim* | Senha do usuário (6-100 chars, *obrigatório dentro de create_login) |

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "João Silva",
  "client_type": "pf",
  "cpf_cnpj": "123.456.789-09",
  "email": "joao@email.com",
  "phone": "(11) 99999-9999",
  "base_currency": "BRL",
  "notes": null,
  "status": "active",
  "rm_user_id": 6,
  "rm_user_name": "Carlos Silva",
  "user_id": null,
  "user_email": null,
  "has_login": false,
  "created_at": "2025-12-08T10:00:00",
  "updated_at": null
}
```

---

### Criar Cliente COM Login (Novo!)

Ao criar o cliente, você pode já criar o usuário de acesso para ele, informando apenas a senha:

```http
POST /api/v1/clients
Content-Type: application/json
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "name": "João Silva",
  "client_type": "pf",
  "cpf_cnpj": "123.456.789-09",
  "email": "joao@email.com",
  "phone": "(11) 99999-9999",
  "rm_user_id": 6,
  "create_login": {
    "password": "senha123"
  }
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "João Silva",
  "client_type": "pf",
  "cpf_cnpj": "123.456.789-09",
  "email": "joao@email.com",
  "phone": "(11) 99999-9999",
  "base_currency": "BRL",
  "notes": null,
  "status": "active",
  "rm_user_id": 6,
  "rm_user_name": "Carlos Silva",
  "user_id": 15,
  "user_email": "joao@email.com",
  "has_login": true,
  "created_at": "2025-12-08T10:00:00",
  "updated_at": null
}
```

**O que acontece:**
1. Cliente é criado com os dados informados
2. Usuário é criado com:
   - `email`: mesmo email do cliente
   - `full_name`: mesmo nome do cliente
   - `password`: senha informada em `create_login.password`
   - `role`: `client` (fixo)
3. Cliente é automaticamente vinculado ao usuário criado

**Validações:**
- `email` é **obrigatório** quando `create_login` é informado
- Email não pode estar já cadastrado como usuário

### Atualizar Cliente (Alterar RM)

```http
PUT /api/v1/clients/{client_id}
Content-Type: application/json
Authorization: Bearer {token}
```

**Request Body (apenas campos a alterar):**
```json
{
  "rm_user_id": 7
}
```

**Response (200 OK):** Mesmo formato do POST.

### Listar Clientes sem Login (disponíveis para vincular)

```http
GET /api/v1/clients?has_login=false&status=active
```

**Use para:** Popular select de "Cliente" no cadastro de usuário com role=client.

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

### Listar Clientes por RM

```http
GET /api/v1/clients?rm_user_id=6
```

**Use para:** Visualizar clientes de um RM específico (somente Admin pode usar este filtro).

---

## Fluxo Recomendado no Frontend

### Tela de Criação de Cliente

```
┌─────────────────────────────────────────────────────────┐
│                   Novo Cliente                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Nome: [________________________]                       │
│                                                         │
│  Tipo:  ○ Pessoa Física   ○ Pessoa Jurídica            │
│         ○ Family Office   ○ Empresa                     │
│                                                         │
│  CPF/CNPJ: [________________________]                   │
│                                                         │
│  Email: [________________________]                      │
│                                                         │
│  Telefone: [________________________]                   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ RM Responsável (opcional)                        │   │
│  │                                                  │   │
│  │  [▼ Selecione um RM                        ]    │   │
│  │     - Carlos Silva (rm1@starke.com.br)          │   │
│  │     - Maria Santos (rm2@starke.com.br)          │   │
│  │     - (Nenhum)                                   │   │
│  │                                                  │   │
│  │  * Campo visível apenas para Admin              │   │
│  │  * Para RM, o cliente é vinculado               │   │
│  │    automaticamente                              │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│                        [Cancelar]  [Salvar]            │
└─────────────────────────────────────────────────────────┘
```

### Lógica de Exibição do Campo RM

```javascript
// Pseudocódigo
const currentUser = getCurrentUser();

// Só exibe select de RM se for Admin
const showRmSelect = currentUser.role === 'admin';

// Se for RM, o campo é preenchido automaticamente (não precisa enviar)
// O backend ignora rm_user_id enviado por RM e usa o ID do usuário logado
```

### Tela de Edição de Cliente

```
┌─────────────────────────────────────────────────────────┐
│                   Editar Cliente                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Nome: [João Silva_____________________]                │
│                                                         │
│  CPF/CNPJ: 123.456.789-09 (não editável)               │
│                                                         │
│  Email: [joao@email.com________________]               │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ RM Responsável                                   │   │
│  │                                                  │   │
│  │  Atual: Carlos Silva                            │   │
│  │                                                  │   │
│  │  [▼ Alterar para...                        ]    │   │  ← Só Admin
│  │     - Carlos Silva (atual)                      │   │
│  │     - Maria Santos                              │   │
│  │     - (Remover RM)                              │   │
│  │                                                  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│                        [Cancelar]  [Salvar]            │
└─────────────────────────────────────────────────────────┘
```

### Lista de Clientes

| Nome | CPF/CNPJ | Tipo | RM Responsável | Status | Ações |
|------|----------|------|----------------|--------|-------|
| João Silva | ***.456.789-** | PF | Carlos Silva | Ativo | ✏️ 🗑️ |
| Maria Santos | **.123.456/****-** | PJ | - | Ativo | ✏️ 🗑️ |

---

## Erros Comuns

| Código | Mensagem | Causa |
|--------|----------|-------|
| 400 | `CPF/CNPJ já cadastrado` | CPF/CNPJ duplicado |
| 400 | `CPF inválido` | Dígitos verificadores do CPF incorretos |
| 400 | `CNPJ inválido` | Dígitos verificadores do CNPJ incorretos |
| 400 | `Email é obrigatório para criar login do cliente` | `create_login` foi informado mas `email` está vazio |
| 400 | `Este email já está cadastrado como usuário` | Email já existe na tabela de usuários |
| 403 | `RM não pode alterar atribuição de cliente` | RM tentou alterar `rm_user_id` |
| 404 | `Cliente não encontrado` | ID inválido ou sem permissão de acesso |

---

## Exemplos de Código

### React - Carregar RMs para Select

```typescript
interface User {
  id: number;
  full_name: string;
  email: string;
}

async function loadRMs(): Promise<User[]> {
  const response = await fetch('/api/v1/users?role=rm&is_active=true', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  const data = await response.json();
  return data.items;
}
```

### React - Criar Cliente com RM

```typescript
interface CreateClientData {
  name: string;
  client_type: 'pf' | 'pj' | 'family' | 'company';
  cpf_cnpj: string;
  email?: string;
  phone?: string;
  rm_user_id?: number;
}

async function createClient(data: CreateClientData) {
  const response = await fetch('/api/v1/clients', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }

  return response.json();
}
```

### React - Componente Select de RM

```tsx
interface RMSelectProps {
  value?: number;
  onChange: (rmId: number | null) => void;
  disabled?: boolean;
}

function RMSelect({ value, onChange, disabled }: RMSelectProps) {
  const [rms, setRms] = useState<User[]>([]);
  const currentUser = useCurrentUser();

  useEffect(() => {
    loadRMs().then(setRms);
  }, []);

  // Só Admin pode ver/usar este select
  if (currentUser.role !== 'admin') {
    return null;
  }

  return (
    <div className="form-group">
      <label>RM Responsável</label>
      <select
        value={value || ''}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
        disabled={disabled}
      >
        <option value="">Nenhum</option>
        {rms.map((rm) => (
          <option key={rm.id} value={rm.id}>
            {rm.full_name} ({rm.email})
          </option>
        ))}
      </select>
    </div>
  );
}
```

---

## Diagrama de Relacionamento

```
┌─────────────────────────────────────────────────────────────────┐
│                           users                                  │
├─────────────────────────────────────────────────────────────────┤
│ id=6  │ role='rm'     │ full_name='Carlos Silva'               │
│ id=7  │ role='rm'     │ full_name='Maria Santos'               │
│ id=10 │ role='client' │ full_name='João Silva'                 │
└───┬───────────────────────────────────────────────────────┬─────┘
    │                                                       │
    │ rm_user_id                                   user_id │
    ▼                                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        pat_clients                               │
├─────────────────────────────────────────────────────────────────┤
│ id='abc-123' │ name='João Silva' │ rm_user_id=6 │ user_id=10   │
│              │                    │              │               │
│              │ RM responsável: Carlos Silva (id=6)              │
│              │ Login: João Silva (id=10, role=client)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Checklist de Implementação

### Tela de Criação de Cliente

- [ ] Carregar lista de RMs ao abrir a tela (`GET /api/v1/users?role=rm&is_active=true`)
- [ ] Exibir select de RM apenas se usuário logado for Admin
- [ ] Enviar `rm_user_id` no POST se selecionado
- [ ] Tratar erros de validação (CPF/CNPJ inválido, duplicado)

### Tela de Edição de Cliente

- [ ] Exibir nome do RM atual (`rm_user_name`)
- [ ] Permitir alteração de RM apenas se usuário for Admin
- [ ] Tratar erro 403 se RM tentar alterar atribuição

### Lista de Clientes

- [ ] Exibir coluna "RM Responsável" com `rm_user_name`
- [ ] Adicionar filtro por RM (dropdown) - apenas para Admin
- [ ] Mostrar "-" quando `rm_user_id` for null

---

## Validações de CPF/CNPJ

O backend valida os dígitos verificadores de CPF e CNPJ. Formatos aceitos:

**CPF:**
- `12345678909` (apenas números)
- `123.456.789-09` (formatado)

**CNPJ:**
- `12345678000190` (apenas números)
- `12.345.678/0001-90` (formatado)

---

*Última atualização: 2025-12-08*

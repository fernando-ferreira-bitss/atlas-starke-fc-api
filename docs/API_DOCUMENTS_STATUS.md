# API de Documentos - Status e Validação

Documentação para implementação do status de validação de documentos no frontend.

---

## Visão Geral

Cada documento enviado pode ter um **status de validação** que indica se foi revisado e aprovado por um usuário autorizado (Admin ou RM).

### Status Disponíveis

| Status | Descrição | Badge Sugerido |
|--------|-----------|----------------|
| `pending` | Aguardando validação | Amarelo/Laranja |
| `validated` | Documento validado/aprovado | Verde |
| `rejected` | Documento rejeitado | Vermelho |

---

## Comportamento por Role

### Quem pode validar documentos?

| Role | Pode validar? |
|------|---------------|
| **Admin** | Sim |
| **RM** | Sim (apenas documentos de seus clientes) |
| **Analyst** | Não |
| **Client** | Não |

---

## Endpoints

### 1. Listar Documentos (com filtro de status)

```http
GET /api/v1/documents?status={status}
```

**Query Parameters:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `page` | int | Não | Página (default: 1) |
| `per_page` | int | Não | Itens por página (default: 20, max: 100) |
| `client_id` | string | Não | Filtrar por cliente |
| `document_type` | string | Não | Filtrar por tipo (contract, report, etc.) |
| `status` | string | Não | Filtrar por status: `pending`, `validated`, `rejected` |
| `start_date` | string | Não | Data inicial (YYYY-MM-DD) |
| `end_date` | string | Não | Data final (YYYY-MM-DD) |

**Exemplo de Request:**
```http
GET /api/v1/documents?status=pending&client_id=550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "client_id": "550e8400-e29b-41d4-a716-446655440000",
      "client_name": "João Silva",
      "account_id": null,
      "asset_id": null,
      "document_type": "contract",
      "title": "Contrato de Investimento",
      "description": "Contrato assinado em 2025",
      "file_name": "contrato_joao.pdf",
      "s3_key": "550e8400.../contract/abc123.pdf",
      "file_size": 1048576,
      "mime_type": "application/pdf",
      "reference_date": "2025-01-15T00:00:00",
      "uploaded_by": 5,
      "uploader_name": "Maria Admin",
      "status": "pending",
      "validated_by": null,
      "validator_name": null,
      "validated_at": null,
      "validation_notes": null,
      "created_at": "2025-12-08T10:00:00",
      "updated_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20,
  "pages": 1
}
```

---

### 2. Obter Documento por ID

```http
GET /api/v1/documents/{document_id}
```

**Response (200 OK):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_name": "João Silva",
  "document_type": "contract",
  "title": "Contrato de Investimento",
  "file_name": "contrato_joao.pdf",
  "status": "validated",
  "validated_by": 6,
  "validator_name": "Carlos RM",
  "validated_at": "2025-12-08T14:30:00",
  "validation_notes": "Documento verificado e aprovado",
  "created_at": "2025-12-08T10:00:00",
  "updated_at": "2025-12-08T14:30:00"
}
```

---

### 3. Validar/Rejeitar Documento

```http
PUT /api/v1/documents/{document_id}/validate
Content-Type: application/json
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "status": "validated",
  "validation_notes": "Documento verificado e aprovado"
}
```

**Campos:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `status` | string | Sim | Novo status: `pending`, `validated`, `rejected` |
| `validation_notes` | string | Não | Notas/observações da validação |

**Response (200 OK):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_name": "João Silva",
  "document_type": "contract",
  "title": "Contrato de Investimento",
  "status": "validated",
  "validated_by": 6,
  "validator_name": "Carlos RM",
  "validated_at": "2025-12-08T14:30:00",
  "validation_notes": "Documento verificado e aprovado",
  "created_at": "2025-12-08T10:00:00",
  "updated_at": "2025-12-08T14:30:00"
}
```

**Comportamento:**
- Quando `status` é `validated` ou `rejected`:
  - `validated_by` é preenchido com o ID do usuário que validou
  - `validated_at` é preenchido com a data/hora atual
- Quando `status` volta para `pending`:
  - `validated_by` é limpo (null)
  - `validated_at` é limpo (null)

---

## Erros Comuns

| Código | Mensagem | Causa |
|--------|----------|-------|
| 403 | `Apenas administradores e RMs podem validar documentos` | Analyst ou Client tentou validar |
| 404 | `Documento não encontrado` | ID inválido ou sem permissão de acesso |
| 404 | `Cliente não encontrado` | RM tentando acessar documento de cliente de outro RM |

---

## Fluxo Recomendado no Frontend

### Tela de Lista de Documentos

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Documentos                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Filtros:                                                                │
│  [▼ Todos os Status    ] [▼ Todos os Tipos    ] [▼ Todos os Clientes ]  │
│      - Todos os Status                                                   │
│      - Pendente                                                          │
│      - Validado                                                          │
│      - Rejeitado                                                         │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│ Título              │ Cliente      │ Tipo     │ Status     │ Ações     │
├─────────────────────────────────────────────────────────────────────────┤
│ Contrato 2025       │ João Silva   │ Contrato │ 🟡 Pendente│ ✓ ✗ 👁 ⬇  │
│ Extrato Janeiro     │ Maria Santos │ Extrato  │ 🟢 Validado│    👁 ⬇   │
│ Comprovante         │ João Silva   │ Outro    │ 🔴 Rejeitado│ ✓   👁 ⬇  │
└─────────────────────────────────────────────────────────────────────────┘

Legenda:
✓ = Validar    ✗ = Rejeitar    👁 = Visualizar    ⬇ = Download
```

### Ações de Validação

**Botões visíveis apenas para Admin e RM:**

| Status Atual | Ações Disponíveis |
|--------------|-------------------|
| `pending` | Validar (✓), Rejeitar (✗) |
| `validated` | Rejeitar (✗), Voltar para Pendente |
| `rejected` | Validar (✓), Voltar para Pendente |

### Modal de Validação

```
┌─────────────────────────────────────────────────────────────────┐
│                     Validar Documento                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Documento: Contrato de Investimento 2025                       │
│  Cliente: João Silva                                             │
│  Enviado por: Maria Admin em 08/12/2025 às 10:00                │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Notas da validação (opcional):                          │    │
│  │                                                          │    │
│  │ [____________________________________________________]  │    │
│  │                                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│            [Cancelar]  [🔴 Rejeitar]  [🟢 Validar]             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Exemplos de Código

### React - Componente de Badge de Status

```tsx
interface StatusBadgeProps {
  status: 'pending' | 'validated' | 'rejected';
}

const statusConfig = {
  pending: { label: 'Pendente', color: 'yellow', icon: '🟡' },
  validated: { label: 'Validado', color: 'green', icon: '🟢' },
  rejected: { label: 'Rejeitado', color: 'red', icon: '🔴' },
};

function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span className={`badge badge-${config.color}`}>
      {config.icon} {config.label}
    </span>
  );
}
```

### React - Função de Validação

```typescript
interface ValidateDocumentData {
  status: 'pending' | 'validated' | 'rejected';
  validation_notes?: string;
}

async function validateDocument(
  documentId: string,
  data: ValidateDocumentData
): Promise<Document> {
  const response = await fetch(`/api/v1/documents/${documentId}/validate`, {
    method: 'PUT',
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

// Uso:
await validateDocument('123e4567-...', {
  status: 'validated',
  validation_notes: 'Documento verificado e aprovado'
});
```

### React - Filtro de Status na Listagem

```typescript
interface DocumentFilters {
  status?: 'pending' | 'validated' | 'rejected';
  client_id?: string;
  document_type?: string;
}

async function listDocuments(
  page: number,
  perPage: number,
  filters: DocumentFilters
): Promise<PaginatedResponse<Document>> {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  });

  if (filters.status) params.append('status', filters.status);
  if (filters.client_id) params.append('client_id', filters.client_id);
  if (filters.document_type) params.append('document_type', filters.document_type);

  const response = await fetch(`/api/v1/documents?${params}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  return response.json();
}
```

### React - Componente de Ações (Admin/RM)

```tsx
interface DocumentActionsProps {
  document: Document;
  currentUserRole: string;
  onValidate: () => void;
  onReject: () => void;
}

function DocumentActions({ document, currentUserRole, onValidate, onReject }: DocumentActionsProps) {
  const canValidate = ['admin', 'rm'].includes(currentUserRole);

  if (!canValidate) {
    return null;
  }

  return (
    <div className="document-actions">
      {document.status !== 'validated' && (
        <button onClick={onValidate} className="btn btn-success btn-sm" title="Validar">
          ✓
        </button>
      )}
      {document.status !== 'rejected' && (
        <button onClick={onReject} className="btn btn-danger btn-sm" title="Rejeitar">
          ✗
        </button>
      )}
    </div>
  );
}
```

---

## Campos de Resposta

### Documento (DocumentResponse)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | string (UUID) | ID único do documento |
| `client_id` | string (UUID) | ID do cliente |
| `client_name` | string | Nome do cliente |
| `account_id` | string (UUID) | ID da conta (opcional) |
| `asset_id` | string (UUID) | ID do ativo (opcional) |
| `document_type` | string | Tipo: contract, report, statement, certificate, proof, other |
| `title` | string | Título do documento |
| `description` | string | Descrição (opcional) |
| `file_name` | string | Nome original do arquivo |
| `s3_key` | string | Caminho de armazenamento |
| `file_size` | int | Tamanho em bytes |
| `mime_type` | string | Tipo MIME do arquivo |
| `reference_date` | datetime | Data de referência (opcional) |
| `uploaded_by` | int | ID do usuário que fez upload |
| `uploader_name` | string | Nome do usuário que fez upload |
| **`status`** | string | Status de validação: pending, validated, rejected |
| **`validated_by`** | int | ID do usuário que validou |
| **`validator_name`** | string | Nome do usuário que validou |
| **`validated_at`** | datetime | Data/hora da validação |
| **`validation_notes`** | string | Notas da validação |
| `created_at` | datetime | Data de criação |
| `updated_at` | datetime | Data de atualização |

---

## Checklist de Implementação

### Lista de Documentos

- [ ] Adicionar coluna "Status" na tabela
- [ ] Implementar badge colorido por status
- [ ] Adicionar filtro dropdown por status
- [ ] Exibir botões de validação apenas para Admin/RM

### Detalhes do Documento

- [ ] Exibir status atual com badge
- [ ] Exibir informações de validação (quem validou, quando, notas)
- [ ] Adicionar botões de ação (Validar/Rejeitar)

### Modal de Validação

- [ ] Criar modal com campo de notas
- [ ] Implementar botões Validar e Rejeitar
- [ ] Atualizar lista após validação

### Geral

- [ ] Tratar erro 403 para usuários sem permissão
- [ ] Refresh automático da lista após validação
- [ ] Feedback visual (toast/snackbar) após ação

---

*Última atualização: 2025-12-08*

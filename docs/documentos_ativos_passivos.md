# Vinculacao de Documentos a Ativos e Passivos

## Resumo

Foi implementada a funcionalidade de vincular documentos a ativos e passivos no momento da criacao/atualizacao, bem como a exibicao dos documentos vinculados nas listagens.

---

## Endpoints Afetados

### 1. Criar Ativo (`POST /api/v1/assets`)

**Novo campo no body:**
```json
{
  "client_id": "uuid",
  "category": "renda_fixa",
  "name": "CDB Banco X",
  "current_value": 10000.00,
  "document_ids": ["doc-uuid-1", "doc-uuid-2"]  // OPCIONAL
}
```

O campo `document_ids` aceita um array de IDs de documentos ja existentes (previamente criados via `/api/v1/documents`). Os documentos serao vinculados ao ativo criado.

---

### 2. Atualizar Ativo (`PUT /api/v1/assets/{asset_id}`)

**Novo campo no body:**
```json
{
  "current_value": 12000.00,
  "document_ids": ["doc-uuid-3"]  // OPCIONAL - adiciona novos vinculos
}
```

**Comportamento:**
- Passar `document_ids` com IDs adiciona novos vinculos ao ativo
- **NAO remove documentos existentes** - para remover vinculos, usar a tela de documentos
- Passar array vazio `[]` nao faz nada

---

### 3. Criar Passivo (`POST /api/v1/liabilities`)

**Novo campo no body:**
```json
{
  "client_id": "uuid",
  "liability_type": "personal_loan",
  "description": "Emprestimo Pessoal",
  "original_amount": 50000.00,
  "current_balance": 45000.00,
  "document_ids": ["doc-uuid-1"]  // OPCIONAL
}
```

---

### 4. Atualizar Passivo (`PUT /api/v1/liabilities/{liability_id}`)

**Novo campo no body:**
```json
{
  "current_balance": 40000.00,
  "document_ids": ["doc-uuid-2"]  // OPCIONAL - adiciona novos vinculos
}
```

**Comportamento:** Mesmo do ativo - apenas adiciona, nao remove.

---

## Retorno nas Listagens

### Listagem Admin/RM (`GET /api/v1/assets` e `GET /api/v1/liabilities`)

Retorna todos os documentos vinculados:

```json
{
  "items": [
    {
      "id": "asset-uuid",
      "name": "CDB Banco X",
      "current_value": 10000.00,
      "documents": [
        {
          "id": "doc-uuid-1",
          "title": "Extrato Janeiro",
          "document_type": "extrato",
          "file_name": "extrato_jan.pdf",
          "created_at": "2025-12-01T10:00:00"
        },
        {
          "id": "doc-uuid-2",
          "title": "Contrato",
          "document_type": "contrato",
          "file_name": "contrato.pdf",
          "created_at": "2025-11-15T14:30:00"
        }
      ]
    }
  ]
}
```

---

### Listagem Cliente (`GET /api/v1/me/assets` e `GET /api/v1/me/liabilities`)

Retorna apenas o **ultimo documento vinculado** (mais recente por `created_at`):

```json
{
  "client_id": "client-uuid",
  "total": 5,
  "assets": [
    {
      "id": "asset-uuid",
      "name": "CDB Banco X",
      "current_value": 10000.00,
      "last_document": {
        "id": "doc-uuid-1",
        "title": "Extrato Janeiro",
        "document_type": "extrato",
        "file_name": "extrato_jan.pdf",
        "created_at": "2025-12-01T10:00:00"
      }
    },
    {
      "id": "asset-uuid-2",
      "name": "Acoes PETR4",
      "current_value": 5000.00,
      "last_document": null  // Sem documento vinculado
    }
  ]
}
```

---

## Fluxo de Uso

### Vincular documento ao criar ativo:

1. Fazer upload do documento via `POST /api/v1/documents`
2. Obter o `id` do documento criado
3. Criar o ativo passando o `document_ids` com o ID do documento

### Vincular documento a ativo existente:

1. Fazer upload do documento via `POST /api/v1/documents`
2. Obter o `id` do documento criado
3. Atualizar o ativo via `PUT /api/v1/assets/{id}` passando `document_ids`

### Desvincular documento:

- Usar a tela de documentos (`PUT /api/v1/documents/{id}`) para remover o vinculo
- Ou deletar o documento se nao for mais necessario

---

## Observacoes Importantes

1. **Documentos devem existir antes** - os IDs passados em `document_ids` devem ser de documentos ja criados
2. **Mesmo cliente** - o documento deve pertencer ao mesmo cliente do ativo/passivo
3. **Nao ha remocao automatica** - passar array vazio ou nao passar `document_ids` nao remove vinculos existentes
4. **Um documento pode ser vinculado a um ativo OU passivo** - nao ambos simultaneamente

---

## Tipos de Documento Sugeridos

- `extrato` - Extratos bancarios
- `contrato` - Contratos
- `comprovante` - Comprovantes de pagamento
- `nota_fiscal` - Notas fiscais
- `declaracao` - Declaracoes
- `outros` - Outros documentos

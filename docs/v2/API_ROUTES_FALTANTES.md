# API Routes Faltantes - Starke Consolid

Este documento especifica as rotas de API que precisam ser implementadas no backend para suportar todas as funcionalidades do frontend.

---

## 1. Documentos / Uploads (Admin)

### 1.1 Upload de Documento

```yaml
POST /api/v1/documents/upload
description: Upload de documento para um cliente
auth: required (admin)
content-type: multipart/form-data
body:
  file: binary (required)
  client_id: integer (required)
  category: string (comprovante | laudo | extrato | outro)
  description: string (optional)
response:
  201:
    id: integer
    filename: string
    original_filename: string
    url: string
    category: string
    client_id: integer
    description: string | null
    size: integer (bytes)
    mime_type: string
    created_at: datetime
    created_by: integer (user_id)
  400:
    detail: "Arquivo inválido ou categoria não permitida"
  413:
    detail: "Arquivo excede o tamanho máximo (10MB)"
```

### 1.2 Listar Documentos

```yaml
GET /api/v1/documents
description: Listar todos os documentos (admin)
auth: required (admin)
params:
  client_id: integer (optional) - filtrar por cliente
  category: string (optional) - filtrar por categoria
  start_date: YYYY-MM-DD (optional)
  end_date: YYYY-MM-DD (optional)
  skip: integer (default: 0)
  limit: integer (default: 50, max: 100)
response:
  200:
    data:
      - id: integer
        filename: string
        original_filename: string
        url: string
        category: string
        client_id: integer
        client_name: string
        description: string | null
        size: integer
        mime_type: string
        created_at: datetime
        created_by: integer
    total: integer
    skip: integer
    limit: integer
```

### 1.3 Download de Documento

```yaml
GET /api/v1/documents/{id}/download
description: Download do arquivo (admin)
auth: required (admin)
response:
  200:
    content-type: application/octet-stream
    content-disposition: attachment; filename="{original_filename}"
    body: binary
  404:
    detail: "Documento não encontrado"
```

### 1.4 Deletar Documento

```yaml
DELETE /api/v1/documents/{id}
description: Remover documento do sistema
auth: required (admin)
response:
  200:
    message: "Documento removido com sucesso"
  404:
    detail: "Documento não encontrado"
```

---

## 2. Self-Service - Documentos do Cliente

### 2.1 Listar Documentos do Cliente Logado

```yaml
GET /api/v1/me/documents
description: Documentos disponíveis para o cliente logado
auth: required (client)
params:
  category: string (optional)
  period: YYYY-MM (optional) - filtrar por mês de referência
  skip: integer (default: 0)
  limit: integer (default: 20)
response:
  200:
    data:
      - id: integer
        filename: string
        category: string
        description: string | null
        size: integer
        created_at: datetime
        period: string | null (YYYY-MM)
    total: integer
```

### 2.2 Download de Documento (Cliente)

```yaml
GET /api/v1/me/documents/{id}/download
description: Download de documento pelo próprio cliente
auth: required (client)
response:
  200:
    content-type: application/octet-stream
    content-disposition: attachment; filename="{filename}"
    body: binary
  403:
    detail: "Acesso negado a este documento"
  404:
    detail: "Documento não encontrado"
```

---

## 3. Evolução Patrimonial

### 3.1 Série Temporal do Patrimônio

```yaml
GET /api/v1/me/evolution
description: Série temporal de evolução patrimonial do cliente logado
auth: required (client)
params:
  start_date: YYYY-MM-DD (required)
  end_date: YYYY-MM-DD (required)
  granularity: string (daily | monthly) - default: monthly
response:
  200:
    client_id: integer
    base_currency: string (BRL)
    period:
      start: YYYY-MM-DD
      end: YYYY-MM-DD
    data:
      - date: YYYY-MM-DD
        total_assets: number
        total_liabilities: number
        net_worth: number
        assets_by_category:
          renda_fixa: number
          renda_variavel: number
          imoveis: number
          participacoes: number
          alternativos: number
          caixa: number
        variation:
          absolute: number (diferença vs período anterior)
          percentage: number (% vs período anterior)
    summary:
      initial_net_worth: number
      final_net_worth: number
      total_variation_absolute: number
      total_variation_percentage: number
```

### 3.2 Evolução Patrimonial (Admin)

```yaml
GET /api/v1/clients/{client_id}/evolution
description: Série temporal de evolução patrimonial de um cliente específico
auth: required (admin)
params:
  start_date: YYYY-MM-DD (required)
  end_date: YYYY-MM-DD (required)
  granularity: string (daily | monthly) - default: monthly
response:
  200:
    # Mesmo formato de /api/v1/me/evolution
```

---

## 4. Geração de Relatório PDF

### 4.1 Relatório Consolidado (Cliente)

```yaml
GET /api/v1/me/report/pdf
description: Gera PDF consolidado do patrimônio do cliente logado
auth: required (client)
params:
  period: YYYY-MM (required) - mês de referência
  sections: string (optional) - lista separada por vírgula
    # valores possíveis: summary, composition, evolution, liabilities, all
    # default: all
  language: string (optional) - pt-BR | en-US (default: pt-BR)
response:
  200:
    content-type: application/pdf
    content-disposition: attachment; filename="relatorio-patrimonio-{period}.pdf"
    body: binary
  400:
    detail: "Período inválido ou sem dados disponíveis"
```

### 4.2 Relatório Consolidado (Admin)

```yaml
GET /api/v1/clients/{client_id}/report/pdf
description: Gera PDF consolidado para um cliente específico
auth: required (admin)
params:
  period: YYYY-MM (required)
  sections: string (optional)
  language: string (optional)
response:
  200:
    # Mesmo formato de /api/v1/me/report/pdf
```

---

## 5. Posições Históricas (Snapshots)

### 5.1 Listar Posições Mensais

```yaml
GET /api/v1/positions
description: Listar snapshots de posições mensais
auth: required (admin)
params:
  client_id: integer (optional) - filtrar por cliente
  month: integer (1-12) (optional)
  year: integer (optional)
  status: string (processed | pending | error) (optional)
  skip: integer (default: 0)
  limit: integer (default: 50)
response:
  200:
    data:
      - id: integer
        client_id: integer
        client_name: string
        reference_date: YYYY-MM-DD (último dia do mês)
        total_assets: number
        total_liabilities: number
        net_worth: number
        status: string (processed | pending | error)
        snapshot: object | null (JSON com detalhamento)
        created_at: datetime
        updated_at: datetime
    total: integer
```

### 5.2 Detalhes de uma Posição

```yaml
GET /api/v1/positions/{id}
description: Detalhes completos de uma posição/snapshot
auth: required (admin)
response:
  200:
    id: integer
    client_id: integer
    client_name: string
    reference_date: YYYY-MM-DD
    total_assets: number
    total_liabilities: number
    net_worth: number
    status: string
    snapshot:
      assets_by_category:
        renda_fixa:
          total: number
          items:
            - asset_id: integer
              name: string
              value: number
              currency: string
        renda_variavel:
          total: number
          items: [...]
        # ... outras categorias
      liabilities:
        total: number
        items:
          - liability_id: integer
            description: string
            value: number
      entities:
        - entity_id: integer
          name: string
          type: string
          total_assets: number
          total_liabilities: number
    created_at: datetime
    updated_at: datetime
  404:
    detail: "Posição não encontrada"
```

### 5.3 Gerar Snapshot Manual

```yaml
POST /api/v1/positions
description: Criar snapshot mensal para um cliente (manual)
auth: required (admin)
body:
  client_id: integer (required)
  reference_date: YYYY-MM-DD (required) - deve ser último dia do mês
response:
  201:
    id: integer
    client_id: integer
    reference_date: YYYY-MM-DD
    status: "processed"
    message: "Snapshot gerado com sucesso"
  400:
    detail: "Data de referência inválida"
  409:
    detail: "Já existe um snapshot para este cliente/período"
```

### 5.4 Gerar Snapshots em Lote

```yaml
POST /api/v1/positions/generate-all
description: Gerar snapshots para todos os clientes ativos (job mensal)
auth: required (admin)
body:
  reference_date: YYYY-MM-DD (required) - deve ser último dia do mês
  overwrite: boolean (default: false) - sobrescrever existentes
response:
  200:
    total_clients: integer
    total_generated: integer
    total_skipped: integer (já existentes, se overwrite=false)
    errors:
      - client_id: integer
        client_name: string
        error: string
```

### 5.5 Deletar Snapshot

```yaml
DELETE /api/v1/positions/{id}
description: Remover um snapshot específico
auth: required (admin)
response:
  200:
    message: "Snapshot removido com sucesso"
  404:
    detail: "Posição não encontrada"
```

---

## 6. Melhorias nas Rotas Existentes

### 6.1 Composição com Filtros Adicionais

```yaml
GET /api/v1/me/composition
# Adicionar params:
params:
  category: string (optional) - filtrar por categoria
  entity_id: integer (optional) - filtrar por entidade
  min_value: number (optional) - valor mínimo
  currency: string (optional) - filtrar por moeda
```

### 6.2 Ativos com Histórico de Preços

```yaml
GET /api/v1/assets/{id}/history
description: Histórico de valores/preços de um ativo
auth: required (admin)
params:
  start_date: YYYY-MM-DD
  end_date: YYYY-MM-DD
response:
  200:
    asset_id: integer
    name: string
    history:
      - date: YYYY-MM-DD
        value: number
        price: number | null
        quantity: number | null
```

---

## 7. Notificações (Futuro)

### 7.1 Listar Notificações

```yaml
GET /api/v1/me/notifications
description: Notificações do usuário logado
auth: required
params:
  read: boolean (optional) - filtrar por lidas/não lidas
  skip: integer
  limit: integer
response:
  200:
    data:
      - id: integer
        type: string (document_available | report_ready | position_updated)
        title: string
        message: string
        read: boolean
        created_at: datetime
    unread_count: integer
    total: integer
```

### 7.2 Marcar como Lida

```yaml
PATCH /api/v1/me/notifications/{id}/read
description: Marcar notificação como lida
auth: required
response:
  200:
    message: "Notificação marcada como lida"
```

---

## Notas de Implementação

### Autenticação
Todas as rotas requerem autenticação via Bearer Token JWT no header:
```
Authorization: Bearer {access_token}
```

### Permissões
- **admin**: Usuários com `is_superuser=true` ou role específica
- **client**: Usuários comuns (clientes)

### Formato de Datas
- Datas: `YYYY-MM-DD`
- Datetime: `YYYY-MM-DDTHH:mm:ss.sssZ` (ISO 8601)
- Período mensal: `YYYY-MM`

### Paginação
Padrão de resposta paginada:
```json
{
  "data": [...],
  "total": 100,
  "skip": 0,
  "limit": 50
}
```

### Erros
Formato padrão de erro:
```json
{
  "detail": "Mensagem de erro descritiva"
}
```

### Upload de Arquivos
- Tamanho máximo: 10MB
- Tipos permitidos: PDF, PNG, JPG, JPEG, XLS, XLSX, CSV
- Armazenamento: S3 ou filesystem local (configurável)

---

## Prioridade de Implementação

1. **Alta** - Necessários para MVP:
   - Documentos/Uploads (Seção 1 e 2)
   - Evolução Patrimonial (Seção 3)
   - Posições Históricas - básico (5.1, 5.2, 5.3)

2. **Média** - Funcionalidades importantes:
   - Geração de PDF (Seção 4)
   - Geração em lote de posições (5.4)

3. **Baixa** - Melhorias futuras:
   - Notificações (Seção 7)
   - Melhorias em rotas existentes (Seção 6)

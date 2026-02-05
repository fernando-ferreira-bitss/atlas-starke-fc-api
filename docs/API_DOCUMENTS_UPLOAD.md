# API de Upload de Documentos

Documentação para implementação do upload de documentos (simples e múltiplo) no frontend.

---

## Visão Geral

A API de documentos suporta dois tipos de upload:
- **Upload simples**: Envia um arquivo por vez com metadados específicos
- **Upload múltiplo**: Envia vários arquivos de uma vez com metadados compartilhados

### Limites e Formatos

| Configuração | Valor |
|--------------|-------|
| Tamanho máximo por arquivo | 10 MB |
| Formatos permitidos | PDF, PNG, JPG, JPEG, XLS, XLSX, CSV, DOC, DOCX |

### Tipos de Documento

| Tipo | Descrição |
|------|-----------|
| `contract` | Contratos |
| `report` | Relatórios |
| `statement` | Extratos |
| `certificate` | Certificados |
| `proof` | Comprovantes |
| `other` | Outros |

---

## Endpoints

### 1. Upload Simples (um arquivo)

```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data
Authorization: Bearer {token}
```

**Form Data:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `file` | File | Sim | Arquivo a ser enviado |
| `client_id` | string (UUID) | Sim | ID do cliente |
| `document_type` | string | Sim | Tipo do documento |
| `title` | string | Sim | Título do documento |
| `description` | string | Não | Descrição |
| `reference_date` | string | Não | Data de referência (ISO 8601) |
| `account_id` | string (UUID) | Não | ID da conta (opcional) |
| `asset_id` | string (UUID) | Não | ID do ativo (opcional) |

**Exemplo com cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer {token}" \
  -F "file=@/path/to/document.pdf" \
  -F "client_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "document_type=contract" \
  -F "title=Contrato de Investimento"
```

**Response (201 Created):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_name": "João Silva",
  "document_type": "contract",
  "title": "Contrato de Investimento",
  "description": null,
  "file_name": "document.pdf",
  "s3_key": "550e8400.../contract/abc123.pdf",
  "file_size": 1048576,
  "mime_type": "application/pdf",
  "status": "pending",
  "validated_by": null,
  "validator_name": null,
  "validated_at": null,
  "validation_notes": null,
  "created_at": "2025-12-08T10:00:00",
  "updated_at": null
}
```

---

### 2. Upload Múltiplo (vários arquivos)

```http
POST /api/v1/documents/upload-multiple
Content-Type: multipart/form-data
Authorization: Bearer {token}
```

**Form Data:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `files` | File[] | Sim | Lista de arquivos a serem enviados |
| `client_id` | string (UUID) | Sim | ID do cliente |
| `document_type` | string | Sim | Tipo do documento (aplicado a todos) |
| `description` | string | Não | Descrição (aplicada a todos) |
| `reference_date` | string | Não | Data de referência (aplicada a todos) |
| `account_id` | string (UUID) | Não | ID da conta (opcional) |
| `asset_id` | string (UUID) | Não | ID do ativo (opcional) |

**Nota:** O título de cada documento será o nome do arquivo (sem extensão).

**Exemplo com cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload-multiple" \
  -H "Authorization: Bearer {token}" \
  -F "files=@/path/to/document1.pdf" \
  -F "files=@/path/to/document2.pdf" \
  -F "files=@/path/to/document3.jpg" \
  -F "client_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "document_type=contract"
```

**Response (201 Created):**
```json
{
  "uploaded": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174001",
      "client_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "document1",
      "file_name": "document1.pdf",
      "status": "pending"
    },
    {
      "id": "123e4567-e89b-12d3-a456-426614174002",
      "client_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "document2",
      "file_name": "document2.pdf",
      "status": "pending"
    },
    {
      "id": "123e4567-e89b-12d3-a456-426614174003",
      "client_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "document3",
      "file_name": "document3.jpg",
      "status": "pending"
    }
  ],
  "errors": [],
  "total_files": 3,
  "success_count": 3,
  "error_count": 0
}
```

**Response com erros parciais:**
```json
{
  "uploaded": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174001",
      "title": "document1",
      "file_name": "document1.pdf",
      "status": "pending"
    }
  ],
  "errors": [
    {
      "file_name": "arquivo_grande.pdf",
      "error": "Arquivo excede o tamanho máximo de 10MB"
    },
    {
      "file_name": "script.exe",
      "error": "Extensão não permitida. Permitidas: .pdf, .png, .jpg, .jpeg, .xls, .xlsx, .csv, .doc, .docx"
    }
  ],
  "total_files": 3,
  "success_count": 1,
  "error_count": 2
}
```

---

## Erros Comuns

| Código | Mensagem | Causa |
|--------|----------|-------|
| 400 | `Tipo de documento inválido` | Tipo não está na lista permitida |
| 400 | `Extensão não permitida` | Arquivo com extensão não suportada |
| 400 | `Tipo de arquivo não permitido` | MIME type inválido |
| 413 | `Arquivo excede o tamanho máximo de 10MB` | Arquivo muito grande |
| 404 | `Cliente não encontrado` | ID do cliente inválido ou sem acesso |
| 404 | `Conta não encontrada` | account_id inválido |
| 404 | `Ativo não encontrado` | asset_id inválido |

---

## Exemplos de Código

### React - Upload Simples

```typescript
async function uploadDocument(
  file: File,
  clientId: string,
  documentType: string,
  title: string
): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('client_id', clientId);
  formData.append('document_type', documentType);
  formData.append('title', title);

  const response = await fetch('/api/v1/documents/upload', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }

  return response.json();
}
```

### React - Upload Múltiplo

```typescript
interface MultipleUploadResult {
  uploaded: Document[];
  errors: { file_name: string; error: string }[];
  total_files: number;
  success_count: number;
  error_count: number;
}

async function uploadMultipleDocuments(
  files: FileList | File[],
  clientId: string,
  documentType: string,
  description?: string
): Promise<MultipleUploadResult> {
  const formData = new FormData();

  // Adicionar cada arquivo
  for (const file of files) {
    formData.append('files', file);
  }

  formData.append('client_id', clientId);
  formData.append('document_type', documentType);

  if (description) {
    formData.append('description', description);
  }

  const response = await fetch('/api/v1/documents/upload-multiple', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }

  return response.json();
}
```

### React - Componente de Upload Múltiplo

```tsx
import { useState } from 'react';

interface UploadMultipleProps {
  clientId: string;
  onSuccess: (result: MultipleUploadResult) => void;
}

function UploadMultiple({ clientId, onSuccess }: UploadMultipleProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [documentType, setDocumentType] = useState('contract');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<MultipleUploadResult | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setUploading(true);
    try {
      const result = await uploadMultipleDocuments(files, clientId, documentType);
      setResult(result);
      onSuccess(result);

      // Limpar arquivos após sucesso
      if (result.error_count === 0) {
        setFiles([]);
      }
    } catch (error) {
      console.error('Erro no upload:', error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-multiple">
      <div className="form-group">
        <label>Tipo de Documento</label>
        <select
          value={documentType}
          onChange={(e) => setDocumentType(e.target.value)}
        >
          <option value="contract">Contrato</option>
          <option value="report">Relatório</option>
          <option value="statement">Extrato</option>
          <option value="certificate">Certificado</option>
          <option value="proof">Comprovante</option>
          <option value="other">Outro</option>
        </select>
      </div>

      <div className="form-group">
        <label>Arquivos</label>
        <input
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,.xls,.xlsx,.csv,.doc,.docx"
          onChange={handleFileChange}
        />
        {files.length > 0 && (
          <ul className="file-list">
            {files.map((file, index) => (
              <li key={index}>
                {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
              </li>
            ))}
          </ul>
        )}
      </div>

      <button
        onClick={handleUpload}
        disabled={uploading || files.length === 0}
      >
        {uploading ? 'Enviando...' : `Enviar ${files.length} arquivo(s)`}
      </button>

      {result && (
        <div className="upload-result">
          <p>
            Sucesso: {result.success_count} / {result.total_files}
          </p>
          {result.errors.length > 0 && (
            <div className="errors">
              <strong>Erros:</strong>
              <ul>
                {result.errors.map((err, index) => (
                  <li key={index}>
                    {err.file_name}: {err.error}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## Fluxo Recomendado no Frontend

### Tela de Upload de Documentos

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Upload de Documentos                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Cliente: [▼ João Silva                                            ]    │
│                                                                          │
│  Tipo: [▼ Contrato                                                 ]    │
│                                                                          │
│  Descrição (opcional): [____________________________________]           │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │     📁 Arraste arquivos aqui ou clique para selecionar          │   │
│  │                                                                  │   │
│  │     Formatos: PDF, PNG, JPG, XLS, XLSX, CSV, DOC, DOCX          │   │
│  │     Máximo: 10MB por arquivo                                     │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Arquivos selecionados:                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 📄 contrato_2025.pdf (2.5 MB)                             [X]   │   │
│  │ 📄 anexo_1.pdf (1.2 MB)                                   [X]   │   │
│  │ 📷 foto_comprovante.jpg (0.8 MB)                          [X]   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│                                         [Cancelar]  [Enviar 3 arquivos] │
└─────────────────────────────────────────────────────────────────────────┘
```

### Resultado do Upload

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Resultado do Upload                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ✅ 2 arquivos enviados com sucesso                                     │
│  ❌ 1 arquivo com erro                                                   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ ✅ contrato_2025.pdf - Enviado                                  │   │
│  │ ✅ anexo_1.pdf - Enviado                                        │   │
│  │ ❌ arquivo_grande.pdf - Arquivo excede o tamanho máximo de 10MB │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│                                                          [Fechar]       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Checklist de Implementação

### Upload Simples

- [ ] Input de arquivo único
- [ ] Campo de título obrigatório
- [ ] Validação de extensão no frontend
- [ ] Preview do arquivo selecionado
- [ ] Progress bar durante upload

### Upload Múltiplo

- [ ] Input de múltiplos arquivos (`multiple`)
- [ ] Lista de arquivos selecionados com opção de remover
- [ ] Validação de tamanho no frontend (10MB)
- [ ] Validação de extensão no frontend
- [ ] Exibição de resultado com sucesso/erros
- [ ] Tratamento de erros parciais

### Drag & Drop (opcional)

- [ ] Área de drop zone
- [ ] Destaque visual ao arrastar arquivos
- [ ] Suporte a múltiplos arquivos

---

*Última atualização: 2025-12-08*

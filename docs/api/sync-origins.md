# API de Sincronização com Múltiplas Origens

## Visão Geral

O sistema agora suporta sincronização de dados de múltiplas fontes:
- **Mega ERP** - Sistema ERP principal
- **UAU (Globaltec/Senior)** - Sistema de gestão imobiliária

O frontend pode permitir que o usuário selecione qual origem sincronizar.

---

## Endpoints

### 1. Listar Origens Disponíveis

```http
GET /api/v1/scheduler/sync/origins
Authorization: Bearer <token>
```

**Resposta (200 OK):**
```json
{
  "origins": [
    {
      "id": "mega",
      "name": "Mega ERP",
      "available": true,
      "description": "Sistema Mega ERP"
    },
    {
      "id": "uau",
      "name": "UAU (Globaltec/Senior)",
      "available": true,
      "description": "Sistema UAU - Globaltec/Senior"
    },
    {
      "id": "both",
      "name": "Ambos",
      "available": true,
      "description": "Sincronizar Mega e UAU simultaneamente"
    }
  ]
}
```

**Campos:**
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | string | Identificador da origem (`mega`, `uau`, `both`) |
| `name` | string | Nome para exibição |
| `available` | boolean | Se a origem está configurada e disponível |
| `description` | string | Descrição da origem |

> **Nota:** Uma origem só está `available: true` se as credenciais estiverem configuradas no servidor.

---

### 2. Disparar Sincronização

```http
POST /api/v1/scheduler/sync
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "origem": "mega",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "empresa_ids": [93, 94]
}
```

**Parâmetros:**
| Campo | Tipo | Obrigatório | Default | Descrição |
|-------|------|-------------|---------|-----------|
| `origem` | string | Não | `"mega"` | Origem: `mega`, `uau` ou `both` |
| `start_date` | string | Não | 12 meses atrás | Data inicial (YYYY-MM-DD) |
| `end_date` | string | Não | Hoje | Data final (YYYY-MM-DD) |
| `empresa_ids` | array[int] | Não | Todas | IDs específicos de empresas/empreendimentos |

**Resposta (200 OK):**
```json
{
  "status": "started",
  "message": "Sincronização Mega iniciada em background",
  "origem": "mega"
}
```

**Campos da Resposta:**
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `status` | string | Status da operação (`started`, `error`) |
| `message` | string | Mensagem descritiva |
| `origem` | string | Origem selecionada |

**Erros:**
| Status | Descrição |
|--------|-----------|
| 400 | Formato de data inválido |
| 401 | Não autenticado |
| 500 | Erro interno |

---

## Exemplos de Uso

### Sincronizar apenas Mega (padrão)
```json
{
  "origem": "mega"
}
```

### Sincronizar apenas UAU
```json
{
  "origem": "uau"
}
```

### Sincronizar ambos
```json
{
  "origem": "both"
}
```

### Sincronizar com período específico
```json
{
  "origem": "both",
  "start_date": "2025-01-01",
  "end_date": "2025-06-30"
}
```

### Sincronizar empresas específicas
```json
{
  "origem": "uau",
  "empresa_ids": [93, 94, 95]
}
```

---

## Implementação Sugerida (Frontend)

### 1. Componente de Seleção

```tsx
// React/TypeScript example
interface SyncOrigin {
  id: 'mega' | 'uau' | 'both';
  name: string;
  available: boolean;
  description: string;
}

const SyncForm = () => {
  const [origins, setOrigins] = useState<SyncOrigin[]>([]);
  const [selectedOrigin, setSelectedOrigin] = useState<string>('mega');
  const [loading, setLoading] = useState(false);

  // Carregar origens disponíveis
  useEffect(() => {
    fetch('/api/v1/scheduler/sync/origins', {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => setOrigins(data.origins));
  }, []);

  // Disparar sincronização
  const handleSync = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/scheduler/sync', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ origem: selectedOrigin })
      });
      const data = await response.json();
      alert(data.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <label>Origem dos Dados:</label>
      <select
        value={selectedOrigin}
        onChange={e => setSelectedOrigin(e.target.value)}
      >
        {origins
          .filter(o => o.available)
          .map(origin => (
            <option key={origin.id} value={origin.id}>
              {origin.name}
            </option>
          ))
        }
      </select>

      <button onClick={handleSync} disabled={loading}>
        {loading ? 'Sincronizando...' : 'Sincronizar'}
      </button>
    </div>
  );
};
```

### 2. UI Sugerida

```
┌─────────────────────────────────────────────────────┐
│  Sincronização de Dados                             │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Origem dos Dados:                                  │
│  ┌─────────────────────────────────────┐           │
│  │ Mega ERP                        ▼   │           │
│  ├─────────────────────────────────────┤           │
│  │ ○ Mega ERP                          │           │
│  │ ○ UAU (Globaltec/Senior)            │           │
│  │ ○ Ambos                             │           │
│  └─────────────────────────────────────┘           │
│                                                     │
│  Período (opcional):                                │
│  ┌──────────────┐  ┌──────────────┐                │
│  │ 2025-01-01   │  │ 2025-12-31   │                │
│  └──────────────┘  └──────────────┘                │
│  Data Inicial       Data Final                      │
│                                                     │
│  ┌─────────────────────────────────────┐           │
│  │       Iniciar Sincronização         │           │
│  └─────────────────────────────────────┘           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Comportamento

1. **Execução em Background**: A sincronização é executada em background, permitindo que o usuário continue usando o sistema.

2. **Logs**: O progresso pode ser acompanhado nos logs do servidor ou consultando o endpoint `/api/v1/scheduler/runs`.

3. **Dados Separados**: Os dados de cada origem são identificados pelo campo `origem` no banco:
   - Dados do Mega têm `origem = 'mega'`
   - Dados do UAU têm `origem = 'uau'`

4. **Conflitos**: Não há conflito entre dados das duas origens, pois são armazenados separadamente.

---

## Endpoint Legado

O endpoint antigo ainda funciona para compatibilidade:

```http
POST /api/v1/scheduler/trigger?exec_date=2025-01-15
```

Este endpoint sincroniza apenas o **Mega** (comportamento original).

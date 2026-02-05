# CLAUDE.md - Especificações Técnicas do Sistema Starke

**Sistema de Gestão de Dados Financeiros e Portfólio de Empreendimentos Imobiliários**

Este documento contém especificações técnicas detalhadas do sistema Starke, destinado a auxiliar no desenvolvimento, manutenção e extensão do projeto.

---

## Índice

1. [Visão Geral do Sistema](#visão-geral-do-sistema)
2. [Arquitetura](#arquitetura)
3. [Fluxo de Dados](#fluxo-de-dados)
4. [Integração com Mega API](#integração-com-mega-api)
5. [Transformadores de Dados](#transformadores-de-dados)
6. [Modelos de Domínio](#modelos-de-domínio)
7. [Sincronização e Backfill](#sincronização-e-backfill)
8. [APIs e Endpoints](#apis-e-endpoints)
9. [Banco de Dados](#banco-de-dados)
10. [CLI Commands](#cli-commands)
11. [Configuração](#configuração)
12. [Boas Práticas](#boas-práticas)
13. [Troubleshooting](#troubleshooting)

---

## Visão Geral do Sistema

O **Starke** é um sistema de gestão de dados financeiros para empreendimentos imobiliários que:

- **Integra** com a API Mega ERP para coletar dados de contratos, parcelas e finanças
- **Transforma** dados brutos em modelos analíticos (CashIn, CashOut, Portfolio Stats)
- **Armazena** dados históricos em PostgreSQL com versionamento
- **Expõe** APIs REST para consumo de dados por dashboards e relatórios
- **Sincroniza** dados automaticamente via schedulers
- **Calcula** métricas financeiras avançadas (VP, LTV, Duration, Prazo Médio)

### Principais Capacidades

- ✅ Sincronização completa de empreendimentos e contratos
- ✅ Backfill histórico de dados financeiros (CashIn/CashOut)
- ✅ Cálculo automático de métricas de portfólio
- ✅ API REST para consulta de dados
- ✅ Scheduler automático para sync diário
- ✅ Suporte a múltiplos empreendimentos e filiais

---

## Arquitetura

### Clean Architecture

O projeto segue os princípios de **Clean Architecture** com separação clara de responsabilidades:

```
src/starke/
├── domain/                    # Camada de Domínio (Core Business Logic)
│   ├── entities/              # Entidades de domínio (Development, Contract, etc.)
│   ├── repositories/          # Interfaces de repositórios
│   └── services/              # Serviços de domínio
│       ├── mega_transformer.py      # Transformação de dados Mega → Starke
│       ├── mega_sync_service.py     # Orquestração de sincronização
│       └── portfolio_calculator.py  # Cálculo de métricas financeiras
│
├── infrastructure/            # Camada de Infraestrutura
│   ├── database/              # SQLAlchemy models e repositories
│   │   ├── models/            # Modelos ORM (mapeamento DB)
│   │   └── repositories/      # Implementações de repositórios
│   ├── external_apis/         # Clientes de APIs externas
│   │   ├── mega_api_client.py      # Cliente HTTP para Mega API
│   │   └── datawarehouse_client.py # Cliente para DW
│   ├── email/                 # Serviços de email
│   └── sheets/                # Integração Google Sheets
│
├── api/                       # Camada de Apresentação (FastAPI)
│   ├── main.py                # App FastAPI principal
│   ├── routes/                # Routers por domínio
│   │   ├── developments.py    # Endpoints de empreendimentos
│   │   ├── contracts.py       # Endpoints de contratos
│   │   ├── cash_flow.py       # Endpoints de fluxo de caixa
│   │   └── financeiro.py      # Endpoints financeiros
│   └── dependencies.py        # Dependency injection
│
├── presentation/              # Templates e assets
│   └── templates/
│       └── report.html        # Template de relatório HTML
│
├── core/                      # Configurações e utilities
│   ├── config_loader.py       # Carregamento de configurações
│   ├── database.py            # Setup de database session
│   └── logging.py             # Setup de logging
│
└── cli/                       # Interface de linha de comando
    ├── __main__.py            # Entry point do CLI
    └── commands/              # Comandos CLI
        ├── sync.py            # Comandos de sincronização
        └── backfill.py        # Comandos de backfill
```

### Camadas e Responsabilidades

1. **Domain Layer** (Núcleo do negócio)
   - Entidades de domínio puras (sem dependências externas)
   - Interfaces de repositórios (contratos)
   - Lógica de negócio e transformações
   - Cálculos financeiros

2. **Infrastructure Layer** (Implementações técnicas)
   - Implementações de repositórios (SQLAlchemy)
   - Clientes HTTP para APIs externas
   - Integrações com serviços (email, sheets)
   - Persistência em banco de dados

3. **API Layer** (Interface externa)
   - Endpoints REST (FastAPI)
   - Validação de entrada (Pydantic)
   - Serialização/deserialização
   - Documentação automática (OpenAPI)

4. **CLI Layer** (Interface de linha de comando)
   - Comandos administrativos
   - Scripts de sincronização
   - Ferramentas de backfill

---

## Fluxo de Dados

### 1. Sincronização de Contratos (sync-contracts)

```
┌─────────────┐
│  CLI/Cron   │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ MegaSyncService     │ ← Orquestração principal
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ MegaAPIClient       │ ← Busca dados da API Mega
│                     │   GET /api/globalestruturas/Empreendimentos
│                     │   GET /api/Carteira/DadosContrato/IdEmpreendimento={id}
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ MegaTransformer     │ ← Transforma dados Mega → Starke
│                     │   - transform_empreendimento()
│                     │   - transform_contrato()
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Repositories        │ ← Persiste no PostgreSQL
│ - DevelopmentRepo   │
│ - ContractRepo      │
└─────────────────────┘
```

### 2. Backfill de Dados Financeiros (backfill)

```
┌─────────────┐
│  CLI        │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ BackfillCommand     │ ← Comando de backfill
└──────┬──────────────┘
       │
       ├─────────────────────────────────┐
       │                                 │
       ▼                                 ▼
┌──────────────┐                  ┌──────────────┐
│ Sync CashIn  │                  │ Sync CashOut │
└──────┬───────┘                  └──────┬───────┘
       │                                 │
       ▼                                 ▼
┌──────────────────────┐          ┌──────────────────────┐
│ Mega API:            │          │ Mega API:            │
│ DadosParcelas        │          │ FaturaPagar/Saldo    │
└──────┬───────────────┘          └──────┬───────────────┘
       │                                 │
       ▼                                 ▼
┌──────────────────────┐          ┌──────────────────────┐
│ Transform Parcelas   │          │ Transform Faturas    │
│ → CashIn Records     │          │ → CashOut Records    │
└──────┬───────────────┘          └──────┬───────────────┘
       │                                 │
       └─────────────┬───────────────────┘
                     ▼
            ┌─────────────────┐
            │ Upsert no DB    │
            │ (por ref_month) │
            └─────────────────┘
```

### 3. Cálculo de Métricas de Portfólio

```
┌─────────────────────┐
│ Scheduler/API Call  │
└──────┬──────────────┘
       │
       ▼
┌──────────────────────────┐
│ PortfolioCalculator      │
└──────┬───────────────────┘
       │
       ├─ Calcula VP (Valor Presente)
       ├─ Calcula LTV (Loan-to-Value)
       ├─ Calcula Prazo Médio Ponderado
       ├─ Calcula Duration (Macaulay)
       ├─ Calcula Inadimplência (aging buckets)
       │
       ▼
┌──────────────────────────┐
│ Persiste Portfolio Stats │
└──────────────────────────┘
```

---

## Integração com Mega API

### Cliente HTTP: MegaAPIClient

**Localização:** `src/starke/infrastructure/external_apis/mega_api_client.py`

#### Autenticação

```python
# POST /api/Auth/SignIn
{
    "username": "usuario",
    "password": "senha"
}

# Resposta:
{
    "accessToken": "eyJhbGciOi...",
    "expirationToken": "2025-10-31T17:36:34...",
    "refreshToken": "XEi0lKcqpO9m5g..."
}
```

O token é incluído em todas as requisições como `Authorization: Bearer {accessToken}`.

#### Endpoints Utilizados

| Endpoint | Método | Descrição | Retorno |
|----------|--------|-----------|---------|
| `/api/globalestruturas/Empreendimentos` | GET | Lista empreendimentos | Array de empreendimentos |
| `/api/Carteira/DadosContrato/IdEmpreendimento={id}` | GET | Contratos de um empreendimento | Array de contratos |
| `/api/Carteira/DadosParcelas/IdContrato={id}` | GET | Parcelas de um contrato | Array de parcelas |
| `/api/FinanceiroMovimentacao/FaturaPagar/Saldo/{start}/{end}` | GET | Contas a pagar (CashOut) | Array de faturas |

#### Formato de Dados

**IMPORTANTE:** A API Mega retorna dados em **PascalCase** (ex: `cod_contrato`, `vlr_original`, `DataVencimento`).

Veja documentação completa em: `docs/exemplo_retorno_mega.md`

### Rate Limiting e Retry

- Timeout padrão: 60s
- Max retries: 3
- Delay entre retries: 5s

Configurável em `config/mega_mapping.yaml`.

---

## Transformadores de Dados

### MegaTransformer

**Localização:** `src/starke/domain/services/mega_transformer.py`

Responsável por transformar dados brutos da API Mega em modelos Starke.

#### Métodos Principais

##### 1. `transform_empreendimento(mega_data: Dict) -> Dict`

Transforma dados de empreendimento da API Mega.

**Entrada (Mega API):**
```python
{
    "codigo": 24905,
    "nome": "LOTEAMENTO RESIDENCIAL GREEN VILLAGE",
    "codigoFilial": 10301,
    "nomeFilial": "GREEN VILLAGE EMPREENDIMENTOS",
    "centroCusto": {"reduzido": 21},
    "projeto": {"reduzido": 36},
    "status": "A"
}
```

**Saída (Starke):**
```python
{
    "mega_id": 24905,
    "name": "LOTEAMENTO RESIDENCIAL GREEN VILLAGE",
    "is_active": True,
    "filial_codigo": 10301,
    "filial_nome": "GREEN VILLAGE EMPREENDIMENTOS",
    "centro_custo_id": 21,
    "projeto_id": 36
}
```

##### 2. `transform_contrato(contrato: Dict, development_id: int) -> Dict`

Transforma dados de contrato da API Mega.

**Entrada (Mega API):**
```python
{
    "cod_contrato": 11530,
    "nome_cliente": "MARCELO HENRIQUE DE OLIVEIRA",
    "cpf_cnpj_cliente": "032.079.152-13",
    "valor_contrato": 139800,
    "status_contrato": "Ativo",
    "data_assinatura": "14/03/2025"
}
```

**Saída (Starke):**
```python
{
    "mega_id": 11530,
    "development_id": 24015,
    "customer_name": "MARCELO HENRIQUE DE OLIVEIRA",
    "customer_cpf_cnpj": "032.079.152-13",
    "value": Decimal("139800.00"),
    "status": "A",  # Mapeado de "Ativo" → "A"
    "signed_at": date(2025, 3, 14)
}
```

##### 3. `transform_parcela_to_cash_in(parcela: Dict, development_id: int, development_name: str) -> List[Dict]`

Transforma parcela em registros de CashIn (forecast + actual).

**Entrada (Mega API):**
```python
{
    "cod_parcela": 4577971,
    "cod_contrato": 11530,
    "vlr_original": 4194,
    "vlr_pago": 4194,
    "data_vencimento": "28/03/2025",
    "data_baixa": "27/03/2025",
    "situacao": "Pago"
}
```

**Saída (Starke) - 2 registros:**
```python
[
    # Forecast (previsão)
    {
        "development_id": 24015,
        "development_name": "LOTEAMENTO REVOAR",
        "ref_month": "2025-03",
        "record_type": "forecast",
        "category": "parcelas",
        "amount": Decimal("4194.00"),
        "transaction_date": date(2025, 3, 28),
        "origin_id": "parcela_4577971"
    },
    # Actual (realizado)
    {
        "development_id": 24015,
        "development_name": "LOTEAMENTO REVOAR",
        "ref_month": "2025-03",
        "record_type": "actual",
        "category": "parcelas",
        "amount": Decimal("4194.00"),
        "transaction_date": date(2025, 3, 27),
        "origin_id": "parcela_4577971"
    }
]
```

##### 4. `transform_fatura_pagar_to_cash_out(fatura: Dict, development_id: int, development_name: str) -> Dict`

Transforma fatura a pagar em registro de CashOut (apenas forecast).

**Entrada (Mega API - Endpoint Saldo):**
```python
{
    "NumeroAP": 921,
    "TipoDocumento": "DISTRATO",
    "NumeroDocumento": "000001",
    "NumeroParcela": "011",
    "DataVencimento": "30/10/2025",
    "ValorParcela": 10000.0,
    "Agente": {
        "Codigo": 8245,
        "Nome": "FORNECEDOR XYZ"
    }
}
```

**Saída (Starke) - 1 registro (forecast apenas):**
```python
{
    "development_id": 24015,
    "development_name": "LOTEAMENTO REVOAR",
    "ref_month": "2025-10",
    "record_type": "forecast",
    "category": "distrato",  # Mapeado de TipoDocumento
    "amount": Decimal("10000.00"),
    "transaction_date": date(2025, 10, 30),
    "origin_id": "fatura_921_011"
}
```

**IMPORTANTE:** O endpoint `/api/FinanceiroMovimentacao/FaturaPagar/Saldo` retorna **apenas dados de orçamento/previsão**, não dados de pagamentos realizados. Por isso, CashOut só gera registros `forecast`.

### Mapeamento de Status

**Contratos:**
```python
STATUS_MAPPING = {
    "Ativo": "A",
    "Normal": "N",
    "Inadimplente": "I",
    "Quitado": "Q",
    "Distratado": "D"
}
```

**Categorias de CashOut:**
```yaml
# config/mega_mapping.yaml
cash_out_categories:
  DISTRATO: "distrato"
  NOTA FISCAL: "fornecedores"
  BOLETO: "impostos"
  OUTROS: "outras"
```

---

## Modelos de Domínio

### Development (Empreendimento)

**Tabela:** `developments`

```python
class Development:
    id: int                    # PK auto-increment
    mega_id: int               # ID no sistema Mega (unique)
    name: str                  # Nome do empreendimento
    is_active: bool            # Se está ativo
    filial_codigo: int         # Código da filial
    filial_nome: str           # Nome da filial
    centro_custo_id: int       # ID do centro de custo
    projeto_id: int            # ID do projeto
    created_at: datetime
    updated_at: datetime
```

### Contract (Contrato)

**Tabela:** `contracts`

```python
class Contract:
    id: int                    # PK auto-increment
    mega_id: int               # ID no sistema Mega (unique)
    development_id: int        # FK → developments
    customer_name: str         # Nome do cliente
    customer_cpf_cnpj: str     # CPF/CNPJ do cliente
    value: Decimal             # Valor total do contrato
    status: str                # Status: A/N/I/Q/D
    signed_at: date            # Data de assinatura
    created_at: datetime
    updated_at: datetime
```

### CashIn (Entrada de Caixa)

**Tabela:** `cash_in`

```python
class CashIn:
    id: int                    # PK auto-increment
    development_id: int        # FK → developments
    development_name: str      # Nome do empreendimento (desnormalizado)
    ref_month: str             # Mês de referência (YYYY-MM)
    record_type: str           # forecast | actual
    category: str              # parcelas | distrato | outros
    amount: Decimal            # Valor
    transaction_date: date     # Data da transação
    origin_id: str             # ID de origem (parcela_X)
    created_at: datetime
    updated_at: datetime
```

**Índices:**
- `idx_cash_in_dev_month` (development_id, ref_month)
- `idx_cash_in_origin` (origin_id) UNIQUE

### CashOut (Saída de Caixa)

**Tabela:** `cash_out`

```python
class CashOut:
    id: int                    # PK auto-increment
    development_id: int        # FK → developments
    development_name: str      # Nome do empreendimento (desnormalizado)
    ref_month: str             # Mês de referência (YYYY-MM)
    record_type: str           # forecast | actual
    category: str              # fornecedores | impostos | outras
    amount: Decimal            # Valor
    transaction_date: date     # Data da transação
    origin_id: str             # ID de origem (fatura_X)
    created_at: datetime
    updated_at: datetime
```

**Índices:**
- `idx_cash_out_dev_month` (development_id, ref_month)
- `idx_cash_out_origin` (origin_id) UNIQUE

### PortfolioStats (Métricas de Portfólio)

**Tabela:** `portfolio_stats`

```python
class PortfolioStats:
    id: int                    # PK auto-increment
    development_id: int        # FK → developments
    ref_date: date             # Data de referência
    vp: Decimal                # Valor Presente (recebíveis futuros)
    ltv: Decimal               # Loan-to-Value (%)
    prazo_medio: Decimal       # Prazo médio ponderado (meses)
    duration: Decimal          # Duration Macaulay
    total_contracts: int       # Total de contratos
    active_contracts: int      # Contratos ativos
    delinquency_total: Decimal # Total inadimplência
    created_at: datetime
```

---

## Sincronização e Backfill

### Sync Contracts (Sincronização de Contratos)

**Comando:** `starke.cli sync-contracts`

**O que faz:**
1. Busca todos os empreendimentos da API Mega
2. Para cada empreendimento:
   - Transforma e salva/atualiza no banco
   - Busca todos os contratos desse empreendimento
   - Transforma e salva/atualiza contratos no banco
3. Marca empreendimentos como ativos/inativos baseado em existência de contratos

**Uso:**
```bash
# Sync completo
PYTHONPATH=src:$PYTHONPATH python3 -m starke.cli sync-contracts

# Sync de empreendimentos específicos
PYTHONPATH=src:$PYTHONPATH python3 -m starke.cli sync-contracts --empreendimento-ids 24905,24015
```

### Backfill (Preenchimento Histórico)

**Comando:** `starke.cli backfill`

**O que faz:**
1. Busca contratos do empreendimento especificado
2. Para cada contrato, busca parcelas (CashIn)
3. Busca faturas a pagar no período especificado (CashOut)
4. Transforma e persiste dados com upsert (por `origin_id`)

**Uso:**
```bash
# Backfill de 1 ano para empreendimento 24905
PYTHONPATH=src:$PYTHONPATH python3 -m starke.cli backfill \
  --start-date=2025-01-01 \
  --end-date=2025-12-31 \
  --empreendimento-ids=24905

# Backfill de múltiplos empreendimentos
PYTHONPATH=src:$PYTHONPATH python3 -m starke.cli backfill \
  --start-date=2025-01-01 \
  --end-date=2025-12-31 \
  --empreendimento-ids=24905,24015
```

**Performance:**
- Processa parcelas em lotes
- Usa upsert para evitar duplicatas
- Agrupa por mês de referência (`ref_month`)

---

## APIs e Endpoints

### FastAPI Application

**Entry Point:** `src/starke/api/main.py`

**Base URL:** `http://localhost:8000`

**Documentação Automática:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Rotas Disponíveis

#### 1. Developments (Empreendimentos)

```
GET /api/developments
```
Lista todos os empreendimentos.

**Query Parameters:**
- `skip`: int (default: 0)
- `limit`: int (default: 100)
- `is_active`: bool (optional)

**Response:**
```json
[
    {
        "id": 1,
        "mega_id": 24905,
        "name": "LOTEAMENTO RESIDENCIAL GREEN VILLAGE",
        "is_active": true,
        "filial_codigo": 10301,
        "filial_nome": "GREEN VILLAGE EMPREENDIMENTOS"
    }
]
```

```
GET /api/developments/{id}
```
Busca empreendimento por ID.

#### 2. Contracts (Contratos)

```
GET /api/contracts
```
Lista contratos com filtros.

**Query Parameters:**
- `development_id`: int (optional)
- `status`: str (optional)
- `skip`: int (default: 0)
- `limit`: int (default: 100)

```
GET /api/contracts/{id}
```
Busca contrato por ID.

#### 3. Cash Flow (Fluxo de Caixa)

```
GET /api/cash-flow/cash-in
```
Retorna entradas de caixa.

**Query Parameters:**
- `development_id`: int (required)
- `start_date`: str YYYY-MM-DD (required)
- `end_date`: str YYYY-MM-DD (required)
- `record_type`: str forecast|actual (optional)

**Response:**
```json
[
    {
        "development_id": 24905,
        "development_name": "GREEN VILLAGE",
        "ref_month": "2025-03",
        "record_type": "actual",
        "category": "parcelas",
        "amount": 4194.00,
        "transaction_date": "2025-03-27"
    }
]
```

```
GET /api/cash-flow/cash-out
```
Retorna saídas de caixa (mesmos parâmetros que cash-in).

#### 4. Financeiro (Datawarehouse)

```
GET /api/financeiro/development/{development_id}/cash-flow
```
Calcula fluxo de caixa consolidado de um empreendimento.

**Query Parameters:**
- `start_date`: str YYYY-MM-DD
- `end_date`: str YYYY-MM-DD

**Response:**
```json
{
    "development_id": 24905,
    "period": {
        "start_date": "2025-01-01",
        "end_date": "2025-12-31"
    },
    "cash_in": {
        "forecast": 1000000.00,
        "actual": 800000.00
    },
    "cash_out": {
        "forecast": 500000.00,
        "actual": 450000.00
    },
    "balance": {
        "forecast": 500000.00,
        "actual": 350000.00
    }
}
```

---

## Banco de Dados

### PostgreSQL Schema

**Database:** `starke`

**Tabelas Principais:**
- `developments` - Empreendimentos
- `contracts` - Contratos
- `cash_in` - Entradas de caixa
- `cash_out` - Saídas de caixa
- `portfolio_stats` - Métricas de portfólio

### Migrações (Alembic)

**Criar nova migração:**
```bash
PYTHONPATH=src:$PYTHONPATH python3 -m alembic revision --autogenerate -m "description"
```

**Aplicar migrações:**
```bash
PYTHONPATH=src:$PYTHONPATH python3 -m alembic upgrade head
```

**Reverter migração:**
```bash
PYTHONPATH=src:$PYTHONPATH python3 -m alembic downgrade -1
```

### Connection String

```
postgresql://user:password@host:port/starke
```

Configurado via variável de ambiente `DATABASE_URL` no `.env`.

---

## CLI Commands

### Comandos Disponíveis

```bash
# Sincronizar contratos
PYTHONPATH=src:$PYTHONPATH python3 -m starke.cli sync-contracts

# Backfill histórico
PYTHONPATH=src:$PYTHONPATH python3 -m starke.cli backfill \
  --start-date=2025-01-01 \
  --end-date=2025-12-31 \
  --empreendimento-ids=24905

# Iniciar API
PYTHONPATH=src python3 -m uvicorn starke.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Variáveis de Ambiente Necessárias

```bash
export PYTHONPATH=/path/to/starke/src:$PYTHONPATH
export DATABASE_URL=postgresql://user:password@localhost:5432/starke
```

---

## Configuração

### Arquivos de Configuração

#### 1. `.env`

Variáveis de ambiente principais:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/starke

# Mega API
MEGA_API_URL=https://api.mega.com.br
MEGA_API_USER=usuario
MEGA_API_PASSWORD=senha

# Logging
LOG_LEVEL=INFO
```

#### 2. `config/mega_mapping.yaml`

Mapeamentos de categorias e configurações da API:

```yaml
# Mapeamento de categorias de CashOut
cash_out_categories:
  DISTRATO: distrato
  NOTA FISCAL: fornecedores
  BOLETO: impostos
  OUTROS: outras

# Configurações de API
api:
  timeout: 60
  max_retries: 3
  retry_delay: 5
```

---

## Boas Práticas

### 1. Transformadores de Dados

- ✅ Use **apenas** campos PascalCase da API Mega atual
- ❌ **Nunca** use campos legacy com prefixos (`prl_*`, `ctr_*`, `est_*`)
- ✅ Valide e converta tipos antes de persistir
- ✅ Use `_parse_decimal()` e `_parse_date()` para parsing seguro

### 2. Persistência

- ✅ Use `upsert` para evitar duplicatas (baseado em `origin_id`)
- ✅ Agrupe inserções por mês de referência (`ref_month`)
- ✅ Use transações para operações em lote

### 3. APIs

- ✅ Sempre use paginação em endpoints de listagem
- ✅ Valide parâmetros com Pydantic
- ✅ Retorne erros claros com códigos HTTP apropriados
- ✅ Use dependency injection para repositórios

### 4. Logging

- ✅ Use logger estruturado
- ✅ Log níveis apropriados (INFO, WARNING, ERROR)
- ✅ Inclua contexto relevante (development_id, contract_id, etc.)

### 5. Testes

- ✅ Escreva testes unitários para transformadores
- ✅ Use fixtures para dados de teste
- ✅ Mock chamadas a APIs externas

---

## Troubleshooting

### Problema: CashOut não está sincronizando

**Causa:** O endpoint `/api/FinanceiroMovimentacao/FaturaPagar/Saldo` só retorna dados de orçamento/previsão.

**Solução:** CashOut sempre terá apenas `record_type = "forecast"`. Para dados realizados, seria necessário outro endpoint da API Mega.

### Problema: Contratos não estão sendo marcados como ativos

**Causa:** Status da API pode vir em formato diferente ou campo ausente.

**Solução:** Verificar mapeamento de status em `mega_transformer.py`:
```python
STATUS_MAPPING = {
    "Ativo": "A",
    "Normal": "N",
    ...
}
```

### Problema: Erros de parsing de data

**Causa:** API Mega usa formato `DD/MM/YYYY`, mas Python espera `YYYY-MM-DD`.

**Solução:** Usar método `_parse_date()` do transformer que trata ambos os formatos.

### Problema: Duplicatas no banco de dados

**Causa:** `origin_id` não está sendo gerado corretamente.

**Solução:** Verificar geração de `origin_id` nos transformadores:
```python
origin_id = f"parcela_{parcela_id}"
origin_id = f"fatura_{numero_ap}_{numero_parcela}"
```

### Problema: Performance lenta no backfill

**Causa:** Muitas requisições individuais à API.

**Solução:**
- Processar em lotes
- Usar bulk insert no banco
- Limitar período de backfill

---

## Referências Importantes

- **Documentação da API Mega:** `docs/exemplo_retorno_mega.md`
- **README Principal:** `README.md`
- **Scripts úteis:** `scripts/`
- **Exemplos de API:** `api_samples/`

---

**Última Atualização:** 2025-10-31

**Versão do Sistema:** 1.0.0

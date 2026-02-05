# Conversao de Moedas nas Rotas /me

Documentacao do sistema de conversao de moedas para rotas do cliente.

---

## Visao Geral

As rotas `/api/v1/me/*` convertem automaticamente valores monetarios de acordo com a preferencia do usuario (`default_currency`). A conversao usa cotacoes oficiais PTAX do Banco Central do Brasil.

### Moedas Suportadas

| Codigo | Nome |
|--------|------|
| BRL | Real Brasileiro (padrao) |
| USD | Dolar Americano |
| EUR | Euro |

---

## Configurando a Preferencia de Moeda

### Atualizar Preferencia

```http
PUT /api/v1/auth/me/preferences
Authorization: Bearer {token}
Content-Type: application/json

{
  "default_currency": "USD",
  "theme": "light"
}
```

### Verificar Preferencia Atual

```http
GET /api/v1/auth/me/preferences
Authorization: Bearer {token}
```

---

## Rotas com Conversao de Moeda

### 1. Dashboard (`GET /api/v1/me/dashboard`)

Retorna totais convertidos para a moeda preferida do usuario.

**Campos de conversao na resposta:**

| Campo | Descricao |
|-------|-----------|
| `currency` | Moeda dos valores retornados |
| `exchange_rate` | Taxa de cambio usada (BRL para moeda destino) |
| `exchange_date` | Data da cotacao |

**Exemplo de resposta (preferencia USD):**

```json
{
  "client_id": "abc123",
  "client_name": "Joao Silva",
  "currency": "USD",
  "exchange_rate": 5.457,
  "exchange_date": "2025-12-09",
  "data": {
    "net_worth": 18325.09,
    "total_assets": 20000.00,
    "total_liabilities": 1674.91,
    "composition": [
      {"category": "renda_fixa", "value": 10000.00, "percentage": 50}
    ]
  }
}
```

---

### 2. Ativos (`GET /api/v1/me/assets`)

Retorna ativos com valores convertidos. Valores originais sao preservados.

**Campos adicionais por ativo:**

| Campo | Descricao |
|-------|-----------|
| `current_value` | Valor atual convertido |
| `base_value` | Valor base convertido |
| `original_currency` | Moeda original do ativo |
| `original_current_value` | Valor atual na moeda original |
| `original_base_value` | Valor base na moeda original |

**Exemplo de resposta (preferencia USD):**

```json
{
  "client_id": "abc123",
  "total": 3,
  "currency": "USD",
  "exchange_rate": 5.457,
  "exchange_date": "2025-12-09",
  "assets": [
    {
      "id": "asset1",
      "name": "CDB Banco X",
      "category": "renda_fixa",
      "current_value": 18325.09,
      "base_value": 16260.16,
      "original_currency": "BRL",
      "original_current_value": 100000.00,
      "original_base_value": 88750.00,
      "quantity": null,
      "base_date": "2024-01-15",
      "institution_name": "Banco X"
    }
  ]
}
```

---

### 3. Passivos (`GET /api/v1/me/liabilities`)

Retorna passivos com valores convertidos. Valores originais sao preservados.

**Campos adicionais por passivo:**

| Campo | Descricao |
|-------|-----------|
| `current_balance` | Saldo atual convertido |
| `original_amount` | Valor original convertido |
| `monthly_payment` | Parcela mensal convertida |
| `original_currency` | Moeda original (BRL) |
| `original_current_balance` | Saldo na moeda original |
| `original_original_amount` | Valor original na moeda original |
| `original_monthly_payment` | Parcela na moeda original |

**Exemplo de resposta (preferencia USD):**

```json
{
  "client_id": "abc123",
  "total": 1,
  "total_value": 9140.04,
  "total_monthly_payment": 457.00,
  "currency": "USD",
  "exchange_rate": 5.457,
  "exchange_date": "2025-12-09",
  "liabilities": [
    {
      "id": "liab1",
      "liability_type": "financiamento",
      "description": "Financiamento Imovel",
      "current_balance": 9140.04,
      "original_amount": 18280.08,
      "monthly_payment": 457.00,
      "original_currency": "BRL",
      "original_current_balance": 49880.00,
      "original_original_amount": 99760.00,
      "original_monthly_payment": 2494.20,
      "interest_rate": 0.79,
      "start_date": "2022-01-01",
      "end_date": "2032-01-01",
      "institution_name": "Banco Y"
    }
  ]
}
```

---

### 4. Evolucao (`GET /api/v1/me/evolution`)

Retorna evolucao patrimonial com **cotacoes historicas** para cada periodo.

**Campos de conversao na resposta:**

| Campo | Descricao |
|-------|-----------|
| `currency` | Moeda dos valores |
| `evolution[].exchange_rate` | Taxa de cambio daquela data |

**Exemplo de resposta (preferencia USD):**

```json
{
  "client_id": "abc123",
  "currency": "USD",
  "period_months": 12,
  "data_points": 6,
  "variation": 2500.00,
  "variation_pct": 15.5,
  "evolution": [
    {
      "date": "2025-07-31",
      "total_assets": 16100.00,
      "total_liabilities": 1800.00,
      "net_worth": 14300.00,
      "exchange_rate": 5.31
    },
    {
      "date": "2025-08-31",
      "total_assets": 16500.00,
      "total_liabilities": 1750.00,
      "net_worth": 14750.00,
      "exchange_rate": 5.42
    },
    {
      "date": "2025-09-30",
      "total_assets": 17200.00,
      "total_liabilities": 1700.00,
      "net_worth": 15500.00,
      "exchange_rate": 5.50
    }
  ]
}
```

---

## Logica de Conversao

### Cotacoes Usadas

- **Posicoes atuais:** Cotacao do dia (com cache de 1 hora)
- **Posicoes historicas:** Cotacao do ultimo dia util do periodo

### Direcao da Conversao

| De | Para | Formula |
|----|------|---------|
| BRL | USD/EUR | valor / cotacao |
| USD/EUR | BRL | valor * cotacao |
| USD | EUR | valor * cotacao_usd / cotacao_eur |

### Tratamento de Fins de Semana/Feriados

O BCB nao publica cotacoes em fins de semana e feriados. O sistema busca automaticamente a ultima cotacao disponivel (ate 7 dias atras).

---

## API de Cotacoes BCB

O sistema usa a API PTAX do Banco Central:

```
https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata
```

### Cache

- **Cotacoes de datas passadas:** Cache permanente (cotacoes historicas nao mudam)
- **Cotacao do dia:** Cache de 1 hora

---

## Fluxo de Uso - Frontend

### Carregar Dashboard

1. Verificar preferencia: `GET /api/v1/auth/me`
2. Carregar dados: `GET /api/v1/me/dashboard`
3. Exibir valores usando o campo `currency` para formatacao

### Trocar Moeda

1. Atualizar preferencia: `PUT /api/v1/auth/me/preferences`
2. Recarregar dados do dashboard/ativos/passivos
3. Valores serao automaticamente convertidos

### Exemplo TypeScript

```typescript
interface DashboardResponse {
  client_id: string;
  client_name: string;
  currency: 'BRL' | 'USD' | 'EUR';
  exchange_rate: number | null;
  exchange_date: string | null;
  data: {
    net_worth: number;
    total_assets: number;
    total_liabilities: number;
  };
}

// Formatacao de moeda
const formatCurrency = (value: number, currency: string) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: currency,
  }).format(value);
};

// Exemplo de uso
const dashboard = await fetchDashboard();
console.log(formatCurrency(dashboard.data.net_worth, dashboard.currency));
// Output: "US$ 18,325.09" ou "R$ 100.000,00"
```

---

## Consideracoes de Performance

1. **Primeira requisicao pode ser mais lenta:** A primeira chamada a API BCB pode levar ~500ms
2. **Chamadas subsequentes sao rapidas:** Cache em memoria evita requisicoes repetidas
3. **Evolucao historica:** Pode fazer multiplas chamadas ao BCB (uma por periodo)

---

**Ultima Atualizacao:** 2025-12-09

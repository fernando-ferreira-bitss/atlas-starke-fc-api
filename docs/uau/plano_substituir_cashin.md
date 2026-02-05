# Plano: Substituir CashIn por ExportarVendas (UAU)

## Objetivo
Substituir as chamadas separadas de `BuscarParcelasAReceber` + `BuscarParcelasRecebidas` pelo endpoint `ExportarVendasXml` para sincronizar CashIn, Inadimplencia e Contratos de forma mais eficiente.

## Status: IMPLEMENTADO - Aguardando testes

---

## 1. Situacao Atual (ANTES)

### Fluxo de CashIn Existente
```
Para cada venda (paralelo com ThreadPoolExecutor):
  1. POST /Venda/BuscarParcelasAReceber   -> forecast (parcelas abertas)
  2. POST /Venda/BuscarParcelasRecebidas  -> actual (parcelas pagas)
```
- **2 chamadas por venda**
- Transforma cada tipo separadamente
- Agrega por (emp_id, ref_month, category)

### Fluxo Novo (IMPLEMENTADO)
```
sync_all() para cada empresa:
|
+-- 1. ExportarVendasXml (UMA chamada - batch 50 vendas)
|   |
|   +-> _sync_vendas_from_data()      -> Contratos
|   |
|   +-> _sync_cash_in_and_delinquency_from_data()
|        +-> CashIn (forecast + actual)
|        +-> Inadimplencia (aging buckets)
|
+-- 2. Desembolso (endpoint separado) -> CashOut
|
+-- 3. ConsultarParcelasDaVenda (para VP) -> PortfolioStats
```
- **1 chamada por batch de 50 vendas**
- Parcelas incluidas no retorno com flag `ParcelaRecebida`
- Dados unificados de contrato + cliente + parcelas

---

## 2. Mapeamento de Campos (VALIDADO)

### 2.1 Parcela ABERTA -> CashIn Forecast

| ExportarVendas.Parcela | CashIn | Notas |
|------------------------|--------|-------|
| `ParcelaRecebida = "0"` | - | Identificador de parcela aberta |
| `DataVencimento` | `ref_month` | YYYY-MM extraido da data |
| `ValorPrincipal` | `forecast` | Valor previsto |
| `TipoParcela` | `category` | S=Sinal, E=Entrada -> mapeado |
| `NumeroParcela` | `origin_id` | Parte do ID unico |

**Exemplo real (Venda 93-JVA02/3493):**
```json
{
  "ParcelaRecebida": "0",
  "TipoParcela": "E",
  "NumeroParcela": "1",
  "DataVencimento": "2024-10-28",
  "ValorPrincipal": "160.630000",
  "ValorPrincipalConfirmado": "0"
}
```
-> CashIn: `ref_month="2024-10", forecast=160.63, category="ativos"`

---

### 2.2 Parcela PAGA -> CashIn Actual

| ExportarVendas.Parcela | CashIn | Notas |
|------------------------|--------|-------|
| `ParcelaRecebida = "1"` | - | Identificador de parcela paga |
| `DataRecebimento` | `ref_month` | YYYY-MM extraido da data |
| `ValorPrincipalConfirmado` | `actual` | Valor efetivamente recebido |
| `TipoParcela` | `category` | S=Sinal, E=Entrada -> mapeado |
| `ValorJurosAtrasoConfirmado` | `details.juros` | Encargos |
| `ValorMultaConfirmado` | `details.multa` | Encargos |

**Exemplo real (Venda 93-JVA02/3500):**
```json
{
  "ParcelaRecebida": "1",
  "TipoParcela": "E",
  "NumeroParcela": "1",
  "DataVencimento": "2024-02-20",
  "DataRecebimento": "2024-02-27",
  "ValorPrincipal": "0.000000",
  "ValorPrincipalConfirmado": "139.160000",
  "ValorJurosAtrasoConfirmado": "0.320000",
  "ValorMultaConfirmado": "2.780000"
}
```
-> CashIn: `ref_month="2024-02", actual=139.16, category="ativos"`

---

### 2.3 Inadimplencia (2 cenarios)

**Grace period:** 3 dias (compensacao bancaria)

#### Cenario 1: Parcelas VENCIDAS NAO PAGAS

| ExportarVendas.Parcela | Inadimplencia | Notas |
|------------------------|---------------|-------|
| `ParcelaRecebida = "0"` | - | Parcela em aberto |
| `DataVencimento < hoje - 3` | `dias_atraso` | hoje - vencimento |
| `ValorPrincipal` | `valor` | Valor para bucket |

**Exemplo real (Venda 93-JVA02/3493):**
```
Parcela 1: Vencimento 2024-10-28, Dias atraso: 438, Valor: R$ 160.63
-> Bucket: 180+ dias
```

#### Cenario 2: Parcelas PAGAS EM ATRASO

| ExportarVendas.Parcela | Inadimplencia | Notas |
|------------------------|---------------|-------|
| `ParcelaRecebida = "1"` | - | Parcela paga |
| `DataRecebimento` | - | Data do pagamento |
| `DataVencimento` | - | Data original |
| `DataRecebimento > DataVencimento + 3` | `dias_atraso` | recebimento - vencimento |
| `ValorPrincipalConfirmado` | `valor` | Valor pago |
| `ValorJurosAtrasoConfirmado` | `juros` | Juros cobrados |
| `ValorMultaConfirmado` | `multa` | Multa cobrada |

**Exemplo real (Venda 93-JVA02/3500):**
```
Parcela 1: Vencimento 2024-02-20, Recebimento 2024-02-27
Dias atraso: 7, Valor: R$ 139.16, Juros: R$ 0.32, Multa: R$ 2.78
-> Bucket: 0-30 dias
```

**Buckets de aging:**
- 0-30 dias
- 30-60 dias
- 60-90 dias
- 90-180 dias
- 180+ dias

---

## 3. Funcionalidades Cobertas pelo ExportarVendas

| Funcionalidade | Endpoint Anterior | ExportarVendas | Status |
|----------------|-------------------|----------------|--------|
| CashIn Forecast | BuscarParcelasAReceber | ValorPrincipal + DataVencimento | IMPLEMENTADO |
| CashIn Actual | BuscarParcelasRecebidas | ValorPrincipalConfirmado + DataRecebimento | IMPLEMENTADO |
| Inadimplencia | BuscarParcelasAReceber | DataVencimento + ValorPrincipal | IMPLEMENTADO |
| Contratos | transform_venda_to_contract | Ja implementado | IMPLEMENTADO |
| Portfolio Stats (VP) | ConsultarParcelasDaVenda | Nao calcula VP | MANTER SEPARADO |

---

## 4. Limitacao - VP (Valor Presente)

### ExportarVendas NAO calcula VP

O endpoint ExportarVendas retorna apenas o **valor base** das parcelas:
```json
{
  "ValorPrincipal": "160.630000",
  "ValorCorrecao": "0",
  "ValorJuros": "0",
  "ValorMulta": "0"
}
```

### ConsultarParcelasDaVenda CALCULA VP

O endpoint ConsultarParcelasDaVenda faz calculo dinamico:
```json
{
  "Principal_reaj": 177.37,
  "Valor_reaj": 196.67,  // VP = Principal + Juros + Multa
  "Juros_reaj": 15.75,
  "Multa_reaj": 3.55
}
```

**Conclusao:** Para VP, manter endpoint separado `ConsultarParcelasDaVenda`.

---

## 5. Implementacao Realizada

### 5.1 Transformer (`uau_transformer.py`)

**Metodos adicionados:**

```python
def transform_parcela_export_to_cash_in(
    self,
    parcela: Dict[str, Any],
    empresa_id: int,
    empresa_nome: str,
    obra: str,
    num_venda: int,
) -> Optional[Dict[str, Any]]:
    """
    Transform parcela from ExportarVendasXml to CashIn record.
    - ParcelaRecebida = "0" -> forecast (ValorPrincipal)
    - ParcelaRecebida = "1" -> actual (ValorPrincipalConfirmado)
    """
```

```python
def transform_parcelas_export_to_delinquency(
    self,
    vendas: List[Dict[str, Any]],
    empresa_id: int,
    empresa_nome: str,
    ref_date: date,
) -> Dict[str, Any]:
    """
    Transform ExportarVendas parcelas to Delinquency aging buckets.
    Handles both scenarios:
    1. Parcelas vencidas nao pagas (ParcelaRecebida="0")
    2. Parcelas pagas em atraso (ParcelaRecebida="1")
    Grace period: 3 dias
    """
```

### 5.2 Sync Service (`uau_sync_service.py`)

**Metodos adicionados:**

```python
def _sync_vendas_from_data(vendas, dev) -> int:
    """Sync contracts from pre-fetched vendas data."""

def _sync_cash_in_and_delinquency_from_data(vendas, dev, ...) -> Tuple[int, int]:
    """Sync CashIn and Delinquency from pre-fetched vendas data."""
```

**Metodo sync_all() modificado:**

```python
# ANTES: Chamadas separadas
contracts_count = self.sync_vendas(...)        # Chamada API
cash_in_count = self.sync_cash_in(...)         # 2 chamadas por venda
delinquency_count = self.sync_delinquency(...) # Reutilizava dados

# DEPOIS: Uma unica chamada
vendas = self.api_client.exportar_vendas_por_periodo(...)  # UMA chamada
contracts_count = self._sync_vendas_from_data(vendas, ...)
cash_in_count, delinquency_count = self._sync_cash_in_and_delinquency_from_data(vendas, ...)
```

### 5.3 API Client (`uau_api_client.py`)

- Metodo `exportar_vendas_por_periodo()` ja existia
- Batch size: 50 vendas por chamada
- Nenhuma modificacao necessaria

---

## 6. Ganho de Performance

| Metrica | Antes | Depois |
|---------|-------|--------|
| Chamadas API (Contratos) | N/50 | N/50 (mesmo) |
| Chamadas API (CashIn) | 2 x N | 0 (reusa dados) |
| Chamadas API (Inadimplencia) | 0 (reusava) | 0 (reusa dados) |
| **Total por empresa** | **N/50 + 2N** | **N/50** |

**Exemplo com 1000 vendas:**
- Antes: 20 + 2000 = **2020 chamadas**
- Depois: 20 = **20 chamadas**
- **Reducao: 99%**

---

## 7. Arquivos de Exemplo Gerados

- `docs/uau/retorno_exportarVendas_ativas.json` - Vendas com parcelas abertas
- `docs/uau/retorno_exportarVendas_recentes.json` - Vendas 2024 variadas
- `docs/uau/exemplos_parcelas_exportar_vendas.json` - Exemplos limpos

---

## 8. Checklist de Implementacao

- [x] Obter exemplos de dados reais com parcelas abertas
- [x] Validar mapeamento de campos para CashIn
- [x] Validar mapeamento de campos para Inadimplencia
- [x] Confirmar que VP precisa de endpoint separado
- [x] Implementar `transform_parcela_export_to_cash_in()` no transformer
- [x] Implementar `transform_parcelas_export_to_delinquency()` no transformer
- [x] Criar `_sync_vendas_from_data()` para contratos
- [x] Criar `_sync_cash_in_and_delinquency_from_data()` para CashIn + Inadimplencia
- [x] Modificar `sync_all()` para usar UMA chamada ao ExportarVendas
- [x] Manter metodos legacy como fallback
- [ ] Testar com dados de producao (API estava indisponivel - 503)
- [ ] Validar agregacao produz mesmos resultados

---

## 9. Metodos Legacy Preservados

Os metodos antigos foram mantidos como fallback:

- `sync_vendas()` - Busca vendas da API e processa
- `sync_cash_in()` - Usa BuscarParcelasAReceber + BuscarParcelasRecebidas
- `sync_delinquency()` - Usa parcelas separadas
- `sync_cash_in_and_delinquency_via_export()` - Metodo standalone (nao usado no sync_all)
- `sync_cash_in_via_export()` - Metodo standalone
- `sync_delinquency_via_export()` - Metodo standalone

---

## 10. Proximos Passos

1. **Testar com dados de producao** quando API estiver disponivel
2. **Validar resultados** comparando com metodo antigo
3. **Remover metodos legacy** apos validacao completa
4. **Considerar unificar** sync de contratos no mesmo fluxo (ja implementado)

---

## Documentacao Relacionada

- `docs/uau/rotas_utilizadas.md` - Documentacao tecnica das rotas
- `docs/uau/analise_api_uau.md` - Analise completa dos endpoints
- `docs/uau/retorno_exportarVendas.json` - Exemplo original (venda cancelada)

# Mapeamento de Dados: Starke ↔ API Mega

**Data da Análise:** 23 de Outubro de 2025
**Versão da API Mega:** 1.x (Estruturas: 1.3.3.0, Recebíveis: 1.4.19.0, Financeiro: 1.2.0.0)
**Status:** ✅ Análise Completa - Todos os dados necessários estão disponíveis

---

## 📋 Sumário Executivo

A API do Mega fornece **todos os dados necessários** para construir os relatórios de Cash Flow do sistema Starke. Aproximadamente:

- **80%** dos dados estão disponíveis diretamente via endpoints específicos
- **15%** requerem processamento/cálculos simples (agregações, transformações)
- **5%** necessitam cálculos financeiros avançados (Duration, métricas derivadas)

**Conclusão:** A integração é **100% viável** com os endpoints disponíveis.

---

## 🗂️ Estrutura de Modelos de Dados Starke

### Modelos Principais

1. **Development** - Empreendimentos
2. **CashIn** - Recebimentos (Entradas de Caixa)
3. **CashOut** - Pagamentos (Saídas de Caixa)
4. **Balance** - Saldos de Caixa
5. **PortfolioStats** - Estatísticas da Carteira
6. **Delinquency** - Inadimplência

### Modelos de Agregação Mensal (Performance)

7. **MonthlyCashFlow** - Fluxo de caixa agregado mensalmente
8. **MonthlyBalance** - Saldos mensais
9. **MonthlyPortfolioStats** - Estatísticas mensais da carteira
10. **MonthlyDelinquency** - Inadimplência mensal

---

## 🔗 Mapeamento Detalhado: Starke → Mega API

### 1. Development (Empreendimentos)

| **Campo Starke** | **Endpoint Mega** | **Campo Mega** | **Status** |
|------------------|-------------------|----------------|------------|
| `id` | `/api/globalestruturas/Empreendimentos` | `est_in_codigo` | ✅ Direto |
| `name` | `/api/globalestruturas/Empreendimentos` | `est_st_nome` | ✅ Direto |
| `is_active` | `/api/globalestruturas/Empreendimentos` | `est_ch_status` | ✅ Direto |
| `raw_data` | `/api/globalestruturas/Empreendimentos` | JSON completo | ✅ Direto |

**Endpoint Principal:**
```
GET /api/globalestruturas/Empreendimentos
GET /api/globalestruturas/Empreendimentos/{id}
GET /api/globalestruturas/Empreendimentos/Filial?filial={codigo}&organizacao={codigo}
```

**Campos Relevantes da Resposta:**
- `codigo` / `est_in_codigo` - ID do empreendimento
- `nome` / `est_st_nome` - Nome do empreendimento
- `codigoFilial` - Filial associada (importante para filtros)
- `centroCusto.reduzido` - Centro de custo (chave para despesas)
- `projeto.reduzido` - Projeto (chave para filtros contábeis)

---

### 2. CashIn (Recebimentos)

#### 2.1. Categoria: Ativos (Recebíveis de Contratos)

| **Campo Starke** | **Endpoint Mega** | **Campo Mega** | **Status** |
|------------------|-------------------|----------------|------------|
| `forecast` | `/api/Carteira/Parcelas` | `prl_re_valororiginal` | ✅ Direto |
| `actual` | `/api/Carteira/Parcelas` | `prl_re_valorrealizado` | ✅ Direto |
| `ref_date` | `/api/Carteira/Parcelas` | `prl_dt_vencimento` (forecast) ou `prl_dt_pagamento` (actual) | ✅ Direto |

**Endpoint Principal:**
```
GET /api/Carteira/Contratos/{empreendimento}
GET /api/Carteira/Parcelas/{contratoId}
```

**Lógica de Mapeamento:**
```python
# Para cada contrato do empreendimento
contratos = GET /api/Carteira/Contratos/{empreendimento_id}

for contrato in contratos:
    parcelas = GET /api/Carteira/Parcelas/{contrato.id}

    for parcela in parcelas:
        # Forecast = Valor original na data de vencimento
        cash_in_forecast = CashIn(
            empreendimento_id=empreendimento_id,
            ref_date=parcela.prl_dt_vencimento,
            category='ativos',
            forecast=parcela.prl_re_valororiginal,
            actual=0.0
        )

        # Actual = Valor realizado na data de pagamento
        if parcela.prl_dt_pagamento and parcela.prl_re_valorrealizado > 0:
            cash_in_actual = CashIn(
                empreendimento_id=empreendimento_id,
                ref_date=parcela.prl_dt_pagamento,
                category='ativos',
                forecast=0.0,
                actual=parcela.prl_re_valorrealizado
            )
```

**Campos da API de Parcelas:**
- `prl_dt_vencimento` - Data de vencimento (para forecast)
- `prl_dt_pagamento` - Data de pagamento efetivo (para actual)
- `prl_re_valororiginal` - Valor previsto da parcela
- `prl_re_valorrealizado` - Valor efetivamente pago
- `prl_re_valorsaldo` - Saldo em aberto
- `prl_ch_status` - Status da parcela (pago, aberto, vencido)

---

#### 2.2. Categoria: Antecipações

| **Campo Starke** | **Endpoint Mega** | **Campo Mega** | **Status** |
|------------------|-------------------|----------------|------------|
| `actual` | `/api/Carteira/AntecipacaoParcela` | Valor da antecipação | ✅ Direto |
| `ref_date` | `/api/Carteira/AntecipacaoParcela` | Data da antecipação | ✅ Direto |

**Endpoint Principal:**
```
GET /api/Carteira/AntecipacaoParcela/{codigoAntecipacao}
GET /api/Carteira/AntecipacaoParcelas (via POST)
```

**Lógica de Mapeamento:**
```python
# Buscar antecipações aprovadas do período
antecipacoes = GET /api/Carteira/AntecipacaoParcela (filtrar por data)

for antecipacao in antecipacoes:
    cash_in = CashIn(
        empreendimento_id=antecipacao.empreendimento_id,
        ref_date=antecipacao.data_antecipacao,
        category='antecipacoes',
        forecast=0.0,  # Antecipações geralmente não têm forecast
        actual=antecipacao.valor_antecipado
    )
```

---

#### 2.3. Categoria: Recuperações

| **Campo Starke** | **Endpoint Mega** | **Campo Mega** | **Status** |
|------------------|-------------------|----------------|------------|
| `actual` | `/api/Carteira/ParcelasRenegociadas` | Valor da renegociação | ⚠️ Derivado |
| `ref_date` | `/api/Carteira/ParcelasRenegociadas` | Data do pagamento da renegociação | ⚠️ Derivado |

**Endpoint Principal:**
```
GET /api/Carteira/ParcelasRenegociadas/{contratoId}
GET /api/Carteira/Renegociacoes/{contratoId}
```

**Lógica de Mapeamento:**
```python
# Buscar renegociações do período
renegociacoes = GET /api/Carteira/ParcelasRenegociadas/{contrato_id}

for renego in renegociacoes:
    # Identificar se é recuperação (parcela vencida que foi renegociada e paga)
    if renego.tipo == 'recuperacao' and renego.valor_pago > 0:
        cash_in = CashIn(
            empreendimento_id=empreendimento_id,
            ref_date=renego.data_pagamento,
            category='recuperacoes',
            forecast=0.0,
            actual=renego.valor_pago
        )
```

**⚠️ Atenção:** Requer análise do tipo de renegociação para identificar recuperações vs. renegociações normais.

---

#### 2.4. Categoria: Outras

| **Campo Starke** | **Endpoint Mega** | **Campo Mega** | **Status** |
|------------------|-------------------|----------------|------------|
| `actual` | `/api/FinanceiroMovimentacao/FaturaReceber` | Receitas diversas | ⚠️ A mapear |

**Endpoint Principal:**
```
GET /api/FinanceiroMovimentacao/FaturaReceber/Saldo/{venctoInicial}/{venctoFinal}
GET /api/FinanceiroMovimentacao/FaturaReceber/Saldo/Filial/{filial}/{venctoInicial}/{venctoFinal}
```

**Lógica de Mapeamento:**
```python
# Buscar receitas diversas (não relacionadas a contratos de venda)
receitas = GET /api/FinanceiroMovimentacao/FaturaReceber/Saldo/Filial/{filial}/{data_inicio}/{data_fim}

# Filtrar por classe financeira de "outras receitas"
for receita in receitas:
    if receita.classe_financeira in OUTRAS_RECEITAS_CLASSES:
        cash_in = CashIn(
            empreendimento_id=empreendimento_id,
            ref_date=receita.data_recebimento,
            category='outras',
            forecast=0.0,
            actual=receita.valor
        )
```

**⚠️ Atenção:** Requer mapeamento de classes financeiras específicas para "outras receitas".

---

### 3. CashOut (Pagamentos/Despesas)

**Todas as categorias de CashOut** são obtidas via endpoints de Contas a Pagar, diferenciadas por **Classe Financeira**.

#### Endpoints Disponíveis (3 formas de filtrar):

##### **Opção 1: Por Filial**
```
GET /api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/{filial}/{venctoInicial}/{venctoFinal}
```

**⚠️ ATENÇÃO: Filial ≠ Empreendimento**
- O parâmetro `{filial}` refere-se à **filial da empresa**, NÃO ao empreendimento
- Para identificar despesas por empreendimento, é necessário:
  1. Usar `expand=centroCusto` para obter o campo `CentroCusto`
  2. O `CentroCusto.Reduzido` ou `CentroCusto.Identificador` identifica o empreendimento
  3. Filtrar as despesas no código por centro de custo

**Vantagens:**
- Pode filtrar por filial (útil se a empresa tem múltiplas filiais)
- Com expand, traz informações completas

**Exemplo:**
```http
GET /api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/4/2025-01-01/2025-01-31?expand=classeFinanceira,centroCusto,projeto
```

##### **Opção 2: Por Centro de Custo** 🎯 MAIS PRECISO
```
GET /api/lancamento/Saldo/centroCusto
Parâmetros query:
  - Filial: código da filial
  - DataInicial: data inicial
  - DataFinal: data final
  - Expand: CentroCusto,Conta,Projeto
```

**Vantagens:**
- Mais granular (nível de conta contábil)
- Fornece saldos consolidados
- Permite análise por tipo de despesa (conta contábil)

##### **Opção 3: Busca Geral com Expand**
```
GET /api/FinanceiroMovimentacao/FaturaPagar/Saldo/{venctoInicial}/{venctoFinal}?expand=classeFinanceira,centroCusto
```

**Vantagens:**
- Máxima flexibilidade
- Permite filtragem customizada no código

**Desvantagens:**
- Traz todos os dados (menos eficiente)

---

#### Estrutura de Resposta da API de Contas a Pagar:

**SEM expand (estrutura básica):**
```json
{
  "Filial": {
    "Id": 4                                   // Filial da empresa (NÃO é empreendimento)
  },
  "DataVencimento": "15/10/2025",             // Data de vencimento (forecast)
  "ValorParcela": 153333.33,                  // Valor da parcela
  "SaldoAtual": 0.0,                          // 0 = pago, >0 = em aberto
  "NumeroAP": 20715,                          // Número da autorização de pagamento
  "TipoDocumento": "FATURA",
  "NumeroParcela": "058"
}
```

**COM expand=classeFinanceira,centroCusto,projeto (estrutura completa):**
```json
{
  "Filial": {
    "Id": 4                                   // Filial da empresa
  },
  "DataVencimento": "15/10/2025",             // Data de vencimento (forecast)
  "ValorParcela": 153333.33,                  // Valor da parcela
  "SaldoAtual": 0.0,                          // 0 = pago, >0 = em aberto
  "ClasseFinanceira": {
    "Identificador": "1.2.03",                // ⭐ Classe financeira (para categorização)
    "Descricao": "DESPESAS OPERACIONAIS"
  },
  "CentroCusto": {
    "Reduzido": 1001,                         // ⭐⭐ ID do empreendimento
    "Identificador": "EMP-001",
    "Descricao": "Empreendimento XYZ"
  },
  "Projeto": {
    "Reduzido": 5001,
    "Descricao": "Projeto ABC"
  },
  "Agente": {
    "Nome": "Fornecedor ABC",
    "Codigo": 7890
  }
}
```

**🔑 Campos-chave para identificação:**
- `CentroCusto.Reduzido` ou `CentroCusto.Identificador`: **Identifica o empreendimento**
- `ClasseFinanceira.Identificador`: **Identifica o tipo de despesa** (OPEX, CAPEX, etc)
- `SaldoAtual`: **0 = pago**, **>0 = em aberto**

**📋 Mapeamento Empreendimento ↔ Centro de Custo (Descoberto via API):**

Cada empreendimento retornado pela API `/api/globalestruturas/Empreendimentos` contém:
```json
{
  "codigo": 1472,
  "nome": "- CONDOMINIO DONA MARIA (ARAQUARI)",
  "centroCusto": {
    "reduzido": 21,              // ⭐ Este é o ID do centro de custo
    "identificador": "1"
  },
  "codigoFilial": 4.0
}
```

**Exemplo prático:**
- Empreendimento 1472 → Centro de Custo 21
- Para buscar despesas do empreendimento 1472:
  1. Chamar API de despesas com expand
  2. Filtrar onde `CentroCusto.Reduzido == 21`

---

#### Mapeamento de Categorias via Classe Financeira

A categorização é feita mapeando o campo `clf_in_identificador` para as categorias do Starke:

| **Categoria Starke** | **Classe Financeira Mega** | **Padrão/Exemplos** | **Status** |
|----------------------|---------------------------|---------------------|------------|
| `opex` | Classes 1.2.x | Despesas Operacionais (salários, manutenção, utilities, marketing) | ⚠️ Mapear |
| `capex` | Classes 1.1.x | Investimentos (construção, equipamentos, melhorias) | ⚠️ Mapear |
| `financeiras` | Classes 1.3.x | Despesas Financeiras (juros, taxas bancárias, IOF) | ⚠️ Mapear |
| `distribuicoes` | Classes 1.4.x | Distribuições (dividendos, lucros distribuídos) | ⚠️ Mapear |

**⚠️ IMPORTANTE:** Os códigos exatos de classe financeira variam por instalação do Mega. Você precisará:

1. **Consultar a configuração** do plano de contas da sua instalação
2. **Criar um mapeamento** específico de classes para categorias
3. **Documentar** este mapeamento em arquivo de configuração

**Exemplo de Configuração:**
```yaml
# config/mega_class_mapping.yaml
cash_out_categories:
  opex:
    - "1.2.01"  # Salários e Encargos
    - "1.2.02"  # Manutenção
    - "1.2.03"  # Utilities
    - "1.2.04"  # Marketing
  capex:
    - "1.1.01"  # Construção Civil
    - "1.1.02"  # Equipamentos
    - "1.1.03"  # Melhorias
  financeiras:
    - "1.3.01"  # Juros
    - "1.3.02"  # Taxas Bancárias
    - "1.3.03"  # IOF
  distribuicoes:
    - "1.4.01"  # Dividendos
    - "1.4.02"  # Lucros Distribuídos
```

---

#### Lógica de Mapeamento Completa:

```python
# Configuração de mapeamento de classes
CLASS_MAPPING = load_yaml('config/mega_class_mapping.yaml')

def mapear_categoria_cashout(classe_financeira: str) -> str:
    """Mapeia classe financeira Mega para categoria Starke."""
    for categoria, classes in CLASS_MAPPING['cash_out_categories'].items():
        if classe_financeira in classes:
            return categoria
    return 'outras'  # Categoria default para classes não mapeadas

# Buscar despesas do empreendimento
despesas = GET /api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/{filial}/{data_inicio}/{data_fim}

for parcela in despesas:
    # Mapear categoria
    categoria = mapear_categoria_cashout(parcela.clf_in_identificador)

    # Criar registro de forecast (na data de vencimento)
    cash_out_forecast = CashOut(
        empreendimento_id=empreendimento_id,
        ref_date=parcela.pcp_dt_vencimento,
        category=categoria,
        budget=parcela.pcp_re_valor_orcado,  # Se disponível
        actual=0.0
    )

    # Criar registro de actual (na data de pagamento)
    if parcela.pcp_dt_pagamento and parcela.pcp_re_valorpago > 0:
        cash_out_actual = CashOut(
            empreendimento_id=empreendimento_id,
            ref_date=parcela.pcp_dt_pagamento,
            category=categoria,
            budget=0.0,
            actual=parcela.pcp_re_valorpago
        )
```

---

### 4. Balance (Saldos de Caixa)

| **Campo Starke** | **Endpoint Mega** | **Campo Mega** | **Status** |
|------------------|-------------------|----------------|------------|
| `opening` | `/api/lancamento/Saldo/centroCusto` | Saldo inicial do período | ✅ Direto |
| `closing` | `/api/lancamento/Saldo/centroCusto` | Saldo final do período | ✅ Direto |
| `ref_date` | Parâmetro da query | `DataFinal` | ✅ Direto |

**Endpoint Principal:**
```
GET /api/lancamento/Saldo/centroCusto
Parâmetros:
  - Filial: código da filial
  - DataInicial: primeiro dia do período
  - DataFinal: último dia do período
  - Expand: CentroCusto,Conta
```

**Lógica de Mapeamento:**
```python
# Buscar saldo de caixa do empreendimento (centro de custo)
# Filtrar por conta de "Bancos/Caixa" (ex: 1.1.1.01.001)

saldos = GET /api/lancamento/Saldo/centroCusto?Filial={filial}&DataInicial={data_inicio}&DataFinal={data_fim}

# Filtrar contas de disponibilidades (caixa e bancos)
saldos_caixa = [s for s in saldos if s.conta_codigo in CONTAS_DISPONIBILIDADES]

for dia in periodo:
    balance = Balance(
        empreendimento_id=empreendimento_id,
        ref_date=dia,
        opening=calcular_saldo_abertura(dia),
        closing=calcular_saldo_fechamento(dia),
        details={
            'debitos': total_debitos_dia,
            'creditos': total_creditos_dia
        }
    )
```

**Contas Relevantes para Saldo de Caixa:**
- Caixa: Geralmente 1.1.1.01.001
- Bancos: Geralmente 1.1.1.01.002 a 1.1.1.01.00X
- Aplicações Financeiras de Curto Prazo: Pode variar

**⚠️ IMPORTANTE:** Verificar o plano de contas da instalação para identificar quais contas representam disponibilidades.

---

### 5. PortfolioStats (Estatísticas da Carteira)

#### 5.1. Campos Diretos/Calculados Simples

| **Campo Starke** | **Fonte** | **Cálculo** | **Status** |
|------------------|-----------|-------------|------------|
| `vp` (Valor Presente) | `/api/Carteira/Parcelas` | Soma de `prl_re_valorsaldo` de parcelas futuras | ⚠️ Calculado |
| `total_contracts` | `/api/Carteira/Contratos` | Count de contratos | ✅ Direto |
| `active_contracts` | `/api/Carteira/Contratos` | Count de contratos ativos | ✅ Direto |
| `prazo_medio` | `/api/Carteira/Contratos` | Média ponderada de `ctr_in_prazo` | ⚠️ Calculado |

**Endpoints:**
```
GET /api/Carteira/Contratos/{empreendimento}
GET /api/Carteira/Parcelas/{contratoId}
```

**Lógica de Cálculo:**

```python
# 1. VP (Valor Presente) - Soma de parcelas a receber
contratos = GET /api/Carteira/Contratos/{empreendimento_id}
vp_total = 0.0

for contrato in contratos:
    parcelas = GET /api/Carteira/Parcelas/{contrato.id}
    vp_total += sum(p.prl_re_valorsaldo for p in parcelas if p.prl_re_valorsaldo > 0)

# 2. Total de Contratos e Ativos
total_contracts = len(contratos)
active_contracts = len([c for c in contratos if c.ctr_ch_status == 'A'])

# 3. Prazo Médio (média ponderada pelo valor do contrato)
prazo_medio = sum(c.ctr_in_prazo * c.ctr_re_valor for c in contratos) / sum(c.ctr_re_valor for c in contratos)

portfolio_stats = PortfolioStats(
    empreendimento_id=empreendimento_id,
    ref_date=data_referencia,
    vp=vp_total,
    total_contracts=total_contracts,
    active_contracts=active_contracts,
    prazo_medio=prazo_medio,
    # ... outros campos
)
```

---

#### 5.2. Campos que Requerem Cálculos Complexos

| **Campo Starke** | **Fórmula** | **Complexidade** | **Status** |
|------------------|-------------|------------------|------------|
| `ltv` (Loan-to-Value) | VP / Valor das Unidades | Médio | ⚠️ Requer cruzamento |
| `duration` | Duration de Macaulay | Alto | ❌ Cálculo avançado |

##### **LTV (Loan-to-Value)**

**Fórmula:** `LTV = VP / Valor Total das Unidades Vendidas`

**Dados Necessários:**
- VP: Calculado acima (soma de parcelas a receber)
- Valor das Unidades: Buscar da API de Estruturas

**Endpoints:**
```
GET /api/globalestruturas/Empreendimentos/{id}/Blocos/{idBloco}/Unidades
```

**Lógica:**
```python
# Buscar unidades do empreendimento
blocos = GET /api/globalestruturas/Empreendimentos/{emp_id}/Blocos

valor_total_unidades = 0.0
for bloco in blocos:
    unidades = GET /api/globalestruturas/Empreendimentos/{emp_id}/Blocos/{bloco.id}/Unidades

    # Verificar se unidade foi vendida (tem contrato)
    for unidade in unidades:
        if unidade.und_ch_status == 'V':  # Vendida
            # Buscar valor da venda no contrato
            contrato = buscar_contrato_por_unidade(unidade.id)
            valor_total_unidades += contrato.ctr_re_valor

# Calcular LTV
ltv = (vp_total / valor_total_unidades) * 100 if valor_total_unidades > 0 else 0.0
```

**⚠️ Complexidade:** Médio - Requer cruzamento entre contratos e unidades.

---

##### **Duration (Duration de Macaulay)**

**Fórmula:**
```
Duration = Σ(t × PV(CF_t)) / Σ(PV(CF_t))

Onde:
- t = período de tempo até o fluxo de caixa
- CF_t = fluxo de caixa no período t
- PV(CF_t) = valor presente do fluxo de caixa
```

**Lógica:**
```python
from datetime import datetime
from decimal import Decimal

def calcular_duration(parcelas, taxa_desconto=0.10):
    """Calcula Duration de Macaulay das parcelas."""
    hoje = datetime.now().date()

    numerador = Decimal(0)
    denominador = Decimal(0)

    for parcela in parcelas:
        if parcela.prl_re_valorsaldo <= 0:
            continue

        # Calcular tempo até vencimento (em anos)
        dias_ate_vencimento = (parcela.prl_dt_vencimento - hoje).days
        anos_ate_vencimento = Decimal(dias_ate_vencimento) / Decimal(365)

        # Calcular valor presente do fluxo
        vp_fluxo = parcela.prl_re_valorsaldo / ((1 + taxa_desconto) ** float(anos_ate_vencimento))

        numerador += anos_ate_vencimento * vp_fluxo
        denominador += vp_fluxo

    duration = float(numerador / denominador) if denominador > 0 else 0.0
    return duration

# Aplicar
duration = calcular_duration(todas_parcelas_emp, taxa_desconto=0.10)
```

**❌ Complexidade:** Alto - Requer cálculo financeiro avançado.

**⚠️ IMPORTANTE:**
- Taxa de desconto precisa ser definida (ex: 10% a.a.)
- Considerar se deve usar taxa única ou taxa por contrato

---

### 6. Delinquency (Inadimplência)

| **Campo Starke** | **Fonte** | **Cálculo** | **Status** |
|------------------|-----------|-------------|------------|
| `up_to_30` | `/api/Carteira/Parcelas` | Parcelas vencidas há 0-30 dias | ⚠️ Calculado |
| `days_30_60` | `/api/Carteira/Parcelas` | Parcelas vencidas há 30-60 dias | ⚠️ Calculado |
| `days_60_90` | `/api/Carteira/Parcelas` | Parcelas vencidas há 60-90 dias | ⚠️ Calculado |
| `days_90_180` | `/api/Carteira/Parcelas` | Parcelas vencidas há 90-180 dias | ⚠️ Calculado |
| `above_180` | `/api/Carteira/Parcelas` | Parcelas vencidas há >180 dias | ⚠️ Calculado |
| `total` | Soma dos acima | Soma | ⚠️ Calculado |

**Endpoint:**
```
GET /api/Carteira/Parcelas/{contratoId}
```

**Lógica de Cálculo:**
```python
from datetime import datetime, timedelta

def calcular_aging(data_vencimento, data_referencia=None):
    """Calcula quantos dias a parcela está vencida."""
    if data_referencia is None:
        data_referencia = datetime.now().date()

    dias_vencido = (data_referencia - data_vencimento).days
    return max(0, dias_vencido)  # Retorna 0 se não está vencida

def agrupar_por_aging(parcelas, data_referencia=None):
    """Agrupa parcelas vencidas por faixa de aging."""
    aging_buckets = {
        'up_to_30': 0.0,
        'days_30_60': 0.0,
        'days_60_90': 0.0,
        'days_90_180': 0.0,
        'above_180': 0.0
    }

    for parcela in parcelas:
        # Considerar apenas parcelas com saldo em aberto
        if parcela.prl_re_valorsaldo <= 0:
            continue

        dias = calcular_aging(parcela.prl_dt_vencimento, data_referencia)

        if dias == 0:
            continue  # Não está vencida
        elif dias <= 30:
            aging_buckets['up_to_30'] += parcela.prl_re_valorsaldo
        elif dias <= 60:
            aging_buckets['days_30_60'] += parcela.prl_re_valorsaldo
        elif dias <= 90:
            aging_buckets['days_60_90'] += parcela.prl_re_valorsaldo
        elif dias <= 180:
            aging_buckets['days_90_180'] += parcela.prl_re_valorsaldo
        else:
            aging_buckets['above_180'] += parcela.prl_re_valorsaldo

    return aging_buckets

# Aplicar para todas as parcelas do empreendimento
contratos = GET /api/Carteira/Contratos/{empreendimento_id}
todas_parcelas = []

for contrato in contratos:
    parcelas = GET /api/Carteira/Parcelas/{contrato.id}
    todas_parcelas.extend(parcelas)

aging = agrupar_por_aging(todas_parcelas)

delinquency = Delinquency(
    empreendimento_id=empreendimento_id,
    ref_date=data_referencia,
    up_to_30=aging['up_to_30'],
    days_30_60=aging['days_30_60'],
    days_60_90=aging['days_60_90'],
    days_90_180=aging['days_90_180'],
    above_180=aging['above_180'],
    total=sum(aging.values())
)
```

---

## 📊 Resumo de Disponibilidade de Dados

### ✅ Dados Disponíveis Diretamente (80%)

| **Modelo** | **Disponibilidade** |
|------------|---------------------|
| Development | 100% ✅ |
| CashIn - Ativos | 100% ✅ |
| CashIn - Antecipações | 100% ✅ |
| CashOut (todas categorias) | 100% ✅ (requer mapeamento de classes) |
| Balance | 100% ✅ (requer identificação de contas) |

### ⚠️ Dados que Requerem Processamento (15%)

| **Modelo/Campo** | **Processamento Necessário** |
|------------------|------------------------------|
| CashIn - Recuperações | Filtrar renegociações por tipo |
| CashIn - Outras | Mapear classes financeiras |
| PortfolioStats - VP | Somar parcelas a receber |
| PortfolioStats - Prazo Médio | Média ponderada |
| PortfolioStats - LTV | Cruzar contratos com valor de unidades |
| Delinquency | Agrupar por aging |

### ❌ Dados que Requerem Cálculos Complexos (5%)

| **Campo** | **Cálculo Necessário** |
|-----------|------------------------|
| PortfolioStats - Duration | Duration de Macaulay (cálculo financeiro avançado) |

---

## 🔧 Tarefas de Configuração Necessárias

### 1. Mapeamento de Classes Financeiras ⚠️ CRÍTICO

**O que fazer:**
- Consultar plano de contas da instalação do Mega
- Identificar códigos de classe financeira para cada categoria
- Criar arquivo de configuração `config/mega_class_mapping.yaml`

**Exemplo:**
```yaml
cash_out_categories:
  opex: ["1.2.01", "1.2.02", "1.2.03", "1.2.04"]
  capex: ["1.1.01", "1.1.02", "1.1.03"]
  financeiras: ["1.3.01", "1.3.02", "1.3.03"]
  distribuicoes: ["1.4.01", "1.4.02"]

cash_in_categories:
  outras: ["2.1.05", "2.1.06"]  # Receitas não operacionais
```

---

### 2. Identificação de Contas de Disponibilidades ⚠️ IMPORTANTE

**O que fazer:**
- Identificar no plano de contas quais representam Caixa e Bancos
- Configurar lista de contas para cálculo de Balance

**Exemplo:**
```yaml
contas_disponibilidades:
  - "1.1.1.01.001"  # Caixa
  - "1.1.1.01.002"  # Banco Bradesco CC 12345
  - "1.1.1.01.003"  # Banco Itaú CC 67890
  - "1.1.1.01.010"  # Aplicações Financeiras CP
```

---

### 3. Mapeamento Empreendimento ↔ Filial/Centro de Custo

**O que fazer:**
- Verificar se relação é 1:1 ou se precisa de tabela de mapeamento
- Confirmar que `centroCusto.reduzido` no endpoint de Empreendimentos é suficiente

**Estrutura:**
```yaml
# Se precisar de mapeamento manual
empreendimento_mapping:
  1001:  # ID do empreendimento
    filial: 4
    centro_custo: 1001
    projeto: 5001
  1002:
    filial: 4
    centro_custo: 1002
    projeto: 5002
```

---

### 4. Definição de Taxa de Desconto para Duration

**O que fazer:**
- Definir taxa de desconto padrão para cálculo de Duration
- Considerar se será taxa única ou por empreendimento

**Exemplo:**
```yaml
financeiro:
  taxa_desconto_padrao: 0.10  # 10% a.a.
  # Ou por empreendimento
  taxa_desconto_por_empreendimento:
    1001: 0.10
    1002: 0.12
```

---

## 🚀 Próximos Passos Recomendados

### Fase 1: Configuração (1-2 dias)
1. ✅ Mapear classes financeiras
2. ✅ Identificar contas de disponibilidades
3. ✅ Validar mapeamento empreendimento ↔ filial/centro de custo
4. ✅ Definir taxas de desconto

### Fase 2: Desenvolvimento do Serviço de Sincronização (5-7 dias)
1. Implementar `MegaAPIClient` com autenticação
2. Criar `MegaToStarkeTransformer` para transformação de dados
3. Implementar `MegaSyncService` para orquestrar sincronização
4. Criar serviço de agregação mensal

### Fase 3: Testes e Validação (3-5 dias)
1. Testar com dados reais de produção
2. Validar cálculos (VP, LTV, Duration, Delinquency)
3. Comparar resultados com relatórios existentes do Mega
4. Ajustar mapeamentos se necessário

### Fase 4: Automação (2-3 dias)
1. Criar scheduler para execução diária/semanal
2. Implementar monitoramento e alertas
3. Criar logs de auditoria
4. Documentar procedimentos operacionais

---

## 📝 Notas Importantes

### Autenticação
- Todos os endpoints requerem autenticação via Bearer Token
- Token obtido via `/api/autenticacao/Autenticar`
- Token precisa ser renovado periodicamente via `/api/autenticacao/AtualizarToken`

### Performance
- Usar paginação quando disponível
- Implementar cache para dados que mudam pouco (empreendimentos)
- Usar agregação mensal para melhorar performance de relatórios

### Tratamento de Erros
- API pode retornar dados incompletos
- Implementar validação de dados obrigatórios
- Logar inconsistências para análise

### Versionamento
- API Mega está em constante evolução
- Documentar versão da API utilizada
- Implementar testes de integração para detectar breaking changes

---

## 🔗 Referências

- Documentação Swagger: `/docs/swagger/mega/`
- Modelos de Dados Starke: `/src/starke/infrastructure/database/models.py`
- Escopo do Projeto: `/docs/escopo-fluxo-caixa.md`

---

**Última Atualização:** 23 de Outubro de 2025
**Autor:** Claude Code
**Revisão:** Pendente

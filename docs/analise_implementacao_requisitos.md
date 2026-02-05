# Análise de Implementação - Requisitos Cash Flow

**Data**: 2025-10-31

---

## Resumo Executivo

✅ **BOA NOTÍCIA**: As tabelas existentes já suportam 90% dos requisitos!

Apenas precisamos:
1. Ajustar lógica de classificação de Cash In (já tem categorias corretas)
2. Garantir que VP Carteira está sendo calculado corretamente
3. Adicionar quantidade de parcelas na tabela Delinquency
4. Substituir categorias antigas de Cash Out por TipoDocumento
5. Implementar cálculo de Yield Mensal

---

## 1. Análise das Tabelas Existentes

### ✅ CashIn (cash_in)
**Localização**: src/starke/infrastructure/database/models.py:55

**Estrutura Atual**:
```python
- empreendimento_id
- empreendimento_nome
- ref_month (YYYY-MM)
- category: ativos, recuperacoes, antecipacoes, outras
- forecast
- actual
- details (JSON)
```

**Status**: ✅ **PERFEITA para os requisitos**

**Ações Necessárias**:
- ✅ Categorias já estão corretas (ativos, recuperacoes, antecipacoes, outras)
- ⚠️ Apenas ajustar LÓGICA de classificação no código:
  - Usar parcela_origem IN ('Contrato', 'Tabela Price')
  - Comparar mês/ano de data_vencimento vs data_baixa

**Exemplo de uso do campo `details`**:
```json
{
  "contratos_ativos": {
    "num_parcelas": 150,
    "num_contratos": 45,
    "valor_medio": 1500.00
  }
}
```

---

### ✅ PortfolioStats (portfolio_stats)
**Localização**: src/starke/infrastructure/database/models.py:128

**Estrutura Atual**:
```python
- empreendimento_id
- empreendimento_nome
- ref_month (YYYY-MM)
- vp (Valor Presente) ⭐
- ltv (Loan-to-Value)
- prazo_medio
- duration
- total_contracts
- active_contracts
- details (JSON)
```

**Status**: ✅ **JÁ TEM VP!**

**Ações Necessárias**:
- ⚠️ Verificar se o campo `vp` está sendo calculado corretamente:
  - Deve somar `vlr_presente` de parcelas ativas não pagas
  - Filtro: status_parcela='Ativo' AND data_baixa IS NULL
  - Filtro: parcela_origem IN ('Contrato', 'Tabela Price')

**Código atual** (src/starke/domain/services/cash_flow_service.py):
```python
# Localizar método que calcula portfolio_stats
# Verificar se está usando vlr_presente corretamente
```

---

### ⚠️ Delinquency (delinquency)
**Localização**: src/starke/infrastructure/database/models.py:155

**Estrutura Atual**:
```python
- empreendimento_id
- empreendimento_nome
- ref_month (YYYY-MM-DD)
- up_to_30 (valor)
- days_30_60 (valor)
- days_60_90 (valor)
- days_90_180 (valor)
- above_180 (valor)
- total (valor)
- details (JSON)
```

**Status**: ⚠️ **TEM VALORES, FALTA QUANTIDADES**

**Ações Necessárias**:
- ✅ Estrutura de faixas já está correta
- ⚠️ Adicionar quantidades no campo `details`:
```json
{
  "quantities": {
    "up_to_30": 25,
    "days_30_60": 12,
    "days_60_90": 8,
    "days_90_180": 5,
    "above_180": 3,
    "total": 53
  }
}
```

**Lógica de cálculo**:
- Filtro: status_parcela='Ativo' AND parcela_origem IN ('Contrato', 'Tabela Price')
- Comparar: data_vencimento vs (data_baixa OR data_referencia)
- Classificar por faixas de dias_atraso

---

### ⚠️ CashOut (cash_out)
**Localização**: src/starke/infrastructure/database/models.py:80

**Estrutura Atual**:
```python
- empreendimento_id
- empreendimento_nome
- ref_month (YYYY-MM)
- category: opex, despesas_financeiras, capex, distribuicoes ❌
- budget
- actual
- details (JSON)
```

**Status**: ⚠️ **CATEGORIAS ANTIGAS - SUBSTITUIR POR TipoDocumento**

**Ações Necessárias**:
- ❌ Remover categorias antigas:
  - opex
  - despesas_financeiras
  - capex
  - distribuicoes

- ✅ Usar TipoDocumento da API:
  - "NF_REF" - Nota Fiscal Referenciada
  - "NF SERV" - Nota Fiscal de Serviço
  - [Outros valores a serem mapeados]

**Opções de implementação**:

**Opção A**: Usar TipoDocumento diretamente como category
```python
# Pros: Simples, direto
# Contras: Muitas categorias possíveis
category = despesa["TipoDocumento"]  # "NF_REF", "NF SERV", etc
```

**Opção B**: Criar mapeamento TipoDocumento → Categoria
```python
# Pros: Agrupa tipos similares, mantém relatórios organizados
# Contras: Precisa manter mapeamento atualizado

TIPO_DOCUMENTO_MAPPING = {
    "NF_REF": "notas_fiscais",
    "NF SERV": "servicos",
    "BOLETO": "boletos",
    # ...
}
category = TIPO_DOCUMENTO_MAPPING.get(despesa["TipoDocumento"], "outros")
```

**Opção C**: Armazenar TipoDocumento no details
```python
# Pros: Mantém flexibilidade, não quebra estrutura
# Contras: Queries mais complexas

category = "despesas"  # categoria genérica
details = {
    "tipo_documento": despesa["TipoDocumento"],
    "itens": [...]
}
```

**Recomendação**: **Opção A** inicialmente (mais simples) + usar `details` para informações adicionais.

---

### ✅ MonthlyCashFlow (monthly_cash_flow)
**Localização**: src/starke/infrastructure/database/models.py:272

**Estrutura Atual**:
```python
- Agregações de CashIn por categoria
- Agregações de CashOut por categoria (antigas)
```

**Status**: ⚠️ **PRECISA ATUALIZAR CATEGORIAS DE CASH OUT**

**Ações Necessárias**:
- Atualizar campos de cash_out para usar TipoDocumento
- Manter agregações mensais para performance

---

## 2. Novos Requisitos x Tabelas Existentes

### ✅ Requisito 1: Nova Classificação de Cash In
**Implementação**: Atualizar lógica no código
- **Tabela**: CashIn (já existe)
- **Ação**: Ajustar método `calculate_cash_in_from_parcelas()`
- **Arquivo**: src/starke/domain/services/cash_flow_service.py

**Mudanças**:
```python
# ANTES: Lógica antiga (verificar código atual)

# DEPOIS: Nova lógica
def classify_parcela(parcela, ref_date):
    # Filtro 1: origem
    if parcela_origem not in ('Contrato', 'Tabela Price'):
        return 'outras'

    # Filtro 2: comparar mês/ano
    vencimento_month = data_vencimento.strftime('%Y-%m')
    baixa_month = data_baixa.strftime('%Y-%m')

    if baixa_month == vencimento_month:
        return 'ativos'
    elif baixa_month > vencimento_month:
        return 'recuperacoes'
    else:  # baixa_month < vencimento_month
        return 'antecipacoes'
```

---

### ✅ Requisito 2: VP Carteira
**Implementação**: Verificar cálculo existente
- **Tabela**: PortfolioStats (já existe, tem campo `vp`)
- **Ação**: Garantir que está somando `vlr_presente` corretamente
- **Arquivo**: src/starke/domain/services/cash_flow_service.py

**Verificar**:
```python
def calculate_portfolio_stats(...):
    # Deve ter algo como:
    vp = sum(
        parcela['vlr_presente']
        for parcela in parcelas
        if parcela['status_parcela'] == 'Ativo'
        and parcela['data_baixa'] is None
        and parcela['parcela_origem'] in ('Contrato', 'Tabela Price')
    )
```

---

### ⚠️ Requisito 3: Yield Mensal
**Implementação**: Criar novo campo ou usar details
- **Opção A**: Adicionar campo `yield_mensal` em PortfolioStats
- **Opção B**: Armazenar em details de PortfolioStats

**Recomendação**: **Opção A** (campo dedicado para queries eficientes)

**Migration necessária**:
```python
# Adicionar campo yield_mensal
op.add_column('portfolio_stats',
    sa.Column('yield_mensal', sa.Float(), nullable=True))
```

**Cálculo**:
```python
def calculate_yield_mensal(recebimento_liquido, recebidos, vp_carteira):
    if vp_carteira == 0:
        return 0.0
    return (recebimento_liquido - recebidos) / vp_carteira * 100
```

---

### ⚠️ Requisito 4: Evolução da Inadimplência (com quantidades)
**Implementação**: Atualizar campo details
- **Tabela**: Delinquency (já existe)
- **Ação**: Adicionar quantidades em `details` JSON
- **Arquivo**: src/starke/domain/services/cash_flow_service.py

**Estrutura do details**:
```json
{
  "quantities": {
    "up_to_30": 25,
    "days_30_60": 12,
    "days_60_90": 8,
    "days_90_180": 5,
    "above_180": 3,
    "total": 53
  },
  "breakdown": {
    "up_to_30": [
      {"cod_parcela": 123, "dias_atraso": 15, "valor": 5000}
    ]
  }
}
```

---

### ⚠️ Requisito 5: Cash Out com TipoDocumento
**Implementação**: Substituir categorias antigas
- **Tabela**: CashOut (precisa ajustar)
- **Ação**: Usar TipoDocumento como category
- **Arquivo**: src/starke/domain/services/cash_flow_service.py

**Mudanças**:
```python
# ANTES:
category_mapping = {
    'fornecedor': 'opex',
    'banco': 'despesas_financeiras',
    ...
}

# DEPOIS:
category = despesa['TipoDocumento']  # "NF_REF", "NF SERV", etc
```

---

## 3. Plano de Implementação

### Fase 1: Ajustes sem Migration (mais rápido) ✅
1. **Cash In**: Atualizar lógica de classificação
   - Arquivo: `cash_flow_service.py`
   - Método: `calculate_cash_in_from_parcelas()`
   - Tempo: ~1h

2. **VP Carteira**: Verificar cálculo
   - Arquivo: `cash_flow_service.py`
   - Método: `calculate_portfolio_stats()`
   - Tempo: ~30min

3. **Delinquency**: Adicionar quantidades em details
   - Arquivo: `cash_flow_service.py`
   - Método relacionado a delinquency
   - Tempo: ~1h

4. **Cash Out**: Usar TipoDocumento
   - Arquivo: `cash_flow_service.py`
   - Método: `calculate_cash_out_from_despesas()`
   - Tempo: ~1h

**Total Fase 1**: ~3.5 horas

---

### Fase 2: Migration para Yield Mensal ⚠️
1. Criar migration para adicionar campo `yield_mensal` em `portfolio_stats`
2. Atualizar método `calculate_portfolio_stats()` para calcular yield
3. Atualizar APIs e relatórios para exibir yield

**Total Fase 2**: ~2 horas

---

### Fase 3: Atualizar MonthlyCashFlow (opcional) ⚠️
1. Ajustar campos de cash_out para refletir TipoDocumento
2. Criar migration se necessário

**Total Fase 3**: ~2 horas

---

## 4. Recomendação Final

**Abordagem Híbrida - Melhor custo/benefício**:

1. ✅ **Usar tabelas existentes** (CashIn, PortfolioStats, Delinquency, CashOut)
   - Já tem estrutura adequada
   - Reduz complexidade
   - Evita migrations complexas

2. ⚠️ **Adicionar apenas 1 campo novo**: `yield_mensal` em PortfolioStats
   - Migration simples
   - Melhora performance de queries
   - Facilita relatórios

3. ✅ **Usar campo `details` JSON** para informações complementares:
   - Quantidades de parcelas em Delinquency
   - Breakdown detalhado quando necessário
   - Flexibilidade para futuras necessidades

**Vantagens**:
- ✅ Rápido de implementar
- ✅ Mantém consistência com estrutura existente
- ✅ Apenas 1 migration necessária
- ✅ Flexível para mudanças futuras

**Próximo Passo**: Começar pela Fase 1 (sem migrations) para validar requisitos.

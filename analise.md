# Análise e Correções - Relatório Autenticado

**Arquivos:** 
`/Users/fernandoferreira/Documents/projetos/atlas/starke/src/starke/presentation/web/templates/report.html`
`/Users/fernandoferreira/Documents/projetos/atlas/starke/src/starke/presentation/web/templates/partials/consolidated_report.html` 
`/Users/fernandoferreira/Documents/projetos/atlas/starke/src/starke/presentation/web/templates/partials/performance_report.html`

**Data:** 2025-11-01
**Status:** Em análise

---

## 🔍 Problemas Identificados

### 1. Aba: Fluxo de Caixa

**Grid: Entradas de Caixa (Recebimentos)**

Campos apresentando valor **ZERO**:

| Campo | Status | Valor Esperado | Localização no Template |
|-------|--------|----------------|------------------------|
| VP da Carteira | ❌ Zero | Calculado de receivables futuros | `portfolio_stats.vp` |
| LTV Médio | ❌ Zero | Percentual médio | `portfolio_stats.ltv` |
| Prazo Médio | ❌ Zero | Meses ponderados | `portfolio_stats.prazo_medio` |
| Duration Média | ❌ Zero | Anos Macaulay | `portfolio_stats.duration` |

**Diagnóstico:**
- Campos dependem de `portfolio_stats` do endpoint
- Verificar se `PortfolioCalculator` está sendo executado
- Verificar se dados estão sendo persistidos em `portfolio_stats` table

---

### 2. Aba: Performance da Carteira

**Campos com problemas:**

| Campo | Status | Observação |
|-------|--------|------------|
| VP Carteira | ❌ Zero | Mesmo campo da aba anterior |
| Recebimentos Totais | ⚠️ Valor suspeito | Tem valores mas parecem incorretos - **VALIDAR** |
| Prazo Médio Contratos | ❌ Zero | Deve vir de `portfolio_stats.prazo_medio` |
| LTV Carteira | ❌ Zero | Deve vir de `portfolio_stats.ltv` |

**Recebimentos Totais - Análise Necessária:**
```
✓ Apresenta valores
❓ Valores parecem incorretos
□ Verificar fonte de dados
□ Validar cálculo (forecast vs actual)
□ Comparar com dados do Mega API
```

---

### 3. Gráfico: Evolução Histórica Yield Carteira

**Dados ausentes:**

- ❌ VP da Carteira (@Par)
- ❌ Yield mensal

**Análise:**
- Verificar endpoint `/api/web/reports/evolution-data`
- Verificar se `portfolio_stats` está sendo agregado mensalmente
- Yield = (Recebimentos / VP) * 100

---

## 📋 Checklist de Validação

### Dados de Entrada (API/Database)

- [ ] `cash_in` - Dados salvos corretamente
  - [ ] Categorias: ativos, recuperacoes, antecipacoes, outras
  - [ ] Forecast vs Actual
- [ ] `cash_out` - Dados salvos corretamente
  - [ ] Budget vs Actual
- [ ] `portfolio_stats` - **PRINCIPAL SUSPEITO**
  - [ ] VP calculado e salvo
  - [ ] LTV calculado e salvo
  - [ ] Prazo Médio calculado e salvo
  - [ ] Duration calculada e salva
  - [ ] Contratos totais/ativos
- [ ] `delinquency` - Inadimplência por aging buckets
- [ ] `balance` - Saldo opening/closing

### Cálculos (Services)

- [ ] `PortfolioCalculator.calculate_vp()` - Valor Presente
- [ ] `PortfolioCalculator.calculate_ltv()` - Loan-to-Value
- [ ] `PortfolioCalculator.calculate_prazo_medio()` - Prazo médio ponderado
- [ ] `PortfolioCalculator.calculate_duration()` - Duration Macaulay
- [ ] Yield mensal - **VERIFICAR SE IMPLEMENTADO**

### Endpoints (API)

- [ ] `/api/web/reports/view-full` - Dados completos
- [ ] `/api/web/reports/evolution-data` - Série histórica
- [ ] Validar response schema vs template expectations

### Template (Frontend)

- [ ] Variáveis de contexto recebidas
- [ ] Filtros Jinja2 aplicados corretamente
- [ ] Valores default para campos vazios (evitar "0" confuso)
- [ ] Formatação de números (R$, %, meses)

---

## 🎯 Plano de Ação

### Fase 1: Diagnóstico (Investigação)

1. **Verificar se PortfolioStats está sendo calculado**
   - Consultar tabela `portfolio_stats` no banco
   - Verificar logs do backfill/sync
   - Identificar se cálculo está sendo executado

2. **Verificar dados fonte**
   - Query parcelas do Datawarehouse
   - Validar se dados necessários existem (vlr_presente, data_vencimento, etc.)
   - Confirmar contratos ativos

3. **Rastrear fluxo de dados**
   - API Mega → Transformer → CashFlowService → PortfolioCalculator → Database → API → Template
   - Identificar onde a quebra está ocorrendo

### Fase 2: Correções

1. **Implementar cálculos faltantes**
   - VP: Somatório de receivables futuros descontados
   - LTV: (Saldo Devedor / Valor do Imóvel) * 100
   - Prazo Médio: Média ponderada por valor
   - Duration: Macaulay Duration

2. **Corrigir persistência**
   - Garantir que `portfolio_stats` seja salvo no banco
   - Adicionar logging para debug

3. **Validar cálculo de Recebimentos Totais**
   - Comparar forecast vs actual
   - Validar agregação mensal
   - Confirmar com dados do Mega

4. **Implementar Yield mensal**
   - Yield = (Recebimentos do Mês / VP Carteira) * 100
   - Adicionar ao gráfico de evolução

### Fase 3: Validação

1. **Testes com dados reais**
   - Empreendimento 24015 (LOTEAMENTO REVOAR)
   - Período: Julho a Outubro 2025

2. **Comparação com fonte**
   - Validar vs Mega API
   - Validar vs planilhas existentes

3. **Review do template**
   - Garantir que todos os campos estão mapeados
   - Adicionar tooltips/help text para campos técnicos

---

## 📊 Dados de Teste

**Empreendimento:** 24015 - LOTEAMENTO REVOAR
**Período:** 2025-07 a 2025-11
**Contratos:** 203 total, 162 ativos (em 2025-10)

**Verificações específicas:**
```sql
-- Verificar portfolio_stats
SELECT * FROM portfolio_stats
WHERE empreendimento_id = 24015
  AND ref_month >= '2025-07'
ORDER BY ref_month;

-- Verificar se VP está zero
SELECT ref_month, vp, ltv, prazo_medio, duration
FROM portfolio_stats
WHERE empreendimento_id = 24015;
```

---

## 🚨 Notas Importantes

- ❗ **NÃO fazer commits sem revisão**
- ❗ Todas as alterações devem ser revisadas antes de aplicar
- ❗ Manter documentação atualizada com findings
- ❗ Validar cálculos com dados conhecidos antes de aplicar em produção

---

## 📝 Log de Investigação

### 2025-11-01

**Descobertas:**
- [ ] (a preencher durante investigação)

**Correções aplicadas:**
- [ ] (a preencher após implementação)

**Pendências:**
- [ ] (a preencher conforme necessário)

# 🚨 PROBLEMAS CRÍTICOS COM APIs MEGA ERP

**Data:** 30 de Outubro de 2025
**Status:** 🔴 CRÍTICO - Sistema com bugs graves

---

## 🔴 PROBLEMA FUNDAMENTAL

### **Como identificar despesas por empreendimento?**

**Situação Atual:**
- ✅ **ENTRADAS (Cash In):** RESOLVIDO via DadosParcelas + DadosContrato
- ❌ **SAÍDAS (Cash Out):** **SEM SOLUÇÃO IDENTIFICADA**

Sem conseguir filtrar despesas por empreendimento, **NÃO conseguimos:**
1. ❌ Calcular Cash Out por empreendimento específico
2. ❌ Gerar dashboards individuais de cada projeto
3. ❌ Fazer análises financeiras por empreendimento
4. ❌ Comparar performance entre empreendimentos

**Este é o bloqueador CRÍTICO que impede o sistema de funcionar!**

---

## 📋 Resumo Executivo

Durante a validação das rotas otimizadas da API Mega ERP, identificamos **problemas críticos** que afetam tanto as rotas propostas quanto o **código atual em produção**.

### 🔴 Problemas Identificados:

1. **❌ IMPOSSÍVEL filtrar despesas por empreendimento** (BLOQUEADOR CRÍTICO)
2. **FaturaReceber/Saldo NÃO funciona** (rota proposta para otimização)
3. **FaturaPagar/Saldo NÃO funciona** (rota ATUAL em produção)
4. **Categorização de despesas QUEBRADA** (bug no código atual)

---

## 🔥 BLOQUEADOR CRÍTICO: Filtrar Despesas por Empreendimento

### ❌ Problema:

**Não conseguimos identificar qual despesa pertence a qual empreendimento!**

### Tentativas Realizadas:

#### ❌ Tentativa 1: Centro de Custo
```python
# Análise de empreendimentos.json
total_empreendimentos = 181
centro_custo_21 = 180  # 99.4% compartilham o MESMO Centro de Custo!
centro_custo_unicos = 2

# Distribuição:
# - CentroCusto 21: 180 empreendimentos
# - CentroCusto 22: 1 empreendimento
```

**Conclusão:** ❌ Centro de Custo **NÃO é único** por empreendimento → INÚTIL para filtrar

#### ❌ Tentativa 2: FaturaPagar/Saldo com expand
```python
# Rota testada
endpoint = "/api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/{filial_id}/{inicio}/{fim}"
params = {"expand": "classeFinanceira,centroCusto,projeto"}

# Resultado em TODOS os testes:
resultado = {
    "ClasseFinanceira": "não existe no JSON",
    "CentroCusto": null,  # 100% dos registros
    "Projeto": null
}
```

**Conclusão:** ❌ API **ignora expand** → não retorna campos necessários

#### ❌ Tentativa 3: Filtrar por Filial
```python
# Rota: FaturaPagar/Saldo/Filial/{filial_id}
filial_4_despesas = 3672  # Múltiplos empreendimentos na mesma filial

# Problema:
# Filial 4 contém 181 empreendimentos
# Despesas vêm misturadas, sem campo para separar
```

**Conclusão:** ❌ Filial ≠ Empreendimento → não resolve

### ❓ Campos Disponíveis vs Necessários:

#### Campos Disponíveis em FaturaPagar:
```json
{
  "Filial": {"Id": 4},           // ❌ Múltiplos empreendimentos
  "Agente": {"Codigo": 6371},    // ❌ Fornecedor, não empreendimento
  "NumeroDocumento": "749122",   // ❌ Número da fatura
  "TipoDocumento": "CONTPG",     // ❌ Tipo do documento
  "DataVencimento": "25/10/2025"
}
```

#### Campos NECESSÁRIOS (faltando):
```json
{
  "CentroCusto": "???",           // ❌ null
  "Projeto": "???",               // ❌ null
  "Empreendimento": "???",        // ❌ não existe
  "cod_empreendimento": "???",    // ❌ não existe
  "IdEmpreendimento": "???"       // ❌ não existe
}
```

### 🎯 Perguntas CRÍTICAS para Mega ERP:

```markdown
1. ❓ Qual campo relaciona uma despesa a um empreendimento?
   - CentroCusto? (99% compartilham o mesmo)
   - Projeto?
   - Outro campo?

2. ❓ Como a Mega ERP controla despesas por empreendimento internamente?
   - Deve haver algum relacionamento no banco de dados
   - Qual campo é usado?

3. ❓ Existe alguma rota que retorna:
   - Despesas COM identificação de empreendimento?
   - Algo como "DadosDespesas" ou "ParcelasPagar" detalhado?

4. ❓ Por que expand não funciona?
   - Documentação diz que aceita expand
   - Na prática, API retorna null para todos campos expandidos

5. ❓ Alternativa: Buscar despesas por NumeroDocumento?
   - Existe algum documento que relaciona despesa → empreendimento?
   - Podemos buscar documentos por empreendimento?
```

### 💡 Possíveis Soluções (a validar com cliente):

#### Solução 1: Rota alternativa de despesas detalhadas
```python
# Similar a DadosParcelas, mas para despesas
# VERIFICAR COM CLIENTE se existe:
despesas = mega_client.get("/api/Carteira/DadosDespesas/Empreendimento/{emp_id}")
# ou
despesas = mega_client.get("/api/FinanceiroMovimentacao/DespesasDetalhadas/...")
```

#### Solução 2: Lançamentos contábeis
```python
# Se não houver rota de despesas, usar lançamentos
lancamentos = mega_client.get(
    "/api/contabilidadelancamentos/saldo/centrocusto/projeto",
    params={
        "centroCusto": emp.centro_custo,
        "projeto": emp.codigo,  # Se projeto for único por empreendimento
        "dataInicio": inicio,
        "dataFim": fim
    }
)
```

#### Solução 3: Buscar por Projeto (se disponível)
```python
# Se campo Projeto for único por empreendimento
# E se expand funcionasse (TESTAR)
despesas = mega_client.get(
    "/api/FinanceiroMovimentacao/FaturaPagar/Saldo/{inicio}/{fim}",
    params={"expand": "projeto"}
)
# Filtrar em código por projeto
despesas_emp = [d for d in despesas if d.get("Projeto", {}).get("Id") == emp.projeto_id]
```

### ⚠️ Impacto Atual:

**Sem solução para filtrar despesas por empreendimento:**

```python
# Dashboard por empreendimento - IMPOSSÍVEL
dashboard_emp_1472 = {
    "cash_in": "✅ Funcionando (via DadosParcelas)",
    "cash_out": "❌ IMPOSSÍVEL - não consegue filtrar despesas",
    "balance": "❌ INCORRETO - sem cash_out correto"
}

# Dashboard consolidado - PARCIALMENTE POSSÍVEL
dashboard_geral = {
    "cash_in": "✅ Soma de todos empreendimentos",
    "cash_out": "⚠️ Todas despesas misturadas",
    "por_empreendimento": "❌ IMPOSSÍVEL"
}
```

**BLOQUEIO TOTAL do recurso principal do sistema!**

---

## 1️⃣ PROBLEMA: FaturaReceber/Saldo (Entradas)

### Rota Testada:
```
GET /api/FinanceiroMovimentacao/FaturaReceber/Saldo/{inicio}/{fim}
    ?expand=centroCusto,projeto,situacao,parcela,dataBaixa,tipoParcela
```

### ❌ Campos Disponíveis:
```json
{
  "Filial": {"Id": 8770},
  "Agente": {"Codigo": 12916},
  "TipoDocumento": "CONTRATO",
  "NumeroDocumento": "9994",
  "NumeroParcela": "013",
  "DataVencimento": "01/10/2025",
  "DataProrrogado": "01/10/2025",
  "ValorParcela": 26000.0,
  "SaldoAtual": 26000.0
}
```

### ❌ Campos FALTANTES (Críticos):
- `DataBaixa` / `DataPagamento` → Quando foi pago
- `TipoParcela` → Tipo (Mensal, Antecipação, etc)
- `CentroCusto` → Para filtrar por empreendimento
- `Situacao` → Status de pagamento

### 🔴 Bloqueadores:

#### Bloqueador 1: NumeroDocumento ≠ cod_contrato
**Teste Realizado:**
1. Buscamos contratos do empreendimento 1472
   - Retornou 6 contratos: `872, 1051, 1052, 1170, 1286, 7144`
2. Tentamos filtrar FaturaReceber por NumeroDocumento="872"
   - Resultado: **0 parcelas**

**Valores encontrados:**
- `NumeroDocumento` em FaturaReceber: `16820000, 193, 21, 224, 283...`
- `cod_contrato` em DadosContrato: `872, 1051, 1052, 1170, 1286...`

**Conclusão:** Não há correspondência → **Impossível filtrar por empreendimento**

#### Bloqueador 2: Expand não funciona
**Teste Realizado:**
```bash
# Teste sem expand
curl ".../FaturaReceber/Saldo/2025-10-01/2025-10-31"
# Retornou: 36 parcelas, 9 campos

# Teste com expand completo
curl ".../FaturaReceber/Saldo/2025-10-01/2025-10-31?expand=centroCusto,projeto,situacao,parcela,dataBaixa,tipoParcela,status,statusParcela"
# Retornou: 36 parcelas, 9 campos (MESMOS!)
```

**Conclusão:** API **ignora completamente** o parâmetro `expand`

#### Bloqueador 3: Sem campos para categorização
Necessidade:
```python
categorias = {
    "ativos": parcelas_regulares_pagas_no_prazo,
    "recuperacoes": parcelas_vencidas_pagas_depois,
    "antecipacoes": parcelas_pagas_antes_vencimento,
    "outras": demais_receitas
}
```

Sem `DataBaixa` e `TipoParcela` → **Impossível categorizar**

### ✅ Evidências:
- `/api_samples/validacao_20251030_103630/teste1_base.json`
- `/api_samples/validacao_20251030_103630/teste3_expand_completo.json`
- `/api_samples/validacao_20251030_103630/teste4_fatura_receber.json` (vazio)

---

## 2️⃣ PROBLEMA: FaturaPagar/Saldo (Saídas)

### Rota ATUAL em Produção:
```python
# mega_client.py:326-331
endpoint = f"/api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/{filial_id}/{data_inicio}/{data_fim}"
params = {"expand": "classeFinanceira,centroCusto,projeto"}
```

### ❌ Campos Disponíveis (dados reais):
```json
{
  "Filial": {"Id": 4},
  "Agente": {"Codigo": 6371},
  "NumeroAP": 31864,
  "TipoDocumento": "CONTPG",
  "NumeroDocumento": "749122",
  "NumeroParcela": "052",
  "DataVencimento": "25/10/2025",
  "DataProrrogado": "25/10/2025",
  "ValorParcela": 50000.0,
  "SaldoAtual": 50000.0
}
```

### ❌ Campos FALTANTES (Críticos):
- `ClasseFinanceira` → Para categorizar OPEX/CAPEX/Financeiras
- `CentroCusto` → Para filtrar por empreendimento
- `DataBaixa` / `DataPagamento` → Quando foi pago
- `Situacao` → Status de pagamento

### 🔴 Análise dos Dados:

#### Arquivo: saldo_pagar.json (809KB)
```json
{
  "total_registros": 1485,
  "centro_custo": "null" (100% dos registros),
  "classe_financeira": "não existe no JSON"
}
```

#### Arquivo: contas_pagar_all.json (2.2MB)
```json
{
  "total_registros": 3672,
  "centro_custo": "null" (100% dos registros),
  "classe_financeira": "não existe no JSON"
}
```

**Conclusão:** Expand **também não funciona** para FaturaPagar!

### ✅ Evidências:
- `/api_samples/saldo_pagar.json` (809KB, 1,485 registros)
- `/api_samples/contas_pagar_all.json` (2.2MB, 3,672 registros)

---

## 3️⃣ BUG CRÍTICO: Categorização de Despesas QUEBRADA

### Código Atual (cash_flow_service.py:273-280):
```python
# Map to category using Classe Financeira
classe_financeira = None
if "ClasseFinanceira" in despesa_dict:
    clf = despesa_dict.get("ClasseFinanceira", {})
    if isinstance(clf, dict):
        classe_financeira = clf.get("Identificador") or clf.get("identificador")

category = mapper.map_to_category(classe_financeira)
```

### Lógica do Mapper (classe_financeira_mapper.py:68-70):
```python
if not classe_identificador:
    logger.debug("No classe financeira provided, using OPEX as default")
    return CashOutCategory.OPEX
```

### 🔴 Problema:
1. Dados reais **NÃO têm** campo `ClasseFinanceira`
2. `classe_financeira` é sempre `None`
3. `map_to_category(None)` retorna **SEMPRE `OPEX`**

### ❌ Impacto:
```python
# TODAS as 3,672 despesas são categorizadas como OPEX!
resultado_incorreto = {
    "OPEX": 100%,      # ❌ ERRADO
    "CAPEX": 0%,       # ❌ Não calculado
    "Financeiras": 0%, # ❌ Não calculado
    "Distribuições": 0% # ❌ Não calculado
}
```

**Dashboard está mostrando dados INCORRETOS!**

### 🔴 Segundo Problema: Timing de Pagamento

Código (cash_flow_service.py:289-294):
```python
# ACTUAL: Parcelas pagas (SaldoAtual = 0) with vencimento in reference month
# Assuming payment happens on due date for paid items
if saldo_atual == 0 and venc_in_month:
    valor_pago = valor_parcela - saldo_atual
    categories[category]["actual"] += valor_pago
```

**Problema:** Assume que se `SaldoAtual = 0`, foi pago no mês do vencimento.

**Realidade:** Sem `DataBaixa`, não sabemos QUANDO foi realmente pago!

Exemplo:
```python
# Parcela vence em janeiro, mas foi paga em março
parcela = {
    "DataVencimento": "2025-01-15",
    "DataBaixa": "2025-03-10",  # ❌ Campo não existe na API!
    "SaldoAtual": 0.0
}

# Código atual:
# ❌ Contabiliza em JANEIRO (vencimento)
# ✅ Deveria contabilizar em MARÇO (pagamento)
```

---

## 📊 Comparação: Campos Necessários vs Disponíveis

| Campo | DadosParcelas | FaturaReceber/Saldo | FaturaPagar/Saldo |
|-------|---------------|---------------------|-------------------|
| **DataVencimento** | ✅ | ✅ | ✅ |
| **ValorParcela** | ✅ | ✅ | ✅ |
| **SaldoAtual** | ✅ | ✅ | ✅ |
| **DataBaixa** | ✅ | ❌ | ❌ |
| **TipoParcela** | ✅ | ❌ | ❌ |
| **Situacao** | ✅ | ❌ | ❌ |
| **CentroCusto** | ✅ | ❌ | ❌ |
| **ClasseFinanceira** | N/A | N/A | ❌ |
| **Expand funciona?** | ✅ | ❌ | ❌ |
| **Filtra por empreendimento?** | ✅ Via contratos | ❌ | ❌ Via CC (180/181 = CC 21) |

---

## 🎯 Impacto nos Dashboards

### Dashboard Atual (PRODUÇÃO):
```python
# Cash Out (Saídas) - INCORRETO
cash_out = {
    "OPEX": "TODAS as despesas",  # ❌ ERRADO
    "CAPEX": 0,                   # ❌ ERRADO
    "Financeiras": 0,             # ❌ ERRADO
    "Distribuições": 0            # ❌ ERRADO
}

# Timing - APROXIMADO
actual = {
    "mes_correto": "Aproximado",  # ⚠️ Assume pagamento no vencimento
    "mes_errado": "Possível"      # ❌ Sem DataBaixa
}
```

### Dashboard Proposto (com rotas otimizadas):
```python
# Cash In (Entradas) - IMPOSSÍVEL
cash_in = {
    "filtrar_por_empreendimento": False,  # ❌ NumeroDocumento ≠ cod_contrato
    "categorizar": False,                 # ❌ Falta TipoParcela e DataBaixa
    "timing_correto": False               # ❌ Falta DataBaixa
}

# Cash Out (Saídas) - IMPOSSÍVEL
cash_out = {
    "categorizar": False,                 # ❌ Falta ClasseFinanceira
    "filtrar_por_empreendimento": False,  # ❌ CentroCusto não é único
    "timing_correto": False               # ❌ Falta DataBaixa
}
```

---

## 🔍 Problemas com Centro de Custo

### Análise de empreendimentos.json:
```python
total_empreendimentos = 181
centro_custo_21 = 180  # 99.4% dos empreendimentos!
centro_custo_unicos = 2  # Apenas 2 valores distintos
```

### Conclusão:
❌ **Centro de Custo NÃO pode ser usado para filtrar por empreendimento**

Mesmo que FaturaPagar retornasse CentroCusto, seria inútil para filtrar.

---

## ✅ SOLUÇÃO: Rotas Corretas

### Para ENTRADAS (Cash In):

#### Rota Atual (✅ MANTER):
```python
# 1. Buscar contratos do empreendimento
GET /api/Carteira/DadosContrato?codEmpreendimento={emp_id}

# 2. Para cada contrato, buscar parcelas
GET /api/Carteira/DadosParcelas/IdContrato={contrato_id}
```

**Campos disponíveis:**
```json
{
  "cod_contrato": 872,
  "data_vencimento": "01/10/2025",
  "data_baixa": "15/10/2025",           // ✅ Timing correto
  "tipo_parcela": "Mensal",             // ✅ Categorização
  "situacao": "Pago",                   // ✅ Status
  "vlr_original": 26000.0,
  "vlr_pago": 26000.0,
  "status_parcela": "Ativo"
}
```

**Vantagens:**
- ✅ Filtra por empreendimento (via contratos)
- ✅ Tem TODOS os campos necessários
- ✅ Permite categorização correta
- ✅ Timing de pagamento correto

**Desvantagens:**
- ⚠️ Performance: ~50 requests por empreendimento

### Para SAÍDAS (Cash Out):

#### 🔴 PROBLEMA: Não encontramos rota adequada!

**Rotas testadas:**
- `/api/FinanceiroMovimentacao/FaturaPagar/Saldo` → ❌ Sem ClasseFinanceira, sem CentroCusto
- `/api/FinanceiroMovimentacao/FaturaPagar/SaldoEmAberto` → ❌ Mesma estrutura

**Rotas no Swagger:**
```json
{
  "rotas_disponiveis": [
    "/api/FinanceiroMovimentacao/FaturaPagar/Saldo/{inicio}/{fim}",
    "/api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/{filial}/{inicio}/{fim}",
    "/api/FinanceiroMovimentacao/FaturaPagar/Saldo/Agente/{agente}/{inicio}/{fim}",
    "/api/FinanceiroMovimentacao/FaturaPagar/SaldoEmAberto/{inicio}/{fim}"
  ],
  "problema": "NENHUMA retorna ClasseFinanceira ou CentroCusto mesmo com expand"
}
```

#### ❓ AÇÃO NECESSÁRIA:
**Contatar cliente Mega ERP para verificar:**

1. **Existe rota alternativa para despesas detalhadas?**
   - Equivalente a `DadosParcelas` mas para contas a pagar?
   - Algo como `DadosDespesas` ou `ParcelasPagar`?

2. **Por que expand não funciona em FaturaPagar/Saldo?**
   - Documentação diz que aceita expand
   - Na prática, API ignora completamente

3. **Como obter ClasseFinanceira e CentroCusto?**
   - Campos essenciais para categorização
   - Sem eles, dashboard não funciona corretamente

4. **Como obter DataBaixa/DataPagamento?**
   - Necessário para timing correto de pagamentos
   - Atualmente assumindo pagamento no vencimento (incorreto)

---

## 🎯 Recomendações

### 1. **URGENTE: Corrigir código de despesas**

Opção A: Implementar rota correta (se existir)
```python
# Descobrir com cliente qual rota usar
despesas = mega_client.get_despesas_detalhadas(
    empreendimento_id=emp_id,
    data_inicio=inicio,
    data_fim=fim,
    expand="classeFinanceira,centroCusto,dataBaixa"
)
```

Opção B: Usar lançamentos contábeis (temporário)
```python
# Se não houver rota de despesas, usar lançamentos
lancamentos = mega_client.get_lancamentos_by_centro_custo(
    centro_custo=emp.centro_custo,
    data_inicio=inicio,
    data_fim=fim
)
# Filtrar apenas débitos (saídas)
# Categorizar via ClasseFinanceira
```

### 2. **NÃO implementar FaturaReceber/Saldo**
- ❌ NumeroDocumento ≠ cod_contrato
- ❌ Falta campos críticos
- ❌ Expand não funciona
- ✅ Manter DadosParcelas

### 3. **Otimização: Cache em banco de dados**

```python
class ParcelasRepository:
    def sync_daily(self):
        """Sincroniza parcelas 1x por dia."""
        for emp in empreendimentos:
            # ENTRADAS
            contratos = get_contratos(emp.id)
            for contrato in contratos:
                parcelas = get_parcelas(contrato.id)
                salvar_no_banco(parcelas)

            # SAÍDAS (quando rota correta for identificada)
            despesas = get_despesas_detalhadas(emp.id)
            salvar_no_banco(despesas)

    def get_cash_flow_sql(self, emp_id, mes):
        """Agregação rápida via SQL."""
        return db.query("""
            SELECT
                categoria,
                SUM(valor_previsto) as forecast,
                SUM(valor_realizado) as actual
            FROM parcelas
            WHERE empreendimento_id = ? AND mes = ?
            GROUP BY categoria
        """, emp_id, mes)
```

**Vantagens:**
- 🚀 Sync 1x por dia (agendado)
- 🚀 Queries SQL (milissegundos)
- ✅ Dados completos e corretos
- ✅ Histórico disponível
- ✅ Performance excelente

### 4. **🔴 URGENTE: Perguntas Críticas para Mega ERP**

#### Prioridade 1 - BLOQUEADOR:
```markdown
❓ Como identificar a qual empreendimento pertence cada despesa?

Contexto:
- Temos 181 empreendimentos
- 180 compartilham Centro de Custo = 21
- FaturaPagar/Saldo não retorna CentroCusto mesmo com expand
- Sem esse campo, não conseguimos separar despesas por empreendimento

Opções testadas que NÃO funcionaram:
✗ CentroCusto (99% compartilham o mesmo)
✗ Filial (múltiplos empreendimentos por filial)
✗ Expand (ignorado pela API)

Perguntas:
1. Qual campo relaciona despesa → empreendimento?
2. Existe rota que retorna despesas COM identificação de empreendimento?
3. Como a Mega ERP controla isso internamente?
```

#### Prioridade 2 - Campos Necessários:
```markdown
❓ Como obter ClasseFinanceira nas despesas?

Contexto:
- Necessário para categorizar OPEX/CAPEX/Financeiras/Distribuições
- FaturaPagar/Saldo não retorna mesmo com expand="classeFinanceira"
- Código atual categorizando TUDO como OPEX (bug)

Perguntas:
1. Qual rota retorna ClasseFinanceira?
2. Por que expand não funciona em FaturaPagar/Saldo?
3. Existe rota alternativa de despesas detalhadas?
```

#### Prioridade 3 - Timing:
```markdown
❓ Como obter DataBaixa/DataPagamento?

Contexto:
- Necessário para saber QUANDO foi efetivamente pago
- Atualmente assumindo pagamento no vencimento (incorreto)
- FaturaPagar/Saldo só tem DataVencimento

Perguntas:
1. Qual rota retorna data de pagamento efetivo?
2. Existe campo equivalente a DataBaixa para despesas?
```

#### Prioridade 4 - Rotas Alternativas:
```markdown
❓ Existe rota equivalente a DadosParcelas mas para despesas?

Contexto:
- DadosParcelas funciona perfeitamente para entradas
- Retorna TODOS os campos necessários
- Precisamos equivalente para saídas

Rotas que procuramos:
- /api/Carteira/DadosDespesas?
- /api/FinanceiroMovimentacao/DespesasDetalhadas?
- /api/FinanceiroMovimentacao/ParcelasPagar?

Campos necessários:
- CentroCusto ou cod_empreendimento (filtrar por empreendimento)
- ClasseFinanceira (categorização)
- DataBaixa/DataPagamento (timing)
- Situacao (pago/aberto)
```

---

## 📁 Arquivos de Evidência

### Validação FaturaReceber:
- `/docs/resultado-validacao-rotas.md` - Relatório completo
- `/api_samples/validacao_20251030_103630/` - Todos os testes
  - `teste1_base.json` - 36 parcelas, 9 campos
  - `teste3_expand_completo.json` - Mesmos 9 campos (expand ignorado)
  - `teste4_contratos.json` - 6 contratos do emp 1472
  - `teste4_dados_parcelas.json` - 662 parcelas corretas
  - `teste4_fatura_receber.json` - Vazio (filtro não funciona)

### Dados FaturaPagar:
- `/api_samples/saldo_pagar.json` - 809KB, 1,485 despesas
- `/api_samples/contas_pagar_all.json` - 2.2MB, 3,672 despesas

### Análise Empreendimentos:
- `/api_samples/empreendimentos.json` - 181 empreendimentos
  - 180 com CentroCusto = 21 (99.4%)

### Código Afetado:
- `/src/starke/domain/services/cash_flow_service.py:273-294` - Bug categorização
- `/src/starke/domain/services/classe_financeira_mapper.py:68-70` - Fallback OPEX
- `/src/starke/infrastructure/external_apis/mega_client.py:326-331` - Rota atual

---

## ✅ Conclusão

### Status Atual:
```python
sistema_atual = {
    "entradas": "✅ Funcionando (DadosParcelas)",
    "saidas": "🔴 QUEBRADO (categorizando tudo como OPEX)",
    "performance": "⚠️ Lenta (múltiplos requests)",
    "precisao_dados": "❌ INCORRETA (categorização errada)"
}
```

### Próximos Passos:
1. 🔴 **URGENTE:** Contatar Mega ERP sobre rota correta para despesas
2. 🔴 **URGENTE:** Corrigir bug de categorização
3. ✅ Manter DadosParcelas para entradas
4. ✅ Implementar cache em banco de dados
5. ❌ NÃO migrar para FaturaReceber/Saldo

---

**Documento criado em:** 30 de Outubro de 2025, 10:50 AM
**Status:** 🔴 Aguardando ação do cliente Mega ERP

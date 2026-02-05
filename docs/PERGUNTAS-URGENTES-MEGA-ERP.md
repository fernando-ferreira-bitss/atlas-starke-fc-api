# ❓ PERGUNTAS URGENTES PARA MEGA ERP

**Data:** 30 de Outubro de 2025
**Assunto:** Bloqueadores críticos na integração de APIs
**Prioridade:** 🔴 URGENTE

---

## 🔴 PROBLEMA PRINCIPAL - BLOQUEADOR CRÍTICO

### **Como identificar a qual empreendimento pertence cada despesa?**

**Situação:**
- Temos 181 empreendimentos cadastrados
- Precisamos calcular Cash Out (despesas) por empreendimento
- **NÃO conseguimos identificar qual despesa pertence a qual empreendimento**

**Tentativas que NÃO funcionaram:**

#### ❌ Centro de Custo
- 180 de 181 empreendimentos compartilham o mesmo Centro de Custo (21)
- Apenas 2 valores únicos no total
- **Inútil para filtrar por empreendimento**

#### ❌ FaturaPagar/Saldo com expand
```
Rota testada:
GET /api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/{filial}/2025-10-01/2025-10-31
    ?expand=classeFinanceira,centroCusto,projeto

Resultado:
- CentroCusto: null (100% dos 3,672 registros)
- ClasseFinanceira: não existe no JSON
- Projeto: null
```

**API ignora completamente o parâmetro expand**

#### ❌ Filtrar por Filial
- Filial 4 contém os 181 empreendimentos
- Despesas retornam misturadas
- Sem campo para separar por empreendimento

---

## 🎯 PERGUNTAS CRÍTICAS

### Prioridade 1 - BLOQUEADOR (Sistema não funciona sem isso):

#### 1. Qual campo relaciona despesa → empreendimento?

**Campos disponíveis atualmente:**
```json
{
  "Filial": {"Id": 4},           // Múltiplos empreendimentos
  "Agente": {"Codigo": 6371},    // Fornecedor
  "NumeroDocumento": "749122",   // Número da fatura
  "TipoDocumento": "CONTPG",
  "DataVencimento": "25/10/2025",
  "ValorParcela": 50000.0
}
```

**Campos que precisamos (faltando):**
- `CentroCusto` → null
- `Projeto` → null
- `Empreendimento` / `cod_empreendimento` → não existe

**Pergunta:** Como a Mega ERP controla internamente qual despesa pertence a qual empreendimento?

---

#### 2. Existe rota de despesas detalhadas por empreendimento?

**Contexto:**
- Para ENTRADAS (Cash In) usamos:
  ```
  GET /api/Carteira/DadosContrato?codEmpreendimento={emp_id}
  GET /api/Carteira/DadosParcelas/IdContrato={contrato_id}
  ```
  ✅ Funciona perfeitamente - retorna todos campos necessários

- Para SAÍDAS (Cash Out) tentamos:
  ```
  GET /api/FinanceiroMovimentacao/FaturaPagar/Saldo/...
  ```
  ❌ Não funciona - faltam campos críticos

**Pergunta:** Existe rota equivalente a `DadosParcelas` mas para despesas?

Exemplos de rotas que procuramos:
- `/api/Carteira/DadosDespesas?codEmpreendimento={emp_id}`
- `/api/FinanceiroMovimentacao/DespesasDetalhadas/Empreendimento/{emp_id}`
- `/api/FinanceiroMovimentacao/ParcelasPagar/...`

---

### Prioridade 2 - Campos Necessários:

#### 3. Como obter ClasseFinanceira nas despesas?

**Necessidade:**
- Categorizar despesas em: OPEX, CAPEX, Financeiras, Distribuições
- Atualmente todas despesas sendo categorizadas como OPEX (bug)

**Problema:**
- FaturaPagar/Saldo com `expand=classeFinanceira` → não retorna o campo
- Sem ClasseFinanceira, dashboard mostra dados incorretos

**Pergunta:** Qual rota retorna despesas com ClasseFinanceira?

---

#### 4. Como obter data de pagamento efetivo?

**Necessidade:**
- Saber QUANDO a despesa foi efetivamente paga (não apenas vencimento)
- Calcular realizado no mês correto

**Problema:**
- FaturaPagar/Saldo só tem `DataVencimento`
- Sem data de pagamento, assumimos pagamento no vencimento (incorreto)

**Pergunta:** Existe campo `DataBaixa`, `DataPagamento` ou equivalente para despesas?

---

### Prioridade 3 - Entendimento da API:

#### 5. Por que expand não funciona em FaturaPagar/Saldo E FaturaReceber/Saldo?

**Evidências - TESTES COMPLETOS REALIZADOS:**

**Rotas testadas:**
- ✗ `/api/FinanceiroMovimentacao/FaturaReceber/Saldo/{inicio}/{fim}` (genérica)
- ✗ `/api/FinanceiroMovimentacao/FaturaReceber/Saldo/Filial/{filial}/{inicio}/{fim}` (por filial)
- ✗ `/api/FinanceiroMovimentacao/FaturaPagar/Saldo/{inicio}/{fim}` (genérica)
- ✗ `/api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/{filial}/{inicio}/{fim}` (por filial)

**Valores de expand testados:**
- ✗ `expand=empreendimento`
- ✗ `expand=centroCusto`
- ✗ `expand=projeto`
- ✗ `expand=classeFinanceira`
- ✗ `expand=dataBaixa`
- ✗ `expand=tipoParcela`
- ✗ `expand=situacao`
- ✗ `expand=empreendimento,centroCusto,projeto` (múltiplos)
- ✗ `expand=empreendimento,classeFinanceira,centroCusto` (múltiplos)

**Resultado:** TODOS retornam mesmos 9-10 campos básicos!

**Verificação específica:**
```bash
# Campo Empreendimento existe?
has("Empreendimento") → false

# Campo CentroCusto existe?
has("CentroCusto") → false

# Campo ClasseFinanceira existe?
has("ClasseFinanceira") → false
```

**Pergunta:** Expand está implementado nestas rotas ou é apenas placeholder na documentação?

---

## 💡 POSSÍVEIS SOLUÇÕES

Se não houver rota específica de despesas, poderíamos usar:

### Solução A: Lançamentos Contábeis
```
GET /api/contabilidadelancamentos/saldo/centrocusto/projeto
```

**Questões:**
1. Esta rota retorna lançamentos de despesas?
2. Podemos filtrar por empreendimento usando Centro de Custo + Projeto?
3. Retorna ClasseFinanceira e data de pagamento?

### Solução B: Campo Projeto
```
GET /api/FinanceiroMovimentacao/FaturaPagar/Saldo/...?expand=projeto
```

**Questões:**
1. Campo Projeto é único por empreendimento?
2. Se expand funcionasse, retornaria dados de Projeto?
3. Poderíamos usar Projeto para filtrar?

### Solução C: Buscar por NumeroDocumento
**Questões:**
1. Existe documento/registro que relaciona despesa → empreendimento?
2. Podemos buscar esses documentos por empreendimento?
3. Depois buscar despesas por NumeroDocumento?

---

## 📊 IMPACTO ATUAL

**Sem solução para filtrar despesas:**

### Dashboard por Empreendimento:
```
✅ Cash In (Entradas): Funcionando via DadosParcelas
❌ Cash Out (Saídas): IMPOSSÍVEL - não consegue filtrar
❌ Balance (Saldo): INCORRETO - sem cash out correto
```

### Dashboard Consolidado:
```
✅ Cash In: Soma de todos empreendimentos
⚠️ Cash Out: Todas despesas misturadas (sem categorização)
❌ Análise por empreendimento: IMPOSSÍVEL
```

**Resultado:** Sistema principal de dashboard **bloqueado**.

---

## 📁 EVIDÊNCIAS

### Dados analisados:
- `saldo_pagar.json`: 1,485 despesas - CentroCusto null em 100%
- `contas_pagar_all.json`: 3,672 despesas - CentroCusto null em 100%
- `empreendimentos.json`: 181 empreendimentos - 180 com mesmo Centro de Custo

### Testes realizados:
1. FaturaPagar/Saldo sem expand → 10 campos básicos
2. FaturaPagar/Saldo com expand completo → mesmos 10 campos
3. Análise de Centro de Custo → 99.4% compartilham valor 21
4. Tentativa de correlação → nenhum campo relaciona despesa a empreendimento

**Documentação completa:** `/docs/PROBLEMAS-CRITICOS-APIS.md`

---

## ✅ O QUE FUNCIONA

Para referência, a solução de **Entradas (Cash In)** funciona perfeitamente:

```python
# 1. Buscar contratos do empreendimento
contratos = GET /api/Carteira/DadosContrato?codEmpreendimento=1472

# 2. Para cada contrato, buscar parcelas
for contrato in contratos:
    parcelas = GET /api/Carteira/DadosParcelas/IdContrato={contrato.id}

# Campos retornados (50+ campos incluindo):
- data_vencimento ✅
- data_baixa ✅ (quando foi pago)
- tipo_parcela ✅ (para categorizar)
- situacao ✅ (pago/aberto)
- vlr_original ✅
- vlr_pago ✅
```

**Precisamos de solução equivalente para despesas!**

---

## 🎯 RESUMO DAS PERGUNTAS

**BLOQUEADORES (urgente):**
1. ❓ Como identificar qual despesa pertence a qual empreendimento?
2. ❓ Existe rota de despesas detalhadas por empreendimento?

**Campos necessários:**
3. ❓ Como obter ClasseFinanceira nas despesas?
4. ❓ Como obter data de pagamento efetivo (DataBaixa)?

**Entendimento:**
5. ❓ Por que expand não funciona em FaturaPagar/Saldo?

---

**Aguardamos retorno urgente para desbloquear o desenvolvimento.**

Obrigado!

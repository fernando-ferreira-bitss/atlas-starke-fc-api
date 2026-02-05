# 🔴 TESTE: Rotas /Filial/ com Expand

**Data:** 30 de Outubro de 2025
**Objetivo:** Verificar se rotas `/Filial/` aceitam expand e se conseguimos trazer empreendimento

---

## 🎯 Pergunta Original

**"Nas rotas de FaturaReceber e FaturaPagar por filial, conseguimos add o expand? Será que não conseguimos trazer o empreendimento nesse expand?"**

---

## ✅ Testes Realizados

### Rotas Testadas:

#### 1. FaturaReceber/Saldo/Filial/{filial}
```bash
# Sem expand
GET /api/FinanceiroMovimentacao/FaturaReceber/Saldo/Filial/4/2025-10-01/2025-10-31

# Com expand=empreendimento
GET /api/FinanceiroMovimentacao/FaturaReceber/Saldo/Filial/4/2025-10-01/2025-10-31?expand=empreendimento

# Com expand=centroCusto
GET /api/FinanceiroMovimentacao/FaturaReceber/Saldo/Filial/4/2025-10-01/2025-10-31?expand=centroCusto

# Com expand múltiplo
GET /api/FinanceiroMovimentacao/FaturaReceber/Saldo/Filial/4/2025-10-01/2025-10-31?expand=empreendimento,centroCusto,projeto
```

#### 2. FaturaPagar/Saldo/Filial/{filial}
```bash
# Sem expand
GET /api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/4/2025-10-01/2025-10-31

# Com expand múltiplo
GET /api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/4/2025-10-01/2025-10-31?expand=empreendimento,classeFinanceira,centroCusto
```

---

## 📊 Resultados

### FaturaReceber/Saldo/Filial/4

#### ❌ SEM Expand:
```json
{
  "Filial": {"Id": 4, "Nome": null},
  "Agente": {"Codigo": 7969, "Nome": null},
  "TipoDocumento": "CONTRATO",
  "NumeroDocumento": "224",
  "NumeroParcela": "004",
  "DataVencimento": "01/10/2025",
  "DataProrrogado": "01/10/2025",
  "ValorParcela": 163800.0,
  "SaldoAtual": 163800.0
}
```

**Registros retornados:** 23 parcelas

#### ❌ COM Expand (empreendimento, centroCusto, projeto):
```json
{
  "Filial": {"Id": 4, "Nome": null},
  "Agente": {"Codigo": 7969, "Nome": null},
  "TipoDocumento": "CONTRATO",
  "NumeroDocumento": "224",
  "NumeroParcela": "004",
  "DataVencimento": "01/10/2025",
  "DataProrrogado": "01/10/2025",
  "ValorParcela": 163800.0,
  "SaldoAtual": 163800.0
}
```

**Registros retornados:** 23 parcelas

**Análise:**
```bash
diff sem_expand.json com_expand.json
# → SEM DIFERENÇAS!
```

---

### FaturaPagar/Saldo/Filial/4

#### ❌ SEM Expand:
```json
{
  "Filial": {"Id": 4, "Nome": null},
  "Agente": {"Codigo": 13199, "Nome": null},
  "NumeroAP": 84733,
  "TipoDocumento": "NF",
  "NumeroDocumento": "64",
  "NumeroParcela": "002",
  "DataVencimento": "20/10/2025",
  "DataProrrogado": "20/10/2025",
  "ValorParcela": 1667.0,
  "SaldoAtual": 1667.0
}
```

**Registros retornados:** 1,821 despesas

#### ❌ COM Expand (empreendimento, classeFinanceira, centroCusto):
```json
{
  "Filial": {"Id": 4, "Nome": null},
  "Agente": {"Codigo": 13199, "Nome": null},
  "NumeroAP": 84733,
  "TipoDocumento": "NF",
  "NumeroDocumento": "64",
  "NumeroParcela": "002",
  "DataVencimento": "20/10/2025",
  "DataProrrogado": "20/10/2025",
  "ValorParcela": 1667.0,
  "SaldoAtual": 1667.0
}
```

**Registros retornados:** 1,821 despesas

**Análise:**
```bash
diff sem_expand.json com_expand.json
# → SEM DIFERENÇAS!
```

---

## 🔍 Verificação Específica de Campos

### Campos testados explicitamente:

#### ❌ Campo "Empreendimento":
```bash
cat receber_filial_expand_empreendimento.json | jq '.[0] | has("Empreendimento")'
# Resultado: false
```

#### ❌ Campo "CentroCusto":
```bash
cat receber_filial_expand_centrocusto.json | jq '.[0] | has("CentroCusto")'
# Resultado: false
```

#### ❌ Campo "ClasseFinanceira":
```bash
cat pagar_filial_expand_multi.json | jq '.[0] | has("ClasseFinanceira")'
# Resultado: false
```

---

## 📋 Comparação de Campos

### Campos disponíveis (idênticos com ou sem expand):

#### FaturaReceber:
```json
[
  "Agente",
  "DataProrrogado",
  "DataVencimento",
  "Filial",
  "NumeroDocumento",
  "NumeroParcela",
  "SaldoAtual",
  "TipoDocumento",
  "ValorParcela"
]
```

#### FaturaPagar:
```json
[
  "Agente",
  "DataProrrogado",
  "DataVencimento",
  "Filial",
  "NumeroAP",
  "NumeroDocumento",
  "NumeroParcela",
  "SaldoAtual",
  "TipoDocumento",
  "ValorParcela"
]
```

### Campos FALTANDO (que tentamos expandir):
- ❌ `Empreendimento` → não adicionado
- ❌ `CentroCusto` → não adicionado
- ❌ `Projeto` → não adicionado
- ❌ `ClasseFinanceira` → não adicionado
- ❌ `DataBaixa` → não adicionado
- ❌ `TipoParcela` → não adicionado
- ❌ `Situacao` → não adicionado

---

## ❌ CONCLUSÃO

### Resposta à pergunta:

**"Conseguimos add expand na rota /Filial/?"**
→ ❌ **NÃO**. API ignora completamente o parâmetro expand.

**"Conseguimos trazer empreendimento nesse expand?"**
→ ❌ **NÃO**. Campo Empreendimento não é adicionado mesmo com `expand=empreendimento`.

---

## 🔴 Problemas Confirmados

### 1. Expand NÃO funciona
- Testado em **AMBAS** rotas (FaturaReceber e FaturaPagar)
- Testado com **rota genérica** e **rota /Filial/**
- Testado com **valores únicos** e **múltiplos**
- **TODOS** retornam mesmos campos

### 2. Impossível identificar empreendimento
- Campo `Empreendimento` não existe no response
- Campo `CentroCusto` não existe no response
- Campo `Projeto` não existe no response
- **SEM forma de filtrar/identificar empreendimento**

### 3. Campos críticos ausentes
- `ClasseFinanceira` → categorização OPEX/CAPEX
- `DataBaixa` → timing de pagamento
- `TipoParcela` → categorização de receitas
- `Situacao` → status de pagamento

---

## 📊 Comparação: Rotas Genéricas vs /Filial/

| Aspecto | Rota Genérica | Rota /Filial/{id} | Diferença? |
|---------|---------------|-------------------|------------|
| **Campos retornados** | 9-10 campos | 9-10 campos | ❌ Não |
| **Expand funciona?** | ❌ Não | ❌ Não | ❌ Não |
| **Tem Empreendimento?** | ❌ Não | ❌ Não | ❌ Não |
| **Tem CentroCusto?** | ❌ Não | ❌ Não | ❌ Não |
| **Tem ClasseFinanceira?** | ❌ Não | ❌ Não | ❌ Não |

**Conclusão:** ❌ **Rota /Filial/ NÃO oferece vantagem alguma!**

---

## 🎯 Diferença entre Rotas

### Única diferença identificada:

#### Rota Genérica:
```bash
GET /api/FinanceiroMovimentacao/FaturaReceber/Saldo/2025-10-01/2025-10-31
# Retorna: Parcelas de TODAS as filiais
```

#### Rota /Filial/:
```bash
GET /api/FinanceiroMovimentacao/FaturaReceber/Saldo/Filial/4/2025-10-01/2025-10-31
# Retorna: Parcelas apenas da FILIAL 4
```

**Diferença:** Apenas **filtragem** por filial, **MAS:**
- ✅ Reduz volume de dados
- ❌ Não adiciona campos
- ❌ Expand não funciona
- ❌ Não resolve problema de empreendimento (181 empreendimentos na Filial 4)

---

## 📁 Evidências

### Arquivos gerados:
```
/api_samples/teste_filial/
├── receber_filial_sem_expand.json (23 registros)
├── receber_filial_expand_empreendimento.json (23 registros - IDÊNTICO)
├── receber_filial_expand_centrocusto.json (23 registros - IDÊNTICO)
├── receber_filial_expand_multi.json (23 registros - IDÊNTICO)
├── pagar_filial_sem_expand.json (1,821 registros)
└── pagar_filial_expand_multi.json (1,821 registros - IDÊNTICO)
```

### Script de teste:
```bash
/scripts/teste_filial.sh
# Executa todos os 6 testes automaticamente
```

---

## ❓ Perguntas para Mega ERP (ATUALIZADAS)

### 🔴 Prioridade CRÍTICA:

**1. Por que expand não funciona em NENHUMA variação das rotas?**

Testamos:
- ✗ Rota genérica: `/FaturaReceber/Saldo/{inicio}/{fim}`
- ✗ Rota por filial: `/FaturaReceber/Saldo/Filial/{filial}/{inicio}/{fim}`
- ✗ Valores únicos: `?expand=empreendimento`
- ✗ Valores múltiplos: `?expand=empreendimento,centroCusto,projeto`
- ✗ Diferentes campos: empreendimento, centroCusto, projeto, classeFinanceira, dataBaixa, etc.

**TODOS retornam resposta idêntica!**

Pergunta: Expand está implementado ou é apenas placeholder na documentação?

---

**2. Como identificar empreendimento de cada despesa/receita?**

Tentativas que FALHARAM:
- ✗ Campo Empreendimento via expand
- ✗ Campo CentroCusto via expand (99% compartilham mesmo valor)
- ✗ Campo Projeto via expand
- ✗ Filtrar por Filial (181 empreendimentos na mesma filial)

**SEM esse campo, sistema NÃO pode funcionar!**

Pergunta: Qual campo relaciona despesa/receita → empreendimento?

---

**3. Existe rota alternativa com campos completos?**

O que funciona para RECEITAS:
```
✅ DadosParcelas → 41 campos incluindo tipo_parcela, data_baixa, situacao
✅ Filtrado por contrato → permite separar por empreendimento
✅ Expand funciona → campos bem documentados
```

Pergunta: Existe equivalente para DESPESAS?
- `/api/Carteira/DadosDespesas`?
- `/api/FinanceiroMovimentacao/DespesasDetalhadas`?

---

## ✅ Decisão Final

**Rotas FaturaReceber/Saldo e FaturaPagar/Saldo (com ou sem /Filial/):**

❌ **NÃO PODEM SER USADAS** porque:
1. Expand **não funciona**
2. **Impossível** identificar empreendimento
3. **Faltam** campos críticos (ClasseFinanceira, DataBaixa, TipoParcela)
4. Rota /Filial/ **não oferece vantagem** (mesmos problemas)

**Recomendação:**
- ✅ Manter DadosParcelas para receitas (funciona)
- ❌ Buscar rota alternativa para despesas com cliente Mega ERP
- ✅ Implementar cache em banco de dados para performance

---

**Testes realizados em:** 30 de Outubro de 2025, 11:15 AM
**Status:** ✅ Validação completa - Expand não funciona em nenhuma variação

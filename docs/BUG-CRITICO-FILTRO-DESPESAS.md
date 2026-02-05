# 🔴 BUG CRÍTICO: Filtro de Despesas Sempre Retorna Zero

**Data:** 30 de Outubro de 2025
**Severidade:** 🔴 CRÍTICA - Sistema não funciona
**Status:** ❌ Bug ativo em produção

---

## 📋 Resumo

O código atual tenta filtrar despesas por Centro de Custo, mas o campo **não existe** no response da API. Resultado: **ZERO despesas** são processadas, dashboard fica vazio.

---

## 🔍 Análise do Bug

### Código Atual (ingestion_service.py:278-307)

```python
# Linha 278-279: Comentário indica problema conhecido
# NOTE: We use empreendimento_id as filial_id here, but the API may return
# despesas for multiple centro de custo, so we need to filter below

# Linha 280-284: Busca despesas
all_despesas = self.api_client.get_despesas_by_filial(
    filial_id=empreendimento_id,  # ❌ PROBLEMA 1: empreendimento ≠ filial
    data_inicio=first_day.isoformat(),
    data_fim=last_day.isoformat(),
)

# Linha 286-294: Tenta filtrar por CentroCusto
despesas = []
for despesa in all_despesas:
    # Check if despesa has centro de custo info
    centro_custo = despesa.get("CentroCusto") or despesa.get("centroCusto")  # ❌ PROBLEMA 2: campo não existe
    if centro_custo and isinstance(centro_custo, dict):
        cc_reduzido = centro_custo.get("Reduzido") or centro_custo.get("reduzido")
        if cc_reduzido and int(cc_reduzido) == centro_custo_id:
            despesas.append(despesa)  # ❌ NUNCA executa!
```

---

## 🔴 Problema 1: empreendimento_id ≠ filial_id

### Situação Real:
```python
# Temos 181 empreendimentos
empreendimentos = get_empreendimentos()  # 181 registros

# TODOS pertencem à mesma filial
for emp in empreendimentos:
    print(emp.cod_filial)  # 4 (sempre 4!)
```

### O Que o Código Faz:
```python
# Passa empreendimento_id como filial_id
get_despesas_by_filial(filial_id=1472)  # ❌ 1472 é empreendimento, não filial!

# API interpreta como:
GET /api/FaturaPagar/Saldo/Filial/1472/2025-10-01/2025-10-31
                                   ^^^^
                                   API provavelmente ignora ou retorna erro
```

### Evidência no Código (mega_client.py:313):
```python
def get_despesas_by_filial(
    self, filial_id: int, data_inicio: str, data_fim: str
) -> list[dict[str, Any]]:
    """
    Get all despesas (contas a pagar) for a specific filial and date range.

    Args:
        filial_id: ID of the filial (empreendimento)  # ❌ COMENTÁRIO INCORRETO!
```

**Problema:** Comentário diz "filial (empreendimento)" mas **filial ≠ empreendimento**!

---

## 🔴 Problema 2: Campo CentroCusto Não Existe

### Tentativa de Expand (mega_client.py:331):
```python
params = {"expand": "classeFinanceira,centroCusto,projeto"}
```

### Resultado da API:
```json
{
  "Filial": {"Id": 4},
  "Agente": {"Codigo": 13199},
  "NumeroAP": 84733,
  "TipoDocumento": "NF",
  "NumeroDocumento": "64",
  "ValorParcela": 1667.0
  // ❌ CentroCusto: NÃO EXISTE
  // ❌ ClasseFinanceira: NÃO EXISTE
  // ❌ Projeto: NÃO EXISTE
}
```

### Tentativa de Filtro:
```python
centro_custo = despesa.get("CentroCusto")  # None
if centro_custo and isinstance(centro_custo, dict):  # False
    despesas.append(despesa)  # ❌ NUNCA executa
```

---

## 📊 Evidências Quantitativas

### Teste Realizado:
```bash
# Rota testada
GET /api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/4/2025-10-01/2025-10-31?expand=classeFinanceira,centroCusto,projeto

# Resultado
total_despesas: 1821
despesas_com_centro_custo: 0
percentual: 0%
```

### Verificação:
```bash
cat pagar_filial_expand_multi.json | jq '.[0] | has("CentroCusto")'
# Resultado: false

cat pagar_filial_expand_multi.json | jq '[.[] | select(has("CentroCusto"))] | length'
# Resultado: 0

cat pagar_filial_expand_multi.json | jq 'length'
# Resultado: 1821
```

**Conclusão:** 0 de 1,821 despesas (0%) têm campo CentroCusto

---

## ⚠️ Impacto

### No Dashboard:
```python
# Código busca despesas
all_despesas = get_despesas()  # 1,821 despesas

# Filtro descarta TODAS
despesas_filtradas = filter_by_centro_custo(all_despesas)  # []

# Dashboard recebe ZERO despesas
cash_out = calculate_cash_out(despesas_filtradas)  # Vazio!

# Resultado no Dashboard:
{
    "OPEX": 0,
    "CAPEX": 0,
    "Financeiras": 0,
    "Distribuições": 0
}
```

### Logs Esperados:
```python
logger.info(
    "Filtered despesas by centro de custo",
    total_fetched=1821,
    filtered_count=0,  # ❌ ZERO despesas passam!
    centro_custo_id=21,
)
```

---

## 🎯 Por Que Esse Bug Existe?

### Hipótese de Como Foi Criado:

**1. Versão inicial (funcionava?):**
```python
# Talvez expand funcionasse antes?
despesas = get_despesas_by_filial(filial_id=4)  # Filial correta
# API retornava CentroCusto?
# Filtro funcionava?
```

**2. Mudança na API:**
```python
# Mega ERP atualiza API
# Expand para de funcionar
# CentroCusto não vem mais
# Filtro quebra silenciosamente
```

**3. Adaptação incorreta:**
```python
# Alguém tenta adaptar passando empreendimento_id
filial_id=empreendimento_id  # ❌ Incorreto

# Adiciona comentário reconhecendo problema
# "NOTE: We use empreendimento_id as filial_id here"
# Mas não resolve o problema real
```

---

## 🔧 Por Que Não Foi Detectado Antes?

### Possíveis Razões:

**1. Falha Silenciosa:**
```python
# Código não levanta exceção
despesas = []  # Lista vazia é "válida"
cash_out = calculate_cash_out([])  # Retorna zeros (sem erro)
```

**2. Logs Podem Passar Despercebidos:**
```python
logger.info(
    "Filtered despesas by centro de custo",
    filtered_count=0  # ⚠️ Pode parecer "sem despesas no período"
)
```

**3. Testing Incompleto:**
```python
# Teste pode verificar apenas se rota responde
assert response.status_code == 200  # ✅ Passa
# Mas não verifica se dados estão corretos
assert len(despesas) > 0  # ❌ Não existe
```

**4. Ambiente de Dev vs Produção:**
```python
# Talvez em dev havia despesas com CentroCusto mock?
# Ou expand funcionava em versão antiga da API?
```

---

## ✅ Soluções Possíveis

### Solução 1: Usar Filial Correta + Filtrar em Código (NÃO RESOLVE)
```python
# Usar filial correta
all_despesas = get_despesas_by_filial(
    filial_id=4,  # ✅ Filial correta, não empreendimento
    data_inicio=inicio,
    data_fim=fim
)

# MAS: ainda não tem CentroCusto para filtrar!
# Resultado: recebe 1,821 despesas sem forma de filtrar
```

**❌ Não resolve:** Sem CentroCusto, não consegue separar por empreendimento

---

### Solução 2: Rota Alternativa de Despesas (VALIDAR COM MEGA ERP)
```python
# Buscar rota que retorna despesas com CentroCusto
# Equivalente a DadosParcelas mas para despesas
despesas = mega_client.get(
    "/api/Carteira/DadosDespesas",  # Existe?
    params={"codEmpreendimento": emp_id}
)
```

**✅ Resolve SE** rota existir com campos necessários

---

### Solução 3: Lançamentos Contábeis (ALTERNATIVA)
```python
# Usar lançamentos contábeis
lancamentos = mega_client.get(
    "/api/contabilidadelancamentos/saldo/centrocusto",
    params={
        "centroCusto": emp.centro_custo,
        "dataInicio": inicio,
        "dataFim": fim
    }
)
# Filtrar apenas débitos (saídas)
```

**⚠️ Validar:**
- Esta rota retorna despesas?
- Tem ClasseFinanceira?
- Centro de Custo é confiável? (99% compartilham)

---

### Solução 4: Relacionamento via NumeroDocumento (COMPLEXA)
```python
# 1. Buscar documentos relacionados ao empreendimento
docs = get_documentos_empreendimento(emp_id)

# 2. Buscar despesas por NumeroDocumento
for doc in docs:
    despesas = get_despesas_by_numero(doc.numero)
```

**⚠️ Validar:**
- Existe rota de documentos por empreendimento?
- NumeroDocumento é confiável?

---

## 🔴 Ação Imediata Necessária

### Para o Cliente Mega ERP:

**Perguntas URGENTES:**

1. **Qual rota usar para despesas detalhadas por empreendimento?**
   - Atual (FaturaPagar/Saldo) não retorna CentroCusto
   - Expand não funciona
   - Impossível filtrar por empreendimento

2. **Como relacionar despesa → empreendimento?**
   - Centro de Custo não vem na API
   - 180 de 181 empreendimentos compartilham mesmo Centro de Custo
   - Precisa de outro campo

3. **Existe rota equivalente a DadosParcelas para despesas?**
   - DadosParcelas funciona perfeitamente para receitas
   - Precisamos equivalente para despesas

---

### Para o Time de Desenvolvimento:

**Ações Temporárias (até cliente responder):**

#### Opção A: Desabilitar Filtro (mostra dados incorretos, mas funciona)
```python
# Remove filtro por CentroCusto
# ⚠️ Mostra TODAS despesas misturadas
despesas = all_despesas  # Sem filtro
```

**Vantagens:**
- ✅ Dashboard mostra dados
- ✅ Não quebra completamente

**Desvantagens:**
- ❌ Dados incorretos (despesas de todos empreendimentos misturadas)
- ❌ Gráficos por empreendimento não fazem sentido

---

#### Opção B: Adicionar Alertas (transparência)
```python
if len(despesas) == 0:
    logger.error(
        "❌ CRÍTICO: Filtro de despesas retornou ZERO!",
        total_fetched=len(all_despesas),
        centro_custo_id=centro_custo_id,
        message="Campo CentroCusto não existe no response. Filtro sempre falha!"
    )
    # Notificar usuário no dashboard
    raise ValueError("Não foi possível filtrar despesas por empreendimento")
```

**Vantagens:**
- ✅ Torna problema visível
- ✅ Evita dados silenciosamente incorretos

**Desvantagens:**
- ❌ Dashboard quebra (mas transparente)

---

#### Opção C: Fallback Temporário (paliativo)
```python
# Se filtro falhar, buscar via rota de contrato (se existir)
if len(despesas) == 0:
    logger.warning("Filtro por CentroCusto falhou, tentando abordagem alternativa")
    # Tentar buscar via outra rota?
    # Ou retornar dados agregados sem filtro com warning?
```

---

## 📁 Arquivos Relacionados

### Código com Bug:
- `/src/starke/domain/services/ingestion_service.py:278-307` - Filtro que sempre retorna zero
- `/src/starke/infrastructure/external_apis/mega_client.py:306-337` - Busca com expand que não funciona
- `/src/starke/domain/services/cash_flow_service.py:212-300` - Calcula cash_out com lista vazia

### Evidências:
- `/api_samples/teste_filial/pagar_filial_expand_multi.json` - 1,821 despesas SEM CentroCusto
- `/api_samples/saldo_pagar.json` - 1,485 despesas SEM CentroCusto
- `/docs/TESTE-ROTAS-FILIAL-EXPAND.md` - Testes completos provando que expand não funciona

---

## ✅ Conclusão

**Bug Confirmado:**
- ✅ Campo CentroCusto não existe em 100% das despesas
- ✅ Filtro sempre retorna zero despesas
- ✅ Dashboard fica vazio
- ✅ Sistema não funciona

**Causa Raiz:**
- API não retorna campo CentroCusto (expand não funciona)
- Código assume que campo existe
- Falha silenciosa (não levanta exceção)

**Próximo Passo:**
- 🔴 **URGENTE:** Contatar Mega ERP para rota alternativa
- ⚠️ Decidir ação temporária (desabilitar filtro, adicionar alertas, ou quebrar explicitamente)

---

**Documento criado em:** 30 de Outubro de 2025, 11:30 AM
**Status:** ❌ Bug ativo, aguardando solução do cliente Mega ERP

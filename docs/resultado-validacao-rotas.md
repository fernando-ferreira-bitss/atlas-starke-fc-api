# Resultado da Validação de Rotas Otimizadas

**Data dos Testes:** 30 de Outubro de 2025
**Executado por:** Claude Code (Automático)
**Ambiente:** Produção (rest.megaerp.online)

---

## 📊 Resumo Executivo

**Decisão Final:** ❌ **NÃO MIGRAR para FaturaReceber/Saldo**

**Motivo Principal:** Validação V1 FALHOU - NumeroDocumento ≠ cod_contrato

---

## ✅ Resultados das Validações

### Validações Obrigatórias

#### ❌ V1: NumeroDocumento = cod_contrato
- **Resultado:** ❌ **FALHOU**
- **Observações:**
  - NumeroDocumento em FaturaReceber **NÃO corresponde** a cod_contrato
  - Exemplos encontrados:
    - `NumeroDocumento`: 16820000, 193, 21, 224, 283...
    - `cod_contrato`: 872, 1051, 1052, 1170, 1286...
  - **Não há correspondência entre os dois campos**
  - **BLOQUEADOR** - Impossível filtrar por empreendimento

#### ✅ V2: Múltiplas filiais/empreendimentos
- **Resultado:** ✅ **SIM**
- **Quantidade de filiais:** Múltiplas
- **Observações:** API retorna dados de múltiplas filiais conforme esperado

#### ❌ V3: Campo DataBaixa disponível
- **Resultado:** ❌ **NÃO**
- **Nome do campo:** N/A
- **Observações:**
  - Não há campo DataBaixa ou DataPagamento
  - Impossível saber QUANDO a parcela foi paga
  - **BLOQUEADOR** - Não consegue calcular realizado no mês correto

#### ❌ V4: Campo TipoParcela disponível
- **Resultado:** ❌ **NÃO**
- **Nome do campo:** N/A
- **Observações:**
  - Não há campo TipoParcela
  - Impossível categorizar (Ativos/Recuperações/Antecipações)
  - **BLOQUEADOR** - Não consegue fazer categorização

#### ✅ V5: Volume de dados aceitável
- **Resultado:** ✅ **SIM**
- **Tamanho do JSON:** 16KB
- **Quantidade de registros:** 36 parcelas
- **Observações:** Volume gerenciável e performance boa

### Validações Desejáveis

#### ❌ V6: Campo Situacao/Status
- **Resultado:** ❌ **NÃO**
- **Nome do campo:** N/A
- **Observações:** Não há campo de situação/status

#### ❌ V7: Expand adiciona campos
- **Resultado:** ❌ **NÃO**
- **Campos testados:** centroCusto, projeto, situacao, parcela, dataBaixa, tipoParcela, status, statusParcela
- **Campos adicionados:** NENHUM
- **Observações:**
  - API **NÃO suporta** os expands testados
  - Retorna mesmos campos com ou sem expand
  - `?expand=...` é ignorado pela API

#### ⚠️ V8: Performance melhor
- **Resultado:** ⚠️ **POTENCIALMENTE SIM (não testado a fundo)**
- **Observações:**
  - 1 request vs múltiplos (teoria)
  - MAS sem poder filtrar por empreendimento, irrelevante

---

## 📋 Campos Disponíveis em FaturaReceber/Saldo

```json
{
  "Filial": {
    "Id": 8770
  },
  "Agente": {
    "Codigo": 12916
  },
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
- `DataBaixa` / `DataPagamento` - Quando foi pago
- `TipoParcela` - Tipo da parcela (Mensal, Antecipação, etc)
- `StatusParcela` - Status de cadastro
- `Situacao` - Situação de pagamento (Pago, Aberto)
- `CentroCusto` - Para filtrar por empreendimento
- `Projeto` - Para análises extras

---

## 🔍 Análise Detalhada

### Problema 1: NumeroDocumento ≠ cod_contrato

**Teste Realizado:**
1. Buscamos contratos do empreendimento 1472
   - Retornou 6 contratos: 872, 1051, 1052, 1170, 1286, 7144

2. Buscamos parcelas do contrato 872 via DadosParcelas
   - Retornou 662 parcelas

3. Tentamos filtrar FaturaReceber por NumeroDocumento="872"
   - Resultado: 0 parcelas

**Conclusão:**
- NumeroDocumento em FaturaReceber **NÃO é** o código do contrato
- **Impossível** correlacionar com contratos/empreendimentos
- **Impossível** filtrar por empreendimento

---

### Problema 2: Falta de Campos para Categorização

**Necessidade:**
```python
# Queremos categorizar em:
categorias = {
    "ativos": parcelas_regulares_pagas_no_prazo,
    "recuperacoes": parcelas_vencidas_pagas_depois,
    "antecipacoes": parcelas_pagas_antes_vencimento,
    "outras": demais_receitas
}
```

**Campos Disponíveis:**
- ✅ `DataVencimento` - data prevista
- ❌ `DataBaixa` - **FALTA** data do pagamento
- ❌ `TipoParcela` - **FALTA** tipo da parcela

**Conclusão:**
- ❌ **Impossível** determinar se é antecipação (precisa comparar DataBaixa < DataVencimento)
- ❌ **Impossível** determinar se é recuperação (precisa verificar TipoParcela ou timing)
- ❌ Só consegue valor total previsto (DataVencimento) e saldo em aberto (SaldoAtual)

---

### Problema 3: Expand Não Funciona

**Teste Realizado:**
```bash
# Tentamos múltiplos expands
?expand=centroCusto,projeto,situacao,parcela,dataBaixa,tipoParcela,status,statusParcela
```

**Resultado:**
- ❌ NENHUM campo foi adicionado
- ❌ API ignora o parâmetro expand
- ❌ Mesmo response com ou sem expand

**Conclusão:**
- API **não suporta** expand nesta rota
- Não há como adicionar campos extras

---

## 🎯 Decisão Final

### **Cenário Identificado:** Cenário 3

**❌ NumeroDocumento NÃO é cod_contrato**

### **Decisão:** ❌ **NÃO MIGRAR**

### **Justificativa:**

1. **Validação V1 FALHOU (CRÍTICO):**
   - NumeroDocumento não corresponde a cod_contrato
   - Impossível filtrar por empreendimento
   - Impossível correlacionar com DadosContrato

2. **Validações V3 e V4 FALHARAM (CRÍTICAS):**
   - Falta DataBaixa → não sabe quando foi pago
   - Falta TipoParcela → não consegue categorizar
   - Falta Situacao → não sabe se foi pago

3. **Expand não funciona:**
   - API ignora parâmetro expand
   - Sem possibilidade de adicionar campos

4. **Ganho de performance irrelevante:**
   - Mesmo sendo 1 request vs múltiplos
   - Sem poder filtrar por empreendimento, não serve

---

## 📝 Próximas Ações

### ✅ Ações Recomendadas:

#### 1. **Manter DadosParcelas (Abordagem Atual)**
```python
# ✅ Continuar usando
contratos = get_contratos_by_empreendimento(emp_id)
for contrato in contratos:
    parcelas = get_parcelas(contrato.id)
```

**Motivo:** É a **ÚNICA** forma de:
- ✅ Filtrar por empreendimento (via contratos)
- ✅ Ter DataBaixa (quando foi pago)
- ✅ Ter TipoParcela (para categorizar)
- ✅ Ter Situacao (status de pagamento)
- ✅ Ter TODOS os campos necessários

---

#### 2. **Otimizar com Cache/Banco (Próxima Sprint)**
```python
class ParcelasRepository:
    def sync_once_per_day(self):
        """Sincroniza parcelas 1x por dia."""
        for emp in empreendimentos:
            contratos = get_contratos(emp.id)
            for contrato in contratos:
                parcelas = get_parcelas(contrato.id)
                salvar_no_banco(parcelas)  # Cache persistente

    def get_agregado_sql(self, emp_id, mes):
        """Busca agregado do banco (milissegundos)."""
        return db.query("SELECT SUM(...) FROM parcelas WHERE ...")
```

**Vantagens:**
- 🚀 Sync 1x por dia (agendado)
- 🚀 Queries em SQL (super rápidas)
- ✅ Dados completos
- ✅ Histórico disponível

---

#### 3. **NÃO implementar FaturaReceber**

**Motivo:**
- ❌ Não tem campos necessários
- ❌ Não permite filtrar por empreendimento
- ❌ Não agrega valor
- ❌ Adiciona complexidade sem benefício

---

## 📊 Comparação Final

| Aspecto | DadosParcelas (Atual) | FaturaReceber/Saldo | Vencedor |
|---------|----------------------|---------------------|----------|
| **Filtro por Empreendimento** | ✅ Via contratos | ❌ Impossível | DadosParcelas |
| **DataBaixa** | ✅ Tem | ❌ Não tem | DadosParcelas |
| **TipoParcela** | ✅ Tem | ❌ Não tem | DadosParcelas |
| **Situacao** | ✅ Tem | ❌ Não tem | DadosParcelas |
| **Categorização** | ✅ Completa | ❌ Impossível | DadosParcelas |
| **Performance** | ⚠️ N requests | ✅ 1 request | FaturaReceber |
| **Campos Completos** | ✅ 50+ campos | ❌ 9 campos | DadosParcelas |
| **Expand** | ✅ Funciona | ❌ Não funciona | DadosParcelas |

**Resultado:** ✅ **DadosParcelas é SUPERIOR em todos os aspectos relevantes**

---

## 🔗 Arquivos Gerados

Todos os arquivos de teste estão em:
```
/api_samples/validacao_20251030_103630/
```

### Arquivos de Teste:
- `teste1_base.json` - FaturaReceber sem expand (16KB, 36 registros)
- `teste2_expand_basico.json` - FaturaReceber com expand básico
- `teste3_expand_completo.json` - FaturaReceber com expand completo
- `teste4_contratos.json` - Contratos do empreendimento 1472
- `teste4_dados_parcelas.json` - Parcelas via DadosParcelas (662 parcelas)
- `teste4_fatura_receber.json` - Tentativa de filtro (0 parcelas)

### Arquivos de Análise:
- `teste1_campos.txt` - Lista de campos teste 1
- `teste1_filiais.txt` - Filiais encontradas
- `teste2_campos.txt` - Lista de campos teste 2

---

## ✅ Conclusão

**A rota `/api/FinanceiroMovimentacao/FaturaReceber/Saldo` NÃO pode substituir `DadosParcelas` porque:**

1. ❌ **NumeroDocumento ≠ cod_contrato** (impossível filtrar por empreendimento)
2. ❌ **Falta DataBaixa** (impossível saber quando foi pago)
3. ❌ **Falta TipoParcela** (impossível categorizar)
4. ❌ **Expand não funciona** (sem possibilidade de adicionar campos)

**Recomendação:** ✅ **Manter DadosParcelas + implementar cache no banco de dados**

---

**Validação Concluída em:** 30 de Outubro de 2025, 10:36 AM
**Status:** ✅ Validação completa - Decisão documentada

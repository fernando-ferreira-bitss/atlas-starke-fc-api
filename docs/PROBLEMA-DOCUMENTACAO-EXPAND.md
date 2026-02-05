# 🔴 PROBLEMA: Documentação Insuficiente do Parâmetro Expand

**Data:** 30 de Outubro de 2025
**Problema:** Não sabemos quais valores usar no parâmetro `expand`

---

## 📋 Resumo do Problema

Os Swaggers da API Mega ERP documentam que algumas rotas aceitam parâmetro `expand`, mas **NÃO documentam:**
- ❌ Quais valores são válidos
- ❌ Quais campos podem ser expandidos
- ❌ Exemplos de uso
- ❌ Schema de resposta quando expandido

---

## 🔍 Análise da Documentação

### Swagger: movimentosfinanceiros.json

#### Documentação do parâmetro expand:
```json
{
  "name": "expand",
  "in": "query",
  "description": "Expandir os dados do saldo da parcela",
  "schema": {
    "type": "string"  // ❌ Apenas "string" genérico
  }
}
```

**Problemas:**
- ❌ Não há `enum` com valores válidos
- ❌ Não há `example` mostrando uso
- ❌ Descrição genérica sem detalhes
- ❌ `components.schemas` está **null** (sem definição de estruturas)

### Swagger: recebiveis.json

**✅ Schemas bem documentados:**
- `DadosParcelas`: 41 campos documentados
- `DadosContrato`: campos com tipo, descrição, exemplo
- Total: 20+ schemas definidos

**❌ Mas não documenta expand:**
- Não há rotas com parâmetro expand em `/api/Carteira/*`
- Campos já vêm completos sem necessidade de expand

---

## 🤔 Como Escolhemos os Valores de Expand?

### Método Atual: "Adivinhação Educada"

Baseamos em:
1. **Nomes comuns** de campos relacionais em APIs
2. **Estrutura de dados** observada nos responses
3. **Convenções** de outras APIs similares

#### Valores testados:
```python
expand_tentativas = [
    # Baseado em campos que "fazem sentido" existir:
    "classeFinanceira",   # Para categorização OPEX/CAPEX
    "centroCusto",        # Para filtrar por empreendimento
    "projeto",            # Para análises por projeto
    "situacao",           # Status de pagamento
    "parcela",            # Detalhes da parcela
    "dataBaixa",          # Data de pagamento
    "tipoParcela",        # Tipo da parcela
    "status",             # Status geral
    "statusParcela"       # Status específico
]
```

**Resultado:** ❌ TODOS retornam `null` ou são ignorados pela API

---

## ⚠️ Impacto

### Não sabemos se:
1. Os valores que tentamos estão **errados** (nomes diferentes?)
2. O parâmetro expand **não funciona** de fato
3. Precisamos usar **outra sintaxe** (ex: `expand=classeFinanceira.identificador`)
4. Há **limitações** não documentadas

### Consequências:
```python
# Tentativa 1: expand genérico
response = api.get("/FaturaPagar/Saldo/...", params={"expand": "classeFinanceira"})
# Resultado: ClasseFinanceira não existe no JSON

# Tentativa 2: expand completo
response = api.get("/FaturaPagar/Saldo/...", params={
    "expand": "classeFinanceira,centroCusto,projeto,situacao"
})
# Resultado: TODOS os campos null

# Tentativa 3: camelCase vs snake_case?
response = api.get("/FaturaPagar/Saldo/...", params={"expand": "classe_financeira"})
# Resultado: Também não funciona
```

---

## 🎯 Comparação com Outras APIs

### OData (Microsoft):
```javascript
// Bem documentado
GET /api/Orders?$expand=Customer,OrderDetails
// Documentação lista campos expandíveis
```

### GraphQL:
```graphql
# Explícito no schema
query {
  order {
    customer { name }  # Campos disponíveis no schema
    items { product }
  }
}
```

### Mega ERP:
```bash
# ❌ Sem documentação
GET /api/FaturaPagar/Saldo/...?expand=???
# Não sabemos o que colocar em ???
```

---

## 📊 Evidências nos Testes

### Teste 1: Base (sem expand)
```bash
curl "/api/FaturaReceber/Saldo/2025-10-01/2025-10-31"
```

**Resultado:** 36 parcelas, 9 campos
```json
{
  "Filial": {"Id": 8770},
  "Agente": {"Codigo": 12916},
  "NumeroDocumento": "9994",
  "DataVencimento": "01/10/2025",
  "ValorParcela": 26000.0,
  "SaldoAtual": 26000.0
  // ... 3 campos adicionais
}
```

### Teste 2: Com expand completo
```bash
curl "/api/FaturaReceber/Saldo/2025-10-01/2025-10-31?expand=centroCusto,projeto,situacao,parcela,dataBaixa,tipoParcela,status,statusParcela"
```

**Resultado:** 36 parcelas, **MESMOS 9 campos**
```json
{
  "Filial": {"Id": 8770},
  "Agente": {"Codigo": 12916},
  "NumeroDocumento": "9994",
  "DataVencimento": "01/10/2025",
  "ValorParcela": 26000.0,
  "SaldoAtual": 26000.0
  // ... mesmos 3 campos adicionais
  // ❌ Nenhum campo adicional foi adicionado!
}
```

### Análise:
```bash
diff teste1_base.json teste3_expand_completo.json
# Resultado: SEM DIFERENÇAS
```

---

## ❓ Perguntas para Mega ERP

### 1. Documentação de Expand
```markdown
❓ Quais valores são válidos para o parâmetro expand?

Rotas afetadas:
- /api/FinanceiroMovimentacao/FaturaPagar/Saldo/...?expand=
- /api/FinanceiroMovimentacao/FaturaReceber/Saldo/...?expand=

Perguntas específicas:
1. Existe uma lista de campos expandíveis?
2. A sintaxe é "expand=campo1,campo2,campo3"?
3. Os nomes são case-sensitive?
4. Há documentação adicional além do Swagger?
```

### 2. Schemas de Resposta
```markdown
❓ Por que components.schemas está vazio em movimentosfinanceiros.json?

Observação:
- recebiveis.json tem schemas bem documentados (DadosParcelas, etc)
- movimentosfinanceiros.json tem components.schemas = null
- Impossível saber estrutura de resposta esperada

Pergunta:
Podem adicionar schemas no Swagger de movimentosfinanceiros?
```

### 3. Funcionalidade do Expand
```markdown
❓ O parâmetro expand está funcional nas rotas FaturaPagar/FaturaReceber?

Evidências:
- Testamos 8+ valores diferentes
- Nenhum adiciona campos ao response
- Response idêntico com ou sem expand

Possibilidades:
1. Expand não está implementado ainda?
2. Estamos usando valores errados?
3. Há outra forma de obter campos adicionais?
```

### 4. Campos Necessários
```markdown
❓ Como obter ClasseFinanceira, CentroCusto, DataBaixa nas despesas?

Necessidade:
- ClasseFinanceira → categorização OPEX/CAPEX
- CentroCusto → filtrar por empreendimento
- DataBaixa → timing correto de pagamento

Situação atual:
- FaturaPagar/Saldo retorna apenas 10 campos básicos
- Expand não adiciona esses campos
- Sem eles, sistema não funciona corretamente

Pergunta:
Qual rota retorna esses campos?
```

---

## 💡 Sugestões de Melhoria na Documentação

### Para o Swagger da Mega:

#### 1. Adicionar enum de valores válidos:
```json
{
  "name": "expand",
  "in": "query",
  "description": "Campos relacionados a expandir",
  "schema": {
    "type": "string",
    "enum": [
      "classeFinanceira",
      "centroCusto",
      "projeto",
      "situacao"
    ]
  },
  "example": "classeFinanceira,centroCusto"
}
```

#### 2. Adicionar schemas de resposta:
```json
{
  "components": {
    "schemas": {
      "FaturaPagarSaldo": {
        "type": "object",
        "properties": {
          "Filial": {"$ref": "#/components/schemas/Filial"},
          "ValorParcela": {"type": "number"},
          "ClasseFinanceira": {
            "description": "Disponível com expand=classeFinanceira",
            "$ref": "#/components/schemas/ClasseFinanceira"
          }
        }
      }
    }
  }
}
```

#### 3. Adicionar exemplos de uso:
```json
{
  "paths": {
    "/api/FaturaPagar/Saldo/{inicio}/{fim}": {
      "get": {
        "parameters": [...],
        "responses": {
          "200": {
            "description": "Saldos das parcelas",
            "content": {
              "application/json": {
                "examples": {
                  "sem_expand": {
                    "summary": "Resposta sem expand",
                    "value": {"Filial": {...}, "ValorParcela": 1000}
                  },
                  "com_expand": {
                    "summary": "Resposta com expand=classeFinanceira",
                    "value": {
                      "Filial": {...},
                      "ValorParcela": 1000,
                      "ClasseFinanceira": {"Identificador": "1.2.01"}
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

---

## 📁 Arquivos de Evidência

### Swaggers analisados:
- `/docs/swagger/mega/movimentosfinanceiros.json` - ❌ Sem schemas, expand não documentado
- `/docs/swagger/mega/recebiveis.json` - ✅ Schemas completos, 41 campos em DadosParcelas

### Testes realizados:
- `/api_samples/validacao_20251030_103630/teste1_base.json` - Sem expand
- `/api_samples/validacao_20251030_103630/teste2_expand_basico.json` - Com expand básico
- `/api_samples/validacao_20251030_103630/teste3_expand_completo.json` - Com expand completo
- **Resultado:** Todos idênticos

### Comparação:
```bash
# Campos em teste 1 (sem expand):
jq '.[0] | keys' teste1_base.json
# → 9 campos

# Campos em teste 3 (com expand completo):
jq '.[0] | keys' teste3_expand_completo.json
# → 9 campos (MESMOS!)
```

---

## ✅ Conclusão

**Situação atual:**
- ❌ Não sabemos quais valores usar em `expand`
- ❌ Swagger não documenta campos expandíveis
- ❌ Testes mostram que expand é **ignorado**
- ❌ Sem schemas, impossível saber estrutura esperada

**Ação necessária:**
1. 🔴 **URGENTE:** Mega ERP documentar valores válidos de expand
2. 🔴 **URGENTE:** Confirmar se expand funciona ou não
3. ⚠️ Adicionar schemas no Swagger de movimentosfinanceiros
4. ⚠️ Adicionar exemplos de uso

**Enquanto isso:**
- Assumir que expand **NÃO funciona** nessas rotas
- Buscar rotas alternativas que retornem campos completos
- Documentar necessidade de campos via outras rotas

---

**Última atualização:** 30 de Outubro de 2025

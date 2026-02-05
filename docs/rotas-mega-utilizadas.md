# Rotas da API Mega Utilizadas no Starke

**Data:** 30 de Outubro de 2025
**Versão da API Mega:** 1.x

---

## 📋 Resumo

Este documento lista todas as rotas da API Mega utilizadas pelo sistema Starke para construir os gráficos e relatórios de fluxo de caixa.

---

## 🔐 1. Autenticação

### Endpoint
```
POST /api/Auth/SignIn
```

### Dados Coletados
- `accessToken` - Token de acesso para autenticação
- `refreshToken` - Token para renovação
- `expirationToken` - Data/hora de expiração

### Por que usamos
Obter token de autenticação necessário para todas as outras chamadas da API.

---

## 🏢 2. Buscar Empreendimentos

### Endpoint
```
GET /api/globalestruturas/Empreendimentos
```

### Dados Coletados
- `codigo` - ID do empreendimento
- `nome` - Nome do empreendimento
- `codigoFilial` - ID da filial à qual pertence
- `centroCusto.reduzido` - ID do centro de custo (usado para filtrar despesas)

### Por que usamos
- Listar todos os empreendimentos disponíveis
- Obter o mapeamento **Empreendimento → Centro de Custo**
- Saber a qual filial o empreendimento pertence

### Observação Importante
⚠️ **Centro de Custo é a chave** para filtrar despesas por empreendimento!

---

## 📝 3. Buscar Contratos do Empreendimento

### Endpoint
```
GET /api/Carteira/DadosContrato/IdEmpreendimento={empreendimento_id}
```

### Dados Coletados
- `cod_contrato` - ID do contrato (necessário para buscar parcelas)
- `nome_cliente` - Nome do cliente
- `valor_contrato` - Valor total do contrato
- `status_contrato` - Status (Ativo, Inadimplente, Quitado, etc)
- `cod_empreendimento` - Confirma o empreendimento

### Por que usamos
- Obter lista de contratos do empreendimento
- Calcular métricas de portfólio (VP, LTV, prazo médio)
- Buscar parcelas de cada contrato

---

## 💰 4. Buscar Parcelas do Contrato (ENTRADAS)

### Endpoint
```
GET /api/Carteira/DadosParcelas/IdContrato={contrato_id}
```

### Dados Coletados

| Campo | Uso |
|-------|-----|
| `status_parcela` | Filtrar apenas parcelas "Ativo" |
| `tipo_parcela` | Categorizar (Mensal, Antecipação, etc) |
| `data_vencimento` | Calcular entradas previstas (forecast) |
| `data_baixa` | Calcular entradas realizadas (actual) |
| `vlr_original` | Valor previsto da parcela |
| `vlr_pago` | Valor efetivamente pago |
| `situacao` | Verificar se foi paga (Pago, Aberto, etc) |
| `parcela_processo` | Identificar renegociações |
| `parcela_origem` | Origem da parcela |

### Por que usamos
- **Calcular entradas de caixa** (Cash In)
- **Categorizar recebimentos:**
  - **Ativos:** Parcelas regulares pagas no prazo
  - **Recuperações:** Parcelas vencidas que foram pagas ou renegociadas
  - **Antecipações:** Parcelas pagas antes do vencimento
  - **Outras:** Demais receitas

### Observação Importante
✅ Esta rota **já inclui parcelas renegociadas** - não é necessário chamar rotas separadas de renegociação!

---

## 💸 5. Buscar Despesas (SAÍDAS)

### Endpoint
```
GET /api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/{filial_id}/{data_inicio}/{data_fim}
    ?expand=classeFinanceira,centroCusto,projeto
```

### Exemplo
```
GET /api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/4/2025-01-01/2025-12-31
    ?expand=classeFinanceira,centroCusto,projeto
```

### Dados Coletados

| Campo | Uso |
|-------|-----|
| `CentroCusto.Reduzido` | **Filtrar despesas por empreendimento** |
| `ClasseFinanceira.Identificador` | **Categorizar tipo de despesa** (OPEX, CAPEX, etc) |
| `DataVencimento` | Calcular saídas orçadas (budget) |
| `ValorParcela` | Valor da despesa |
| `SaldoAtual` | Se = 0, despesa foi paga; se > 0, está em aberto |
| `Agente.Nome` | Nome do fornecedor |
| `TipoDocumento` | Tipo de documento (NF, FATURA, etc) |

### Por que usamos
- **Calcular saídas de caixa** (Cash Out)
- **Categorizar despesas:**
  - **OPEX:** Despesas operacionais (salários, manutenção, utilities)
  - **CAPEX:** Investimentos (construção, equipamentos)
  - **Financeiras:** Juros, taxas bancárias
  - **Distribuições:** Dividendos, distribuição de lucros

### Observações Importantes
⚠️ **SEMPRE usar `?expand=classeFinanceira,centroCusto,projeto`** - sem expand, não temos os dados necessários!

⚠️ Esta rota retorna despesas de **TODOS os empreendimentos da filial** - é necessário **filtrar por `CentroCusto.Reduzido`** no código!

### Mapeamento de Categorias
A categorização é feita através do campo `ClasseFinanceira.Identificador`:

```
Exemplos de Mapeamento (variam por instalação):
- "1.1.x" → CAPEX (Investimentos)
- "1.2.x" → OPEX (Operacionais)
- "1.3.x" → Financeiras
- "1.4.x" → Distribuições
```

---

## 🔄 Fluxo de Coleta de Dados

Para processar **1 empreendimento**:

```
1. Buscar dados do empreendimento
   ↓
2. Obter mapeamento: empreendimento → centro de custo → filial
   ↓
3. Buscar contratos do empreendimento
   ↓
4. Para cada contrato:
   └─ Buscar parcelas (entradas)
   ↓
5. Buscar despesas da filial (com expand)
   ↓
6. Filtrar despesas pelo centro de custo do empreendimento
   ↓
7. Categorizar entradas e saídas
   ↓
8. Calcular saldos
   ↓
9. Salvar no banco de dados
   ↓
10. Gerar gráficos
```

---

## 📊 Quantidade de Requests

Para **1 empreendimento** em **1 mês**:

| Rota | Quantidade |
|------|------------|
| Empreendimentos | 1x |
| Contratos | 1x |
| Parcelas | N contratos (ex: 50x) |
| Despesas | 1x |
| **Total** | **~52 requests** |

Para **12 meses** do mesmo empreendimento:
- **~52 requests** (porque despesas já busca período completo)

---

## ⚠️ Pontos Críticos de Atenção

### 1. Filial ≠ Empreendimento

```
FILIAL 4 (empresa)
  ├── Empreendimento A (centro custo 21)
  ├── Empreendimento B (centro custo 22)
  └── Empreendimento C (centro custo 23)
```

**Sempre filtrar por Centro de Custo após buscar despesas da filial!**

---

### 2. Sempre usar expand em Despesas

❌ **Sem expand:**
```json
{
  "DataVencimento": "25/10/2025",
  "ValorParcela": 50000.0,
  "SaldoAtual": 0.0
}
```

✅ **Com expand:**
```json
{
  "DataVencimento": "25/10/2025",
  "ValorParcela": 50000.0,
  "SaldoAtual": 0.0,
  "ClasseFinanceira": {"Identificador": "1.2.03"},
  "CentroCusto": {"Reduzido": 21}
}
```

**Sem expand, não conseguimos categorizar nem filtrar por empreendimento!**

---

### 3. Parcelas já incluem Renegociações

Não é necessário chamar rotas separadas:
- ❌ `/api/Carteira/DadosParcelasReneg`
- ❌ `/api/Carteira/DadosRenegociacoes`

A rota **DadosParcelas** já traz todas as informações de renegociação nos campos:
- `parcela_processo`
- `parcela_origem`
- `vlr_jurosreneg`

---

## 🎯 Resumo

| Dado | Rota Usada | Campo-chave |
|------|------------|-------------|
| **Entradas (Cash In)** | DadosParcelas | `data_baixa`, `vlr_pago`, `tipo_parcela` |
| **Saídas (Cash Out)** | FaturaPagar/Saldo | `CentroCusto`, `ClasseFinanceira` |
| **Mapeamento** | Empreendimentos | `centroCusto.reduzido` |
| **Contratos** | DadosContrato | `cod_contrato` |

---

**Última Atualização:** 30 de Outubro de 2025

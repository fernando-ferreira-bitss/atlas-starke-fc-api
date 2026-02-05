# Análise da API UAU para Integração com Starke

**Data da análise:** 26-27/12/2025
**Objetivo:** Capturar dados para o relatório de fluxo de caixa
**Status:** ✅ Análise Completa - Pronto para Implementação

---

## 1. Informações de Conexão

### Ambiente
- **URL Base:** `https://gamma-api.seniorcloud.com.br:50801/uauAPI/api/v1.0`
- **Versão API:** 1.0

### Autenticação (Dois Tokens)

| Token | Header | Descrição |
|-------|--------|-----------|
| Integração | `X-INTEGRATION-Authorization` | Token fixo fornecido pelo cliente |
| Sessão | `Authorization` | Token dinâmico obtido no login |

**Passo 1 - Login:**
```bash
curl -X POST "https://gamma-api.seniorcloud.com.br:50801/uauAPI/api/v1.0/Autenticador/AutenticarUsuario" \
  -H "X-INTEGRATION-Authorization: <TOKEN_INTEGRACAO_FIXO>" \
  -H "Content-Type: application/json" \
  -d '{"login": "STARKE", "senha": "***"}'
```

**Passo 2 - Usar ambos os tokens nas chamadas:**
```bash
curl -X POST "<endpoint>" \
  -H "X-INTEGRATION-Authorization: <TOKEN_INTEGRACAO_FIXO>" \
  -H "Authorization: <TOKEN_SESSAO_RETORNADO>" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

---

## 2. Estrutura Organizacional

### Hierarquia UAU
```
Empresa (140 cadastradas) = EMPREENDIMENTO no Starke
  └── Obra (282 ativas) = Fases do empreendimento (agrupar por Empresa)
       └── Venda (contrato com cliente)
            └── Parcela (a receber / recebida)
```

### Mapeamento Organizacional UAU → Starke
| UAU | Starke | Observação |
|-----|--------|------------|
| **Empresa** | **Empreendimento** | Agrupar dados por Empresa |
| Obra | Fase | Não precisa separar no relatório |
| Venda | Contrato | - |
| Parcela | Parcela | - |

> **Importante:** Para o relatório de fluxo de caixa, agrupar todas as Obras por Empresa. A Empresa é o nível de agregação principal.

### Campos das Entidades

#### Empresa
| Campo | Tipo | Descrição |
|-------|------|-----------|
| Codigo_emp | int | ID da empresa |
| Desc_emp | string | Nome/razão social |
| CGC_emp | string | CNPJ |
| IE_emp | string | Inscrição estadual |
| InscrMunic_emp | string | Inscrição municipal |
| Endereco_emp | string | Endereço |
| Fone_emp | string | Telefone |

#### Obra (Empreendimento)
| Campo | Tipo | Descrição |
|-------|------|-----------|
| Cod_obr | string | Código da obra (ex: "JVL00", "JVA16") |
| Empresa_obr | int | FK para empresa |
| Descr_obr | string | Nome da obra |
| Status_obr | int | 0 = ativa |
| DtIni_obr | datetime | Data início |
| Dtfim_obr | datetime | Data fim prevista |
| TipoObra_obr | int | Tipo (3 = financeira) |
| CEI_obr | string | Código CEI |

---

## 3. Endpoints Validados

### 3.1 Empresas - ✅ FUNCIONANDO
```bash
curl -X POST ".../Empresa/ObterEmpresasAtivas" \
  -H "Authorization: <token>" \
  -H "X-INTEGRATION-Authorization: <token_int>" \
  -H "Content-Type: application/json" \
  -d '{}'
```
- **Resultado:** 140 empresas retornadas

### 3.2 Obras - ✅ FUNCIONANDO
```bash
curl -X POST ".../Obras/ObterObrasAtivas" \
  -H "Authorization: <token>" \
  -H "X-INTEGRATION-Authorization: <token_int>" \
  -H "Content-Type: application/json" \
  -d '{}'
```
- **Resultado:** 282 obras (162 financeiras + 120 imobiliárias)

---

### 3.3 CashOut (Desembolso) - ✅ FUNCIONANDO PERFEITAMENTE

```bash
curl -X POST ".../Planejamento/ConsultarDesembolsoPlanejamento" \
  -H "Authorization: <token>" \
  -H "X-INTEGRATION-Authorization: <token_int>" \
  -H "Content-Type: application/json" \
  -d '{
    "Empresa": 2,
    "Obra": "JVL00",
    "MesInicial": "01/2024",
    "MesFinal": "12/2025"
  }'
```

**Resultado de exemplo (JVL00):** 1074 registros

| Status | Quantidade | Uso no Starke |
|--------|------------|---------------|
| Projetado | 119 | `budget` (orçamento) |
| Pagar | 237 | pendente |
| Pago | 718 | `actual` (realizado) |

**Campos retornados:**
| Campo | Tipo | Descrição | Uso no Starke |
|-------|------|-----------|---------------|
| Status | string | "Projetado", "Pagar", "Pago" | record_type |
| Empresa | int | Código empresa | empreendimento_id |
| Obra | string | Código obra | empreendimento_id |
| Contrato | int | Código contrato | detalhes |
| Produto | int | Código produto | detalhes |
| Composicao | string | Código composição (ex: "C0023") | categoria |
| Item | string | Código item (ex: "00.01.01") | categoria |
| Insumo | string | Código insumo (ex: "A00158") | categoria |
| DtaRef | datetime | Data de referência | - |
| DtaRefMes | int | Mês (1-12) | ref_month |
| DtaRefAno | int | Ano | ref_month |
| Total | decimal | Valor total | valor |
| Acrescimo | decimal | Acréscimos | ajustes |
| Desconto | decimal | Descontos | ajustes |
| TotalLiq | decimal | Total líquido | valor_liquido |
| TotalBruto | decimal | Total bruto | valor_bruto |

**Exemplo de registro:**
```json
{
  "Status": "Pago",
  "Empresa": 2,
  "Obra": "JVL00",
  "Contrato": 1,
  "Produto": 999,
  "Composicao": "C0023",
  "Item": "00.01.01",
  "Insumo": "A00162",
  "DtaRef": "2024-08-30T00:00:00",
  "DtaRefMes": 8,
  "DtaRefAno": 2024,
  "Total": 3029250.00,
  "Acrescimo": 0.0,
  "Desconto": 0.0,
  "TotalLiq": 40000.00,
  "TotalBruto": 40000.00
}
```

---

### 3.4 CashIn (Parcelas) - ✅ FUNCIONANDO

#### 3.4.1 Listar Vendas por Período
```bash
curl -X POST ".../Venda/RetornaChavesVendasPorPeriodo" \
  -H "Authorization: <token>" \
  -H "X-INTEGRATION-Authorization: <token_int>" \
  -H "Content-Type: application/json" \
  -d '{
    "data_inicio": "2020-01-01T00:00:00",
    "data_fim": "2025-12-31T00:00:00",
    "statusVenda": "0",
    "listaEmpresaObra": [
      {"codigoEmpresa": 93, "codigoObra": "JVA16"}
    ]
  }'
```
**Retorno:** Lista de chaves no formato `00093-JVA16/00006`

#### 3.4.2 Parcelas a Receber (FORECAST + INADIMPLÊNCIA)
```bash
curl -X POST ".../Venda/BuscarParcelasAReceber" \
  -H "Authorization: <token>" \
  -H "X-INTEGRATION-Authorization: <token_int>" \
  -H "Content-Type: application/json" \
  -d '{
    "empresa": 93,
    "obra": "JVA16",
    "num_ven": 6
  }'
```

**Campos principais:**
| Campo | Tipo | Exemplo | Uso no Starke |
|-------|------|---------|---------------|
| Empresa_prc | int | 93 | empreendimento_id |
| Obra_Prc | string | "JVA16" | empreendimento_id |
| NumVend_prc | int | 6 | origin_id |
| NumParc_Prc | int | 1 | origin_id |
| Data_Prc | datetime | "2021-06-10" | **ref_month (forecast)** / **inadimplência** |
| Valor_Prc | decimal | 486.70 | **forecast** |
| Status_Prc | byte | 0 | status (0=aberto) |
| Tipo_Prc | string | "E" | category (E=Entrada) |
| Cliente_Prc | int | 28526 | cliente_id |
| nome_pes | string | "DEOLINDO CASSIMIRO" | nome_cliente |
| Descricao_par | string | "Entrada" | tipo_parcela |
| DataPror_Prc | datetime | "2025-06-24" | data_prorrogacao |
| ValorReaj | decimal | 486.70 | valor_reajustado |
| vlrPrincReal | decimal | 486.70 | valor_principal |

**Exemplo de registro:**
```json
{
  "Empresa_prc": 93,
  "Obra_Prc": "JVA16",
  "NumVend_prc": 6,
  "NumParc_Prc": 1,
  "Data_Prc": "2021-06-10T00:00:00",
  "Valor_Prc": 486.700000,
  "Status_Prc": 0,
  "Tipo_Prc": "E",
  "Cliente_Prc": 28526,
  "nome_pes": "DEOLINDO CASSIMIRO",
  "Descricao_par": "Entrada",
  "Desc_emp": "JVA EMPREENDIMENTOS IMOBILIARIOS LTDA",
  "ValorReaj": 486.7,
  "vlrPrincReal": 486.7
}
```

**Cálculo de Inadimplência:**
```python
# Parcela vencida = Data_Prc < hoje AND Status_Prc = 0
dias_atraso = (hoje - Data_Prc).days
if dias_atraso > 0 and Status_Prc == 0:
    if dias_atraso <= 30: faixa = "0-30"
    elif dias_atraso <= 60: faixa = "30-60"
    elif dias_atraso <= 90: faixa = "60-90"
    elif dias_atraso <= 180: faixa = "90-180"
    else: faixa = "180+"
```

#### 3.4.3 Parcelas Recebidas (ACTUAL)
```bash
curl -X POST ".../Venda/BuscarParcelasRecebidas" \
  -H "Authorization: <token>" \
  -H "X-INTEGRATION-Authorization: <token_int>" \
  -H "Content-Type: application/json" \
  -d '{
    "empresa": 93,
    "obra": "JVA16",
    "num_ven": 6
  }'
```

**Estrutura do retorno:**
```json
[
  {
    "Recebidas": [
      { "schema..." },
      { "dados reais..." }
    ]
  }
]
```

**Campos principais:**
| Campo | Tipo | Exemplo | Uso no Starke |
|-------|------|---------|---------------|
| Empresa_rec | int | 93 | empreendimento_id |
| Obra_Rec | string | "JVA16" | empreendimento_id |
| NumVend_Rec | int | 6 | origin_id |
| NumParc_Rec | int | 1 | origin_id |
| **Data_Rec** | datetime | "2021-04-30" | **ref_month (actual)** |
| DataVenci_Rec | datetime | "2021-04-27" | data_vencimento |
| **ValorConf_Rec** | decimal | 1081.55 | **actual** |
| Status_Rec | byte | 1 | status (1=confirmado) |
| ParcType_Rec | string | "E" | category |
| Cliente_Rec | int | 28526 | cliente_id |
| VlMultaConf_Rec | decimal | 21.63 | multa |
| VlJurosConf_Rec | decimal | 1.07 | juros |
| User_Rec | string | "PANMELLA" | usuario_baixa |

**Exemplo de registro:**
```json
{
  "Empresa_rec": 93,
  "Obra_Rec": "JVA16",
  "NumVend_Rec": 6,
  "NumParc_Rec": 1,
  "Data_Rec": "2021-04-30T00:00:00",
  "DataVenci_Rec": "2021-04-27T00:00:00",
  "ValorConf_Rec": 1081.550000,
  "Status_Rec": 1,
  "ParcType_Rec": "E",
  "Tipo_Rec": "S",
  "Cliente_Rec": 28526,
  "VlMultaConf_Rec": 21.630000,
  "VlJurosConf_Rec": 1.070000,
  "User_Rec": "PANMELLA",
  "ValorPrincipalPrice_rec": 1081.550000
}
```

---

### 3.5 Portfolio Stats (Valor Presente) - ✅ FUNCIONANDO

```bash
curl -X POST ".../Venda/ConsultarParcelasDaVenda" \
  -H "Authorization: <token>" \
  -H "X-INTEGRATION-Authorization: <token_int>" \
  -H "Content-Type: application/json" \
  -d '{
    "empresa": 93,
    "obra": "JVA16",
    "num_venda": 6,
    "data_calculo": "2025-12-27T00:00:00",
    "boleto_antecipado": false
  }'
```

**Este endpoint calcula automaticamente o Valor Presente das parcelas!**

**Campos principais:**
| Campo | Tipo | Exemplo | Uso no Starke |
|-------|------|---------|---------------|
| Empresa_reaj | int | 93 | empreendimento_id |
| Obra_reaj | string | "JVA16" | empreendimento_id |
| NumVenda_reaj | int | 6 | origin_id |
| NumParc_reaj | int | 1 | origin_id |
| **Principal_reaj** | decimal | 486.70 | **Valor original** |
| **Valor_reaj** | decimal | 763.20 | **Valor Presente (VP)** |
| Juros_reaj | decimal | 266.77 | Juros calculados |
| Multa_reaj | decimal | 9.73 | Multa |
| Correcao_reaj | decimal | 0.0 | Correção monetária |
| DataVenc_reaj | datetime | "2021-06-10" | Data vencimento |
| DataCalculo_reaj | datetime | "2025-12-27" | Data do cálculo |
| Tipo_reaj | string | "E" | Tipo parcela |

**Exemplo de registro:**
```json
{
  "Empresa_reaj": 93,
  "Obra_reaj": "JVA16",
  "NumVenda_reaj": 6,
  "Principal_reaj": 486.700000,
  "Valor_reaj": 763.20,
  "Juros_reaj": 266.77,
  "Multa_reaj": 9.73,
  "Correcao_reaj": 0.0,
  "DataVenc_reaj": "2021-06-10T00:00:00",
  "DataCalculo_reaj": "2025-12-27T00:00:00",
  "NumParc_reaj": 1,
  "Tipo_reaj": "E"
}
```

**Verificação do cálculo:**
```
Parcela 1:
  Principal:  R$ 486,70
  + Juros:    R$ 266,77
  + Multa:    R$   9,73
  = VP Total: R$ 763,20 ✅
```

**Cálculo de Portfolio Stats:**
```python
# VP da carteira = soma de todos Valor_reaj
vp_carteira = sum(p['Valor_reaj'] for p in parcelas)

# Prazo médio ponderado
prazo_medio = sum(p['Valor_reaj'] * dias_ate_venc(p) for p in parcelas) / vp_carteira
```

---

## 4. Mapeamento Completo UAU → Starke

### 4.1 CashOut (Saídas) - ✅ DEFINIDO

| Campo Starke | Campo UAU | Transformação |
|--------------|-----------|---------------|
| **empreendimento_id** | **Empresa** | Agrupar todas as Obras por Empresa |
| ref_month | DtaRefAno + DtaRefMes | `f"{DtaRefAno}-{DtaRefMes:02d}"` |
| categoria | Composicao ou Item | Usar Composicao |
| budget | Total (Status="Projetado") | Somar por categoria/mês/empresa |
| actual | Total (Status="Pago") | Somar por categoria/mês/empresa |
| origin_id | Empresa+Obra+Contrato+Item+Mês | Chave única |
| origem | - | "uau" |

### 4.2 CashIn (Entradas) - ✅ DEFINIDO

#### Forecast (Parcelas a Receber)
| Campo Starke | Campo UAU | Transformação |
|--------------|-----------|---------------|
| **empreendimento_id** | **Empresa_prc** | Agrupar por Empresa |
| ref_month | Data_Prc | `Data_Prc[:7]` (YYYY-MM) |
| category | Tipo_Prc | "E"=Entrada, mapear outros |
| forecast | Valor_Prc | Valor original da parcela |
| actual | - | 0 |
| record_type | - | "forecast" |
| origin_id | - | `f"uau_{Emp}_{Obra}_{Venda}_{Parc}_forecast"` |
| origem | - | "uau" |

#### Actual (Parcelas Recebidas)
| Campo Starke | Campo UAU | Transformação |
|--------------|-----------|---------------|
| **empreendimento_id** | **Empresa_rec** | Agrupar por Empresa |
| ref_month | Data_Rec | `Data_Rec[:7]` (YYYY-MM do pagamento) |
| category | ParcType_Rec | "E"=Entrada, mapear outros |
| forecast | - | 0 |
| actual | ValorConf_Rec | Valor confirmado/recebido |
| record_type | - | "actual" |
| origin_id | - | `f"uau_{Emp}_{Obra}_{Venda}_{Parc}_actual"` |
| origem | - | "uau" |

### 4.3 Portfolio Stats - ✅ DEFINIDO

| Campo Starke | Campo UAU | Transformação |
|--------------|-----------|---------------|
| **empreendimento_id** | **Empresa_reaj** | Agrupar por Empresa |
| vp | Valor_reaj | `sum(Valor_reaj)` por Empresa |
| valor_original | Principal_reaj | `sum(Principal_reaj)` |
| juros_acumulados | Juros_reaj | `sum(Juros_reaj)` |
| multa_acumulada | Multa_reaj | `sum(Multa_reaj)` |
| prazo_medio | DataVenc_reaj | Calcular média ponderada |

### 4.4 Inadimplência - ✅ DEFINIDO

| Campo Starke | Campo UAU | Transformação |
|--------------|-----------|---------------|
| faixa_atraso | Data_Prc | `(hoje - Data_Prc).days` |
| valor | Valor_Prc | Valor da parcela vencida |
| status | Status_Prc | 0 = em aberto |

---

## 5. Resumo de Status dos Endpoints

| Endpoint | Status | Dados |
|----------|--------|-------|
| Empresa/ObterEmpresasAtivas | ✅ OK | 140 empresas |
| Obras/ObterObrasAtivas | ✅ OK | 282 obras |
| Planejamento/ConsultarDesembolsoPlanejamento | ✅ OK | CashOut completo |
| Venda/RetornaChavesVendasPorPeriodo | ✅ OK | Lista de vendas |
| Venda/BuscarParcelasAReceber | ✅ OK | CashIn forecast + Inadimplência |
| Venda/BuscarParcelasRecebidas | ✅ OK | CashIn actual |
| **Venda/ConsultarParcelasDaVenda** | ✅ OK | **Portfolio Stats (VP)** |

---

## 6. Pontos de Atenção

### 6.1 ⚠️ Performance - Muitas Chamadas para CashIn

**Problema:**
```
CashOut: 1 chamada por Empresa+Obra (retorna tudo) ✅ OK

CashIn:
  1. Listar vendas (RetornaChavesVendasPorPeriodo)
  2. Para CADA venda: BuscarParcelasAReceber
  3. Para CADA venda: BuscarParcelasRecebidas

  → Se tiver 100 vendas = 200+ chamadas à API ❌
```

**Impacto:** Sincronização pode ser lenta para empreendimentos com muitas vendas.

**Mitigação possível:**
- Paralelizar chamadas
- Cache de dados
- Sincronização incremental (só vendas novas/alteradas)

**Pergunta para o cliente:** Existe endpoint que retorna todas as parcelas de uma Empresa de uma vez?

---

### 6.2 ❓ Categorização Não Definida

| Dado | Campo UAU | Exemplo | Mapeamento Starke | Status |
|------|-----------|---------|-------------------|--------|
| Tipo parcela (CashIn) | `Tipo_Prc` | "E" | ATIVOS? RECUPERACOES? OUTRAS? | ❓ Pendente |
| Categoria saída (CashOut) | `Composicao` | "C0023" | OPEX? CAPEX? | ❓ Pendente |
| Categoria saída (CashOut) | `Item` | "00.01.01" | ? | ❓ Pendente |

**Perguntas para o cliente:**
- [ ] Quais são todos os valores possíveis de `Tipo_Prc`?
- [ ] Existe tabela de mapeamento de Composição/Item para categorias?
- [ ] Como classificar despesas (OPEX, CAPEX, etc.)?

---

### 6.3 ❓ Status_Prc - Significado Não Confirmado

```
Status_Prc = 0 → Em aberto? Pago?
Status_Prc = 1 → ?
Outros valores → ?
```

**Impacto:** Afeta cálculo de inadimplência (precisamos saber quais parcelas estão em aberto).

**Pergunta para o cliente:** Quais são os valores possíveis e seus significados?

---

### 6.4 📋 Schema no Primeiro Registro

Todas as respostas da API retornam o **schema como primeiro item** do array:

```json
[
  {"Campo": "System.Int32, mscorlib, Version=4.0.0.0, ..."},  // ← Schema (ignorar)
  {"Campo": 123, ...},  // ← Dados reais
  {"Campo": 456, ...}
]
```

**Tratamento necessário no código:**
```python
def processar_resposta(response):
    if len(response) > 1:
        return response[1:]  # Ignorar primeiro registro (schema)
    return []
```

---

### 6.5 📅 Dados Históricos

Não foi testado se a API retorna dados de anos anteriores (2020, 2021, etc.).

**Validar:** Fazer teste com período mais antigo para confirmar disponibilidade de histórico.

---

### 6.6 Resumo das Perguntas para o Cliente

| # | Pergunta | Impacto |
|---|----------|---------|
| 1 | Existe endpoint para buscar todas as parcelas de uma Empresa de uma vez? | Performance |
| 2 | Quais são os valores possíveis de `Tipo_Prc` (tipo de parcela)? | Categorização CashIn |
| 3 | Existe mapeamento de `Composicao`/`Item` para categorias (OPEX/CAPEX)? | Categorização CashOut |
| 4 | Quais são os valores de `Status_Prc` e seus significados? | Inadimplência |
| 5 | Dados históricos estão disponíveis (2020, 2021)? | Relatórios passados |

---

## 7. Próximos Passos

### Fase 1: Implementação (Pronto para iniciar)
1. ✅ Análise completa dos endpoints
2. 🔲 Criar `uau_api_client.py`
3. 🔲 Criar `uau_transformer.py`
4. 🔲 Adicionar campo `origem` nas tabelas (migration)
5. 🔲 Implementar sincronização CashOut
6. 🔲 Implementar sincronização CashIn
7. 🔲 Implementar cálculo Portfolio Stats
8. 🔲 Implementar cálculo Inadimplência

### Fase 2: Testes
1. 🔲 Testar sincronização com obra JVA16
2. 🔲 Validar relatório de fluxo de caixa
3. 🔲 Comparar com dados existentes

---

## 8. Diferenças UAU vs Mega

| Aspecto | Mega | UAU |
|---------|------|-----|
| Empreendimento | `empreendimento_id` (numérico) | **Empresa** (código int) |
| Sub-nível | - | Obra (fase do empreendimento) |
| CashOut | FaturaPagar/Saldo (só forecast) | ConsultarDesembolsoPlanejamento **(forecast + realizado!)** |
| CashIn Forecast | Parcelas (data_vencimento) | BuscarParcelasAReceber |
| CashIn Actual | Parcelas (data_baixa) | BuscarParcelasRecebidas |
| **Portfolio Stats** | Calcular VP manualmente | **ConsultarParcelasDaVenda (VP automático!)** |
| Autenticação | Bearer token simples | **Token + Token Integração** |
| IDs | Numéricos | Empresa = int, Obra = string |

### Vantagens UAU
- **CashOut completo:** Endpoint de desembolso retorna Projetado, A Pagar e Pago
- **VP automático:** API calcula valor presente com juros/multa/correção
- No Mega, só temos forecast de contas a pagar, não os pagamentos reais

> **Nota:** O sistema Starke está sendo padronizado para usar apenas "Empreendimento" como nível de agregação principal. No UAU, a **Empresa** equivale ao Empreendimento.

---

## 9. Observações Técnicas

### Formato de Data
- **Request período:** `"MM/YYYY"` (ex: "01/2024")
- **Request datetime:** `"YYYY-MM-DDTHH:MM:SS"` (ex: "2021-04-30T00:00:00")
- **Response:** `"YYYY-MM-DDTHH:MM:SS"` (ISO 8601)

### Retorno de Schema
O primeiro registro do array sempre contém o schema (tipos dos campos):
```json
{
  "Campo": "System.Int32, mscorlib, Version=4.0.0.0, ..."
}
```
**Tratamento:** Ignorar o primeiro registro do array ao processar.

### Tratamento de Erros
- **401 Unauthorized:** Token inválido ou expirado
- **400 Bad Request:** Parâmetros inválidos (mensagem descritiva)
- **200 com lista vazia:** Sem dados para os filtros
- **200 com apenas schema:** Sem permissão ou sem dados

### Filtros Principais
A maioria dos endpoints usa **Empresa + Obra** como filtro base:

| Recurso | Filtro Mínimo |
|---------|---------------|
| Empresas | Nenhum |
| Obras | Nenhum |
| Contratos/Vendas | `Empresa + Obra` + Período |
| Parcelas | `Empresa + Obra + NumVenda` |
| Desembolso | `Empresa + Obra` + Período |

---

## 10. Arquivos do Projeto

| Arquivo | Descrição |
|---------|-----------|
| `scripts/test_uau_api.py` | Script de testes da API |
| `docs/uau/analise_api_uau.md` | Esta documentação |
| `docs/uau/exemplos_retorno_api_uau.md` | Exemplos de retorno JSON |
| `docs/uau/retorno_BuscarParcelasAReceber` | Retorno completo do endpoint |
| `docs/uau/retorno_BuscarParcelasRecebidas` | Retorno completo do endpoint |
| `docs/uau/retorno_ConsultarParcelasDaVenda.json` | Retorno com VP calculado |
| `docs/swagger/mega/uauAPI_1.0.json` | Swagger da API (2.8MB) |

---

## 11. Resumo Final - Dados Disponíveis

| Componente do Relatório | Endpoint | Campo Principal | Status |
|------------------------|----------|-----------------|--------|
| **CashIn Forecast** | BuscarParcelasAReceber | `Valor_Prc` | ✅ |
| **CashIn Actual** | BuscarParcelasRecebidas | `ValorConf_Rec` | ✅ |
| **CashOut Forecast** | ConsultarDesembolsoPlanejamento | `Total` (Projetado) | ✅ |
| **CashOut Actual** | ConsultarDesembolsoPlanejamento | `Total` (Pago) | ✅ |
| **VP Carteira** | ConsultarParcelasDaVenda | `Valor_reaj` | ✅ |
| **Inadimplência** | BuscarParcelasAReceber | `Data_Prc` vs hoje | ✅ |

**✅ TODOS OS DADOS NECESSÁRIOS ESTÃO DISPONÍVEIS!**

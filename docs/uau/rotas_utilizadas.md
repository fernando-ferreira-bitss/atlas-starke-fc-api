# Rotas Utilizadas da API UAU

Este documento descreve as rotas da API UAU (Globaltec/Senior) utilizadas no sistema Starke.

## Base URL

```
https://gamma-api.seniorcloud.com.br:50801/uauAPI/api/v1.0
```

## Autenticacao

A API UAU usa autenticacao de dois tokens:
- **X-INTEGRATION-Authorization**: Token fixo de integracao
- **Authorization**: Token de sessao obtido via login

---

## 1. Autenticacao

### POST /Autenticador/AutenticarUsuario

Autentica o usuario e retorna o token de sessao.

**Headers:**
```
X-INTEGRATION-Authorization: {TOKEN_INTEGRACAO}
Content-Type: application/json
```

**Request Body:**
```json
{
    "login": "usuario",
    "senha": "senha123"
}
```

**Response:** Token de sessao (string)

**Curl:**
```bash
curl -X POST "https://gamma-api.seniorcloud.com.br:50801/uauAPI/api/v1.0/Autenticador/AutenticarUsuario" \
  -H "X-INTEGRATION-Authorization: $INT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"login": "usuario", "senha": "senha123"}'
```

---

## 2. Empresas

### POST /Empresa/ObterEmpresasAtivas

Retorna lista de empresas ativas. No contexto Starke, Empresa UAU = Empreendimento (Development).

**Headers:**
```
X-INTEGRATION-Authorization: {TOKEN_INTEGRACAO}
Authorization: {TOKEN_SESSAO}
Content-Type: application/json
```

**Request Body:** `{}` (vazio)

**Response:**
```json
[
    {"Codigo_emp": "System.Int32, ...", "Desc_emp": "System.String, ..."},
    {"Codigo_emp": 4, "Desc_emp": "JVF SERVICOS EIRELI - ME", "CGC_emp": "12.345.678/0001-99"},
    {"Codigo_emp": 93, "Desc_emp": "JV NEGOCIOS LTDA", "CGC_emp": "98.765.432/0001-11"}
]
```

**Nota:** O primeiro registro e sempre o schema (ignorar).

**Curl:**
```bash
curl -X POST "https://gamma-api.seniorcloud.com.br:50801/uauAPI/api/v1.0/Empresa/ObterEmpresasAtivas" \
  -H "X-INTEGRATION-Authorization: $INT_TOKEN" \
  -H "Authorization: $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 3. Obras

### POST /Obras/ObterObrasAtivas

Retorna lista de obras ativas. Obra = Fase do empreendimento.

**Headers:**
```
X-INTEGRATION-Authorization: {TOKEN_INTEGRACAO}
Authorization: {TOKEN_SESSAO}
Content-Type: application/json
```

**Request Body:** `{}` (vazio)

**Response:**
```json
[
    {"Cod_obr": "System.String, ...", "Empresa_obr": "System.Int32, ..."},
    {"Cod_obr": "JVL00", "Empresa_obr": 4, "Descr_obr": "OBRA PRINCIPAL", "Status_obr": 0},
    {"Cod_obr": "JVA16", "Empresa_obr": 93, "Descr_obr": "FASE 16", "Status_obr": 0}
]
```

**Curl:**
```bash
curl -X POST "https://gamma-api.seniorcloud.com.br:50801/uauAPI/api/v1.0/Obras/ObterObrasAtivas" \
  -H "X-INTEGRATION-Authorization: $INT_TOKEN" \
  -H "Authorization: $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 4. CashOut - Desembolsos

### POST /Planejamento/ConsultarDesembolsoPlanejamento

Retorna dados de desembolso (contas a pagar). Usado para CashOut (orcamento e realizado).

**Headers:**
```
X-INTEGRATION-Authorization: {TOKEN_INTEGRACAO}
Authorization: {TOKEN_SESSAO}
Content-Type: application/json
```

**Request Body:**
```json
{
    "Empresa": 4,
    "Obra": "JVL00",
    "MesInicial": "01/2024",
    "MesFinal": "12/2024"
}
```

**Response:**
```json
[
    {"Status": "System.String, ...", "Empresa": "System.Int32, ..."},
    {
        "Status": "Projetado",
        "Empresa": 4,
        "Obra": "JVL00",
        "Contrato": "CT001",
        "Produto": "PROD01",
        "Composicao": "C0023",
        "Item": "I001",
        "Insumo": "A00159",
        "DtaRef": "2024-07-30T00:00:00",
        "DtaRefMes": 7,
        "DtaRefAno": 2024,
        "Total": 20110.14,
        "Acrescimo": 0,
        "Desconto": 0,
        "TotalLiq": 20110.14,
        "TotalBruto": 20110.14
    },
    {
        "Status": "Pago",
        "Empresa": 4,
        "Obra": "JVL00",
        "Total": 173538.05
    }
]
```

**Campos importantes:**
- `Status`: "Projetado" | "Pagar" | "Pago"
  - Projetado + Pagar = Orcamento
  - Pago = Realizado
- `Composicao`: Usado como categoria do CashOut
- `DtaRef`: Data de referencia para o mes

**Curl:**
```bash
curl -X POST "https://gamma-api.seniorcloud.com.br:50801/uauAPI/api/v1.0/Planejamento/ConsultarDesembolsoPlanejamento" \
  -H "X-INTEGRATION-Authorization: $INT_TOKEN" \
  -H "Authorization: $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Empresa": 4,
    "Obra": "JVL00",
    "MesInicial": "01/2024",
    "MesFinal": "12/2024"
  }'
```

---

## 5. CashIn - Vendas

### POST /Venda/RetornaChavesVendasPorPeriodo

Retorna as chaves de vendas em um periodo.

**Headers:**
```
X-INTEGRATION-Authorization: {TOKEN_INTEGRACAO}
Authorization: {TOKEN_SESSAO}
Content-Type: application/json
```

**Request Body:**
```json
{
    "data_inicio": "2000-01-01T00:00:00",
    "data_fim": "2024-12-31T00:00:00",
    "listaEmpresaObra": [
        {"codigoEmpresa": 4, "codigoObra": "JVL00"}
    ],
    "statusVenda": null
}
```

**Response:** String com chaves separadas por virgula
```
"00004-JVL00/00001,00004-JVL00/00002,00004-JVL00/00003"
```

**Formato da chave:** `{EMPRESA}-{OBRA}/{NUM_VENDA}`

**Curl:**
```bash
curl -X POST "https://gamma-api.seniorcloud.com.br:50801/uauAPI/api/v1.0/Venda/RetornaChavesVendasPorPeriodo" \
  -H "X-INTEGRATION-Authorization: $INT_TOKEN" \
  -H "Authorization: $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data_inicio": "2000-01-01T00:00:00",
    "data_fim": "2024-12-31T00:00:00",
    "listaEmpresaObra": [{"codigoEmpresa": 4, "codigoObra": "JVL00"}]
  }'
```

---

## 6. CashIn - Parcelas a Receber

### POST /Venda/BuscarParcelasAReceber

Retorna parcelas a receber (previsao de entradas). Usado para CashIn forecast e calculo de inadimplencia.

**Headers:**
```
X-INTEGRATION-Authorization: {TOKEN_INTEGRACAO}
Authorization: {TOKEN_SESSAO}
Content-Type: application/json
```

**Request Body:**
```json
{
    "empresa": 4,
    "obra": "JVL00",
    "num_ven": 123
}
```

**Response:**
```json
[
    {"Empresa_prc": "System.Int32, ...", "Obra_Prc": "System.String, ..."},
    {
        "Empresa_prc": 4,
        "Obra_Prc": "JVL00",
        "NumVend_prc": 123,
        "NumParc_Prc": 1,
        "Data_Prc": "2024-03-28T00:00:00",
        "Valor_Prc": 4194.00,
        "Status_Prc": 0,
        "Tipo_Prc": "M",
        "Cliente_Prc": 1234,
        "nome_pes": "CLIENTE EXEMPLO"
    }
]
```

**Campos importantes:**
- `Data_Prc`: Data de vencimento (determina mes de referencia)
- `Valor_Prc`: Valor previsto (forecast)
- `Status_Prc`: 0 = Em aberto
- `Tipo_Prc`: Tipo da parcela (usado como categoria)

**Curl:**
```bash
curl -X POST "https://gamma-api.seniorcloud.com.br:50801/uauAPI/api/v1.0/Venda/BuscarParcelasAReceber" \
  -H "X-INTEGRATION-Authorization: $INT_TOKEN" \
  -H "Authorization: $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "empresa": 4,
    "obra": "JVL00",
    "num_ven": 123
  }'
```

---

## 7. CashIn - Parcelas Recebidas

### POST /Venda/BuscarParcelasRecebidas

Retorna parcelas ja recebidas (entradas realizadas). Usado para CashIn actual.

**Headers:**
```
X-INTEGRATION-Authorization: {TOKEN_INTEGRACAO}
Authorization: {TOKEN_SESSAO}
Content-Type: application/json
```

**Request Body:**
```json
{
    "empresa": 4,
    "obra": "JVL00",
    "num_ven": 123
}
```

**Response:** (estrutura com wrapper)
```json
[
    {
        "Recebidas": [
            {"Empresa_rec": "System.Int32, ...", "Obra_Rec": "System.String, ..."},
            {
                "Empresa_rec": 4,
                "Obra_Rec": "JVL00",
                "NumVend_Rec": 123,
                "NumParc_Rec": 1,
                "Data_Rec": "2024-03-27T00:00:00",
                "ValorConf_Rec": 4194.00,
                "Status_Rec": 1,
                "ParcType_Rec": "M"
            }
        ]
    }
]
```

**Campos importantes:**
- `Data_Rec`: Data do recebimento (determina mes de referencia)
- `ValorConf_Rec`: Valor recebido (actual)
- `Status_Rec`: 1 = Confirmado
- `ParcType_Rec`: Tipo da parcela (usado como categoria)

**Curl:**
```bash
curl -X POST "https://gamma-api.seniorcloud.com.br:50801/uauAPI/api/v1.0/Venda/BuscarParcelasRecebidas" \
  -H "X-INTEGRATION-Authorization: $INT_TOKEN" \
  -H "Authorization: $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "empresa": 4,
    "obra": "JVL00",
    "num_ven": 123
  }'
```

---

## 8. CashIn - Parcelas com VP (Valor Presente)

### POST /Venda/ConsultarParcelasDaVenda

Retorna parcelas com calculo automatico de Valor Presente (juros, multa, correcao).

**Headers:**
```
X-INTEGRATION-Authorization: {TOKEN_INTEGRACAO}
Authorization: {TOKEN_SESSAO}
Content-Type: application/json
```

**Request Body:**
```json
{
    "empresa": 4,
    "obra": "JVL00",
    "num_venda": 123,
    "data_calculo": "2024-12-31T00:00:00",
    "boleto_antecipado": false
}
```

**Response:**
```json
[
    {"Principal_reaj": "System.Decimal, ...", "Valor_reaj": "System.Decimal, ..."},
    {
        "Empresa_reaj": 4,
        "Obra_reaj": "JVL00",
        "NumParc_reaj": 1,
        "Principal_reaj": 4194.00,
        "Valor_reaj": 4523.76,
        "Juros_reaj": 210.45,
        "Multa_reaj": 83.88,
        "Correcao_reaj": 35.43,
        "DataVenc_reaj": "2024-03-28T00:00:00"
    }
]
```

**Campos importantes:**
- `Principal_reaj`: Valor original da parcela
- `Valor_reaj`: Valor Presente (VP) = Principal + Juros + Multa + Correcao
- `Juros_reaj`: Juros calculados ate data_calculo
- `Multa_reaj`: Multa por atraso
- `Correcao_reaj`: Correcao monetaria

**Curl:**
```bash
curl -X POST "https://gamma-api.seniorcloud.com.br:50801/uauAPI/api/v1.0/Venda/ConsultarParcelasDaVenda" \
  -H "X-INTEGRATION-Authorization: $INT_TOKEN" \
  -H "Authorization: $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "empresa": 4,
    "obra": "JVL00",
    "num_venda": 123,
    "data_calculo": "2024-12-31T00:00:00",
    "boleto_antecipado": false
  }'
```

---

## Observacoes Importantes

### 1. Schema como Primeiro Registro

A API UAU retorna o **schema** como primeiro registro em todas as respostas de array. O schema tem valores tipo `"System.Int32, mscorlib, ..."` e deve ser **filtrado/ignorado**.

### 2. Estrutura de Resposta de Parcelas Recebidas

O endpoint `/Venda/BuscarParcelasRecebidas` tem estrutura diferente com wrapper:
```json
[{"Recebidas": [schema, data1, data2, ...]}]
```

### 3. Formato de Datas

- Request: `"2024-01-01T00:00:00"` ou `"01/2024"` (mes/ano para desembolsos)
- Response: `"2024-01-01T00:00:00"`

### 4. Status de Desembolso (CashOut)

O status representa o ciclo de vida:
```
Projetado -> Pagar -> Pago
```

Para agregacao:
- **Orcamento**: Status = "Projetado" + "Pagar"
- **Realizado**: Status = "Pago"

### 5. Variaveis de Ambiente

```bash
UAU_API_URL=https://gamma-api.seniorcloud.com.br:50801/uauAPI/api/v1.0
UAU_INTEGRATION_TOKEN=<token_de_integracao>
UAU_USERNAME=<usuario>
UAU_PASSWORD=<senha>
UAU_TIMEOUT=60
UAU_MAX_RETRIES=3
UAU_MAX_WORKERS=5
```

---

## Mapeamento UAU -> Starke

| UAU | Starke |
|-----|--------|
| Empresa | Filial (Development) |
| Obra | Fase do empreendimento |
| Desembolso | CashOut (saidas_caixa) |
| Parcela a Receber | CashIn forecast |
| Parcela Recebida | CashIn actual |
| Composicao | Categoria |

---

**Ultima Atualizacao:** 2026-01-05

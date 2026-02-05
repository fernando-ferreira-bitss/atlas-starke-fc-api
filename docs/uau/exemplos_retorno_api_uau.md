# Exemplos de Retorno da API UAU

**Data:** 26/12/2025
**Objetivo:** Documentar estrutura de dados para integração Starke
**Ambiente:** `https://gamma-api.seniorcloud.com.br:50801/uauAPI/api/v1.0`

---

## 1. Empresas

**Endpoint:** `POST /Empresa/ObterEmpresasAtivas`

```json
[
  {
    "Codigo_emp": 1,
    "Desc_emp": "S&J INCORPORADORA LTDA",
    "CGC_emp": "10144917000113",
    "IE_emp": "",
    "InscrMunic_emp": "",
    "Endereco_emp": "RUA 86 N. 386 QD. F-33 LT. 30",
    "Fone_emp": "32132288"
  },
  {
    "Codigo_emp": 2,
    "Desc_emp": "JVF NEGOCIOS IMOBILIARIOS LTDA",
    "CGC_emp": "10866771000110",
    "IE_emp": "105958883",
    "InscrMunic_emp": "2664461",
    "Endereco_emp": "AVENIDA T 15 QD 592 LT 10 ESQUINA COM A RUA C-264",
    "Fone_emp": "32132288"
  },
  {
    "Codigo_emp": 93,
    "Desc_emp": "JVA EMPREENDIMENTOS IMOBILIARIOS LTDA",
    "CGC_emp": "20781116000112",
    "IE_emp": "",
    "InscrMunic_emp": "",
    "Endereco_emp": "...",
    "Fone_emp": ""
  }
]
```

**Total:** 140 empresas cadastradas

---

## 2. Obras (Empreendimentos)

**Endpoint:** `POST /Obras/ObterObrasAtivas`

```json
[
  {
    "Cod_obr": "JVL00",
    "Empresa_obr": 2,
    "Descr_obr": "ADMINISTRAÇÃO GOIANIA",
    "Status_obr": 0,
    "Ender_obr": "RUA 82 - Nº 547 - PRAÇA CIVICA",
    "Fone_obr": "3213-2288",
    "DtIni_obr": "2014-03-01T00:00:00",
    "Dtfim_obr": "2035-12-31T00:00:00",
    "TipoObra_obr": 3,
    "CEI_obr": null
  },
  {
    "Cod_obr": "JVL29",
    "Empresa_obr": 2,
    "Descr_obr": "SETOR SOLANGE FUNDO ATIVO REAL (ENTRADA) - 1ª ETAPA",
    "Status_obr": 0,
    "DtIni_obr": "2017-01-01T00:00:00",
    "Dtfim_obr": "2050-07-31T00:00:00",
    "TipoObra_obr": 3
  },
  {
    "Cod_obr": "JVA16",
    "Empresa_obr": 93,
    "Descr_obr": "RESIDENCIAL ESMERALDA DOS TAPAJOS",
    "Status_obr": 0,
    "DtIni_obr": "2021-02-01T00:00:00",
    "TipoObra_obr": 3
  }
]
```

**Total:** 282 obras ativas (120 imobiliárias + 162 financeiras)

---

## 3. Contas a Pagar (Desembolso) - ✅ FUNCIONANDO

**Endpoint:** `POST /Planejamento/ConsultarDesembolsoPlanejamento`

**Request:**
```json
{
  "Empresa": 2,
  "Obra": "JVL00",
  "MesInicial": "01/2024",
  "MesFinal": "12/2024"
}
```

### 3.1 Status "Projetado" (Orçamento/Forecast)
```json
{
  "Status": "Projetado",
  "Empresa": 2,
  "Obra": "JVL00",
  "Contrato": 1,
  "Produto": 999,
  "Composicao": "C0023",
  "Item": "00.01.01",
  "Insumo": "A00158",
  "DtaRef": "2024-01-01T00:00:00",
  "DtaRefMes": 1,
  "DtaRefAno": 2024,
  "Total": 80100.00,
  "Acrescimo": 0.0,
  "Desconto": 0.0,
  "TotalLiq": 0.0,
  "TotalBruto": 0.0
}
```

### 3.2 Status "Pagar" (Pendente de Pagamento)
```json
{
  "Status": "Pagar",
  "Empresa": 2,
  "Obra": "JVL00",
  "Contrato": 1,
  "Produto": 300,
  "Composicao": "0016",
  "Item": "01.00.01",
  "Insumo": "0026",
  "DtaRef": "2024-01-02T00:00:00",
  "DtaRefMes": 1,
  "DtaRefAno": 2024,
  "Total": 4103.40,
  "Acrescimo": 0.0,
  "Desconto": 61.55,
  "TotalLiq": 4041.85,
  "TotalBruto": 4103.40
}
```

### 3.3 Status "Pago" (Realizado)
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

**Resumo Obra JVL00 (2024):**
- Total de registros: 1074
- Projetado: 119 registros
- A Pagar: 237 registros
- Pago: 718 registros

---

## 4. Contas a Receber (Vendas/Parcelas) - ⚠️ PRECISA PERMISSÃO

### 4.1 Vendas Encontradas

**Endpoint:** `POST /Venda/RetornaChavesVendasPorPeriodo`

**Request:**
```json
{
  "data_inicio": "2020-01-01T00:00:00",
  "data_fim": "2025-12-31T00:00:00",
  "statusVenda": "0",
  "listaEmpresaObra": [
    {"codigoEmpresa": 93, "codigoObra": "JVA16"}
  ]
}
```

**Response (lista de vendas):**
```
00093-JVA16/00006, 00093-JVA16/00017, 00093-JVA16/00018,
00093-JVA16/00019, 00093-JVA16/00021, 00093-JVA16/00022,
00093-JVA16/00024, 00093-JVA16/00034, 00093-JVA16/00036,
00093-JVA16/00047, 00093-JVA16/00049, 00093-JVA16/00053,
... (30+ vendas encontradas)
```

**Formato:** `Empresa-Obra/NumeroVenda`

### 4.2 Problema: Parcelas Retornam Schema Vazio

**Endpoints testados:**
- `POST /Venda/BuscarParcelasAReceber`
- `POST /Venda/BuscarParcelasRecebidas`
- `POST /ExtratoDoCliente/ConsultarDadosDemonstrativoPagtoCliente`

**Request exemplo:**
```json
{
  "empresa": 93,
  "obra": "JVA16",
  "num_ven": 6
}
```

**Response (schema sem dados):**
```json
[
  {
    "Tipo": "System.String, mscorlib, Version=4.0.0.0...",
    "NumParc": "System.Int32, mscorlib, Version=4.0.0.0...",
    "TotalParcela": "System.Double, mscorlib, Version=4.0.0.0...",
    "DataVencimento": "System.DateTime, mscorlib, Version=4.0.0.0...",
    "ValorParcela": "System.Double, mscorlib, Version=4.0.0.0...",
    "DataRecebimento": "System.DateTime, mscorlib, Version=4.0.0.0..."
  }
]
```

> **Nota:** O endpoint `RetornaChavesVendasPorPeriodo` lista as vendas existentes, mas os endpoints de parcelas retornam apenas o schema (tipos dos campos) em vez dos dados reais.

---

## 5. Solicitação ao Cliente

### Para completar a integração de Contas a Receber (CashIn), precisamos:

1. **Permissão de leitura de parcelas para o usuário STARKE**
   - Atualmente conseguimos listar vendas, mas não ler as parcelas

2. **Informar uma obra com vendas ativas que o usuário STARKE tenha acesso completo**
   - Obras candidatas encontradas:
     - Empresa 93, Obra JVA16 (30+ vendas)
     - Empresa 27, Obra RFLOR
     - Empresa 64, Obras 1532/1533

3. **Ou fornecer um CPF de cliente para testar o endpoint:**
   ```
   POST /Recebiveis/ParcelasECobrancasDoCliente
   Body: {"Cpf": "12345678900", "ValorReajustado": false}
   ```

---

## 6. Campos Esperados para Contas a Receber

Com base no schema retornado, os campos das parcelas são:

| Campo | Tipo | Descrição Esperada |
|-------|------|-------------------|
| Tipo | string | Tipo da parcela |
| NumParc | int | Número da parcela |
| TotalParcela | double | Valor total |
| DataVencimento | datetime | Data de vencimento |
| ValorParcela | double | Valor original |
| DataRecebimento | datetime | Data do pagamento |
| Principal | double | Valor principal |
| Juros | double | Juros |
| Correcao | double | Correção monetária |
| Multa | double | Multa |
| JurosAtraso | double | Juros por atraso |
| Acrescimo | double | Acréscimos |
| Desconto | double | Descontos |

---

## 7. Resumo

| Funcionalidade | Status | Observação |
|---------------|--------|------------|
| Empresas | ✅ OK | 140 empresas |
| Obras | ✅ OK | 282 obras |
| Contas a Pagar (CashOut) | ✅ OK | Projetado + Pagar + Pago |
| Contas a Receber (CashIn) | ⚠️ Pendente | Precisa permissão |

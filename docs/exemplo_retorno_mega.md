# Mega API - Referência de Retornos

Documentação dos retornos da API Mega para integração com o sistema Starke.

## Índice

- [Autenticação](#autenticação)
- [Empreendimentos](#empreendimentos)
- [Contratos](#contratos)
- [Parcelas](#parcelas)
- [Contas a Pagar](#contas-a-pagar)

---

## Autenticação

### POST /api/Auth/SignIn

Endpoint de autenticação que retorna tokens de acesso e refresh.

**Resposta:**

```json
{
	"expirationToken": "2025-10-31T17:36:34.6945524-03:00",
	"accessToken": "eyJhbGciOiJodHRwOi8vd3d3LnczLm9yZy8yMDAxLzA0L3htbGRzaWctbW9yZSNobWFjLXNoYTI1NiIsInR5cCI6IkpXVCJ9...",
	"expirationRefreshToken": "2025-10-31T19:36:34.6945524-03:00",
	"refreshToken": "XEi0lKcqpO9m5gSGAOa3AQFzmNCtw2atDUMbY4z9AE"
}
```

**Campos:**
- `accessToken`: Token JWT usado nas requisições (Bearer token)
- `expirationToken`: Data/hora de expiração do accessToken
- `refreshToken`: Token para renovar o accessToken
- `expirationRefreshToken`: Data/hora de expiração do refreshToken

**Uso:** O `accessToken` deve ser incluído no header `Authorization: Bearer {token}` em todas as requisições.

---

## Empreendimentos

### GET /api/globalestruturas/Empreendimentos

Lista todos os empreendimentos (developments) disponíveis.

**Resposta:** Array de objetos de empreendimento

```json
[
	{
		"codigo": 320.0,
		"codigoOrganizacao": 99.0,
		"codigoFilial": 100.0,
		"nomeFilial": "Filial Teste",
		"fantasiaFilial": "FILIAL TESTE",
		"cnpjFilial": "100               ",
		"codigo_externo": "01",
		"nome": "SIMULAÇÃO",
		"nomeReal": null,
		"tipoImovel": "VAZIO",
		"disponivelPortalCliente": "N",
		"disponivelHomepay": "N",
		"inicioObra": "2016/09/21",
		"fimObra": "2016/09/21",
		"habite": "0001/01/01",
		"previsaoHabite": "0001/01/01",
		"averbacao": "0001/01/01",
		"instalacaoCondominio": "0001/01/01",
		"cadastro": "2016/09/21",
		"lancamento": "2016/09/21",
		"vencimentoDivida": "0001/01/01",
		"conclusaoPastaMae": "0001/01/01",
		"entregaAreaComum": "0001/01/01",
		"areaTerreno": 0.0,
		"areaEquivalente": 0.0,
		"areaPrivada": 0.0,
		"areaTotal": 0.0,
		"areaConstrucaoPrefeitura": 0.0,
		"areaConstrucaoEquivalente": 0.0,
		"areaConstrucaoTotal": 0.0,
		"codigoCentroCustoComercial": 17.0,
		"codigoPadraoCentroCustoCliente": 0.0,
		"codigoCentroCustoCliente": 0.0,
		"dataCriacao": "2016/09/21",
		"dataAlteracao": "2016/09/21",
		"endereco": {
			"cep": "89.248-000",
			"pais": "BRA",
			"estado": "SC",
			"municipio": "GARUVA",
			"bairro": "SAO JOAO ABAIXO",
			"tipoLogradouro": "R",
			"logradouro": "SAO JOAO ABAIXO",
			"numero": null,
			"complemento": null,
			"referencia": null
		},
		"centroCusto": {
			"padrao": 1,
			"identificador": "1",
			"reduzido": 21,
			"extenso": null,
			"descricao": null,
			"global": "",
			"usuarios": null,
			"id": "McO4McO4MjE"
		},
		"projeto": {
			"padrao": 1,
			"identificador": "9",
			"reduzido": 36,
			"extenso": null,
			"descricao": null,
			"global": "",
			"usuarios": null,
			"id": "McO4OcO4MzY"
		},
		"tabOrganizacao": 53.0,
		"padraoOrganizacao": 1.0,
		"expand": "projeto,centrocusto",
		"id": "NTPDuDHDuDk5w7gzMjA"
	}
]
```

**Campos Importantes:**
- `codigo`: ID numérico do empreendimento (usado para buscar contratos)
- `nome`: Nome do empreendimento
- `codigoFilial`: Código da filial
- `nomeFilial`: Nome da filial
- `tipoImovel`: Tipo do imóvel (URBANO, VAZIO, etc)
- `disponivelPortalCliente`: Se está disponível no portal do cliente ("S"/"N")
- `centroCusto.reduzido`: ID do centro de custo
- `projeto.reduzido`: ID do projeto
- `endereco`: Objeto com informações de endereço completo

**Uso:** O campo `codigo` deve ser convertido para `int` e usado no endpoint de contratos.

---

## Contratos

### GET /api/Carteira/DadosContrato/IdEmpreendimento={id}

Retorna todos os contratos de um empreendimento específico usando o ID numérico.

**Parâmetros:**
- `id`: ID numérico do empreendimento (campo `codigo` do endpoint de empreendimentos)

**Exemplo:** `/api/Carteira/DadosContrato/IdEmpreendimento=24905`

**Resposta:** Array de objetos de contrato

```json
[
	{
		"cod_filial": 10301,
		"nome_filial": "GREEN VILLAGE EMPREENDIMENTOS IMOBILIÁRIOS LTDA - FILIAL",
		"cod_contrato": 11530,
		"cod_proposta": 117069,
		"nome_cliente": "MARCELO HENRIQUE DE OLIVEIRA",
		"tipo_pessoa": "F",
		"cpf_cnpj_cliente": "032.079.152-13",
		"cod_cliente": 13326,
		"valor_contrato": 139800,
		"tipo_contrato": "Venda",
		"data_cadastro": "14/03/2025",
		"status_contrato": "Ativo",
		"data_status": "14/03/2025",
		"classificacaocto": "Compra e Venda",
		"data_classificacaocto": "14/03/2025",
		"perc_multa": 2,
		"perc_mora": 1,
		"data_entrega": "14/03/2025",
		"data_assinatura": "14/03/2025",
		"tipo_estrutura": "Unidade",
		"status_estrutura": "Vendida",
		"cod_empreendimento": 24905,
		"cod_est_emp": "01",
		"nome_empreendimento": "LOTEAMENTO RESIDENCIAL GREEN VILLAGE",
		"cod_etapa": 24906,
		"cod_st_etapa": "01",
		"nome_etapa": "UNICA",
		"cod_bloco": 24959,
		"cod_est_bloco": "09",
		"nome_bloco": "QUADRA I",
		"cod_unidade": 25244,
		"cod_est_unidade": "16",
		"nome_unidade": "LOTE 16",
		"desc_classificacao": "Compra e Venda - Green Village",
		"data_EntregaChaves": null
	}
]
```

**Campos Importantes:**
- `cod_contrato`: ID numérico do contrato (usado para buscar parcelas)
- `cod_filial`: ID da filial
- `nome_cliente`: Nome do cliente
- `cpf_cnpj_cliente`: CPF/CNPJ do cliente
- `valor_contrato`: Valor total do contrato
- `status_contrato`: Status do contrato (valores possíveis abaixo)
- `data_assinatura`: Data de assinatura do contrato
- `cod_empreendimento`: ID do empreendimento
- `nome_empreendimento`: Nome do empreendimento
- `cod_unidade`: ID da unidade vendida
- `nome_unidade`: Nome/número da unidade

**Status de Contrato:**
- `"Ativo"`: Contrato ativo e em dia
- `"Normal"`: Contrato em situação normal
- `"Inadimplente"`: Contrato com parcelas em atraso
- `"Quitado"`: Contrato totalmente pago
- `"Distratado"`: Contrato cancelado/distratado

**Uso:** O campo `cod_contrato` deve ser usado para buscar as parcelas do contrato.

---

## Parcelas

### GET /api/Carteira/DadosParcelas/IdContrato={id}

Retorna todas as parcelas (installments) de um contrato específico usando o ID numérico do contrato.

**Parâmetros:**
- `id`: ID numérico do contrato (campo `cod_contrato` do endpoint de contratos)

**Exemplo:** `/api/Carteira/DadosParcelas/IdContrato=11530`

**Resposta:** Array de objetos de parcela

```json
[
	{
		"cod_contrato": 11530,
		"cod_parcela": 4577971,
		"cod_condicao": 117069,
		"cod_serie": 245351,
		"status_parcela": "Ativo",
		"data_status": "14/03/2025",
		"tipo_parcela": "Sinal",
		"sequencia": "001/002",
		"data_vencimento": "28/03/2025",
		"data_movimento": "28/03/2025",
		"vlr_original": 4194,
		"vlr_corrigido": 4194,
		"vlr_multa": 0,
		"vlr_atraso": 0,
		"vlr_juros": 0,
		"vlr_desconto": 0,
		"vlr_taxas": 0,
		"vlr_pago": 4194,
		"data_baixa": "27/03/2025",
		"receita_pgto": "Bloqueto Bancario",
		"situacao": "Pago",
		"vlr_presente": 0,
		"vlr_residuoagerar": 0,
		"vlr_residuo_anual": 0,
		"rescob_re_correcaocobrada": 0,
		"vlr_residuo_cobranca": 0,
		"receita_parcela": "Carteira",
		"parcela_contratual": "Sim",
		"parcela_termo": "Não",
		"parcela_processo": "Contrato",
		"vlr_jurosreneg": 0,
		"vlr_correcaomonetaria": 0,
		"data_vigenciacorrecao": null,
		"vlr_residuo_cobrado": 0,
		"parcela_origem": "Contrato",
		"nosso_numero": "0000000010",
		"data_Venc_boleto": "28/03/2025",
		"nome_banco": "BANCO SICOOB 155114-0 (GREEN VILLAGE)",
		"agencia": "3031-7",
		"conta_corrente": "155114      -0",
		"motivo_inativacao": null
	}
]
```

**Campos Importantes:**
- `cod_parcela`: ID numérico da parcela
- `cod_contrato`: ID do contrato (FK)
- `status_parcela`: Status da parcela (valores possíveis abaixo)
- `tipo_parcela`: Tipo da parcela (Sinal, Intermediária, Mensal, Final, etc)
- `sequencia`: Sequência da parcela (ex: "001/120")
- `data_vencimento`: Data de vencimento da parcela (formato DD/MM/YYYY)
- `vlr_original`: Valor original da parcela
- `vlr_corrigido`: Valor corrigido (com índices)
- `vlr_pago`: Valor efetivamente pago
- `data_baixa`: Data em que a parcela foi paga (formato DD/MM/YYYY)
- `situacao`: Situação da parcela ("Pago", "Ativo", etc)
- `receita_pgto`: Forma de pagamento ("Bloqueto Bancario", "Dinheiro", etc)

**Status de Parcela:**
- `"Ativo"`: Parcela ativa/pendente (a receber)
- `"Pago"`: Status obsoleto, verificar campo `situacao`
- `"P"`: Parcela paga (formato curto)

**Situação de Parcela:**
- `"Pago"`: Parcela quitada
- `"Ativo"`: Parcela pendente de pagamento
- `"Vencido"`: Parcela vencida e não paga

**Lógica de CashIn:**
- **Forecast (Previsão):** Criado na `data_vencimento` com `vlr_original`
- **Actual (Realizado):** Criado na `data_baixa` com `vlr_pago` (somente se pago)

**Nota:** Datas estão no formato `DD/MM/YYYY` e devem ser convertidas para `date` objects.

---

## Contas a Pagar

### GET /api/FinanceiroMovimentacao/FaturaPagar/Saldo/{startDate}/{endDate}

Retorna contas a pagar (accounts payable) dentro de um período de datas.

**Parâmetros:**
- `startDate`: Data inicial (formato YYYY-MM-DD)
- `endDate`: Data final (formato YYYY-MM-DD)

**Exemplo:** `/api/FinanceiroMovimentacao/FaturaPagar/Saldo/2025-10-30/2025-10-30`

**Resposta:** Array de objetos de fatura a pagar

```json
[
	{
		"Filial": {
			"Id": 5984,
			"Nome": null,
			"NomeFantasia": null,
			"Agente": null,
			"OrganizacaoPai": null
		},
		"Agente": {
			"Expand": "tipos",
			"Id": "1-8245",
			"Padrao": 1,
			"Codigo": 8245,
			"Tipo": null,
			"Nome": null,
			"NomeFantasia": null,
			"Cnpj": null,
			"Consolidador": null,
			"Tipos": null
		},
		"NumeroAP": 921,
		"TipoDocumento": "DISTRATO",
		"NumeroDocumento": "000001",
		"NumeroParcela": "011",
		"DataVencimento": "30/10/2025",
		"DataProrrogado": "30/10/2025",
		"ValorParcela": 10000.0,
		"SaldoAtual": 10000.0
	}
]
```

**Campos Importantes:**
- `Filial.Id`: ID da filial
- `Agente.Codigo`: Código do fornecedor/agente
- `NumeroAP`: Número do título a pagar
- `TipoDocumento`: Tipo do documento (DISTRATO, NOTA FISCAL, etc)
- `NumeroDocumento`: Número do documento
- `NumeroParcela`: Número da parcela
- `DataVencimento`: Data de vencimento (formato DD/MM/YYYY)
- `DataProrrogado`: Data prorrogada (se houver)
- `ValorParcela`: Valor da parcela
- `SaldoAtual`: Saldo atual a pagar

**Uso:** Este endpoint é usado para sincronizar CashOut (saídas de caixa).

---

## Notas Importantes

### Conversão de Datas

A API Mega usa diferentes formatos de data:
- Parâmetros de URL: `YYYY-MM-DD`
- Campos de resposta: `DD/MM/YYYY`
- Datas vazias: `0001/01/01`

Sempre valide e converta datas antes de usar.

### IDs e Códigos

- IDs numéricos são usados nos novos endpoints (`cod_contrato`, `cod_parcela`, `codigo`)
- IDs encriptados existem em alguns campos legados (`id` field com strings como `"NTPDuDHDuDk5w7gzMjA"`)
- Use sempre os IDs numéricos (`cod_*`, `codigo`) para integrações

### Status Mapping

Para suportar ambos os formatos (antigo e novo) da API, use o mapeamento:

```python
status_mapping = {
    "Ativo": "A",
    "Normal": "N",
    "Inadimplente": "I",
    "Quitado": "Q",
    "Distratado": "D",
}
```

### Rate Limiting e Timeout

- Timeout padrão: 60 segundos (configurável)
- Max retries: 3 tentativas (configurável)
- Delay entre retries: 5 segundos (configurável)

Veja `config/mega_mapping.yaml` para ajustar essas configurações.

# Requisitos - Melhorias Cash Flow Report

**Data**: 2025-10-31
**Versão**: 1.0

---

## 1. Valores a Receber (Cash In)

### 1.1. Classificação de Recebimentos

Todos os cálculos baseados em **parcelas**, com as seguintes regras:

#### a) Contratos Ativos
```
Critério: Parcelas pagas DENTRO DO MÊS de vencimento
Filtro parcela_origem: IN ('Contrato', 'Tabela Price')

Lógica:
- Extrair mês/ano de data_vencimento
- Extrair mês/ano de data_baixa
- Se mês/ano são iguais: Contrato Ativo

Exemplo:
- data_vencimento: 15/01/2025
- data_baixa: 20/01/2025
- Classificação: Contrato Ativo ✓
```

#### b) Recuperações
```
Critério: Parcelas pagas DEPOIS DO MÊS de vencimento
Filtro parcela_origem: IN ('Contrato', 'Tabela Price')

Lógica:
- Se mês/ano de data_baixa > mês/ano de data_vencimento: Recuperação

Exemplo:
- data_vencimento: 15/01/2025
- data_baixa: 05/02/2025
- Classificação: Recuperação ✓
```

#### c) Antecipações
```
Critério: Parcelas pagas ANTES DO MÊS de vencimento
Filtro parcela_origem: IN ('Contrato', 'Tabela Price')

Lógica:
- Se mês/ano de data_baixa < mês/ano de data_vencimento: Antecipação

Exemplo:
- data_vencimento: 15/02/2025
- data_baixa: 28/01/2025
- Classificação: Antecipação ✓
```

#### d) Outras Entradas
```
Critério: Qualquer parcela_origem diferente
Filtro parcela_origem: NOT IN ('Contrato', 'Tabela Price')

Exemplos de parcela_origem (baseado em análise de 662 parcelas):
- Renegociação: 145 parcelas (21.9%)
- Reajuste: 9 parcelas (1.4%)
- Termo Contratual: 2 parcelas (0.3%)
- Termo Contratual (Não altera valor contrato): 1 parcela (0.2%)
```

### 1.2. VP Carteira (Valor Presente da Carteira)

```
Definição:
Valor presente das parcelas ATIVAS e NÃO PAGAS

Filtros:
- status_parcela = 'Ativo'
- data_baixa IS NULL (não paga)
- parcela_origem IN ('Contrato', 'Tabela Price')

Campo: vlr_presente (já vem calculado da API)

Agregação: Somar vlr_presente de todas as parcelas que atendem aos filtros

Armazenamento:
- Por empreendimento
- Por data de referência - mes de referencia
```

### 1.3. Yield Mensal

```
Fórmula: (Recebimento Líquido - Recebidos) / VP Carteira

Onde:
- Recebimento Líquido = Recebimentos Totais - Deduções
  (já existe no relatório "Evolução Histórica Yield Carteira")

- Recebidos = Total de parcelas pagas no período
  (Contratos Ativos + Recuperações + Antecipações + Outras Entradas)

- VP Carteira = Valor calculado na seção 1.2

Resultado: Percentual (multiplicar por 100 para %)
```

---

## 2. Evolução da Inadimplência

### 2.1. Objetivo
Gerar dados para gráfico de evolução da inadimplência ao longo do tempo.

### 2.2. Regras de Cálculo

#### Filtros Base
```
- status_parcela = 'Ativo'
- parcela_origem IN ('Contrato', 'Tabela Price')
- Comparar: data_vencimento vs data_baixa (ou data_referencia se não paga)
```

#### Cálculo de Dias em Atraso
```python
# Para parcelas pagas
if data_baixa is not None:
    dias_atraso = (data_baixa - data_vencimento).days
else:
    # Para parcelas não pagas
    dias_atraso = (data_referencia - data_vencimento).days

# Considerar apenas se dias_atraso > 0 (vencidas)
```

#### Períodos de Inadimplência
```
1. Até 30 dias:        0 < dias_atraso <= 30
2. 30 a 60 dias:       30 < dias_atraso <= 60
3. 60 a 90 dias:       60 < dias_atraso <= 90
4. 90 a 180 dias:      90 < dias_atraso <= 180
5. Acima de 180 dias:  dias_atraso > 180
```

### 2.3. Métricas Necessárias

Para cada período, calcular:
- **Valor total**: Soma dos valores das parcelas (campo: valor_parcela ou saldo)
- **Quantidade**: Contagem de parcelas

### 2.4. Exemplo de Output
```json
{
  "empreendimento_id": 24905,
  "ref_date": "2025-01-31",
  "inadimplencia": {
    "ate_30_dias": {
      "valor": 150000.00,
      "quantidade": 25
    },
    "30_a_60_dias": {
      "valor": 80000.00,
      "quantidade": 12
    },
    "60_a_90_dias": {
      "valor": 45000.00,
      "quantidade": 8
    },
    "90_a_180_dias": {
      "valor": 30000.00,
      "quantidade": 5
    },
    "acima_180_dias": {
      "valor": 20000.00,
      "quantidade": 3
    },
    "total": {
      "valor": 325000.00,
      "quantidade": 53
    }
  }
}
```

---

## 3. Saldo a Pagar (Cash Out)

### 3.1. Nova Classificação por TipoDocumento

```
IMPORTANTE: Não usar mais as categorias antigas:
- OPEX ❌
- Despesas Financeiras ❌
- CAPEX ❌
- Distribuições ❌

Nova classificação: Usar campo TipoDocumento da API de despesas

Exemplos encontrados:
- "NF_REF" - Nota Fiscal Referenciada
- "NF SERV" - Nota Fiscal de Serviço
- [Outros a serem mapeados conforme surgem nos dados]
```

### 3.2. Estrutura da API de Despesas

```json
{
  "Filial": {
    "Id": 4,
    "Nome": null
  },
  "Agente": {
    "Codigo": 13328,
    "Nome": null
  },
  "NumeroAP": 80258,
  "TipoDocumento": "NF_REF",
  "NumeroDocumento": "1",
  "NumeroParcela": "006",
  "DataVencimento": "29/10/2025",
  "DataProrrogado": "29/10/2025",
  "ValorParcela": 1000.0,
  "SaldoAtual": 0.0
}
```

### 3.3. Campos Relevantes

- **TipoDocumento**: Usar para classificação
- **ValorParcela**: Valor total da parcela
- **SaldoAtual**: Saldo pendente (se 0, já foi pago)
- **DataVencimento**: Data original de vencimento
- **DataProrrogado**: Data ajustada de vencimento
- **Agente.Codigo**: Relacionar com contrato (se aplicável)

---

## 4. Dados Necessários das APIs

### 4.1. Parcelas API (Já existente)
```
Endpoint: /api/Carteira/ParcelasContrato/IdContrato={cod_contrato}

Campos necessários:
- cod_parcela
- cod_contrato
- tipo_parcela (Mensal, Resíduo, Intermediária, Sinal)
- parcela_origem (Contrato, Tabela Price, Renegociação, Reajuste, etc)
- status_parcela (Ativo, Inativo)
- data_vencimento
- data_baixa
- valor_parcela
- vlr_presente ⭐ (já vem calculado da API)
```

### 4.2. Despesas API (Já existente)
```
Endpoint: [endpoint da API de despesas]

Campos necessários:
- NumeroAP
- TipoDocumento ⭐ (usar para classificação)
- DataVencimento
- DataProrrogado
- ValorParcela
- SaldoAtual
- Agente.Codigo
```

---

## 5. Análise de Tipo_Parcela (Referência)

Baseado em análise de 662 parcelas do contrato 872:

### Distribuição tipo_parcela:
- **Mensal**: 650 (98.2%)
- **Resíduo**: 9 (1.4%)
- **Intermediária**: 2 (0.3%)
- **Sinal**: 1 (0.2%)

### Distribuição parcela_origem:
- **Tabela Price**: 324 (48.9%)
- **Contrato**: 181 (27.3%)
- **Renegociação**: 145 (21.9%)
- **Reajuste**: 9 (1.4%)
- **Termo Contratual**: 2 (0.3%)
- **Termo Contratual (Não altera valor contrato)**: 1 (0.2%)

---

## 6. Implementação - Estrutura de Dados

### 6.1. Análise das Tabelas Existentes

**Tabelas atuais (a serem analisadas):**
- `cash_flow_data` - Armazena dados agregados de cash flow
- `raw_payload` - Armazena payloads brutos das APIs
- `portfolio_stats` - Estatísticas da carteira
- Outras tabelas relacionadas

### 6.2. Opções de Implementação

#### Opção A: Estender Tabelas Existentes
- Adicionar novos campos JSON em `cash_flow_data`
- Pros: Mantém dados relacionados juntos
- Contras: Estrutura JSON pode ficar complexa

#### Opção B: Criar Novas Tabelas
- `vp_carteira` - Armazena VP por empreendimento/data
- `inadimplencia_faixas` - Armazena dados de inadimplência
- `yield_mensal` - Armazena cálculos de yield
- Pros: Estrutura relacional clara, queries mais eficientes
- Contras: Mais tabelas para gerenciar

#### Opção C: Híbrido
- Usar tabelas existentes para dados agregados simples
- Criar tabelas específicas para dados complexos (inadimplência)
- Pros: Balance entre simplicidade e eficiência
- Contras: Requer análise cuidadosa

**⏳ PENDENTE**: Analisar tabelas existentes para decidir melhor abordagem

---

## 7. Próximos Passos

### 7.1. Imediato
- [x] Documentar requisitos completos
- [x] Esclarecer "Recebimento Líquido" (recebimentos totais - deduções)
- [x] Confirmar VP Carteira (campo vlr_presente já calculado)
- [x] Analisar TipoDocumento da API de despesas
- [ ] Analisar estrutura de tabelas existentes
- [ ] Definir estratégia de armazenamento

### 7.2. Desenvolvimento
1. Atualizar classificação de Cash In:
   - Contratos Ativos (no mês)
   - Recuperações (depois do mês)
   - Antecipações (antes do mês)
   - Outras Entradas (origem diferente)

2. Implementar cálculo de VP Carteira:
   - Filtrar parcelas ativas não pagas
   - Somar campo vlr_presente
   - Armazenar por empreendimento/data

3. Implementar cálculo de Yield Mensal:
   - Obter Recebimento Líquido (totais - deduções)
   - Calcular Recebidos (soma das categorias)
   - Aplicar fórmula: (Líquido - Recebidos) / VP

4. Implementar Evolução da Inadimplência:
   - Calcular dias em atraso
   - Classificar por faixas
   - Agregar valor e quantidade
   - Gerar estrutura para gráfico

5. Atualizar classificação de Cash Out:
   - Usar TipoDocumento ao invés de categorias antigas
   - Mapear tipos de documento
   - Ajustar relatórios

### 7.3. Testes
- [ ] Testar com empreendimento 24905
- [ ] Validar cálculos com dados reais
- [ ] Comparar com relatórios existentes
- [ ] Validar todas as faixas de inadimplência

---

## 8. Perguntas Respondidas ✅

1. **Yield Mensal - "Recebimento Líquido"**: ✅
   São os recebimentos totais - deduções. Já existe tabela no relatório "Evolução Histórica Yield Carteira"

2. **VP Carteira - Taxa de desconto**: ✅
   O valor já vem calculado no campo `vlr_presente` da API de parcelas

3. **TipoDocumento - Valores possíveis**: ✅
   Exemplos: "NF_REF", "NF SERV". Não usar mais OPEX/CAPEX/etc

4. **Armazenamento**: ⏳
   Analisar tabelas existentes para definir melhor abordagem

---

## 9. Glossário

- **VP Carteira**: Valor Presente da Carteira (present value)
- **Yield**: Rendimento ou retorno sobre o capital
- **parcela_origem**: Campo que indica a origem da parcela (Contrato, Tabela Price, etc)
- **vlr_presente**: Campo da API que já contém o valor presente calculado
- **TipoDocumento**: Campo da API de despesas usado para classificação

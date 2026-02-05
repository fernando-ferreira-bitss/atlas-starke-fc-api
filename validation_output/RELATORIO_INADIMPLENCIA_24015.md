# Relatório de Validação - Inadimplência Empreendimento 24015 (LOTEAMENTO REVOAR)

**Data da Análise:** 18/11/2025
**Mês de Referência:** Novembro/2025
**Data do Cálculo no Sistema:** 07/11/2025 20:33:38

---

## Resumo Executivo

Total de **241 parcelas** vencidas e ativas, totalizando **R$ 2.287.367,04** em inadimplência.

---

## Detalhamento por Faixa de Atraso

| Faixa de Atraso | Valor (R$) | Quantidade de Parcelas | % do Total |
|-----------------|------------|------------------------|------------|
| **Até 30 dias** | **1.485.910,60** | **175** | **64,9%** |
| 30 a 60 dias | 134.702,38 | 27 | 5,9% |
| 60 a 90 dias | 178.664,06 | 22 | 7,8% |
| 90 a 180 dias | 488.090,00 | 17 | 21,3% |
| Acima de 180 dias | 0,00 | 0 | 0,0% |
| **TOTAL** | **2.287.367,04** | **241** | **100%** |

---

## Critérios de Cálculo

O cálculo de inadimplência segue as seguintes regras de negócio:

### Filtros Aplicados
- ✅ **Status da Parcela**: `Ativo` (parcelas não quitadas ou pagas com atraso)
- ✅ **Origem da Parcela**: `Contrato` ou `Tabela Price` (exclui juros, multas, etc.)
- ✅ **Data de Vencimento**: Anterior à data de referência (30/11/2025)

### Cálculo de Dias de Atraso
Para cada parcela vencida:
- Se **não paga** (`data_baixa = NULL`):
  - `dias_atraso = data_referência - data_vencimento`
- Se **paga antes ou na data de referência** (`data_baixa ≤ data_referência`):
  - `dias_atraso = data_baixa - data_vencimento`
- Se **paga após data de referência** (`data_baixa > data_referência`):
  - `dias_atraso = data_referência - data_vencimento`

### Classificação por Faixa
- **Até 30 dias**: 1 a 30 dias de atraso
- **30 a 60 dias**: 31 a 60 dias de atraso
- **60 a 90 dias**: 61 a 90 dias de atraso
- **90 a 180 dias**: 91 a 180 dias de atraso
- **Acima de 180 dias**: mais de 180 dias de atraso

---

## Análise Específica: Parcelas Vencidas até 30 Dias

### Observações
- **175 parcelas** classificadas como vencidas até 30 dias
- **Valor total**: R$ 1.485.910,60
- **Valor médio por parcela**: R$ 8.490,92

### Possíveis Causas para Valor Alto
1. **Contratos recentes com parcelas grandes** que acabaram de vencer
2. **Entrada de caixa (sinal)** que pode estar sendo contabilizada como parcela
3. **Parcelas de distrato** que podem estar ativas mas não são recebiveis
4. **Parcelamentos de entrada** que geram parcelas de alto valor

---

## Recomendações para Validação

Para validar os dados de "Até 30 dias", recomendamos:

1. **Verificar as 10 maiores parcelas vencidas até 30 dias**
   - Confirmar se são parcelas regulares de contrato
   - Identificar se há parcelas de entrada/sinal
   - Verificar se há parcelas de distrato

2. **Analisar distribuição temporal**
   - Quantas parcelas venceram nos últimos 7 dias?
   - Quantas entre 8-15 dias?
   - Quantas entre 16-30 dias?

3. **Verificar origem das parcelas**
   - Confirmar que apenas parcelas de "Contrato" e "Tabela Price" devem ser incluídas
   - Verificar se parcelas de entrada/sinal devem ser excluídas

---

## Próximos Passos

Para investigação mais detalhada, será necessário:

1. ✅ **Dados salvos**: `delinquency_24015_database.json`
2. ⏳ **Aguardando liberação de API**: Devido a rate limiting (429 Too Many Requests), precisamos aguardar para buscar detalhes individuais das parcelas
3. 📊 **Próxima análise**: Quando a API estiver disponível, buscaremos:
   - Lista completa de todas as 175 parcelas até 30 dias
   - Detalhes individuais (contrato, valor, vencimento, dias de atraso)
   - Histórico de pagamentos

---

## Contato

Para mais detalhes ou dúvidas sobre este relatório, entre em contato com a equipe técnica.

**Arquivos Disponíveis:**
- `delinquency_24015_database.json` - Dados completos do banco de dados
- Este relatório em Markdown

---

*Relatório gerado automaticamente pelo sistema Starke*

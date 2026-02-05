# Análise: Salvamento de Parcelas a Pagar do UAU

## Contexto

A API do UAU retorna dados de desembolsos (contas a pagar) através do endpoint `/Planejamento/ConsultarDesembolsoPlanejamento`.

## Problema Identificado

### Estrutura dos Dados da API

A API retorna registros com os seguintes campos:
- `Empresa`, `Obra`, `Contrato`, `Produto`, `Composicao`, `Item`, `Insumo` (identificação)
- `Status`: "Projetado" | "Pagar" | "Pago" (ciclo de vida do pagamento)
- `DtaRef`, `DtaRefMes`, `DtaRefAno` (datas de referência)
- `Total`, `TotalLiq`, `TotalBruto`, `Acrescimo`, `Desconto` (valores)

### Análise dos Dados (Empresa 4, Ano 2024)

| Métrica | Quantidade |
|---------|------------|
| Total de registros da API | 1.133 |
| Registros 100% duplicados | 46 |
| Registros únicos (hash completo) | 1.087 |
| Itens únicos (chave sem Status) | 200 |

### O Problema da Chave Única

Para salvar na tabela `faturas_pagar`, precisamos de uma chave única. Testamos várias combinações:

| Chave | Únicos | Duplicados |
|-------|--------|------------|
| Emp-Obra-Contrato-Produto-Composicao-Item-Insumo + AnoMes | 200 | 933 |
| + Status | 274 | 859 |
| + DtaRef | 472 | 661 |
| + DtaRef + Status | 1.087 | 46 |
| + Total | 724 | 409 |
| + Total + TotalLiq | 1.079 | 54 |
| + DtaRef + Total + TotalLiq | 1.085 | 48 |

### Por que Status NÃO PODE ser usado na chave?

O campo `Status` representa o **ciclo de vida** do pagamento:

```
Projetado → Pagar → Pago
```

Quando um item muda de status, a API retorna o **mesmo registro** com status diferente. Se usarmos Status na chave:
1. Não conseguimos rastrear a evolução do item
2. Criamos duplicatas ao invés de atualizar o registro existente

### Exemplo Real de Duplicatas

O mesmo item aparece múltiplas vezes com diferentes Status:

```json
// Mesmo item (A00159), mesma data, Status diferente
{"Status": "Pagar", "Insumo": "A00159", "DtaRef": "2025-07-30", "Total": 20110.14}
{"Status": "Pago",  "Insumo": "A00159", "DtaRef": "2025-07-30", "Total": 20110.14}
```

Também há **registros 100% idênticos** (provável bug na API ou dados duplicados no UAU):
```json
// 2 registros exatamente iguais
{"Status": "Pago", "Insumo": "A00159", "DtaRef": "2024-01-12", "Total": 173538.05, "TotalLiq": 3340.23}
{"Status": "Pago", "Insumo": "A00159", "DtaRef": "2024-01-12", "Total": 173538.05, "TotalLiq": 3340.23}
```

## Conclusão

**Os 1.133 registros NÃO são 1.133 contas a pagar diferentes.**

São **200 itens** de conta a pagar em diferentes estados (Projetado/Pagar/Pago) e com múltiplos lançamentos ao longo do tempo.

## Solução Adotada

### Usar tabela `saidas_caixa` (CashOut) em vez de `faturas_pagar`

A tabela `saidas_caixa` é mais adequada para estes dados porque:
1. **Agrega por mês e categoria** - ideal para fluxo de caixa
2. **Separa orçamento de realizado**:
   - Status "Projetado" + "Pagar" → `orcamento` (previsto/pendente)
   - Status "Pago" → `realizado`
3. **Não precisa rastrear item individual** - foco em visão consolidada

### Resultado da Agregação

| Métrica | Antes | Depois |
|---------|-------|--------|
| Registros da API | 625 (período 2024) | - |
| Registros no banco | - | 16 |
| Total Orçamento | - | R$ 10.007.562,95 |
| Total Realizado | - | R$ 15.071.583,13 |

### Estrutura do CashOut

```python
{
    "filial_id": 1000004,
    "filial_nome": "JVF SERVIÇOS EIRELI - ME",
    "mes_referencia": "2024-01",
    "categoria": "C0023",
    "orcamento": 816242.62,      # Soma de Status="Projetado" + "Pagar"
    "realizado": 1651249.79,     # Soma de Status="Pago"
    "detalhes": {"records_count": 89},
    "origem": "uau"
}
```

## Alternativas Descartadas

### 1. Usar Status na chave
- **Problema**: Não permite rastrear evolução do pagamento
- **Resultado**: ~274 registros (perde relação entre Projetado e Pago do mesmo item)

### 2. Agregar por item+mês (tabela faturas_pagar)
- **Problema**: Funciona, mas perde granularidade
- **Resultado**: ~104-200 registros
- **Motivo descarte**: Não há valor adicional sobre CashOut para visão de fluxo de caixa

### 3. Salvar todos com sequencial
- **Problema**: Quando Status muda (Projetado → Pago), como identificar registro?
- **Motivo descarte**: Impossível manter integridade sem ID único da API

## Solução Implementada

Para contas a pagar do UAU, usar apenas `sync_cash_out` que:
1. Busca desembolsos da API
2. Agrega por mês + categoria (Composicao)
3. Separa valores de `orcamento` (Projetado + Pagar) e `realizado` (Pago)
4. Salva em `saidas_caixa` com `origem='uau'`

### Código Removido

Os seguintes métodos foram removidos pois não são mais necessários:

- `UAUDataTransformer.transform_desembolso_to_fatura_pagar()`
- `UAUDataTransformer.aggregate_desembolsos_to_faturas_pagar()`
- `UAUSyncService.sync_faturas_pagar()`

### Métodos Disponíveis para UAU

```python
# UAUSyncService
- sync_empresas()      # Sincroniza empresas/empreendimentos
- sync_cash_in()       # Sincroniza entradas (parcelas recebidas)
- sync_cash_out()      # Sincroniza saídas (desembolsos)
- sync_portfolio_stats() # Calcula estatísticas do portfólio
- sync_delinquency()   # Calcula inadimplência
- sync_all()           # Executa todos os syncs
```

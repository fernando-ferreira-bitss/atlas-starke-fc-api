# Relatório de Performance - Sync UAU

**Empresa Teste:** 50 - EL SHADAI AGUA BOA EMPREENDIMENTOS LTDA
**Período:** 2024-01-01 a 2025-12-31

---

## Resumo Executivo - Comparativo

| Métrica | Antes (2026-02-03) | Depois (2026-02-04) | Ganho |
|---------|-------------------|---------------------|-------|
| **Tempo Total** | 2h 36min | **1h 46min** | **-50 min (32%)** |
| **VP Calculation** | 1h 53min | ~1h 06min | **-47 min (42%)** |
| **ExportarVendas** | 41min | ~35min | **-6 min (15%)** |
| **Erros Finais** | 0 | 0 | ✅ |
| **Retries** | N/A | 4 (recuperados) | ✅ |

### Dados Sincronizados (iguais)
| Métrica | Valor |
|---------|-------|
| **Empresas Sincronizadas** | 140 |
| **Contratos** | 934 |
| **CashOut (registros)** | 24 |
| **CashIn (registros)** | 32 |
| **VP Total** | R$ 189.666.523,57 |
| **Parcelas Processadas** | 121.662 |

---

## Teste Real com Otimizações (2026-02-04)

### Configuração Aplicada
```env
UAU_MAX_WORKERS=2      # Aumentado de 1 para 2
batch_size=15          # Aumentado de 10 para 15
retry_delay=30         # Backoff incremental: 30s, 60s, 90s
```

### Resultado
- **Início:** 08:53:02
- **Fim:** 10:39:27
- **Duração Total:** 1h 46min

### Retries Durante o Sync
```
VP Progress: 300/494 vendas - errors: 0
  → Connection reset (retry 1, esperou 30s) → sucesso
  → Connection reset (retry 2, esperou 60s) → sucesso
  → Timeout (retry 1, esperou 30s) → sucesso
  → Timeout (retry 2, esperou 60s) → sucesso
VP Progress: 400/494 vendas - errors: 0
VP Completed: 494 vendas - errors: 0
```

**Conclusão:** Sistema de retry funcionou perfeitamente. Todos os 4 erros de rede foram recuperados automaticamente, sem perda de dados.

---

## Breakdown por Etapa

| # | Etapa | Duração | % Total |
|---|-------|---------|---------|
| 1 | Inicialização + Auth | **3s** | 0.02% |
| 2 | Sync Empresas | **39s** | 0.4% |
| 3 | **ExportarVendas** | **41min** | 26% |
| 4 | Sync Contratos | **49s** | 0.5% |
| 5 | Sync CashOut | **10s** | 0.1% |
| 6 | Sync CashIn + Delinquency | **35s** | 0.4% |
| 7 | **VP Calculation** | **1h 53min** | 73% |
| 8 | Portfolio Stats | **2s** | 0.01% |

---

## Detalhamento de Cada Processo

### 1. Inicialização + Auth (3s)

**O que faz:** Conecta ao banco de dados e autentica na API UAU

**Endpoint:**
```
POST /Autenticador/AutenticarUsuario
```

**Resultado:** Token de sessão válido por 2h

---

### 2. Sync Empresas (39s)

**O que faz:** Busca todas as empresas ativas da API UAU e sincroniza com o banco

**Endpoint:**
```
POST /Empresa/ObterEmpresasAtivas
```

**Resultado:** 140 empresas → Cria/atualiza registros em `filiais` + `empreendimentos`

**Dados salvos:**
- Código, Nome, CNPJ da empresa
- Cria Filial (para agregação de CashOut) + Development (para CashIn/Portfolio)

---

### 3. 🔴 ExportarVendas (41min) - GARGALO

**O que faz:** Busca dados completos de todas as vendas (contratos) da empresa

**Endpoints utilizados:**

| Ordem | Endpoint | Função |
|-------|----------|--------|
| 1 | `POST /Obras/ObterObrasAtivas` | Lista obras da empresa (001, 002, RMARM) |
| 2 | `POST /Venda/RetornaChavesVendasPorPeriodo` | Lista IDs das vendas no período |
| 3 | `POST /Venda/ExportarVendasXml` | Exporta dados completos (batches de 10) |

**Volume processado:**
- 935 vendas encontradas
- 94 batches de 10 vendas cada
- ~26 segundos por batch

**Dados retornados por venda:**
- Dados do contrato (número, data, status, valor)
- Dados do cliente (código, CPF/CNPJ)
- Lista de parcelas (vencimento, valor, status pago/aberto)
- Itens vendidos (produtos, preços)

**Usado para:** Alimentar Contratos, CashIn e Inadimplência (evita múltiplas chamadas)

---

### 4. Sync Contratos (49s)

**O que faz:** Processa as vendas exportadas e salva como contratos

**Fonte:** Dados do ExportarVendas (não faz nova chamada API)

**Resultado:** 934 contratos sincronizados

**Dados salvos em `contratos`:**
- `cod_contrato`, `obra`, `status`
- `valor_contrato`, `valor_atualizado_ipca`
- `data_assinatura`, `cliente_cpf`, `cliente_codigo`

---

### 5. Sync CashOut (10s)

**O que faz:** Busca dados de desembolso (contas a pagar) por obra

**Endpoint:**
```
POST /Planejamento/ConsultarDesembolsoPlanejamento
```

**Payload:**
```json
{
  "Empresa": 50,
  "Obra": "001",
  "MesInicial": "01/2024",
  "MesFinal": "12/2025"
}
```

**Chamadas:** 3 (uma por obra: 001, 002, RMARM)

**Resultado:** 24 registros CashOut

**Dados salvos em `saidas_caixa`:**
- `ref_month`, `categoria` (projetado/pagar/pago)
- `valor`, `data_transacao`
- Agregado por `filial_id`

---

### 6. Sync CashIn + Delinquency (35s)

**O que faz:** Extrai parcelas das vendas já exportadas e calcula inadimplência

**Fonte:** Dados do ExportarVendas (não faz nova chamada API)

**Resultado:**
- 32 registros CashIn (parcelas agregadas por mês)
- 1 registro Delinquency (total: R$ 1.233.304,78)

**Dados salvos em `entradas_caixa`:**
- `ref_month`, `record_type` (forecast/actual)
- `valor` por categoria (parcelas, entrada, etc.)

**Dados salvos em `inadimplencia`:**
- Aging buckets (1-30, 31-60, 61-90, 90+ dias)
- Total em atraso por faixa

---

### 7. 🔴 VP Calculation (1h53min) - MAIOR GARGALO

**O que faz:** Calcula Valor Presente das parcelas a receber (com juros/multa/correção)

**Endpoint:**
```
POST /Venda/ConsultarParcelasDaVenda
```

**Payload:**
```json
{
  "empresa": 50,
  "obra": "002",
  "num_venda": 123,
  "data_calculo": "2026-02-03T00:00:00",
  "boleto_antecipado": false
}
```

**Volume:**
- 494 chamadas (uma por venda com parcelas abertas)
- 1 worker (sequencial devido a rate limiting)
- ~14 segundos por chamada em média

**Por que é lento:**
- API calcula juros/multa/correção monetária em tempo real
- Cada chamada retorna todas as parcelas da venda com valores atualizados
- Rate limiting da API impede paralelização

**Resultado:**
- 121.669 parcelas processadas
- VP Total = R$ 189.670.369,12

**Dados retornados por parcela:**
| Campo | Descrição |
|-------|-----------|
| `Principal_reaj` | Valor original da parcela |
| `Valor_reaj` | Valor presente (VP) |
| `Juros_reaj` | Juros calculados |
| `Multa_reaj` | Multa por atraso |
| `Correcao_reaj` | Correção monetária |
| `DataVenc_reaj` | Data de vencimento |

---

### 8. Portfolio Stats (2s)

**O que faz:** Consolida métricas do portfólio por mês

**Fonte:** Dados do VP Calculation (não faz nova chamada API)

**Resultado:** 12 registros (um por mês de 2024)

**Dados salvos em `estatisticas_portfolio`:**
| Métrica | Valor |
|---------|-------|
| VP (Valor Presente) | R$ 189.670.369,12 |
| Prazo Médio | 189,76 meses |
| Duration | 15,60 |
| Total Parcelas | 121.669 |
| Total Principal | R$ 62.118.669,32 |
| Total Juros | R$ 28.104,30 |
| Total Multa | R$ 4.627,55 |
| Total Correção | R$ 2.757.377,80 |

---

## Gargalos Identificados

| Gargalo | Tempo | % Total | Causa Raiz |
|---------|-------|---------|------------|
| **VP Calculation** | 1h 53min | 73% | 494 chamadas sequenciais (1 worker) devido a rate limiting da API |
| **ExportarVendas** | 41min | 26% | 94 batches de 10 vendas, volume grande de dados por venda |

---

## Endpoints UAU Utilizados

| Endpoint | Método | Uso | Chamadas |
|----------|--------|-----|----------|
| `/Autenticador/AutenticarUsuario` | POST | Autenticação | 1 |
| `/Empresa/ObterEmpresasAtivas` | POST | Lista empresas | 1 |
| `/Obras/ObterObrasAtivas` | POST | Lista obras | 1 |
| `/Venda/RetornaChavesVendasPorPeriodo` | POST | IDs de vendas | 1 |
| `/Venda/ExportarVendasXml` | POST | Dados completos vendas | 94 |
| `/Planejamento/ConsultarDesembolsoPlanejamento` | POST | CashOut por obra | 3 |
| `/Venda/ConsultarParcelasDaVenda` | POST | VP por venda | 494 |

**Total de chamadas API:** ~595

---

## Recomendações de Otimização

### 1. VP Calculation (maior impacto potencial)

**Problema:** 494 chamadas sequenciais levam 1h53min

**Soluções:**
- [x] ~~Testar `UAU_MAX_WORKERS=2` ou `3` com monitoramento de erros~~ → **Testado! workers=2 é 52% mais rápido**
- [ ] Cachear VP por venda (só recalcular se parcela mudou)
- [ ] Verificar com UAU se existe endpoint batch para VP

**Resultado do benchmark:** workers=2 reduz de 1h42min para 1h07min (35 min economizados)

### 2. ExportarVendas

**Problema:** 94 batches de 10 vendas

**Soluções:**
- [x] ~~Testar `batch_size=15` ou `20` se API permitir~~ → **Testado! batch_size=15 é o ideal**
- [ ] Implementar sync incremental (só vendas alteradas)

**Resultado do benchmark:** batch_size=15 é 4% mais rápido. Batches maiores são mais lentos.

### 3. Sync Incremental

**Problema:** Sempre busca todas as vendas do período

**Soluções:**
- [ ] Usar campo `DataDeCadastro` ou `DataAlt` para filtrar vendas alteradas
- [ ] Manter cache de vendas já sincronizadas (por status)
- [ ] Só buscar VP para vendas com parcelas que mudaram

**Potencial:** Reduzir tempo total em 50-70% em syncs subsequentes

---

## Configurações Atuais

```env
# .env
UAU_MAX_WORKERS=1      # Workers para chamadas paralelas
                       # Opção: 2 para 52% mais rápido (com retries ocasionais)
UAU_TIMEOUT=120        # Timeout em segundos
UAU_MAX_RETRIES=3      # Tentativas em caso de erro
```

```python
# uau_api_client.py
batch_size = 15        # Vendas por batch no ExportarVendas (otimizado via benchmark)
retry_delay = 30       # Base para retry incremental: 30s, 60s, 90s
```

---

## Benchmarks Realizados

### Benchmark ExportarVendas (2026-02-03)

**Objetivo:** Encontrar o batch_size ideal para o endpoint `/Venda/ExportarVendasXml`

**Metodologia:**
- Empresa teste: 50 (934 vendas)
- Batch sizes testados: 10, 15, 20, 25, 30
- Pausa entre testes: 10 segundos
- Sem persistência no banco (apenas medição)

**Resultados:**

| Batch Size | Batches | Tempo Total | Vendas/s | Erros | Taxa Erro |
|------------|---------|-------------|----------|-------|-----------|
| 10 | 94 | 2189s (36.5 min) | 0.43 | 0 | 0.0% |
| **15** ⭐ | 63 | **2113s (35.2 min)** | **0.44** | 0 | 0.0% |
| 20 | 47 | 2251s (37.5 min) | 0.41 | 0 | 0.0% |
| 25 | 38 | 2308s (38.5 min) | 0.40 | 0 | 0.0% |
| 30 | 32 | 2224s (37.1 min) | 0.42 | 0 | 0.0% |

**Conclusão:**
- `batch_size = 15` é o sweet spot
- Ganho de ~4% comparado a batch_size=10
- Batches maiores (20-30) são mais lentos (payload maior = processamento mais lento na API)
- Zero erros em todas as configurações

**Ação:** Alterado `batch_size` de 10 para 15 em `uau_api_client.py`

---

### Benchmark VP Calculation (2026-02-04)

**Objetivo:** Testar paralelização do endpoint `/Venda/ConsultarParcelasDaVenda`

**Metodologia:**
- Empresa teste: 50 (935 vendas)
- Workers testados: 1, 2, 3, 4, 5
- Pausa entre testes: 30 segundos
- Retry com backoff exponencial em caso de erro
- Stop automático se taxa de erro > 20% ou 10+ erros consecutivos

**Resultados:**

| Workers | Tempo Total | Vendas/s | Erros | Taxa Erro | Observações |
|---------|-------------|----------|-------|-----------|-------------|
| 1 | 6151s (1h 42min) | 0.15 | 1 | 0.1% | Estável, sem retries |
| **2** ⭐ | **4049s (1h 7min)** | **0.23** | 1 | 0.1% | Alguns retries (503, connection reset) |
| 3 | 4553s (1h 16min) | 0.21 | 1 | 0.1% | Mais retries |
| 4 | 4927s (1h 22min) | 0.19 | 1 | 0.1% | Muitos retries |
| 5 | 4444s (1h 14min) | 0.21 | 1 | 0.1% | Muitos erros 503 |

**Análise detalhada por fase:**

| Workers | Início (0-300 vendas) | Após 300 vendas | Comportamento |
|---------|----------------------|-----------------|---------------|
| 1 | 2.75 vendas/s | 0.15 vendas/s | Estável, sem warnings |
| 2 | 4.83 vendas/s | 0.23 vendas/s | Retries ocasionais |
| 3 | 6.67 vendas/s | 0.21 vendas/s | Muitos retries |
| 4+ | 7+ vendas/s | 0.19 vendas/s | Erros constantes (503) |

**Erros observados:**
- `503 Service Unavailable` - API sobrecarregada
- `Connection reset by peer` - Conexão encerrada pelo servidor
- Rate limiting aparenta ser baseado em volume/tempo, não apenas conexões simultâneas

**Conclusão:**
- `workers = 2` é 52% mais rápido que sequencial
- Mais de 2 workers = mais erros e tempo perdido com retries
- API tem throttling que afeta até requisições sequenciais após ~300 vendas
- Retries com backoff são essenciais para garantir completude

**Recomendação:**
- **Produção:** `UAU_MAX_WORKERS=1` (estabilidade, zero retries)
- **Agressivo:** `UAU_MAX_WORKERS=2` (52% mais rápido, com retries)

---

## Histórico de Alterações

| Data | Alteração | Resultado |
|------|-----------|-----------|
| 2026-02-03 | Reduzido batch_size de 50 para 10 | Evitou timeout na API |
| 2026-02-03 | Adicionado commit antes de chamada longa + SELECT 1 após | Resolveu erro de conexão com banco |
| 2026-02-03 | Alterado batch_size de 10 para 15 | +4% performance ExportarVendas |
| 2026-02-04 | Benchmark VP com 1-5 workers | Identificado workers=2 como 52% mais rápido |
| 2026-02-04 | Alterado UAU_MAX_WORKERS de 1 para 2 | 32% mais rápido no sync real |
| 2026-02-04 | Retry com backoff incremental (30s, 60s, 90s) | Mais tempo para API recuperar entre retries |

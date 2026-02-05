# Benchmark: ExportarVendas - Batch Size

**Data:** 2026-02-03
**Empresa Teste:** 50 - EL SHADAI AGUA BOA EMPREENDIMENTOS LTDA
**Total de Vendas:** 934

---

## Objetivo

Identificar o batch_size ideal para o endpoint `/Venda/ExportarVendasXml` que busca dados completos das vendas (contratos, parcelas, clientes).

---

## Configuração do Teste

- **Endpoint:** `POST /Venda/ExportarVendasXml`
- **Batch sizes testados:** 10, 15, 20, 25, 30
- **Pausa entre testes:** 10 segundos
- **Métrica:** Tempo total para buscar 934 vendas

---

## Resultados

| Batch Size | Batches | Tempo Total | Vendas/s | Erros | Taxa Erro |
|------------|---------|-------------|----------|-------|-----------|
| 10 | 94 | 2189.1s (36.5 min) | 0.43 | 0 | 0.0% |
| **15** ⭐ | 63 | **2112.9s (35.2 min)** | **0.44** | 0 | 0.0% |
| 20 | 47 | 2251.1s (37.5 min) | 0.41 | 0 | 0.0% |
| 25 | 38 | 2307.5s (38.5 min) | 0.40 | 0 | 0.0% |
| 30 | 32 | 2224.0s (37.1 min) | 0.42 | 0 | 0.0% |

---

## Análise

### Melhor Configuração: `batch_size = 15`

**Por que batch_size = 15 é o melhor:**
1. **Menor tempo total:** 35.2 minutos (vs 36.5 min com batch=10)
2. **Maior throughput:** 0.44 vendas/segundo
3. **Zero erros:** Nenhum timeout ou rate limiting
4. **Redução de requests:** 63 batches vs 94 batches (-33% requests)

### Observações

1. **Batches maiores não são melhores:**
   - batch_size=20, 25, 30 foram mais lentos que 15
   - Provavelmente o payload maior demora mais para ser processado pela API

2. **Sweet spot encontrado:**
   - batch_size=15 equilibra bem entre número de requests e tamanho do payload

3. **API estável:**
   - Nenhum erro em todas as configurações
   - API suporta bem até batch_size=30

---

## Recomendação

```python
# uau_api_client.py - linha 758
batch_size = 15  # Otimizado via benchmark (era 10)
```

**Ganho estimado:** ~4% mais rápido (1.3 minutos economizados por sync)

---

## Configuração Aplicada

- [x] Alterado `batch_size` de 10 para 15 em `uau_api_client.py`
- Data da alteração: 2026-02-03

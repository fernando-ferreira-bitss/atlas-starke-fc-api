# UAU API Benchmark Results

**Data:** 2026-02-04 05:12
**Empresa:** 50

---

## Resumo

### Melhor Configuração Encontrada

#### VP Calculation
- **Workers Recomendado:** 2
- **Performance:** 0.23 vendas/segundo
- **Taxa de Erro:** 0.1%

---

## VP Calculation - Resultados por Workers

| Workers | Tempo Total | Vendas/s | Sucesso | Erros | Taxa Erro |
|---------|-------------|----------|---------|-------|-----------|
| 1 | 6150.8s | 0.15 | 934 | 1 | 0.1% |
| 2 | 4048.8s | 0.23 | 934 | 1 | 0.1% |
| 3 | 4552.7s | 0.21 | 934 | 1 | 0.1% |
| 4 | 4926.5s | 0.19 | 934 | 1 | 0.1% |
| 5 | 4443.9s | 0.21 | 934 | 1 | 0.1% |

---

## Erros Encontrados

```
Invalid key
Invalid key
Invalid key
Invalid key
Invalid key
```
---

## Recomendações

### VP Calculation
- Alterar `UAU_MAX_WORKERS` para **2** em `.env`
- Ganho estimado: 52% mais rápido


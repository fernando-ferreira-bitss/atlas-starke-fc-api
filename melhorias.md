# Plano: Otimizações do Sync Mega

## Resumo

| # | Otimização | Problema | Ganho Esperado |
|---|------------|----------|----------------|
| 1 | Paralelização API | Busca sequencial de parcelas | Tempo: 4h → ~1h |
| 2 | Bulk Upsert CashOut | 1338 queries individuais | 1338 → 2 queries |
| 3 | Otimização Memória | Cache global de parcelas | 2.5GB → ~300MB |

---

## 1. Paralelização de Chamadas API

### Teste Realizado
- 50 contratos, 29.674 parcelas
- 8 workers: 12.11s | 16 workers: 8.45s
- **Sem rate limit**

### Arquivo
`src/starke/domain/services/mega_sync_service.py`

### Implementação
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_parcelas_parallel(self, contract_ids: List[int], max_workers: int = 8) -> Dict[int, List]:
    results = {}
    def fetch_one(cid):
        return cid, self.api_client.get_parcelas_by_contract_id(cid)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_one, cid) for cid in contract_ids]
        for future in as_completed(futures):
            cid, parcelas = future.result()
            results[cid] = parcelas
    return results
```

Usar em `sync_cash_in_for_development` para buscar parcelas de todos os contratos do empreendimento em paralelo.

---

## 2. Bulk Upsert CashOut

### Problema (linhas 1171-1210)
```python
for (filial_id, month, category) in all_keys:  # 1338 iterações
    existing = self.db.query(CashOut).filter(...).first()  # 1 query cada
```

### Arquivo
`src/starke/domain/services/mega_sync_service.py` - método `aggregate_cashout_from_faturas`

### Solução
```python
# 1. Buscar todos existentes em 1 query
existing = self.db.query(CashOut).filter(
    CashOut.filial_id.in_([k[0] for k in all_keys])
).all()
existing_map = {(r.filial_id, r.mes_referencia, r.categoria): r for r in existing}

# 2. Separar updates e inserts
to_update = []
to_insert = []
for key in all_keys:
    data = {...}  # montar dados
    if key in existing_map:
        to_update.append({"id": existing_map[key].id, **data})
    else:
        to_insert.append(CashOut(**data))

# 3. Bulk operations
self.db.bulk_update_mappings(CashOut, to_update)
self.db.bulk_save_objects(to_insert)
self.db.commit()
```

---

## 3. Otimização de Memória

### Contexto
Todos os dados são salvos **por empreendimento**:
- CashIn: `empreendimento_id + ref_month + category`
- PortfolioStats: `empreendimento_id + ref_month`
- Delinquency: `empreendimento_id + ref_month`

### Problema Atual
Cache global `development_data_cache` guarda parcelas de TODOS os empreendimentos.

### Arquivo
`src/starke/domain/services/mega_sync_service.py` - método `sync_all`

### Solução: Processar por empreendimento
```python
import gc

for dev in developments:
    # 1. Buscar contratos deste empreendimento (já em cache)
    dev_contratos = contratos_by_dev.get(dev.external_id, [])
    contract_ids = [c["cod_contrato"] for c in dev_contratos if c.get("cod_contrato")]

    # 2. Buscar parcelas em PARALELO (só deste empreendimento)
    parcelas_by_contract = self.fetch_parcelas_parallel(contract_ids, max_workers=8)
    todas_parcelas = [p for ps in parcelas_by_contract.values() for p in ps]

    # 3. Processar tudo para este empreendimento
    self.save_contracts(dev, dev_contratos)
    self.process_cash_in(dev, todas_parcelas, start_date, end_date)
    self.calculate_portfolio_stats(dev, todas_parcelas, months)
    self.calculate_delinquency(dev, todas_parcelas, months)

    # 4. Checkpoint
    dev.last_financial_sync_at = datetime.utcnow()
    self._safe_commit(f"dev_{dev.name}")

    # 5. Limpar memória
    del parcelas_by_contract, todas_parcelas
    if devs_processed % 10 == 0:
        gc.collect()
```

### Mudanças no loop
- Remover `development_data_cache` global
- Calcular PortfolioStats e Delinquency dentro do loop do empreendimento
- Adicionar `gc.collect()` periódico

---

## Ordem de Implementação

1. **Bulk Upsert CashOut** - isolado, sem dependências
2. **Paralelização API** - criar método auxiliar
3. **Otimização Memória** - reestruturar loop principal

---

## Verificação

### Teste 1: Um empreendimento
```bash
PYTHONPATH=src python3 -m starke.cli backfill --start-date=2026-01-01 --empreendimento-ids=1471
```
- Tempo < 2 min
- Memória < 500MB

### Teste 2: Sync completo
```bash
PYTHONPATH=src python3 -m starke.cli backfill --start-date=2025-07-01
```
- Tempo < 2h (vs 4h15min atual)
- Memória estável ~300MB

### Verificar dados
```sql
SELECT COUNT(*) FROM saidas_caixa;
SELECT COUNT(*) FROM estatisticas_portfolio;
SELECT COUNT(*) FROM delinquency;
```

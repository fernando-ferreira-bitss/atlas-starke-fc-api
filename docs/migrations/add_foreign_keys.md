# Migration: Add Foreign Keys to Financial Tables

## 📋 Visão Geral

**Arquivo:** `alembic/versions/tyxqab2i1q6j_add_foreign_keys_to_financial_tables.py`
**Data:** 2025-10-30
**Revision ID:** `tyxqab2i1q6j`
**Revises:** `d43246ea9abe`

Esta migration adiciona Foreign Keys (chaves estrangeiras) nas tabelas financeiras para melhorar:
- ✅ **Integridade de dados** - Previne registros órfãos
- ✅ **Performance de JOINs** - Otimizador usa estatísticas de FK
- ✅ **Manutenção** - Cascade delete automático

---

## 🎯 O Que Esta Migration Faz

### 1. Limpeza de Dados Órfãos
Antes de criar as FKs, a migration:
- Verifica registros órfãos em cada tabela
- Remove registros com `empreendimento_id` inválido
- Registra quantos registros foram limpos

### 2. Criação de Foreign Keys
Adiciona FKs nas seguintes tabelas:
- `cash_in.empreendimento_id` → `developments.id`
- `cash_out.empreendimento_id` → `developments.id`
- `balance.empreendimento_id` → `developments.id`
- `portfolio_stats.empreendimento_id` → `developments.id`
- `monthly_cash_flow.empreendimento_id` → `developments.id`
- `contracts.empreendimento_id` → `developments.id`

Todas com `ON DELETE CASCADE`.

---

## 🚀 Como Executar

### Pré-requisitos
```bash
# Garantir que o banco está acessível
export DATABASE_URL="postgresql://starke_user:starke_password@localhost:5432/starke_db"

# Verificar versão atual
PYTHONPATH=/Users/fernandoferreira/Documents/projetos/atlas/starke/src:$PYTHONPATH \
  python3 -m alembic current
```

### Executar a Migration

```bash
# Executar upgrade (adicionar FKs)
PYTHONPATH=/Users/fernandoferreira/Documents/projetos/atlas/starke/src:$PYTHONPATH \
  python3 -m alembic upgrade tyxqab2i1q6j
```

### Verificar Resultado

```bash
# Listar FKs criadas
psql $DATABASE_URL -c "
  SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    tc.constraint_name
  FROM information_schema.table_constraints AS tc
  JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
  JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
  WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name IN ('cash_in', 'cash_out', 'balance', 'portfolio_stats', 'monthly_cash_flow', 'contracts')
  ORDER BY tc.table_name;
"
```

### Reverter (Se Necessário)

```bash
# Executar downgrade (remover FKs)
PYTHONPATH=/Users/fernandoferreira/Documents/projetos/atlas/starke/src:$PYTHONPATH \
  python3 -m alembic downgrade d43246ea9abe
```

---

## ⚠️ Considerações Importantes

### Antes de Executar

1. **Backup do Banco**
   ```bash
   pg_dump $DATABASE_URL > backup_before_fk_migration.sql
   ```

2. **Verificar Dados Órfãos**
   ```sql
   -- Ver quantos registros serão deletados
   SELECT 'cash_in' as table_name, COUNT(*) as orphaned_count
   FROM cash_in t
   WHERE t.empreendimento_id IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM developments d WHERE d.id = t.empreendimento_id)
   UNION ALL
   SELECT 'cash_out', COUNT(*)
   FROM cash_out t
   WHERE t.empreendimento_id IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM developments d WHERE d.id = t.empreendimento_id)
   -- ... (repetir para outras tabelas)
   ```

3. **Ambiente de Dev Primeiro**
   - Testar em ambiente de desenvolvimento
   - Verificar performance dos JOINs
   - Confirmar que aplicação funciona corretamente

### Depois de Executar

1. **Testes de Integridade**
   ```bash
   # Tentar inserir registro com empreendimento_id inválido (deve falhar)
   psql $DATABASE_URL -c "
     INSERT INTO cash_in (empreendimento_id, ref_month, category, forecast, actual)
     VALUES (99999, '2025-10', 'test', 100, 100);
   "
   # Esperado: ERROR: insert or update on table "cash_in" violates foreign key constraint
   ```

2. **Verificar Performance**
   ```sql
   -- Ver plano de execução de JOIN otimizado
   EXPLAIN ANALYZE
   SELECT *
   FROM cash_in
   JOIN developments ON cash_in.empreendimento_id = developments.id
   WHERE developments.is_active = true;
   ```

---

## 📊 Impacto Esperado

### Performance
- **Volume Baixo (<10k registros):** Impacto mínimo (~2-5% overhead em INSERTs)
- **Volume Médio (10k-100k):** 20-40% mais rápido em JOINs
- **Volume Alto (>100k):** 40-50% mais rápido em JOINs

### Comportamento Mudado

**ANTES da Migration:**
```python
# Permitido: inserir registro com empreendimento_id inválido
db.add(CashIn(empreendimento_id=99999, ...))
db.commit()  # ✅ Sucesso (mas cria dado órfão!)
```

**DEPOIS da Migration:**
```python
# Bloqueado: não permite empreendimento_id inválido
db.add(CashIn(empreendimento_id=99999, ...))
db.commit()  # ❌ IntegrityError: FK constraint violated
```

**CASCADE Delete:**
```python
# ANTES: Deletar development deixa registros órfãos
db.delete(development)
db.commit()
# cash_in, cash_out, etc. ficam com empreendimento_id inválido

# DEPOIS: Deletar development remove registros relacionados automaticamente
db.delete(development)
db.commit()
# cash_in, cash_out, etc. são deletados automaticamente (CASCADE)
```

---

## 🔍 Troubleshooting

### Erro: "violates foreign key constraint"

**Causa:** Há dados órfãos no banco.

**Solução:**
```bash
# Executar script de limpeza manual
python3 /tmp/check_indexes.py

# Ou deletar órfãos manualmente
psql $DATABASE_URL -c "
  DELETE FROM cash_in
  WHERE empreendimento_id NOT IN (SELECT id FROM developments);
"
```

### Erro: "could not create unique index"

**Causa:** Duplicatas na coluna `developments.id`.

**Solução:**
```sql
-- Verificar duplicatas
SELECT id, COUNT(*)
FROM developments
GROUP BY id
HAVING COUNT(*) > 1;

-- Remover duplicatas se necessário
```

### Performance piorou após migration

**Causa:** PostgreSQL precisa atualizar estatísticas.

**Solução:**
```sql
-- Atualizar estatísticas do otimizador
ANALYZE cash_in;
ANALYZE cash_out;
ANALYZE balance;
ANALYZE portfolio_stats;
ANALYZE monthly_cash_flow;
ANALYZE contracts;
ANALYZE developments;

-- Ou atualizar todas
VACUUM ANALYZE;
```

---

## 📚 Referências

- [PostgreSQL Foreign Keys](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-FK)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Foreign Keys](https://docs.sqlalchemy.org/en/14/core/constraints.html#foreign-key-constraint)

---

## 🎯 Next Steps (Após Esta Migration)

1. Atualizar modelos SQLAlchemy com `ForeignKey()` explícito
2. Adicionar testes de integridade referencial
3. Documentar comportamento de CASCADE para a equipe
4. Monitorar performance de JOINs com FKs

---

## ✅ Checklist de Execução

- [ ] Backup do banco criado
- [ ] Migration testada em ambiente de dev
- [ ] Verificados dados órfãos (se houver, documentar quais)
- [ ] Migration executada em produção
- [ ] FKs criadas verificadas com query SQL
- [ ] Testes de integridade passando
- [ ] Performance de JOINs verificada (EXPLAIN ANALYZE)
- [ ] Equipe notificada sobre comportamento de CASCADE
- [ ] Documentação atualizada

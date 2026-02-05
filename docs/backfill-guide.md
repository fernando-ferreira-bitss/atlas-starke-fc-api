# Guia de Backfill - Processamento de Histórico

## O que é Backfill?

O comando `backfill` permite processar **múltiplos meses de uma vez**, ideal para:

- ✅ Carregar histórico completo ao configurar o sistema
- ✅ Reprocessar períodos anteriores após correções
- ✅ Preencher lacunas de dados
- ✅ Migrar dados históricos

## Como Funciona

1. **Busca dados da API** uma vez para cada contrato
2. **Processa cada mês** com a data de referência correta (último dia do mês)
3. **Usa UPSERT** para atualizar registros existentes (sem duplicatas)
4. **Emails são desabilitados** automaticamente durante backfill

## Uso Básico

### Processar todo o ano de 2025
```bash
python -m starke.cli backfill \
  --start-date=2025-01-01 \
  --end-date=2025-12-31
```

### Processar primeiro trimestre de 2025
```bash
python -m starke.cli backfill \
  --start-date=2025-01-01 \
  --end-date=2025-03-31
```

### Processar de janeiro até hoje
```bash
python -m starke.cli backfill \
  --start-date=2025-01-01
```

### Processar apenas um empreendimento
```bash
python -m starke.cli backfill \
  --start-date=2025-01-01 \
  --empreendimento-ids=1472
```

### Processar múltiplos empreendimentos
```bash
python -m starke.cli backfill \
  --start-date=2025-01-01 \
  --empreendimento-ids=1472,1428,1395
```

## Limites e Proteções

### Limite Padrão: 24 meses
Por padrão, o backfill limita a 24 meses para evitar processamento excessivo.

```bash
# Erro: mais de 24 meses
python -m starke.cli backfill \
  --start-date=2020-01-01 \
  --end-date=2025-12-31
# ❌ Erro: Tentando processar 72 meses, mas o limite é 24
```

### Aumentar o Limite
Use `--max-months` para aumentar:

```bash
python -m starke.cli backfill \
  --start-date=2022-01-01 \
  --end-date=2025-12-31 \
  --max-months=48
```

### Forçar Sem Limite
Use `--force` para ignorar o limite e confirmação:

```bash
python -m starke.cli backfill \
  --start-date=2020-01-01 \
  --force
```

## Aviso de Confirmação

Para processamentos com **mais de 12 meses**, você receberá um aviso:

```
⚠️  Atenção: Você está prestes a processar 24 meses!
   Isso pode demorar bastante e gerar muitas chamadas à API.
   Deseja continuar? [y/N]:
```

Você pode:
- Digitar `y` para continuar
- Digitar `n` para cancelar
- Usar `--force` para pular a confirmação

## Exemplo Completo

```bash
# Processar todo o histórico de 2025 para um empreendimento
python -m starke.cli backfill \
  --start-date=2025-01-01 \
  --end-date=2025-12-31 \
  --empreendimento-ids=1472
```

**Output:**
```
🚀 Iniciando backfill de 2025-01-01 até 2025-12-31

📅 Serão processados 12 meses:
   • 2025-01 (ref_date: 2025-01-31)
   • 2025-02 (ref_date: 2025-02-28)
   • 2025-03 (ref_date: 2025-03-31)
   ...
   • 2025-12 (ref_date: 2025-12-31)

⚠️  Atenção: Você está prestes a processar 12 meses!
   Isso pode demorar bastante e gerar muitas chamadas à API.
   Deseja continuar? [y/N]: y

[1/12] Processando 2025-01 (ref_date: 2025-01-31)...
   ✅ Concluído: 1 empreendimentos, 6 contratos, 145 parcelas
[2/12] Processando 2025-02 (ref_date: 2025-02-28)...
   ✅ Concluído: 1 empreendimentos, 6 contratos, 148 parcelas
...
[12/12] Processando 2025-12 (ref_date: 2025-12-31)...
   ✅ Concluído: 1 empreendimentos, 6 contratos, 152 parcelas

================================================================================
✅ Backfill concluído com sucesso!
================================================================================

📊 Resumo Total:
   • Meses processados: 12
   • Empreendimentos processados: 12
   • Contratos coletados: 72
   • Parcelas processadas: 1,780

💡 Dica: Use o dashboard web para visualizar os dados históricos
```

## Opções Completas

| Opção | Descrição | Padrão |
|-------|-----------|--------|
| `--start-date` | Data inicial (YYYY-MM-DD) | **Obrigatório** |
| `--end-date` | Data final (YYYY-MM-DD) | Ontem |
| `--empreendimento-ids` | IDs separados por vírgula | Todos |
| `--max-months` | Limite máximo de meses | 24 |
| `--force` | Ignora limite e confirmação | false |
| `--dry-run` | Não usado em backfill | N/A |

## Diferenças: `run` vs `backfill`

### Comando `run` (Processamento Diário)
```bash
python -m starke.cli run --date=2025-10-23
```

- ✅ Processa **um dia/mês** por vez
- ✅ Usa `--skip-ingestion` para não buscar da API
- ✅ Envia emails (se configurado)
- ✅ Ideal para **execução diária automatizada**

### Comando `backfill` (Histórico)
```bash
python -m starke.cli backfill --start-date=2025-01-01
```

- ✅ Processa **múltiplos meses**
- ✅ Sempre busca dados da API
- ✅ **Nunca envia emails**
- ✅ Ideal para **carga inicial ou reprocessamento**

## Boas Práticas

### 1. Comece com um Empreendimento
Teste primeiro com um único empreendimento:

```bash
python -m starke.cli backfill \
  --start-date=2025-01-01 \
  --end-date=2025-03-31 \
  --empreendimento-ids=1472
```

### 2. Processar em Lotes
Para muitos meses, processe em lotes trimestrais:

```bash
# Q1
python -m starke.cli backfill --start-date=2025-01-01 --end-date=2025-03-31

# Q2
python -m starke.cli backfill --start-date=2025-04-01 --end-date=2025-06-30

# Q3
python -m starke.cli backfill --start-date=2025-07-01 --end-date=2025-09-30

# Q4
python -m starke.cli backfill --start-date=2025-10-01 --end-date=2025-12-31
```

### 3. Monitorar Logs
Acompanhe o progresso pelos logs:

```bash
python -m starke.cli backfill \
  --start-date=2025-01-01 \
  --end-date=2025-12-31 \
  2>&1 | tee backfill-2025.log
```

### 4. Verificar Resultados
Após o backfill, verifique os dados no banco:

```sql
SELECT
  ref_month,
  COUNT(*) as registros,
  SUM(forecast) as total_forecast,
  SUM(actual) as total_actual
FROM cash_in
WHERE empreendimento_id = 1472
GROUP BY ref_month
ORDER BY ref_month;
```

## Troubleshooting

### Erro: "Tentando processar N meses, mas o limite é 24"
**Solução:** Use `--max-months=N` ou `--force`

```bash
python -m starke.cli backfill \
  --start-date=2020-01-01 \
  --max-months=72
```

### Erro: "Data inicial não pode ser maior que data final"
**Solução:** Verifique as datas

```bash
# Errado
python -m starke.cli backfill \
  --start-date=2025-12-31 \
  --end-date=2025-01-01

# Correto
python -m starke.cli backfill \
  --start-date=2025-01-01 \
  --end-date=2025-12-31
```

### Processamento muito lento
**Solução:** Processe por empreendimento

```bash
# Em vez de todos de uma vez
for id in 1472 1428 1395; do
  python -m starke.cli backfill \
    --start-date=2025-01-01 \
    --empreendimento-ids=$id
done
```

## Resumo

✅ **Use `backfill`** para:
- Carga inicial de histórico
- Reprocessar períodos anteriores
- Preencher lacunas de dados

✅ **Use `run`** para:
- Processamento diário automatizado
- Atualização incremental
- Envio de relatórios por email

---

**Dica:** O sistema usa UPSERT, então você pode rodar `backfill` múltiplas vezes para o mesmo período sem criar duplicatas!

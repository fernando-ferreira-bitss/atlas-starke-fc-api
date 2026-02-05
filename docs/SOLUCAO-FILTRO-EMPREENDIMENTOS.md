# ✅ Solução: Filtro de Empreendimentos Usando Contratos

**Data:** 30 de Outubro de 2025
**Status:** 🟢 Implementado

---

## 🎯 Problema Original

### Desafio:
- API `/api/FinanceiroMovimentacao/FaturaPagar/Saldo` retorna despesas **SEM** campo `cod_empreendimento`
- Tentativa de usar `CentroCusto` falhou: 180 de 181 empreendimentos compartilham mesmo Centro de Custo (21)
- Não é possível filtrar despesas por empreendimento diretamente

### Campos disponíveis em FaturaPagar:
```json
{
  "Agente": {"Codigo": 872, "Nome": "..."},
  "DataVencimento": "2025-10-15",
  "ValorParcela": 1500.00,
  "SaldoAtual": 0,
  "TipoDocumento": "AP",
  "NumeroDocumento": "123",
  "NumeroParcela": "1/10",
  "Filial": {"Codigo": 4, "Nome": "..."}
}
```

**❌ Não tem:** `cod_empreendimento`, `CentroCusto`, `ClasseFinanceira`

---

## 💡 Solução: Usar Contratos como Intermediário

### Descoberta do Cliente:
> **"Agente.Codigo corresponde ao código do contrato"**

### Como Funciona:

```
┌─────────────────┐
│ Empreendimento  │
│     1472        │
└────────┬────────┘
         │
         │ tem contratos
         ▼
┌─────────────────────────────┐
│ Contratos                   │
│ - cod_contrato: 872         │
│ - cod_contrato: 1051        │
│ - cod_contrato: 1052        │
│ - status: "Ativo"           │
│ - nome: "Residencial Sol"   │
└────────┬────────────────────┘
         │
         │ Agente.Codigo = cod_contrato
         ▼
┌─────────────────────────────┐
│ Despesas (FaturaPagar)      │
│ - Agente.Codigo: 872  ✅    │
│ - Agente.Codigo: 1051 ✅    │
│ - Agente.Codigo: 5539 ❌    │
└─────────────────────────────┘
```

---

## 🔧 Implementação

### 1. Modelo de Dados (Database)

```python
class Contract(Base):
    """Contracts from Mega API."""

    __tablename__ = "contracts"

    cod_contrato: int              # Contract ID
    cod_empreendimento: int        # Development ID
    nome_empreendimento: str       # Development name
    status: str                    # "Ativo", "Cancelado", etc
    cod_cliente: int
    valor_contrato: float
    saldo_devedor: float
    raw_data: JSON
    last_synced_at: datetime
```

### 2. Serviço de Contratos

```python
class ContractService:
    def fetch_and_save_contracts(self, empreendimento_ids: list[int]):
        """Fetch contracts from API and save to database."""

    def get_active_developments(self) -> list[int]:
        """Get empreendimentos with active contracts (status='Ativo' and not 'teste')."""

    def get_active_contract_codes(self, empreendimento_id: int) -> list[int]:
        """Get list of active contract codes for filtering."""
```

### 3. Rotas da API

**✅ Nova abordagem (genérica - mais eficiente):**
```python
# Busca TODAS as despesas de TODAS as filiais de uma vez
despesas = client.get_despesas(
    data_inicio="2025-10-01",
    data_fim="2025-10-31"
)
# Retorna: 3,951 registros (todas as filiais)

receitas = client.get_receitas(
    data_inicio="2025-10-01",
    data_fim="2025-10-31"
)
# Retorna: 36 registros (todas as filiais)
```

**❌ Abordagem antiga (por filial - menos eficiente):**
```python
# Buscava apenas uma filial por vez
despesas = client.get_despesas_by_filial(
    filial_id=4,
    data_inicio="2025-10-01",
    data_fim="2025-10-31"
)
# Retorna: 1,821 registros (só filial 4)
```

### 4. Fluxo de Ingestão

```python
# PASSO 1: Sincronizar contratos (1x por semana ou sob demanda)
$ python -m starke.cli sync-contracts

# Output:
# - Busca contratos de todos os 181 empreendimentos
# - Salva no banco local
# - Identifica empreendimentos ativos

# PASSO 2: Ingestão diária de despesas
def ingest_despesas_for_empreendimento(empreendimento_id: int, ref_date: date):
    # 2.1. Buscar TODAS as despesas (uma única chamada)
    if not hasattr(self, '_all_despesas_cache'):
        self._all_despesas_cache = self.api_client.get_despesas(
            data_inicio=first_day,
            data_fim=last_day
        )
    all_despesas = self._all_despesas_cache

    # 2.2. Buscar contratos deste empreendimento (banco local - rápido!)
    contract_service = ContractService(self.db, self.api_client)
    active_contracts = contract_service.get_active_contract_codes(empreendimento_id)
    # Resultado: [872, 1051, 1052, ...]

    # 2.3. Filtrar despesas por Agente.Codigo
    contract_codes_set = set(active_contracts)
    despesas_filtradas = [
        d for d in all_despesas
        if d.get("Agente", {}).get("Codigo") in contract_codes_set
    ]

    # 2.4. Processar despesas filtradas
    return self._process_despesas(despesas_filtradas, empreendimento_id, ref_date)
```

---

## 📊 Critérios para Empreendimento Ativo

Um empreendimento é considerado **ativo** se:
1. ✅ Possui pelo menos um contrato com `status = "Ativo"`
2. ✅ Nome do empreendimento **NÃO contém** "teste" (case-insensitive)

```sql
SELECT DISTINCT cod_empreendimento
FROM contracts
WHERE status = 'Ativo'
  AND nome_empreendimento NOT ILIKE '%teste%';
```

---

## 🚀 Comandos CLI

### Sincronizar todos os contratos:
```bash
python -m starke.cli sync-contracts
```

### Sincronizar empreendimentos específicos:
```bash
python -m starke.cli sync-contracts --empreendimento-ids=1472,1500,1550
```

### Ver estatísticas:
```bash
python -m starke.cli sync-contracts

# Output:
# 📊 Estatísticas:
#   • Empreendimentos processados: 181/181
#   • Contratos encontrados: 2,450
#   • Novos contratos salvos: 2,450
#   • Contratos atualizados: 0
#
# ✨ Empreendimentos ativos: 45
#
# 📈 Contratos por status:
#   • Ativo: 1,250
#   • Cancelado: 800
#   • Distratado: 300
#   • Quitado: 100
```

---

## ⚡ Performance

### Antes (usando /Filial/):
```
Por empreendimento:
  1 chamada API por empreendimento
  181 empreendimentos = 181 chamadas/dia

Total: 181 chamadas API por dia
```

### Depois (usando rotas genéricas + contratos):
```
Sincronização de contratos (1x/semana):
  181 chamadas (uma por empreendimento)

Ingestão diária:
  1 chamada para FaturaPagar/Saldo (todas as despesas)
  1 chamada para FaturaReceber/Saldo (todas as receitas)
  + Filtros em memória usando banco local

Total: 2 chamadas API por dia (90x mais eficiente!)
```

**Ganho:** ~90x menos chamadas à API por dia!

---

## ✅ Benefícios

1. **Eficiência**
   - 2 chamadas API vs 181+ chamadas por execução
   - Dados de TODAS as filiais em uma única chamada

2. **Simplicidade**
   - Não precisa conhecer qual filial usar
   - Não precisa se preocupar com Centro de Custo

3. **Completude**
   - Captura despesas de todas as filiais
   - Não perde dados por usar filial errada

4. **Manutenibilidade**
   - Contratos salvos no banco para consultas
   - Sincronização separada da ingestão diária
   - Fácil adicionar novos filtros/critérios

5. **Visibilidade**
   - Dashboard pode mostrar contratos por empreendimento
   - Relatórios com detalhes de contratos ativos
   - Auditoria de mudanças de status

---

## 🔄 Fluxo Operacional

### Setup Inicial:
```bash
# 1. Rodar migration
python -m alembic upgrade head

# 2. Sincronizar contratos
python -m starke.cli sync-contracts
```

### Operação Diária:
```bash
# Ingestão usa contratos do banco automaticamente
python -m starke.cli run --date=2025-10-30
```

### Manutenção Semanal:
```bash
# Re-sincronizar contratos para pegar mudanças
python -m starke.cli sync-contracts
```

---

## 📝 Notas Técnicas

### Cache de Despesas
Durante a ingestão de múltiplos empreendimentos no mesmo dia, as despesas são cacheadas em memória para evitar múltiplas chamadas à API:

```python
# Primeira vez: busca da API
despesas = self.api_client.get_despesas(...)
self._despesas_cache = despesas

# Empreendimentos seguintes: usa cache
despesas = self._despesas_cache
```

### Validação do Mapeamento
Para validar que `Agente.Codigo = cod_contrato`, executamos:

```python
# Pegar todos os contratos
contratos = {c.cod_contrato for c in db.query(Contract).all()}

# Pegar todos os Agente.Codigo das despesas
agentes = {d["Agente"]["Codigo"] for d in despesas}

# Verificar interseção
correspondencia = contratos & agentes
percentual = len(correspondencia) / len(contratos) * 100

print(f"Validação: {percentual:.1f}% dos contratos aparecem em despesas")
```

---

## 🎉 Status Final

- ✅ Tabela `contracts` criada
- ✅ Serviço `ContractService` implementado
- ✅ Comando CLI `sync-contracts` funcionando
- ✅ MegaClient com rotas genéricas `get_despesas()` e `get_receitas()`
- 🔄 Integração com `ingestion_service` (em andamento)

**Próximo passo:** Atualizar `ingestion_service.py` para usar a nova abordagem.

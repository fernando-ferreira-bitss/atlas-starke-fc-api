# Como Funciona o Sistema Starke

## 📖 Índice
1. [Visão Geral](#visão-geral)
2. [Fluxo de Execução](#fluxo-de-execução)
3. [Arquitetura](#arquitetura)
4. [Coleta de Dados](#coleta-de-dados)
5. [Processamento](#processamento)
6. [Geração de Relatórios](#geração-de-relatórios)
7. [Envio de Emails](#envio-de-emails)
8. [Idempotência](#idempotência)

---

## 🎯 Visão Geral

O **Starke** é um sistema automatizado de relatórios de fluxo de caixa que:

1. **Roda automaticamente** todo dia às 08:00 AM
2. **Coleta dados** da API Mega ERP do dia anterior (T-1)
3. **Calcula métricas** de fluxo de caixa (entradas, saídas, saldos)
4. **Gera relatórios HTML** mobile-first e responsivos
5. **Envia por email** para destinatários configurados no Google Sheets

**Por que T-1 (dia anterior)?**
- Garante que todos os dados do dia estão completos
- Pagamentos e recebimentos podem demorar para serem processados
- Evita relatórios com dados parciais ou incorretos

---

## 🔄 Fluxo de Execução

### **Visão Macro**

```
┌─────────────────────────────────────────────────────────────┐
│  08:00 AM - Systemd Timer dispara execução                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 1: Ingestão de Dados                                 │
│  • Coleta contratos da API Mega                             │
│  • Coleta parcelas (recebimentos)                           │
│  • Armazena raw data no banco (idempotência)                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 2: Processamento e Cálculos                          │
│  • Calcula entradas de caixa (4 categorias)                 │
│  • Calcula saídas de caixa (4 categorias)                   │
│  • Calcula saldos (inicial + entradas - saídas)             │
│  • Calcula estatísticas da carteira (VP, LTV, etc)          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 3: Geração de Relatórios HTML                        │
│  • Gera 1 relatório por empreendimento                      │
│  • Gera 1 relatório consolidado (todos juntos)              │
│  • HTML mobile-first com CSS responsivo                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 4: Envio de Emails                                   │
│  • Lê destinatários do Google Sheets                        │
│  • Envia HTML inline (não é anexo)                          │
│  • Registra sucesso/falha no banco                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Arquitetura

O projeto segue **Clean Architecture** com 4 camadas principais:

### **1. Domain (Domínio)**
**Localização**: `src/starke/domain/`

Contém a **lógica de negócio pura**, sem dependências externas.

```
domain/
├── entities/          # Modelos de dados (DTOs)
│   ├── contracts.py   # ContratoData, ParcelaData
│   └── cash_flow.py   # CashInData, CashOutData, BalanceData
│
└── services/          # Regras de negócio
    ├── ingestion_service.py    # Coleta e armazena dados
    └── cash_flow_service.py    # Calcula métricas de fluxo
```

**Exemplo de Entidade**:
```python
class CashInData(BaseModel):
    empreendimento_id: int
    ref_date: date
    category: CashInCategory  # ativos, recuperacoes, antecipacoes, outras
    forecast: Decimal         # Previsto
    actual: Decimal          # Realizado

    @property
    def variance_pct(self) -> Decimal:
        """Calcula variação percentual"""
        return (self.actual - self.forecast) / self.forecast * 100
```

---

### **2. Infrastructure (Infraestrutura)**
**Localização**: `src/starke/infrastructure/`

Implementações de **integrações externas**.

```
infrastructure/
├── database/          # PostgreSQL + SQLAlchemy
│   ├── models.py      # 6 tabelas (runs, cash_in, cash_out, etc)
│   └── base.py        # Conexão e sessões
│
├── external_apis/     # Integrações externas
│   └── mega_client.py # Cliente API Mega com retry
│
├── sheets/            # Google Sheets
│   ├── sheets_client.py       # Service Account
│   └── sheets_oauth_client.py # OAuth2 (sua org)
│
└── email/             # Envio de emails
    └── email_service.py # SMTP/Gmail API
```

**Exemplo: Cliente API Mega**
```python
class MegaAPIClient:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential())
    def get_contratos_by_empreendimento(self, emp_id: int):
        """
        Busca contratos com retry automático
        GET /api/Carteira/DadosContrato/IdEmpreendimento={emp_id}
        """
        response = self.client.get(f"/api/Carteira/DadosContrato/IdEmpreendimento={emp_id}")
        return response.json()
```

---

### **3. Presentation (Apresentação)**
**Localização**: `src/starke/presentation/`

Geração de **relatórios HTML**.

```
presentation/
├── templates/
│   ├── base.html          # Template base (CSS, estrutura)
│   └── report.html        # Relatório de fluxo de caixa
│
└── report_builder.py      # Jinja2 para gerar HTML
```

**Como funciona**:
```python
builder = ReportBuilder()
html = builder.build_report(
    empreendimento_nome="Empreendimento XYZ",
    ref_date=date(2024, 10, 21),
    cash_in_list=[...],    # Lista de entradas
    cash_out_list=[...],   # Lista de saídas
    balance=balance_data,  # Saldo calculado
)
# html = string HTML completo e responsivo
```

---

### **4. Core (Núcleo)**
**Localização**: `src/starke/core/`

**Orquestração** e utilidades compartilhadas.

```
core/
├── config.py          # Configurações (Pydantic Settings)
├── logging.py         # Logs estruturados (structlog)
└── orchestrator.py    # Coordena todo o fluxo
```

**Orchestrator** é o "maestro" que coordena tudo:
```python
class Orchestrator:
    def execute(self, ref_date: date):
        # 1. Ingerir dados
        ingestion_service.ingest_all_for_date(...)

        # 2. Processar e calcular
        cash_flow_service.calculate_cash_in(...)

        # 3. Gerar relatórios
        report_builder.build_report(...)

        # 4. Enviar emails
        email_service.send_html_email(...)
```

---

## 📥 Coleta de Dados (Etapa 1)

### **O que é coletado**

Para cada **empreendimento**, coletamos:

1. **Lista de Contratos**
   ```
   GET /api/Carteira/DadosContrato/IdEmpreendimento={id}

   Retorna:
   - código_contrato
   - nome_cliente, CPF/CNPJ
   - valor_contrato
   - saldo_devedor
   - status (ativo, liquidado, etc)
   ```

2. **Parcelas de cada Contrato**
   ```
   GET /api/Carteira/DadosParcelas/IdContrato={id}

   Retorna:
   - número_parcela
   - data_vencimento
   - data_pagamento (se pago)
   - valor_parcela
   - valor_pago
   - status (pago, aberto, vencido)
   - tipo (normal, antecipacao, renegociacao)
   ```

### **Idempotência (Segurança contra duplicação)**

```python
# 1. Calcula hash SHA-256 do payload
payload_hash = hashlib.sha256(json.dumps(data).encode()).hexdigest()

# 2. Verifica se já processamos esse payload exato
if db.query(RawPayload).filter_by(
    source="contratos_emp_123",
    exec_date="2024-10-21",
    payload_hash=payload_hash
).exists():
    print("Já processado, pulando...")
    return

# 3. Armazena no banco
db.add(RawPayload(
    source="contratos_emp_123",
    exec_date="2024-10-21",
    payload_hash=payload_hash,
    payload_json=data
))
```

**Por que isso importa?**
- Se o sistema rodar 2x no mesmo dia → não duplica dados
- Se a API retornar os mesmos dados → detecta e ignora
- Auditoria completa de tudo que foi coletado

---

## ⚙️ Processamento (Etapa 2)

### **Cálculo de Entradas de Caixa**

Para cada parcela coletada, classificamos em **4 categorias**:

```python
def categorize_parcela(parcela):
    # 1. Antecipações
    if "antecip" in parcela["tipo"].lower():
        return CashInCategory.ANTECIPACOES

    # 2. Recuperações (inadimplência regularizada)
    if parcela["data_vencimento"] < ref_date and parcela["status"] == "pago":
        return CashInCategory.RECUPERACOES

    # 3. Contratos ativos (recebimentos normais)
    if parcela["tipo"] == "normal":
        return CashInCategory.ATIVOS

    # 4. Outras entradas
    return CashInCategory.OUTRAS
```

**Resultado**:
```
Entradas de Caixa (2024-10-21)
├─ Contratos Ativos:    R$ 150.000,00 (previsto) → R$ 145.000,00 (realizado) → -3,3%
├─ Recuperações:        R$  10.000,00 (previsto) → R$  12.000,00 (realizado) → +20%
├─ Antecipações:        R$   5.000,00 (previsto) → R$   5.000,00 (realizado) → 0%
└─ Outras:              R$   2.000,00 (previsto) → R$   1.500,00 (realizado) → -25%
   TOTAL:               R$ 167.000,00              → R$ 163.500,00              → -2,1%
```

### **Cálculo de Saídas de Caixa**

**4 categorias** de despesas:

1. **OPEX** (custos operacionais): salários, aluguel, manutenção
2. **Financeiras**: juros, tarifas bancárias
3. **CAPEX** (investimentos): obras, equipamentos
4. **Distribuições**: dividendos, retiradas de sócios

```python
CashOutData(
    category=CashOutCategory.OPEX,
    budget=50000.00,   # Orçado
    actual=48500.00,   # Realizado
    # variance = -1500 (-3%)  ← gastou MENOS que o orçado (bom!)
)
```

### **Cálculo de Saldo**

```python
def calculate_balance(cash_in_list, cash_out_list, opening_balance):
    total_in = sum(ci.actual for ci in cash_in_list)   # R$ 163.500
    total_out = sum(co.actual for co in cash_out_list) # R$ 120.000

    closing = opening_balance + total_in - total_out
    #         R$ 50.000       + R$ 163.500 - R$ 120.000
    #         = R$ 93.500

    return BalanceData(
        opening=50000.00,
        closing=93500.00,
        total_in=163500.00,
        total_out=120000.00,
        net_flow=43500.00  # Fluxo líquido positivo
    )
```

### **Estatísticas da Carteira**

```python
PortfolioStatsData(
    vp=5000000.00,          # Valor Presente da carteira
    ltv=75.5,               # Loan-to-Value médio
    prazo_medio=36.0,       # Prazo médio em meses
    duration=28.5,          # Duration financeira
    total_contracts=150,    # Total de contratos
    active_contracts=142,   # Contratos ativos (94,7%)
)
```

---

## 📊 Geração de Relatórios (Etapa 3)

### **Template HTML Mobile-First**

O relatório é gerado em **HTML puro** (não PDF), otimizado para:
- ✅ Desktop (telas grandes)
- ✅ Mobile (celular)
- ✅ Tablet
- ✅ Email clients (Gmail, Outlook, etc)

**Estrutura do Relatório**:

```
┌─────────────────────────────────────────┐
│  📊 FLUXO DE CAIXA - EMPREENDIMENTO XYZ │
│  Referência: 21/10/2024                 │
└─────────────────────────────────────────┘

┌─────────────┬─────────────┬─────────────┬─────────────┐
│ Entradas    │ Saídas      │ Saldo Final │ Fluxo Líq.  │
│ R$ 163.500  │ R$ 120.000  │ R$ 93.500   │ R$ 43.500   │
│ -2,1%       │ +3%         │ +87%        │             │
└─────────────┴─────────────┴─────────────┴─────────────┘

┌─────────────────────────────────────────────────────────┐
│  📈 DADOS GERAIS DA CARTEIRA                            │
├─────────────────────────────────────────────────────────┤
│  VP: R$ 5.000.000  │  LTV: 75,5%  │  Prazo: 36 meses   │
│  Contratos: 150    │  Ativos: 142 (94,7%)              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  💰 ENTRADAS DE CAIXA                                   │
├──────────────────┬──────────┬────────────┬─────────────┤
│ Categoria        │ Previsto │ Realizado  │ Variação    │
├──────────────────┼──────────┼────────────┼─────────────┤
│ Contratos Ativos │ 150.000  │ 145.000    │ -3,3% 🔴    │
│ Recuperações     │  10.000  │  12.000    │ +20% 🟢     │
│ Antecipações     │   5.000  │   5.000    │ 0%          │
│ Outras           │   2.000  │   1.500    │ -25% 🔴     │
├──────────────────┼──────────┼────────────┼─────────────┤
│ TOTAL            │ 167.000  │ 163.500    │ -2,1% 🔴    │
└──────────────────┴──────────┴────────────┴─────────────┘

┌─────────────────────────────────────────────────────────┐
│  💸 SAÍDAS DE CAIXA                                     │
├──────────────────┬──────────┬────────────┬─────────────┤
│ Categoria        │ Orçado   │ Realizado  │ Variação    │
├──────────────────┼──────────┼────────────┼─────────────┤
│ OPEX             │  50.000  │  48.500    │ -3% 🟢      │
│ Financeiras      │  20.000  │  21.500    │ +7,5% 🔴    │
│ CAPEX            │  40.000  │  40.000    │ 0%          │
│ Distribuições    │  10.000  │  10.000    │ 0%          │
├──────────────────┼──────────┼────────────┼─────────────┤
│ TOTAL            │ 120.000  │ 120.000    │ 0%          │
└──────────────────┴──────────┴────────────┴─────────────┘

┌─────────────────────────────────────────────────────────┐
│  💼 SALDO DE CAIXA                                      │
├─────────────────────────────────────────────────────────┤
│  Saldo Inicial:  R$  50.000                            │
│  (+) Entradas:   R$ 163.500                            │
│  (-) Saídas:     R$ 120.000                            │
│  ────────────────────────────                           │
│  Saldo Final:    R$  93.500 🟢                         │
│                                                          │
│  Variação: +87% vs período anterior                    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Gerado automaticamente por Starke                      │
│  21/10/2024 às 08:15                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 📧 Envio de Emails (Etapa 4)

### **1. Leitura de Destinatários**

```python
# Conecta no Google Sheets via OAuth2
sheets_client = SheetsClient()
recipients = sheets_client.get_recipients()

# Resultado:
[
    {"name": "João Silva", "email": "joao@example.com"},
    {"name": "Maria Santos", "email": "maria@example.com"},
    {"name": "Pedro Costa", "email": "pedro@example.com"}
]
```

**Formato da Planilha**:
```
     A              B
1  Nome          Email
2  João Silva    joao@example.com
3  Maria Santos  maria@example.com
4  Pedro Costa   pedro@example.com
```

### **2. Envio via SMTP**

```python
email_service = EmailService()

for report in html_reports:
    email_service.send_html_email(
        recipients=recipients,
        subject=f"Fluxo de Caixa - {report['empreendimento_nome']} - 21/10/2024",
        html_body=report['html']  # HTML inline, não anexo!
    )
```

**Resultado**:
```
✅ Email enviado para joao@example.com
✅ Email enviado para maria@example.com
✅ Email enviado para pedro@example.com

Resumo: 3 enviados, 0 falhas
```

---

## 🔐 Idempotência (Anti-Duplicação)

**Problema**: E se o sistema rodar 2x no mesmo dia?

**Solução**: Sistema de idempotência em 3 níveis:

### **Nível 1: Hash de Payload**
```python
# Calcula hash SHA-256 dos dados
payload_hash = hashlib.sha256(json.dumps(data).encode()).hexdigest()

# Verifica se já existe
if exists(source="contratos_emp_123", date="2024-10-21", hash=payload_hash):
    return  # Já processado, ignora
```

### **Nível 2: Constraint Único no Banco**
```sql
ALTER TABLE raw_payloads
ADD CONSTRAINT uq_payload_idempotency
UNIQUE (source, exec_date, payload_hash);
```

### **Nível 3: Registro de Execução**
```python
# Antes de começar
run = Run(exec_date="2024-10-21", status="running")
db.add(run)

try:
    # Executa todo o processamento
    process_everything()

    run.status = "success"
    run.metrics = {"contracts": 150, "emails_sent": 3}
except:
    run.status = "failed"
    run.error = str(exception)
```

---

## 🔍 Monitoramento e Logs

### **Logs Estruturados**

```json
{
  "timestamp": "2024-10-21T08:00:15Z",
  "level": "INFO",
  "event": "workflow_started",
  "ref_date": "2024-10-20",
  "environment": "production"
}

{
  "timestamp": "2024-10-21T08:01:23Z",
  "level": "INFO",
  "event": "ingestion_completed",
  "empreendimento_id": 123,
  "contracts": 50,
  "installments": 180
}

{
  "timestamp": "2024-10-21T08:05:10Z",
  "level": "INFO",
  "event": "emails_sent",
  "sent": 3,
  "failed": 0
}

{
  "timestamp": "2024-10-21T08:05:15Z",
  "level": "INFO",
  "event": "workflow_completed",
  "duration_seconds": 315
}
```

### **Consultar Logs no Servidor**
```bash
# Ver logs do dia
sudo journalctl -u starke.service --since today

# Ver última execução
sudo journalctl -u starke.service -n 100

# Ver erros
sudo journalctl -u starke.service -p err
```

### **Consultar Execuções no Banco**
```sql
-- Últimas 10 execuções
SELECT exec_date, status, started_at, finished_at,
       (finished_at - started_at) as duration
FROM runs
ORDER BY started_at DESC
LIMIT 10;

-- Métricas da última execução bem-sucedida
SELECT exec_date, metrics
FROM runs
WHERE status = 'success'
ORDER BY started_at DESC
LIMIT 1;
```

---

## 🚀 Execução Manual

Você pode executar o sistema manualmente a qualquer momento:

```bash
# Executar para uma data específica
poetry run starke run --date 2024-10-21

# Executar para ontem (padrão)
poetry run starke run

# Dry-run (processa mas não envia emails)
poetry run starke run --dry-run

# Pular ingestão (usar dados já no banco)
poetry run starke run --skip-ingestion

# Especificar empreendimentos
poetry run starke run --empreendimento-ids 123,456,789
```

---

## 🎛️ Configurações Importantes

### **Variáveis de Ambiente (.env)**

```bash
# Data de execução (T-1 automático)
EXECUTION_TIME=08:00
REPORT_TIMEZONE=America/Sao_Paulo

# IDs de empreendimentos (deixar vazio = todos)
# EMPREENDIMENTO_IDS=123,456,789

# Google Sheets
GOOGLE_SHEETS_SPREADSHEET_ID=1ABC...XYZ
GOOGLE_SHEETS_RANGE=Destinatarios!A2:B
```

---

## 📊 Tabelas do Banco de Dados

### **runs** - Registro de Execuções
```
id | exec_date  | status  | started_at          | finished_at         | metrics
---+------------+---------+---------------------+---------------------+----------
1  | 2024-10-21 | success | 2024-10-21 08:00:00 | 2024-10-21 08:05:15 | {...}
2  | 2024-10-22 | success | 2024-10-22 08:00:00 | 2024-10-22 08:04:50 | {...}
```

### **raw_payloads** - Dados Brutos (Auditoria)
```
id | source          | exec_date  | payload_hash  | payload_json
---+-----------------+------------+---------------+--------------
1  | contratos_emp_1 | 2024-10-21 | abc123...     | {...}
2  | parcelas_cto_10 | 2024-10-21 | def456...     | {...}
```

### **cash_in** - Entradas de Caixa
```
id | empreendimento_id | ref_date   | category  | forecast | actual
---+-------------------+------------+-----------+----------+--------
1  | 123               | 2024-10-21 | ativos    | 150000   | 145000
2  | 123               | 2024-10-21 | recuper.. | 10000    | 12000
```

### **cash_out** - Saídas de Caixa
```
id | empreendimento_id | ref_date   | category | budget | actual
---+-------------------+------------+----------+--------+--------
1  | 123               | 2024-10-21 | opex     | 50000  | 48500
2  | 123               | 2024-10-21 | financeir| 20000  | 21500
```

### **balance** - Saldos
```
id | empreendimento_id | ref_date   | opening | closing
---+-------------------+------------+---------+---------
1  | 123               | 2024-10-21 | 50000   | 93500
```

### **portfolio_stats** - Estatísticas da Carteira
```
id | empreendimento_id | ref_date   | vp      | ltv  | prazo_medio | active_contracts
---+-------------------+------------+---------+------+-------------+------------------
1  | 123               | 2024-10-21 | 5000000 | 75.5 | 36.0        | 142
```

---

## ❓ Perguntas Frequentes

### **1. O que acontece se a API Mega estiver fora do ar?**
- O sistema tenta **3 vezes** com backoff exponencial (2s, 4s, 8s)
- Se falhar, registra erro e envia alerta por email
- Pode reprocessar depois: `starke run --date 2024-10-21`

### **2. E se o email não enviar?**
- Sistema tenta enviar para cada destinatário
- Se falhar, registra falha mas continua tentando os outros
- Log mostra quantos foram enviados vs falharam
- Pode reenviar depois processando novamente

### **3. Como adicionar/remover destinatários?**
- Basta editar a planilha do Google Sheets
- Próxima execução pega automaticamente a lista atualizada
- Sem necessidade de reiniciar nada

### **4. Posso processar múltiplas datas de uma vez?**
```bash
# Sim, com um loop bash:
for date in 2024-10-20 2024-10-21 2024-10-22; do
    poetry run starke run --date $date
done
```

### **5. Como ver o HTML do relatório sem enviar?**
```bash
# Modo dry-run salva HTML sem enviar
poetry run starke run --dry-run

# Ou consultar no banco:
SELECT metrics FROM runs ORDER BY started_at DESC LIMIT 1;
```

---

## 🔧 Troubleshooting

### **Sistema não executou às 08:00**
```bash
# Verificar timer
systemctl status starke.timer

# Ver próxima execução
systemctl list-timers | grep starke

# Verificar logs
sudo journalctl -u starke.timer
```

### **Erro de autenticação OAuth2**
```bash
# Re-autenticar
poetry run starke auth-sheets

# Verificar credenciais
ls -la secrets/sheets-credentials.json
cat .env | grep GOOGLE_SHEETS
```

### **Banco de dados com erro**
```bash
# Verificar conexão
PGPASSWORD='...' psql -h 66.94.104.117 -U cxggichesjlqkw -d starke -c '\dt'

# Ver migrations aplicadas
PGPASSWORD='...' psql -h 66.94.104.117 -U cxggichesjlqkw -d starke -c 'SELECT * FROM alembic_version'
```

---

## 📚 Documentos Relacionados

- [README.md](../README.md) - Documentação geral
- [QUICK_START.md](QUICK_START.md) - Guia rápido de instalação
- [GOOGLE_SHEETS_OAUTH_SETUP.md](GOOGLE_SHEETS_OAUTH_SETUP.md) - Setup OAuth2
- [deploy/DEPLOYMENT.md](../deploy/DEPLOYMENT.md) - Deploy em produção

---

**🎉 Sistema pronto para uso! Execute `poetry run starke run --dry-run` para testar!**

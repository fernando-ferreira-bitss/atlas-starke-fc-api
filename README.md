# Starke - Sistema de Relatórios de Fluxo de Caixa

Sistema automatizado para coleta, processamento e envio de relatórios diários de fluxo de caixa.

## Arquitetura

O projeto segue os princípios de **Clean Architecture** com separação clara de responsabilidades:

```
src/starke/
├── domain/           # Entidades e lógica de negócio
│   ├── entities/     # Modelos de domínio
│   ├── repositories/ # Interfaces de repositórios
│   └── services/     # Serviços de domínio
├── infrastructure/   # Implementações de infraestrutura
│   ├── database/     # SQLAlchemy models e repositories
│   ├── external_apis/# Clientes de APIs externas
│   ├── email/        # Serviços de email
│   └── sheets/       # Integração Google Sheets
├── api/             # Camada de API (opcional para futuro)
├── presentation/    # Templates e assets
└── core/            # Configurações e utilities
```

## Requisitos

- Python 3.11+
- Poetry
- PostgreSQL 16+
- Docker & Docker Compose (recomendado)

## Instalação

### Opção 1: Usando Docker (Recomendado)

```bash
# Start PostgreSQL e aplicação
docker-compose up -d

# Ver logs
docker-compose logs -f starke

# Executar comandos dentro do container
docker-compose exec starke poetry run starke --help
```

### Opção 2: Local com Poetry

```bash
# 1. Certifique-se que PostgreSQL está rodando
# Via Docker:
docker-compose up -d postgres

# Ou instalado localmente:
# brew install postgresql (macOS)
# sudo apt install postgresql (Ubuntu)

# 2. Instalar dependências
poetry install

# 3. Ativar ambiente virtual
poetry shell

# 4. Criar banco de dados
createdb starke

# 5. Criar banco de dados de testes (opcional, para rodar testes)
createdb starke_test

# 6. Rodar migrações
poetry run alembic upgrade head
```

### Usando Docker

```bash
# Build e start
docker-compose up -d

# Ver logs
docker-compose logs -f starke
```

## Configuração

1. Copie o arquivo de exemplo:
```bash
cp .env.example .env
```

2. Configure as variáveis de ambiente no `.env`:
   - Credenciais da API Mega
   - Configurações de email (SMTP ou Gmail API)
   - Configurações do Google Sheets
   - Timezone e horário de execução

3. Configure credenciais do Google:
```bash
# Coloque o arquivo de service account em:
./secrets/google-service-account.json
```

## Uso

### Execução Manual

```bash
# Executar relatório para uma data específica
poetry run starke run --date 2024-10-21

# Executar para ontem (T-1)
poetry run starke run

# Dry-run sem enviar emails
poetry run starke run --dry-run
```

### Agendamento

O sistema deve ser executado diariamente às 08:00. Configure usando:

#### systemd (Linux)

```bash
# Copiar unit files
sudo cp deploy/starke.service /etc/systemd/system/
sudo cp deploy/starke.timer /etc/systemd/system/

# Habilitar e iniciar
sudo systemctl enable starke.timer
sudo systemctl start starke.timer
```

#### cron (alternativa)

```bash
# Adicionar ao crontab
0 8 * * * cd /path/to/starke && poetry run starke run
```

## Desenvolvimento

### Executar testes

```bash
# Todos os testes
poetry run pytest

# Com coverage
poetry run pytest --cov

# Apenas unit tests
poetry run pytest tests/unit
```

### Formatação e Linting

```bash
# Format code
poetry run black src/ tests/

# Lint
poetry run ruff check src/ tests/

# Type check
poetry run mypy src/
```

## Estrutura do Banco de Dados (PostgreSQL)

- `runs`: Execuções do job
- `raw_payloads`: Payloads brutos da API (com idempotência)
- `cash_in`: Entradas de caixa por empreendimento
- `cash_out`: Saídas de caixa por empreendimento
- `balance`: Saldos de caixa
- `portfolio_stats`: Estatísticas de carteira (VP, LTV, prazo médio, duration)

### Migrações

```bash
# Criar nova migração
poetry run alembic revision --autogenerate -m "description"

# Aplicar migrações
poetry run alembic upgrade head

# Reverter última migração
poetry run alembic downgrade -1
```

## API Mega ERP

O sistema integra com as seguintes rotas da API Mega:

- `/api/Carteira/DadosContrato/IdEmpreendimento={id}` - Lista contratos por empreendimento
- `/api/Carteira/DadosParcelas/IdContrato={id}` - Dados de parcelas
- Outras rotas conforme necessário para coleta de dados

## Observabilidade

- Logs estruturados (JSON em produção, pretty-print em dev)
- Métricas de execução armazenadas no banco
- Alertas por email em caso de falhas

## Licença

Proprietário - Starke

# Guia de Deployment - Starke

Este documento descreve o processo completo de deployment do sistema Starke em um servidor de produção.

## Pré-requisitos

- Ubuntu 22.04 LTS (ou superior)
- PostgreSQL 16+
- Python 3.11+
- Acesso sudo no servidor
- Credenciais configuradas:
  - API Mega ERP
  - Google Sheets Service Account
  - Servidor SMTP

## 1. Preparação do Servidor

### 1.1 Atualizar sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Instalar dependências

```bash
# PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Python e ferramentas
sudo apt install -y python3.11 python3.11-venv python3-pip git

# Poetry
curl -sSL https://install.python-poetry.org | python3 -
```

### 1.3 Criar usuário do sistema

```bash
sudo useradd -r -m -d /opt/starke -s /bin/bash starke
sudo usermod -aG sudo starke  # Apenas se necessário para setup
```

### 1.4 Configurar PostgreSQL

```bash
# Criar usuário e banco
sudo -u postgres psql << EOF
CREATE USER starke WITH PASSWORD 'senha_segura_aqui';
CREATE DATABASE starke OWNER starke;
GRANT ALL PRIVILEGES ON DATABASE starke TO starke;
EOF

# Permitir conexão local
sudo nano /etc/postgresql/16/main/pg_hba.conf
# Adicionar:
# local   starke          starke                                  md5

sudo systemctl restart postgresql
```

## 2. Deployment da Aplicação

### 2.1 Clonar repositório

```bash
sudo su - starke
cd /opt/starke
git clone <repository-url> .
```

### 2.2 Configurar ambiente Python

```bash
poetry install --only main
```

### 2.3 Configurar variáveis de ambiente

```bash
cp .env.example .env
nano .env
```

Edite o `.env` com as credenciais de produção:

```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

DATABASE_URL=postgresql://starke:senha_segura_aqui@localhost:5432/starke

MEGA_API_URL=https://api.mega.com.br
MEGA_API_USERNAME=techstarke
MEGA_API_PASSWORD=<senha-api>

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=relatorios@example.com
SMTP_PASSWORD=<senha-smtp>
SMTP_USE_TLS=true

EMAIL_FROM_NAME=Relatórios Starke
EMAIL_FROM_ADDRESS=relatorios@example.com

GOOGLE_SHEETS_SPREADSHEET_ID=<id-da-planilha>
GOOGLE_SHEETS_RANGE=Destinatarios!A2:B

REPORT_TIMEZONE=America/Sao_Paulo
EXECUTION_TIME=08:00
```

### 2.4 Configurar credenciais do Google

```bash
mkdir -p /opt/starke/secrets
chmod 700 /opt/starke/secrets

# Copiar arquivo JSON do service account
nano /opt/starke/secrets/google-service-account.json
# Colar o conteúdo do arquivo JSON

chmod 600 /opt/starke/secrets/google-service-account.json
```

### 2.5 Criar estrutura de diretórios

```bash
mkdir -p /opt/starke/data
mkdir -p /opt/starke/logs
chmod 755 /opt/starke/data /opt/starke/logs
```

### 2.6 Inicializar banco de dados

```bash
poetry run alembic upgrade head
```

### 2.7 Testar configuração

```bash
# Testar configuração geral
poetry run starke config

# Testar conexão com Google Sheets
poetry run starke test-sheets

# Testar envio de email
poetry run starke test-email admin@example.com

# Executar dry-run
poetry run starke run --dry-run
```

## 3. Configurar Systemd

### 3.1 Instalar unit files

```bash
sudo cp /opt/starke/deploy/starke.service /etc/systemd/system/
sudo cp /opt/starke/deploy/starke.timer /etc/systemd/system/

# Ajustar permissões
sudo chmod 644 /etc/systemd/system/starke.service
sudo chmod 644 /etc/systemd/system/starke.timer
```

### 3.2 Configurar timezone no servidor

```bash
sudo timedatectl set-timezone America/Sao_Paulo
timedatectl  # Verificar
```

### 3.3 Habilitar e iniciar timer

```bash
# Recarregar systemd
sudo systemctl daemon-reload

# Habilitar timer para iniciar no boot
sudo systemctl enable starke.timer

# Iniciar timer
sudo systemctl start starke.timer

# Verificar status
sudo systemctl status starke.timer
sudo systemctl list-timers --all | grep starke
```

## 4. Monitoramento e Logs

### 4.1 Visualizar logs

```bash
# Logs do serviço
sudo journalctl -u starke.service -f

# Logs do timer
sudo journalctl -u starke.timer -f

# Logs das últimas 24 horas
sudo journalctl -u starke.service --since "24 hours ago"

# Logs de execução específica
sudo journalctl -u starke.service --since "2024-10-22 08:00" --until "2024-10-22 08:30"
```

### 4.2 Verificar execuções

```bash
# Ver quando foi a última execução
systemctl show starke.timer | grep Last

# Ver próxima execução agendada
systemctl show starke.timer | grep Next
```

### 4.3 Consultar banco de dados

```bash
sudo -u starke psql starke << EOF
-- Ver últimas execuções
SELECT id, exec_date, status, started_at, finished_at
FROM runs
ORDER BY started_at DESC
LIMIT 10;

-- Ver métricas da última execução
SELECT exec_date, metrics
FROM runs
WHERE status = 'success'
ORDER BY finished_at DESC
LIMIT 1;
EOF
```

## 5. Manutenção

### 5.1 Executar manualmente

```bash
sudo -u starke bash
cd /opt/starke
poetry run starke run --date 2024-10-21
```

### 5.2 Atualizar código

```bash
sudo -u starke bash
cd /opt/starke
git pull
poetry install
poetry run alembic upgrade head
sudo systemctl restart starke.timer
```

### 5.3 Backup do banco de dados

```bash
# Criar backup
sudo -u postgres pg_dump starke > /backup/starke-$(date +%Y%m%d).sql

# Restaurar backup
sudo -u postgres psql starke < /backup/starke-20241022.sql
```

### 5.4 Rotação de logs

Criar arquivo `/etc/logrotate.d/starke`:

```
/opt/starke/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 starke starke
    sharedscripts
    postrotate
        systemctl reload starke.service > /dev/null 2>&1 || true
    endscript
}
```

## 6. Troubleshooting

### Problema: Serviço não executa

```bash
# Verificar status
sudo systemctl status starke.service
sudo journalctl -u starke.service -n 50

# Verificar permissões
ls -la /opt/starke
ls -la /opt/starke/secrets

# Testar execução manual
sudo -u starke bash
cd /opt/starke
poetry run starke run --dry-run
```

### Problema: Emails não enviados

```bash
# Verificar configuração SMTP
sudo -u starke bash
cd /opt/starke
poetry run starke test-email seu@email.com

# Verificar logs para erros SMTP
sudo journalctl -u starke.service | grep -i smtp
```

### Problema: Erro de conexão com Google Sheets

```bash
# Verificar permissões do arquivo
ls -la /opt/starke/secrets/google-service-account.json

# Testar conexão
sudo -u starke bash
cd /opt/starke
poetry run starke test-sheets

# Verificar se service account tem acesso à planilha
```

### Problema: Erro de conexão com banco

```bash
# Verificar se PostgreSQL está rodando
sudo systemctl status postgresql

# Testar conexão
sudo -u starke psql -h localhost -U starke -d starke

# Verificar URL de conexão no .env
cat /opt/starke/.env | grep DATABASE_URL
```

## 7. Segurança

### 7.1 Permissões de arquivos

```bash
# .env deve ser legível apenas pelo usuário starke
chmod 600 /opt/starke/.env

# Secrets directory
chmod 700 /opt/starke/secrets
chmod 600 /opt/starke/secrets/*

# Data directory
chmod 755 /opt/starke/data
```

### 7.2 Firewall (se aplicável)

```bash
# Permitir apenas conexões locais ao PostgreSQL
sudo ufw allow from 127.0.0.1 to any port 5432
```

### 7.3 Atualizar senhas regularmente

- Senha do banco de dados
- Senha da API Mega
- Senha SMTP
- Rotacionar service account do Google

## 8. Checklist de Deployment

- [ ] Servidor preparado com todas dependências
- [ ] PostgreSQL instalado e configurado
- [ ] Usuário `starke` criado
- [ ] Código clonado em `/opt/starke`
- [ ] Dependências Python instaladas
- [ ] Arquivo `.env` configurado com credenciais de produção
- [ ] Credenciais do Google configuradas em `/opt/starke/secrets`
- [ ] Banco de dados inicializado (migrations aplicadas)
- [ ] Testes de configuração executados com sucesso
- [ ] Systemd service e timer instalados
- [ ] Timer habilitado e iniciado
- [ ] Logs monitorados por 24-48h para validar
- [ ] Backup configurado
- [ ] Documentação atualizada com informações específicas do ambiente

## Contato e Suporte

Para questões ou problemas, entre em contato com:
- Email: tech@atlastech.com
- Documentação: [GitHub Repository]

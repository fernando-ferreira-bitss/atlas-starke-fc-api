# Quick Start - Starke

Guia rápido para começar a usar o Starke.

## 1. Pré-requisitos

```bash
# Verificar versões
python --version  # Deve ser 3.11+
docker --version
```

## 2. Setup Inicial

### 2.1 Clonar e Instalar

```bash
cd /caminho/para/starke
poetry install
```

### 2.2 Subir PostgreSQL

```bash
docker-compose up -d postgres
```

### 2.3 Criar Bancos

```bash
createdb starke
createdb starke_test  # Para testes
```

### 2.4 Aplicar Migrations

```bash
poetry run alembic revision --autogenerate -m "Initial schema"
poetry run alembic upgrade head
```

## 3. Configurar Integrações

### 3.1 Google Sheets (OAuth2)

**Sua organização bloqueia Service Accounts, então use OAuth2:**

1. **Criar credenciais no Google Cloud Console**:
   - Acesse: https://console.cloud.google.com/
   - APIs e Serviços > Credenciais
   - Criar Credenciais > ID do cliente OAuth
   - Tipo: App para computador
   - Baixar JSON

2. **Instalar credenciais**:
   ```bash
   mkdir -p secrets
   mv ~/Downloads/client_secret_*.json secrets/sheets-credentials.json
   chmod 600 secrets/sheets-credentials.json
   ```

3. **Configurar .env**:
   ```bash
   GOOGLE_SHEETS_USE_OAUTH=true
   GOOGLE_SHEETS_SPREADSHEET_ID=<seu-id-aqui>
   GOOGLE_SHEETS_RANGE=Destinatarios!A2:B
   ```

4. **Autenticar (abre navegador)**:
   ```bash
   poetry run starke auth-sheets
   ```

📖 **Guia completo**: `docs/GOOGLE_SHEETS_OAUTH_SETUP.md`

### 3.2 Email (SMTP)

Já configurado no `.env` com suas credenciais:
- ✅ SMTP_HOST: smtp.gmail.com
- ✅ SMTP_USERNAME: brainitsolutionscwb@gmail.com
- ✅ Senha configurada

**Testar**:
```bash
poetry run starke test-email seu@email.com
```

### 3.3 API Mega

Já configurado no `.env`:
- ✅ Username: techstarke
- ✅ Senha: configurada

## 4. Primeiros Testes

### 4.1 Ver Configuração

```bash
poetry run starke config
```

### 4.2 Testar Integrações

```bash
# Email
poetry run starke test-email seu@email.com

# Google Sheets (após auth-sheets)
poetry run starke test-sheets
```

### 4.3 Executar Dry-Run

```bash
# Processa dados mas não envia emails
poetry run starke run --dry-run --date 2024-10-21
```

### 4.4 Executar Real

```bash
# Processa e envia emails
poetry run starke run --date 2024-10-21
```

## 5. Estrutura da Planilha Google Sheets

A planilha deve ter este formato:

| Nome (A) | Email (B) |
|----------|-----------|
| João Silva | joao@example.com |
| Maria Santos | maria@example.com |

- **Coluna A**: Nome do destinatário (opcional)
- **Coluna B**: Email do destinatário (obrigatório)
- Começar da linha 2 (linha 1 é cabeçalho)

## 6. Comandos Disponíveis

```bash
# Ver ajuda
poetry run starke --help

# Inicializar banco
poetry run starke init

# Executar relatório
poetry run starke run [--date YYYY-MM-DD] [--dry-run]

# Autenticar Google Sheets (OAuth2)
poetry run starke auth-sheets

# Testar email
poetry run starke test-email EMAIL

# Testar Google Sheets
poetry run starke test-sheets

# Ver configuração
poetry run starke config
```

## 7. Rodar Testes

```bash
# Todos os testes
poetry run pytest

# Com coverage
poetry run pytest --cov

# Apenas unit tests
poetry run pytest tests/unit -v

# Apenas integration tests
poetry run pytest tests/integration -v
```

## 8. Troubleshooting

### Erro: "Service Account bloqueado"

✅ **Solução**: Use OAuth2 (já configurado)
```bash
poetry run starke auth-sheets
```

### Erro: "Database connection failed"

```bash
# Verificar se PostgreSQL está rodando
docker-compose ps

# Ver logs
docker-compose logs postgres

# Reiniciar
docker-compose restart postgres
```

### Erro: "SMTP authentication failed"

Verifique as credenciais no `.env`:
- SMTP_USERNAME
- SMTP_PASSWORD

Se usar Gmail com 2FA, precisa de "App Password".

### Erro: "Google Sheets API not enabled"

1. Acesse: https://console.cloud.google.com/
2. APIs e Serviços > Biblioteca
3. Busque "Google Sheets API"
4. Clique em "Ativar"

## 9. Próximos Passos

1. ✅ Setup completo
2. ⏭️ Executar primeiro relatório de teste
3. ⏭️ Validar dados no banco
4. ⏭️ Testar envio de emails
5. ⏭️ Deploy em produção (ver `deploy/DEPLOYMENT.md`)

## 10. Arquivos Importantes

```
starke/
├── .env                    ← Suas credenciais
├── secrets/
│   ├── sheets-credentials.json   ← Credenciais OAuth2
│   └── sheets-token.pickle       ← Token (gerado por auth-sheets)
├── data/
│   └── starke.db (ou PostgreSQL)
└── logs/
```

## 11. Links Úteis

- 📖 [Documentação Completa](README.md)
- 🔐 [Setup OAuth2 Google Sheets](GOOGLE_SHEETS_OAUTH_SETUP.md)
- 🚀 [Guia de Deployment](../deploy/DEPLOYMENT.md)
- 📊 [Escopo do Projeto](rascunho-escopo-fluxo-caixa.md)

## Suporte

Dúvidas? Entre em contato:
- Email: tech@atlastech.com
- GitHub Issues: [link-do-repo]

---

**Pronto para começar!** Execute:
```bash
poetry run starke auth-sheets  # Primeiro
poetry run starke run --dry-run  # Depois
```

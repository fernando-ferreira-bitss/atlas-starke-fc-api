# Configuração OAuth2 para Google Sheets

Como sua organização bloqueia a criação de chaves de Service Account, vamos usar **OAuth2** com um usuário real.

## Diferença entre Service Account e OAuth2

| Service Account | OAuth2 (Usuário) |
|----------------|------------------|
| ❌ Requer chave JSON | ✅ Usa token do usuário |
| ❌ Bloqueado pela sua org | ✅ Permitido |
| ✅ Totalmente automatizado | ⚠️ Requer autenticação inicial |
| ✅ Compartilhar planilha com email da SA | ✅ Usa planilha do próprio usuário |

## Passo a Passo Completo

### 1. Criar Credenciais OAuth2 no Google Cloud

1. Acesse: https://console.cloud.google.com/
2. Selecione seu projeto (ou crie um novo)
3. No menu lateral: **"APIs e Serviços"** > **"Credenciais"**
4. Clique em **"Criar Credenciais"** > **"ID do cliente OAuth"**
5. Se solicitado, configure a **Tela de consentimento OAuth**:
   - Tipo: Interno (se disponível) ou Externo
   - Nome do app: "Starke Reports"
   - Email de suporte: seu email
   - Domínio autorizado: pode deixar em branco
   - Email do desenvolvedor: seu email
   - Salvar e continuar
6. Em **"Escopos"**, adicione:
   - `https://www.googleapis.com/auth/spreadsheets.readonly`
7. Volte para **"Credenciais"** > **"Criar Credenciais"** > **"ID do cliente OAuth"**
8. Tipo de aplicativo: **"App para computador"**
9. Nome: "Starke Desktop Client"
10. Clique em **"Criar"**
11. **Baixe o arquivo JSON** (botão de download)
12. Renomeie para `sheets-credentials.json`

### 2. Instalar o arquivo de credenciais

```bash
# Criar diretório secrets (se não existir)
mkdir -p secrets

# Mover o arquivo baixado
mv ~/Downloads/client_secret_*.json secrets/sheets-credentials.json

# Proteger permissões
chmod 600 secrets/sheets-credentials.json
```

### 3. Atualizar configuração

Edite o `.env`:

```bash
# Remover (ou comentar) esta linha:
# GOOGLE_SHEETS_CREDENTIALS_FILE=./secrets/google-service-account.json

# Adicionar:
GOOGLE_SHEETS_USE_OAUTH=true
GOOGLE_SHEETS_SPREADSHEET_ID=1ABC...XYZ  # ID da sua planilha
GOOGLE_SHEETS_RANGE=Destinatarios!A2:B
```

### 4. Autenticar pela primeira vez

Execute o comando de autenticação:

```bash
poetry run starke auth-sheets
```

**O que vai acontecer:**
1. Abrirá uma janela no navegador
2. Faça login com sua conta Google
3. Autorize o app "Starke Reports" a acessar suas planilhas
4. Verá mensagem: "The authentication flow has completed"
5. Um arquivo `sheets-token.pickle` será salvo em `./secrets/`

### 5. Testar

```bash
poetry run starke test-sheets
```

Se funcionar, você verá:
```
✅ Conexão com Google Sheets OK!

📋 Destinatários encontrados: 5

Primeiros 5 destinatários:
   1. João Silva <joao@example.com>
   2. Maria Santos <maria@example.com>
   ...
```

## Estrutura Final

```
starke/
├── secrets/
│   ├── sheets-credentials.json  ← Credenciais OAuth2 (fixo)
│   └── sheets-token.pickle      ← Token do usuário (renovável)
└── .env
```

## Atualizar código para usar OAuth2

Edite `src/starke/infrastructure/sheets/__init__.py`:

```python
"""Google Sheets integration."""

import os
from starke.core.config import get_settings

# Escolher cliente baseado na configuração
settings = get_settings()

if os.getenv("GOOGLE_SHEETS_USE_OAUTH", "false").lower() == "true":
    from starke.infrastructure.sheets.sheets_oauth_client import SheetsOAuthClient as SheetsClient
else:
    from starke.infrastructure.sheets.sheets_client import SheetsClient

__all__ = ["SheetsClient"]
```

## Como funciona OAuth2

1. **Primeira vez**: Autenticação interativa (navegador)
2. **Token salvo**: Válido por ~7 dias
3. **Renovação automática**: Quando expira, renova automaticamente
4. **Re-autenticação**: Apenas se token de refresh expirar (raro)

## Vantagens desta abordagem

✅ **Não precisa de Service Account** (contorna a política da org)
✅ **Token renovável** (não precisa refazer autenticação sempre)
✅ **Mais seguro** (não armazena chaves privadas)
✅ **Usa suas próprias planilhas** (não precisa compartilhar)

## Troubleshooting

### Erro: "Access blocked: Starke Reports has not completed the Google verification process"

**Solução**: Use tipo "Interno" na tela de consentimento (se sua org permitir) ou adicione seu email como testador:
- Console > OAuth consent screen > Test users > Add users

### Token expirou

```bash
# Remover token antigo
rm secrets/sheets-token.pickle

# Autenticar novamente
poetry run starke auth-sheets
```

### Erro de permissões

Verifique se o escopo está correto:
```
https://www.googleapis.com/auth/spreadsheets.readonly
```

## Deploy em Produção

Para servidores sem interface gráfica:

1. **Autentique localmente** (no seu computador):
   ```bash
   poetry run starke auth-sheets
   ```

2. **Copie o token para o servidor**:
   ```bash
   scp secrets/sheets-token.pickle servidor:/opt/starke/secrets/
   ```

3. **No servidor**, garanta permissões:
   ```bash
   chmod 600 /opt/starke/secrets/sheets-token.pickle
   chown starke:starke /opt/starke/secrets/sheets-token.pickle
   ```

4. **Renovação automática** funcionará sem problemas

## Resumo

- ✅ OAuth2 **não requer** chaves de Service Account
- ✅ Autenticação **uma vez** (token salvo)
- ✅ Renovação **automática**
- ✅ Compatível com políticas de segurança da organização

**Pronto para começar? Execute `poetry run starke auth-sheets`!**

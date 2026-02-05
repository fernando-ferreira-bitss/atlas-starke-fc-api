# 🚀 Deploy Rápido - Portainer via GitHub

## Pré-requisitos
- ✅ Código já está no GitHub
- ✅ Acesso admin no Portainer
- ✅ Arquivo `.env` local (vamos copiar as variáveis)

---

## Passo 1: Push das Últimas Alterações

```bash
# No seu Mac
cd /Users/fernandoferreira/Documents/projetos/atlas/starke

git add .
git commit -m "feat: Add Portainer deploy files and fix scheduler for dev environment"
git push
```

---

## Passo 2: Criar Config do mega_mapping.yaml no Portainer

### 2.1 Copiar o conteúdo do arquivo

```bash
# No seu Mac - copiar para clipboard
cat config/mega_mapping.yaml | pbcopy
```

### 2.2 No Portainer

1. **Ir em: Configs** → **Add config**
2. **Preencher**:
   - Name: `starke-mega-mapping`
   - Config: **Colar o conteúdo** (Cmd+V)
3. **Create config**

---

## Passo 3: Criar Stack no Portainer

### 3.1 No Portainer

1. **Ir em: Stacks** → **Add stack**
2. **Preencher**:
   - **Name**: `starke`
   - **Build method**: ✅ **Repository**

### 3.2 Repository configuration

- **Repository URL**: `https://github.com/SEU_USUARIO/starke`
- **Repository reference**: `refs/heads/main` (ou `refs/heads/master`)
- **Compose path**: `docker-compose.portainer.yml`

Se repositório é privado:
- Marcar **Authentication**
- Adicionar **Token** ou **Username/Password**

### 3.3 Environment variables

**Copiar TODAS as variáveis do seu `.env` local e colar aqui:**

Adicione uma por uma ou use o formato:

```env
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

MEGA_API_URL=https://rest.megaerp.online
MEGA_API_TENANT_ID=1odi394df4-2bho-4b0f-by3e-4ebaddi3820e
MEGA_API_USERNAME=techstarke
MEGA_API_PASSWORD=SUA_SENHA_AQUI
MEGA_API_TIMEOUT=30
MEGA_API_MAX_RETRIES=3

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=SEU_EMAIL
SMTP_PASSWORD=SUA_SENHA
SMTP_USE_TLS=true

EMAIL_FROM_NAME=Relatórios Starke
EMAIL_FROM_ADDRESS=SEU_EMAIL

JWT_SECRET_KEY=GERAR_UM_NOVO_AQUI
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

REPORT_TIMEZONE=America/Sao_Paulo
TEST_MODE=false
```

**⚠️ IMPORTANTE**: Gerar novo JWT_SECRET_KEY:
```bash
# No seu Mac
openssl rand -hex 32
```

### 3.4 Deploy

**Clicar em: "Deploy the stack"**

---

## Passo 4: Verificar Deployment

### 4.1 Ver Logs

1. **Containers** → **starke-api** → **Logs**
2. Procurar por: `"Scheduler disabled in development environment"` ✅

### 4.2 Testar API

**Acessar no navegador:**
```
http://SEU_SERVIDOR:8000/health
```

Deve retornar:
```json
{"status":"ok"}
```

### 4.3 Ver Documentação (Swagger)

```
http://SEU_SERVIDOR:8000/docs
```

---

## Passo 5: Executar Comandos

### Via Console do Portainer

1. **Containers** → **starke-api** → **Console** (ícone >_)
2. **Connect** → Selecionar `/bin/bash`

### Comandos úteis:

```bash
# Verificar estrutura
ls -la /app/

# Ver se config existe
cat /app/config/mega_mapping.yaml

# Rodar sync manual
python -m starke.cli sync-contracts

# Rodar backfill de dados históricos
python -m starke.cli backfill --start-date=2025-01-01 --end-date=2025-12-31

# Ver status do banco
python -m starke.cli db-status
```

---

## 🔄 Atualizar Aplicação no Futuro

### Quando fizer alterações no código:

```bash
# 1. No seu Mac - fazer push
git add .
git commit -m "Update"
git push

# 2. No Portainer
# Stacks → starke → "Update the stack"
# Marcar: "Pull latest image"
# Clicar: "Update"
```

---

## ⚠️ Troubleshooting

### Container não inicia

1. Ver logs detalhados: **Containers** → **starke-api** → **Logs**
2. Verificar se todas variáveis estão OK: **Container details** → **Env**
3. Verificar se config existe: Console → `ls -la /app/config/`

### Erro "Config not found"

Significa que o Config `starke-mega-mapping` não foi criado. Voltar no Passo 2.

### Erro de conexão com banco

1. Ver logs do PostgreSQL: **Containers** → **starke-postgres** → **Logs**
2. Aguardar 30s (healthcheck precisa passar)
3. Verificar se porta 5432 está livre no host

---

## ✅ Checklist Final

Antes de fazer deploy, confirme:

- [ ] Código atualizado no GitHub (com `docker-compose.portainer.yml`)
- [ ] Config `starke-mega-mapping` criado no Portainer
- [ ] Todas variáveis do `.env` copiadas
- [ ] JWT_SECRET_KEY gerado (não usar o padrão!)
- [ ] ENVIRONMENT=development (scheduler desabilitado)
- [ ] Senhas/tokens corretos

---

## 🎯 Próximos Passos Após Deploy

1. ✅ Acessar http://SEU_SERVIDOR:8000/docs
2. ✅ Testar endpoint /health
3. ✅ Rodar sync manual via console
4. ✅ Fazer backfill inicial
5. ✅ Verificar dados no PostgreSQL

---

**Está tudo pronto! Basta seguir os 5 passos acima.**

URL do repositório: `https://github.com/SEU_USUARIO/starke`

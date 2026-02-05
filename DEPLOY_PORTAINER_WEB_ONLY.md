# Deploy Starke via Portainer (Somente Web - SEM SSH)

## 📋 Pré-requisitos

1. ✅ Acesso admin ao Portainer
2. ✅ Código no Git (GitHub/GitLab/Bitbucket) **OU** Docker Hub
3. ✅ Arquivo `.env` local (vamos converter para variáveis)
4. ✅ Arquivo `config/mega_mapping.yaml` (vamos criar como Config)

---

## 🚀 Método 1: Deploy via Git Repository (RECOMENDADO)

### Passo 1: Preparar Repositório Git

1. **Criar repositório no GitHub/GitLab**
   - Pode ser privado ou público
   - Nome sugerido: `starke`

2. **Push do código para o Git**:
   ```bash
   # No seu Mac
   cd /Users/fernandoferreira/Documents/projetos/atlas/starke

   # Se ainda não tem git inicializado
   git init
   git add .
   git commit -m "Initial commit"

   # Adicionar repositório remoto
   git remote add origin https://github.com/SEU_USUARIO/starke.git
   git branch -M main
   git push -u origin main
   ```

3. **⚠️ IMPORTANTE: Não commitar o .env com credenciais!**
   - Adicione `.env` ao `.gitignore`
   - Vamos configurar as variáveis direto no Portainer

### Passo 2: Criar Docker Config para mega_mapping.yaml

No Portainer:

1. **Ir em: Configs → Add config**

2. **Preencher**:
   - **Name**: `starke-mega-mapping`
   - **Config content**: Cole o conteúdo completo de `/Users/fernandoferreira/Documents/projetos/atlas/starke/config/mega_mapping.yaml`

3. **Clicar em: Create config**

### Passo 3: Criar Stack no Portainer

1. **Ir em: Stacks → Add stack**

2. **Preencher**:
   - **Name**: `starke`
   - **Build method**: Selecione **Repository**

3. **Repository configuration**:
   - **Repository URL**: `https://github.com/SEU_USUARIO/starke`
   - **Repository reference**: `refs/heads/main`
   - **Compose path**: `docker-compose.portainer.yml`
   - **Authentication**: Se privado, adicionar token/chave

4. **Environment variables** - Adicionar TODAS as variáveis do seu `.env`:

   ```env
   ENVIRONMENT=development
   DEBUG=true
   LOG_LEVEL=INFO

   MEGA_API_URL=https://rest.megaerp.online
   MEGA_API_TENANT_ID=seu_tenant_id
   MEGA_API_USERNAME=seu_usuario
   MEGA_API_PASSWORD=sua_senha
   MEGA_API_TIMEOUT=30
   MEGA_API_MAX_RETRIES=3

   DATABASE_URL=postgresql://starke_user:starke_password@postgres:5432/starke_db

   EMAIL_BACKEND=smtp
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=seu_email@gmail.com
   SMTP_PASSWORD=sua_senha_smtp
   SMTP_USE_TLS=true

   EMAIL_FROM_NAME=Relatórios Starke
   EMAIL_FROM_ADDRESS=seu_email@gmail.com

   JWT_SECRET_KEY=gere_um_secret_key_aqui
   JWT_ALGORITHM=HS256
   JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

   REPORT_TIMEZONE=America/Sao_Paulo
   EXECUTION_TIME=08:00
   DATE_FORMAT=%Y-%m-%d

   ALERT_EMAIL_RECIPIENTS=admin@example.com
   TEST_MODE=false
   TEST_EMAIL_RECIPIENT=seu@email.com
   ```

5. **Clicar em: Deploy the stack**

### Passo 4: Verificar Deployment

1. **Ver containers rodando**:
   - Ir em **Containers**
   - Verificar `starke-api` e `starke-postgres` com status "running"

2. **Ver logs**:
   - Clicar em `starke-api`
   - Ir na aba **Logs**
   - Deve ver: "Scheduler disabled in development environment"

3. **Testar API**:
   - Ir em **Container details** → **Published Ports**
   - Acessar `http://SEU_SERVIDOR:8000/health`
   - Deve retornar: `{"status":"ok"}`

---

## 🚀 Método 2: Deploy via Docker Hub

### Passo 1: Build e Push da Imagem (no seu Mac)

```bash
cd /Users/fernandoferreira/Documents/projetos/atlas/starke

# Login no Docker Hub
docker login

# Build da imagem
docker build -t SEU_USUARIO/starke:latest .

# Push para Docker Hub
docker push SEU_USUARIO/starke:latest
```

### Passo 2: Criar Stack com Imagem do Docker Hub

No Portainer, criar stack com este docker-compose:

```yaml
version: '3.8'

services:
  starke-api:
    image: SEU_USUARIO/starke:latest  # Imagem do Docker Hub
    container_name: starke-api
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://starke_user:starke_password@postgres:5432/starke_db
      # Adicione TODAS as variáveis do .env aqui
    configs:
      - source: starke-mega-mapping
        target: /app/config/mega_mapping.yaml
    volumes:
      - starke-data:/app/data
      - starke-logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - starke-network
    restart: unless-stopped
    command: >
      sh -c "
        sleep 5 &&
        alembic upgrade head &&
        python -m uvicorn starke.api.main:app --host 0.0.0.0 --port 8000
      "

  postgres:
    image: postgres:16-alpine
    container_name: starke-postgres
    environment:
      POSTGRES_USER: starke_user
      POSTGRES_PASSWORD: starke_password
      POSTGRES_DB: starke_db
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - starke-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U starke_user"]
      interval: 10s
      timeout: 5s
      retries: 5

configs:
  starke-mega-mapping:
    external: true

volumes:
  postgres-data:
  starke-data:
  starke-logs:

networks:
  starke-network:
```

---

## 📝 Configurando o mega_mapping.yaml via Portainer Config

### Como criar o Config no Portainer:

1. **Copiar o conteúdo do arquivo localmente**:
   ```bash
   cat /Users/fernandoferreira/Documents/projetos/atlas/starke/config/mega_mapping.yaml
   ```

2. **No Portainer**:
   - **Configs** → **Add config**
   - **Name**: `starke-mega-mapping`
   - **Config**: Colar todo o conteúdo do YAML
   - **Create**

3. **O Config será montado automaticamente no container** em `/app/config/mega_mapping.yaml`

---

## 🔧 Comandos Úteis via Portainer Console

### Acessar Console do Container

1. **Ir em Containers → starke-api**
2. **Clicar em Console** (ícone >_)
3. **Selecionar /bin/bash**

### Executar comandos:

```bash
# Ver estrutura de diretórios
ls -la /app/

# Verificar se config existe
cat /app/config/mega_mapping.yaml

# Rodar sync manual
python -m starke.cli sync-contracts

# Rodar backfill
python -m starke.cli backfill --start-date=2025-01-01 --end-date=2025-12-31

# Ver migrations
alembic history

# Rodar migrations
alembic upgrade head
```

---

## 🔄 Atualizar Aplicação

### Via Git (se usou Método 1):

1. **Fazer push das alterações no Git**:
   ```bash
   # No seu Mac
   git add .
   git commit -m "Update"
   git push
   ```

2. **No Portainer**:
   - **Stacks → starke**
   - **Clicar em "Update the stack"**
   - Marcar **"Pull latest image"**
   - **Update**

### Via Docker Hub (se usou Método 2):

1. **Build e push nova versão**:
   ```bash
   # No seu Mac
   docker build -t SEU_USUARIO/starke:latest .
   docker push SEU_USUARIO/starke:latest
   ```

2. **No Portainer**:
   - **Containers → starke-api**
   - **Recreate**
   - Marcar **"Pull latest image"**
   - **Recreate**

---

## ⚠️ Troubleshooting

### Container não inicia

1. **Ver logs**: Containers → starke-api → Logs
2. **Verificar env vars**: Containers → starke-api → Env (aba Environment)
3. **Verificar config**: Console → `cat /app/config/mega_mapping.yaml`

### Erro de conexão com banco

1. **Ver logs do PostgreSQL**: Containers → starke-postgres → Logs
2. **Testar conexão**: Console do starke-api → `psql -h postgres -U starke_user -d starke_db`

### API não responde

1. **Ver Published Ports**: Containers → starke-api → porta 8000
2. **Testar health**: `curl http://localhost:8000/health`
3. **Ver logs em tempo real**: Logs (marcar "Auto-refresh logs")

---

## 🎯 Próximos Passos Após Deploy

1. ✅ Verificar que scheduler está desabilitado (ver logs)
2. ✅ Testar API: `http://SEU_SERVIDOR:8000/docs`
3. ✅ Rodar sync manual via Console
4. ✅ Verificar se dados estão sendo salvos no PostgreSQL
5. ✅ Fazer backfill inicial dos dados históricos

---

## 💡 Dica: Gerar JWT Secret Key

Para gerar um secret key seguro:

```bash
# No seu Mac, gerar e copiar
openssl rand -hex 32

# Ou no Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copie o resultado e use como `JWT_SECRET_KEY` no Portainer.

---

## 📞 Checklist Final

Antes de fazer deploy, confirme:

- [ ] Código está no Git OU imagem no Docker Hub
- [ ] Config `starke-mega-mapping` criado no Portainer
- [ ] Todas variáveis do `.env` configuradas no Portainer
- [ ] JWT_SECRET_KEY foi gerado (não usar o padrão!)
- [ ] Credenciais Mega API estão corretas
- [ ] ENVIRONMENT=development (para desabilitar scheduler)

---

**Está tudo pronto!** Qual método você prefere usar: Git ou Docker Hub?

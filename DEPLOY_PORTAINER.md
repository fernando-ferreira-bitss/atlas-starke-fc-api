# Deploy Starke no Portainer - Guia Completo

## 📋 Pré-requisitos

1. **Portainer** instalado e rodando
2. **Git** instalado no servidor (para clonar o código)
3. Acesso ao servidor via SSH
4. Credenciais da API Mega

---

## 🚀 Passo a Passo - Deploy Manual

### 1. Preparar o Servidor

Conecte no servidor via SSH e crie o diretório do projeto:

```bash
# Criar diretório do projeto
mkdir -p ~/apps/starke
cd ~/apps/starke

# Clonar ou copiar o código do projeto
# Opção A: Se o projeto está no Git
git clone <URL_DO_REPOSITORIO> .

# Opção B: Usar rsync/scp para copiar código local
# (executar na máquina local)
rsync -av --exclude='.git' --exclude='__pycache__' /Users/fernandoferreira/Documents/projetos/atlas/starke/ usuario@servidor:~/apps/starke/
```

### 2. Copiar Arquivo de Configuração ESSENCIAL

**IMPORTANTE:** O arquivo `config/mega_mapping.yaml` é **obrigatório**!

```bash
# Verificar se o arquivo existe
ls -la config/mega_mapping.yaml

# Se não existe, copiar da máquina local:
scp /Users/fernandoferreira/Documents/projetos/atlas/starke/config/mega_mapping.yaml usuario@servidor:~/apps/starke/config/
```

### 3. Copiar Arquivo .env

```bash
# Copiar .env da máquina local para o servidor
scp /Users/fernandoferreira/Documents/projetos/atlas/starke/.env usuario@servidor:~/apps/starke/.env

# OU criar no servidor:
cd ~/apps/starke
nano .env
```

Cole o conteúdo do seu `.env` atual e ajuste conforme necessário.

### 4. Criar docker-compose.yml para Portainer

No servidor, crie o arquivo `docker-compose.portainer.yml`:

```bash
cd ~/apps/starke
nano docker-compose.portainer.yml
```

Cole o conteúdo abaixo:

```yaml
version: '3.8'

services:
  # ============================================
  # Starke API
  # ============================================
  starke-api:
    build:
      context: .
      target: development
    container_name: starke-api
    image: starke-api:latest
    volumes:
      # Código fonte (só para desenvolvimento)
      - ./src:/app/src
      # Configuração ESSENCIAL
      - ./config:/app/config:ro
      # Variáveis de ambiente
      - ./.env:/app/.env:ro
      # Dados persistentes
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-development}
      - DATABASE_URL=postgresql://starke_user:starke_password@postgres:5432/starke_db
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - starke-network
    restart: unless-stopped
    command: >
      sh -c "
        echo 'Waiting for database...' &&
        sleep 5 &&
        echo 'Running migrations...' &&
        alembic upgrade head &&
        echo 'Starting API...' &&
        python -m uvicorn starke.api.main:app --host 0.0.0.0 --port 8000 --reload
      "
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # ============================================
  # PostgreSQL Database
  # ============================================
  postgres:
    image: postgres:16-alpine
    container_name: starke-postgres
    environment:
      POSTGRES_USER: starke_user
      POSTGRES_PASSWORD: starke_password
      POSTGRES_DB: starke_db
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - starke-network
    ports:
      - "5433:5432"  # Porta 5433 externa para evitar conflitos
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U starke_user -d starke_db"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

volumes:
  postgres-data:
    driver: local

networks:
  starke-network:
    driver: bridge
```

### 5. Deploy no Portainer

1. **Acessar Portainer**:
   - Abra o Portainer no navegador
   - Vá em **Stacks** → **Add stack**

2. **Configurar Stack**:
   - **Name**: `starke`
   - **Build method**: Selecione **Repository** ou **Upload**

3. **Opção A - Via Repository (Git)**:
   - Repository URL: `<URL_DO_SEU_GIT>`
   - Compose path: `docker-compose.portainer.yml`
   - Marque **Enable GitOps updates** (opcional)

4. **Opção B - Upload Manual**:
   - Copie todo o conteúdo de `docker-compose.portainer.yml`
   - Cole no editor do Portainer

5. **Environment Variables** (se necessário):
   - Adicione qualquer variável extra que precise sobrescrever
   - Exemplo: `ENVIRONMENT=development`

6. **Deploy**:
   - Clique em **Deploy the stack**
   - Aguarde os containers subirem

### 6. Verificar Deployment

```bash
# Ver logs da API
docker logs -f starke-api

# Ver logs do PostgreSQL
docker logs -f starke-postgres

# Verificar se containers estão rodando
docker ps | grep starke

# Testar API
curl http://localhost:8000/health
```

Você deve ver:
```json
{"status":"ok"}
```

### 7. Acessar a Aplicação

- **API**: http://SEU_SERVIDOR:8000
- **Documentação (Swagger)**: http://SEU_SERVIDOR:8000/docs
- **Página de Monitoramento**: http://SEU_SERVIDOR:8000/scheduler

---

## 📝 Notas Importantes

### Sobre o Scheduler (Agendamento Automático)

**Em Development (`ENVIRONMENT=development`):**
- ✅ Scheduler **DESABILITADO** automaticamente
- Você pode testar a sincronização manualmente via API ou CLI

**Em Production (`ENVIRONMENT=production`):**
- ✅ Scheduler **ATIVADO** automaticamente
- Sincroniza diariamente conforme configurado

### Arquivos Essenciais

1. **`config/mega_mapping.yaml`** ⚠️ **OBRIGATÓRIO**
   - Contém mapeamentos de categorias (opex, capex, etc)
   - Sem ele, o sistema não funciona!

2. **`.env`** ⚠️ **OBRIGATÓRIO**
   - Credenciais Mega API
   - Configurações de banco
   - Configurações de email (se usar)

3. **`src/`** - Código fonte da aplicação

---

## 🔧 Comandos Úteis

### Executar Comandos no Container

```bash
# Entrar no container
docker exec -it starke-api bash

# Rodar sync manual
docker exec -it starke-api python -m starke.cli sync-contracts

# Rodar backfill
docker exec -it starke-api python -m starke.cli backfill --start-date=2025-01-01 --end-date=2025-12-31

# Ver logs das migrations
docker exec -it starke-api alembic history

# Rodar migration manualmente
docker exec -it starke-api alembic upgrade head
```

### Gerenciar Banco de Dados

```bash
# Conectar ao PostgreSQL
docker exec -it starke-postgres psql -U starke_user -d starke_db

# Fazer backup
docker exec starke-postgres pg_dump -U starke_user starke_db > backup_$(date +%Y%m%d).sql

# Restaurar backup
cat backup.sql | docker exec -i starke-postgres psql -U starke_user -d starke_db
```

---

## 🔄 Atualizar Aplicação

```bash
# 1. Parar stack no Portainer
# (ou via linha de comando)
cd ~/apps/starke
docker-compose -f docker-compose.portainer.yml down

# 2. Atualizar código
git pull
# OU
rsync -av --exclude='.git' /Users/fernandoferreira/Documents/projetos/atlas/starke/ usuario@servidor:~/apps/starke/

# 3. Rebuild e restart no Portainer
# (ou via linha de comando)
docker-compose -f docker-compose.portainer.yml build --no-cache
docker-compose -f docker-compose.portainer.yml up -d
```

---

## ⚠️ Troubleshooting

### Container não inicia

```bash
# Ver logs completos
docker logs starke-api

# Verificar se o .env está correto
docker exec -it starke-api env | grep MEGA

# Verificar se config existe
docker exec -it starke-api ls -la /app/config/
```

### Erro de conexão com banco

```bash
# Verificar se PostgreSQL está rodando
docker ps | grep postgres

# Testar conexão
docker exec -it starke-postgres psql -U starke_user -d starke_db -c "SELECT 1;"
```

### API não responde

```bash
# Verificar health
curl http://localhost:8000/health

# Ver logs em tempo real
docker logs -f starke-api
```

---

## 🎯 Próximos Passos

Após deployment bem-sucedido:

1. ✅ Testar sincronização manual
2. ✅ Verificar se scheduler está desabilitado em dev
3. ✅ Fazer backfill inicial dos dados
4. ✅ Testar API endpoints via Swagger
5. ✅ Configurar backup automático do banco

---

## 📞 Suporte

Se tiver problemas, verifique:
1. Logs do container: `docker logs starke-api`
2. Status do health check: `curl http://localhost:8000/health`
3. Conexão com banco: `docker exec -it starke-postgres psql -U starke_user`

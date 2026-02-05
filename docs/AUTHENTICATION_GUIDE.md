# Guia de Autenticação e Gerenciamento de Destinatários

## 📋 Resumo das Mudanças

O sistema Starke foi atualizado com as seguintes melhorias:

1. ✅ **Autenticação de Usuários** - Sistema completo de login com JWT
2. ✅ **API REST com FastAPI** - Endpoints para gerenciar usuários e destinatários
3. ✅ **Cadastro de Destinatários no Banco** - Substituição do Google Sheets por banco de dados
4. ✅ **Remoção do Google Sheets** - Integração removida completamente

---

## 🚀 Instalação

### 1. Instalar Dependências

```bash
poetry install
```

Novas dependências adicionadas:
- `fastapi` - Framework web para API REST
- `uvicorn` - Servidor ASGI para FastAPI
- `python-jose` - JWT token generation
- `passlib` - Password hashing
- `python-multipart` - Form data handling

### 2. Configurar Variáveis de Ambiente

Atualize seu arquivo `.env` com as novas configurações:

```bash
# Authentication & Security
# IMPORTANT: Change this in production! Generate with: openssl rand -hex 32
JWT_SECRET_KEY=change-this-secret-key-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**⚠️ IMPORTANTE:** Gere uma chave secreta segura em produção:

```bash
openssl rand -hex 32
```

### 3. Remover Configurações Antigas (Opcional)

As seguintes variáveis de ambiente não são mais necessárias:
- `GOOGLE_SHEETS_CREDENTIALS_FILE`
- `GOOGLE_SHEETS_USE_OAUTH`
- `GOOGLE_SHEETS_SPREADSHEET_ID`
- `GOOGLE_SHEETS_RANGE`

---

## 👤 Gerenciamento de Usuários

### Criar Primeiro Usuário (Admin)

```bash
starke create-user --superuser
```

Você será solicitado a fornecer:
- Email
- Password (mínimo 8 caracteres)

### Listar Usuários

```bash
starke list-users
```

### Via API

Depois de autenticado, você pode gerenciar usuários via API:

**Login:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=senha123"
```

Resposta:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Criar Usuário:**
```bash
curl -X POST http://localhost:8000/api/auth/users \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "senha123",
    "is_superuser": false
  }'
```

**Listar Usuários:**
```bash
curl http://localhost:8000/api/auth/users \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📧 Gerenciamento de Destinatários de Email

### Via API

Agora os destinatários são gerenciados pelo banco de dados via API REST.

**Criar Destinatário Global (todos os empreendimentos):**
```bash
curl -X POST http://localhost:8000/api/email-recipients \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "João Silva",
    "email": "joao@example.com",
    "is_active": true
  }'
```

**Criar Destinatário para Empreendimento Específico:**
```bash
curl -X POST http://localhost:8000/api/email-recipients \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Maria Santos",
    "email": "maria@example.com",
    "empreendimento_id": 123,
    "is_active": true
  }'
```

**Listar Destinatários:**
```bash
# Todos os destinatários
curl http://localhost:8000/api/email-recipients \
  -H "Authorization: Bearer YOUR_TOKEN"

# Destinatários de um empreendimento específico (inclui globais)
curl "http://localhost:8000/api/email-recipients?empreendimento_id=123" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Incluir inativos
curl "http://localhost:8000/api/email-recipients?active_only=false" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Atualizar Destinatário:**
```bash
curl -X PUT http://localhost:8000/api/email-recipients/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "João Silva Jr.",
    "email": "joao.jr@example.com"
  }'
```

**Desativar Destinatário (soft delete):**
```bash
curl -X POST http://localhost:8000/api/email-recipients/1/deactivate \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Ativar Destinatário:**
```bash
curl -X POST http://localhost:8000/api/email-recipients/1/activate \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Deletar Destinatário (hard delete):**
```bash
curl -X DELETE http://localhost:8000/api/email-recipients/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🖥️ Iniciar o Servidor API

### Modo Desenvolvimento (com auto-reload)

```bash
starke serve --reload
```

### Modo Produção

```bash
starke serve --host 0.0.0.0 --port 8000
```

### Acessar Documentação

Depois de iniciar o servidor:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 🔄 Migração do Google Sheets

Se você já possui destinatários no Google Sheets, você pode migrá-los manualmente para o banco de dados:

1. Exporte os dados do Google Sheets para CSV
2. Crie um script Python para importar:

```python
import csv
from starke.infrastructure.database.base import SessionLocal
from starke.domain.services.email_recipient_service import EmailRecipientService

def migrate_from_csv(csv_file_path):
    with SessionLocal() as db:
        service = EmailRecipientService(db)

        with open(csv_file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    service.create_recipient(
                        name=row['name'],
                        email=row['email'],
                        empreendimento_id=int(row['empreendimento_id']) if row.get('empreendimento_id') else None,
                        is_active=True
                    )
                    print(f"✅ Migrated: {row['name']} <{row['email']}>")
                except Exception as e:
                    print(f"❌ Error migrating {row['email']}: {e}")

if __name__ == "__main__":
    migrate_from_csv("recipients.csv")
```

---

## 🔒 Segurança

### Boas Práticas

1. **JWT Secret Key:**
   - Use uma chave forte e única em produção
   - Gere com: `openssl rand -hex 32`
   - Nunca cometa a chave no Git

2. **Senhas:**
   - Mínimo 8 caracteres
   - Use senhas fortes para usuários admin

3. **HTTPS:**
   - Em produção, use sempre HTTPS
   - Configure SSL/TLS no proxy reverso (nginx, caddy, etc)

4. **CORS:**
   - Ajuste `allow_origins` em `src/starke/api/main.py`
   - Em produção, substitua `["*"]` por domínios específicos

### Permissões

- **Superuser (Admin):**
  - Criar, listar, atualizar e deletar usuários
  - Acesso total à API

- **Usuário Normal:**
  - Gerenciar destinatários de email
  - Não pode gerenciar outros usuários

---

## 📊 Estrutura do Banco de Dados

### Tabela `users`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Primary key |
| email | String | Email único |
| hashed_password | String | Senha hash (bcrypt) |
| is_active | Boolean | Usuário ativo |
| is_superuser | Boolean | Admin flag |
| created_at | DateTime | Data de criação |
| updated_at | DateTime | Última atualização |

### Tabela `email_recipients`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Primary key |
| name | String | Nome do destinatário |
| email | String | Email |
| empreendimento_id | Integer (NULL) | ID do empreendimento (NULL = global) |
| is_active | Boolean | Destinatário ativo |
| created_at | DateTime | Data de criação |
| updated_at | DateTime | Última atualização |

---

## 🧪 Testes

### Testar Autenticação

```bash
# Criar usuário de teste
starke create-user

# Iniciar servidor
starke serve --reload

# Fazer login (outro terminal)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=senha123"
```

### Testar Destinatários

```bash
# Criar destinatário
curl -X POST http://localhost:8000/api/email-recipients \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "email": "test@example.com", "is_active": true}'

# Listar destinatários
curl http://localhost:8000/api/email-recipients \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🐛 Solução de Problemas

### Erro: "Could not validate credentials"

- Verifique se o token JWT não expirou (padrão: 30 minutos)
- Faça login novamente para obter novo token

### Erro: "User with email X already exists"

- Email já está cadastrado
- Use outro email ou atualize o usuário existente

### Erro: "Not enough permissions"

- Usuário não tem privilégios de superuser
- Use um usuário admin para essa operação

### Erro ao importar módulos

- Execute `poetry install` para instalar todas as dependências
- Verifique se está usando o ambiente virtual correto

---

## 📝 Comandos CLI Disponíveis

```bash
# Gerenciamento de Usuários
starke create-user          # Criar novo usuário
starke create-user --superuser  # Criar admin
starke list-users           # Listar usuários

# API Server
starke serve                # Iniciar servidor API
starke serve --reload       # Modo desenvolvimento
starke serve --host 0.0.0.0 --port 8000  # Customizar host/porta

# Comandos Existentes
starke run                  # Executar workflow
starke init                 # Inicializar banco
starke test-email          # Testar email
starke config              # Ver configuração
```

---

## 🎯 Próximos Passos

1. **Instalar dependências:** `poetry install`
2. **Gerar JWT secret:** `openssl rand -hex 32` e adicionar ao `.env`
3. **Criar primeiro admin:** `starke create-user --superuser`
4. **Iniciar API:** `starke serve --reload`
5. **Migrar destinatários** do Google Sheets para o banco de dados
6. **Testar workflow:** `starke run --dry-run`

---

## 📚 Referências

- FastAPI Documentation: https://fastapi.tiangolo.com/
- JWT Authentication: https://jwt.io/
- SQLAlchemy ORM: https://docs.sqlalchemy.org/
- Pydantic Settings: https://docs.pydantic.dev/

# 🎨 Guia do Frontend Web - Starke

## 📋 Visão Geral

O Starke agora possui um **frontend web completo** desenvolvido com:
- **Python + FastAPI** - Backend que renderiza HTML
- **Jinja2** - Template engine
- **HTMX** - Interatividade moderna sem JavaScript complexo
- **TailwindCSS** - Estilização responsiva
- **Alpine.js** - Pequenas interações (dropdowns, modais)

**Tudo em Python!** Uma aplicação unificada, fácil de manter e deployar.

---

## 🚀 Como Usar

### 1. Instalar Dependências

```bash
poetry install
```

### 2. Configurar Banco de Dados

```bash
# Inicializar banco (se ainda não fez)
starke init
```

### 3. Criar Primeiro Usuário Admin

```bash
starke create-user --superuser
```

Exemplo:
```
Email: admin@starke.com
Password: ******** (mínimo 8 caracteres)
✅ Usuário criado com sucesso! ID: 1
🔑 Privilégios de administrador concedidos
```

### 4. Iniciar Servidor Web

```bash
starke serve --reload
```

Ou especificar porta:
```bash
starke serve --host 0.0.0.0 --port 8000 --reload
```

### 5. Acessar Interface Web

Abra no navegador:
```
http://localhost:8000
```

---

## 🖥️ Páginas Disponíveis

### 🔐 Login (`/login`)
- Autenticação com email e senha
- Sessão segura com cookies HTTP-only
- Mensagens de erro amigáveis

### 📊 Dashboard (`/dashboard`)
- Visão geral do sistema
- Cards com estatísticas:
  - Total de usuários
  - Total de destinatários
  - Destinatários ativos
- Ações rápidas
- Informações do sistema

### 👥 Gerenciar Usuários (`/users`)
- **Apenas para Administradores**
- Listar todos os usuários
- Criar novo usuário
- Ver tipo (Admin / Usuário)
- Ver status (Ativo / Inativo)
- Deletar usuário

### 📧 Gerenciar Destinatários (`/recipients`)
- Listar todos os destinatários
- Filtrar por status (Ativo / Inativo / Todos)
- Criar novo destinatário
- Especificar empreendimento (ou deixar global)
- Ativar / Desativar destinatário
- Deletar destinatário

---

## ✨ Funcionalidades

### 🔄 Atualização Dinâmica (HTMX)

Todas as ações são feitas **sem recarregar a página**:
- ✅ Criar usuário → lista atualiza automaticamente
- ✅ Deletar destinatário → lista atualiza automaticamente
- ✅ Ativar/Desativar → status muda instantaneamente

### 📱 Responsivo

Interface adaptável para:
- 💻 Desktop
- 📱 Tablet
- 📱 Mobile

### 🎨 Componentes Modernos

- **Modais** - Para criar/editar
- **Dropdowns** - Menu de usuário
- **Loading indicators** - Feedback visual
- **Status badges** - Cores por tipo/status
- **Toast notifications** - Mensagens de sucesso/erro

### 🔒 Segurança

- ✅ Autenticação baseada em sessão
- ✅ Cookies HTTP-only (protege contra XSS)
- ✅ CSRF protection via SameSite
- ✅ Senhas hasheadas com bcrypt
- ✅ Controle de permissões (admin vs usuário)

---

## 🎯 Fluxo de Uso

### Primeiro Acesso

1. **Criar Admin via CLI:**
   ```bash
   starke create-user --superuser
   ```

2. **Iniciar servidor:**
   ```bash
   starke serve --reload
   ```

3. **Fazer login:**
   - Acesse http://localhost:8000
   - Entre com email e senha do admin
   - Será redirecionado para o dashboard

### Gerenciar Usuários (Admin)

1. Clique em **"Usuários"** no menu
2. Clique em **"Novo Usuário"**
3. Preencha:
   - Email
   - Senha (mínimo 8 caracteres)
   - Marque "Administrador" se for admin
4. Clique em **"Criar Usuário"**
5. Lista atualiza automaticamente

### Gerenciar Destinatários

1. Clique em **"Destinatários"** no menu
2. Clique em **"Novo Destinatário"**
3. Preencha:
   - Nome
   - Email
   - Empreendimento ID (deixe vazio para global)
   - Status (Ativo/Inativo)
4. Clique em **"Adicionar"**
5. Lista atualiza automaticamente

**Destinatário Global vs Específico:**
- **Global** (sem empreendimento_id): Recebe relatórios de TODOS os empreendimentos
- **Específico** (com empreendimento_id): Recebe apenas de um empreendimento

---

## 🔧 Arquitetura Técnica

### Backend (Python)

```
src/starke/api/routes/web.py
├── Rotas públicas
│   ├── GET  /              → Redirect para dashboard
│   ├── GET  /login         → Página de login
│   ├── POST /login         → Processar login
│   └── GET  /logout        → Logout
│
├── Rotas protegidas (requer autenticação)
│   ├── GET  /dashboard     → Dashboard
│   ├── GET  /users         → Gerenciar usuários (admin only)
│   └── GET  /recipients    → Gerenciar destinatários
│
├── Endpoints HTMX (retornam HTML)
│   ├── GET  /api/web/users           → Lista de usuários
│   ├── POST /api/web/users           → Criar usuário
│   ├── DELETE /api/web/users/{id}    → Deletar usuário
│   ├── GET  /api/web/recipients      → Lista de destinatários
│   ├── POST /api/web/recipients      → Criar destinatário
│   ├── POST /api/web/recipients/{id}/activate   → Ativar
│   ├── POST /api/web/recipients/{id}/deactivate → Desativar
│   └── DELETE /api/web/recipients/{id} → Deletar
│
└── Stats API (para dashboard)
    ├── GET  /api/stats/users             → Total de usuários
    ├── GET  /api/stats/recipients        → Total de destinatários
    └── GET  /api/stats/active-recipients → Destinatários ativos
```

### Frontend (Templates)

```
src/starke/presentation/web/templates/
├── base.html              → Layout base (nav, footer)
├── login.html             → Página de login
├── dashboard.html         → Dashboard
├── users.html             → Gerenciar usuários
├── recipients.html        → Gerenciar destinatários
└── partials/
    ├── users_list.html      → Tabela de usuários
    └── recipients_list.html → Tabela de destinatários
```

### Sessão e Autenticação

```python
# Ao fazer login:
1. Valida credenciais
2. Cria token de sessão com itsdangerous
3. Define cookie HTTP-only
4. Redireciona para dashboard

# Em cada requisição protegida:
1. Lê cookie de sessão
2. Valida token
3. Busca usuário no banco
4. Verifica se está ativo
5. Permite acesso ou redireciona para login
```

---

## 🎨 Customização

### Cores e Estilos

O template usa **TailwindCSS via CDN**. Para customizar:

**Editar `base.html`:**
```html
<style>
    .btn-primary {
        @apply bg-blue-600 hover:bg-blue-700 ...
    }
    /* Mude as cores aqui */
</style>
```

**Classes principais:**
- `.btn-primary` - Botão primário (azul)
- `.btn-secondary` - Botão secundário (cinza)
- `.btn-danger` - Botão de deletar (vermelho)
- `.btn-success` - Botão de sucesso (verde)
- `.input-field` - Campos de input
- `.card` - Cards com sombra

### Logo e Branding

**Editar `base.html`:**
```html
<a href="/dashboard" class="text-2xl font-bold text-blue-600">
    📊 Starke  <!-- Mude aqui -->
</a>
```

### Adicionar Páginas

1. **Criar template:**
   ```html
   <!-- templates/minha_pagina.html -->
   {% extends "base.html" %}
   {% block content %}
       <h1>Minha Página</h1>
   {% endblock %}
   ```

2. **Adicionar rota em `web.py`:**
   ```python
   @router.get("/minha-pagina", response_class=HTMLResponse)
   async def minha_pagina(
       request: Request,
       user: Annotated[User, Depends(require_auth)],
   ):
       return templates.TemplateResponse(
           "minha_pagina.html",
           {"request": request, "user": user},
       )
   ```

3. **Adicionar link na navegação (`base.html`):**
   ```html
   <a href="/minha-pagina" class="...">
       Minha Página
   </a>
   ```

---

## 🐛 Solução de Problemas

### Erro: "Template not found"

Verifique o caminho dos templates em `web.py`:
```python
templates = Jinja2Templates(directory="src/starke/presentation/web/templates")
```

Certifique-se de estar executando o comando **da raiz do projeto**.

### Erro: "Session expired"

A sessão expira após 30 minutos (padrão). Faça login novamente.

Para alterar:
```env
# .env
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### Interface não carrega estilos

Verifique se tem acesso à internet (TailwindCSS e HTMX são carregados via CDN).

Para usar offline, baixe os arquivos e sirva localmente:
```python
app.mount("/static", StaticFiles(directory="src/starke/presentation/web/static"), name="static")
```

### "Apenas administradores podem acessar"

A página `/users` é **exclusiva para admins**. Certifique-se de:
```bash
starke create-user --superuser  # Flag --superuser é obrigatória
```

---

## 🚀 Deploy em Produção

### 1. Variáveis de Ambiente

```bash
# .env
ENVIRONMENT=production
DEBUG=false

# IMPORTANTE: Gere uma chave segura!
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Banco de dados
DATABASE_URL=postgresql://user:pass@host:5432/starke
```

### 2. Iniciar com Gunicorn

```bash
gunicorn starke.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### 3. Proxy Reverso (Nginx)

```nginx
server {
    listen 80;
    server_name starke.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. HTTPS (Certbot)

```bash
certbot --nginx -d starke.example.com
```

### 5. Systemd Service

```ini
# /etc/systemd/system/starke-web.service
[Unit]
Description=Starke Web Application
After=network.target

[Service]
Type=notify
User=starke
WorkingDirectory=/opt/starke
Environment="PATH=/opt/starke/.venv/bin"
ExecStart=/opt/starke/.venv/bin/gunicorn starke.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable starke-web
systemctl start starke-web
```

---

## 📊 Estatísticas de Código

```
Frontend completo implementado em:
- 8 templates HTML
- 1 arquivo de rotas Python (web.py)
- ~600 linhas de código

Funcionalidades:
✅ Sistema de login
✅ Sessão segura
✅ Dashboard interativo
✅ CRUD de usuários
✅ CRUD de destinatários
✅ Interface responsiva
✅ Atualizações em tempo real (HTMX)
```

---

## 🎯 Próximos Passos Possíveis

### Melhorias Futuras

1. **Upload de Avatar** - Foto de perfil do usuário
2. **Histórico de Ações** - Log de atividades
3. **Busca e Filtros Avançados** - Pesquisar usuários/destinatários
4. **Importação em Massa** - Upload CSV de destinatários
5. **Dashboard com Gráficos** - Visualizações de dados
6. **Notificações** - Alertas em tempo real
7. **Dark Mode** - Tema escuro
8. **Exportar Dados** - Download de listas em CSV/Excel
9. **Edição Inline** - Editar sem abrir modal
10. **2FA (Two-Factor Auth)** - Segurança extra

---

## 📚 Referências

- **HTMX:** https://htmx.org/
- **TailwindCSS:** https://tailwindcss.com/
- **Alpine.js:** https://alpinejs.dev/
- **Jinja2:** https://jinja.palletsprojects.com/
- **FastAPI Templates:** https://fastapi.tiangolo.com/advanced/templates/

---

## 🎉 Conclusão

Você agora tem um **frontend web completo e moderno**, tudo construído em **Python**!

**Vantagens desta abordagem:**
- ✅ Uma aplicação só (backend + frontend)
- ✅ Deploy simplificado
- ✅ Manutenção fácil (tudo em Python)
- ✅ Interativo (HTMX)
- ✅ Moderno e responsivo (TailwindCSS)
- ✅ Seguro (sessões, CSRF, permissions)

**Comandos principais:**
```bash
# Criar admin
starke create-user --superuser

# Iniciar servidor
starke serve --reload

# Acessar
http://localhost:8000
```

Aproveite! 🚀

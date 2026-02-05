# Endpoints de Configuracoes do Usuario

Documentacao das rotas para a tela de configuracoes do cliente (`/cliente/configuracoes`).

---

## Visao Geral

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/v1/auth/me` | GET | Obter dados do usuario logado |
| `/api/v1/auth/me` | PUT | Atualizar perfil (nome/email) |
| `/api/v1/auth/me/preferences` | GET | Obter preferencias |
| `/api/v1/auth/me/preferences` | PUT | Atualizar preferencias |
| `/api/v1/auth/forgot-password` | POST | Solicitar reset de senha |
| `/api/v1/auth/reset-password` | POST | Redefinir senha com token |
| `/api/v1/auth/change-password` | POST | Trocar senha (autenticado) |

---

## 1. Obter Dados do Usuario

### `GET /api/v1/auth/me`

Retorna informacoes do usuario logado incluindo permissoes e preferencias.

**Headers:**
```
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "usuario@email.com",
  "full_name": "Nome do Usuario",
  "role": "client",
  "is_active": true,
  "permissions": ["MY_PORTFOLIO", "MY_DOCUMENTS"],
  "preferences": {
    "default_currency": "BRL",
    "theme": "light"
  }
}
```

---

## 2. Atualizar Perfil do Usuario

### `PUT /api/v1/auth/me`

Permite ao usuario atualizar seu nome e/ou email.

**Headers:**
```
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "full_name": "Novo Nome",
  "email": "novo.email@email.com"
}
```

> **Nota:** Ambos os campos sao opcionais. Envie apenas o que deseja atualizar.

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "novo.email@email.com",
  "full_name": "Novo Nome",
  "role": "client",
  "is_active": true,
  "permissions": ["MY_PORTFOLIO", "MY_DOCUMENTS"],
  "preferences": {
    "default_currency": "BRL",
    "theme": "light"
  }
}
```

**Erros:**
- `400 Bad Request` - Email ja cadastrado por outro usuario

---

## 3. Obter Preferencias

### `GET /api/v1/auth/me/preferences`

Retorna apenas as preferencias do usuario.

**Headers:**
```
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "default_currency": "BRL",
  "theme": "light"
}
```

---

## 4. Atualizar Preferencias

### `PUT /api/v1/auth/me/preferences`

Atualiza as preferencias do usuario.

**Headers:**
```
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "default_currency": "USD",
  "theme": "dark"
}
```

**Campos disponiveis:**

| Campo | Tipo | Valores | Default |
|-------|------|---------|---------|
| `default_currency` | string | Codigo da moeda (ex: "BRL", "USD") | "BRL" |
| `theme` | string | "light" ou "dark" | "light" |

**Response (200 OK):**
```json
{
  "default_currency": "USD",
  "theme": "dark"
}
```

---

## 5. Solicitar Reset de Senha

### `POST /api/v1/auth/forgot-password`

Envia email com link para redefinir senha.

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "usuario@email.com"
}
```

**Response (200 OK):**
```json
{
  "message": "Se o email estiver cadastrado, voce recebera um link para redefinir sua senha."
}
```

> **Seguranca:** Sempre retorna sucesso, mesmo se o email nao existir (previne enumeracao de emails).

---

## 6. Redefinir Senha com Token

### `POST /api/v1/auth/reset-password`

Redefine a senha usando o token recebido por email.

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "token": "token_recebido_por_email",
  "new_password": "nova_senha_123"
}
```

**Response (204 No Content):** Senha alterada com sucesso.

**Erros:**
- `400 Bad Request` - Token invalido ou expirado

---

## 7. Trocar Senha (Autenticado)

### `POST /api/v1/auth/change-password`

Permite ao usuario logado trocar sua senha (requer senha atual).

**Headers:**
```
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "current_password": "senha_atual",
  "new_password": "nova_senha_123"
}
```

**Requisitos da nova senha:**
- Minimo 6 caracteres
- Maximo 100 caracteres

**Response (204 No Content):** Senha alterada com sucesso.

**Erros:**
- `400 Bad Request` - Senha atual incorreta

---

## Fluxo de Uso - Tela de Configuracoes

### Carregar Tela

1. Chamar `GET /api/v1/auth/me` para obter todos os dados do usuario

### Salvar Alteracoes de Perfil

1. Chamar `PUT /api/v1/auth/me` com os campos alterados

### Salvar Preferencias

1. Chamar `PUT /api/v1/auth/me/preferences` com as preferencias

### Trocar Senha

**Opcao 1 - Usuario sabe a senha atual:**
1. Chamar `POST /api/v1/auth/change-password` com senha atual e nova

**Opcao 2 - Usuario esqueceu a senha:**
1. Chamar `POST /api/v1/auth/forgot-password` com o email
2. Usuario recebe email com link
3. Frontend redireciona para `/reset-password?token=...`
4. Chamar `POST /api/v1/auth/reset-password` com token e nova senha

---

## Exemplo de Integracao (TypeScript)

```typescript
// Obter dados do usuario
const getUserProfile = async () => {
  const response = await fetch('/api/v1/auth/me', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};

// Atualizar perfil
const updateProfile = async (data: { full_name?: string; email?: string }) => {
  const response = await fetch('/api/v1/auth/me', {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });
  return response.json();
};

// Atualizar preferencias
const updatePreferences = async (preferences: { default_currency?: string; theme?: string }) => {
  const response = await fetch('/api/v1/auth/me/preferences', {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(preferences)
  });
  return response.json();
};

// Solicitar reset de senha
const forgotPassword = async (email: string) => {
  const response = await fetch('/api/v1/auth/forgot-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  });
  return response.json();
};
```

---

**Ultima Atualizacao:** 2025-12-09

# Recuperação de Senha - Guia de Integração Frontend

Documentação para implementação do fluxo de recuperação de senha no frontend.

---

## Visão Geral do Fluxo

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Tela de Login  │────▶│ Esqueci Senha   │────▶│  Checar Email   │
│                 │     │ (inserir email) │     │   (mensagem)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Login Normal   │◀────│ Senha Alterada  │◀────│  Nova Senha     │
│                 │     │   (sucesso)     │     │ (inserir senha) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Endpoints da API

### 1. Solicitar Recuperação de Senha

**Endpoint:** `POST /api/v1/auth/forgot-password`

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

**Response 200:**
```json
{
  "message": "Se o email estiver cadastrado, você receberá um link para redefinir sua senha."
}
```

> **Nota de Segurança:** A API sempre retorna sucesso, mesmo se o email não existir. Isso previne enumeração de emails (descobrir quais emails estão cadastrados).

---

### 2. Redefinir Senha

**Endpoint:** `POST /api/v1/auth/reset-password`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "new_password": "NovaSenha@123"
}
```

**Response 204:** No Content (sucesso)

**Response 400:**
```json
{
  "detail": "Token inválido ou expirado"
}
```

---

## Implementação no Frontend

### Passo 1: Tela "Esqueci Minha Senha"

Criar uma página/modal com:
- Campo de email
- Botão "Enviar link de recuperação"
- Link para voltar ao login

**Exemplo React:**

```tsx
// pages/ForgotPassword.tsx
import { useState } from 'react';
import { api } from '@/services/api';

export function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await api.post('/auth/forgot-password', { email });
      setSubmitted(true);
    } catch (err) {
      setError('Erro ao processar solicitação. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="text-center">
        <h2>Verifique seu email</h2>
        <p>
          Se o email <strong>{email}</strong> estiver cadastrado,
          você receberá um link para redefinir sua senha.
        </p>
        <p className="text-sm text-gray-500">
          O link é válido por 1 hora.
        </p>
        <a href="/login">Voltar para o login</a>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>Esqueci minha senha</h2>
      <p>Digite seu email para receber o link de recuperação.</p>

      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="seu@email.com"
        required
      />

      {error && <p className="error">{error}</p>}

      <button type="submit" disabled={loading}>
        {loading ? 'Enviando...' : 'Enviar link'}
      </button>

      <a href="/login">Voltar para o login</a>
    </form>
  );
}
```

---

### Passo 2: Tela "Redefinir Senha"

Esta página recebe o token via query parameter na URL.

**URL esperada:** `/reset-password?token=eyJhbGciOiJIUzI1NiIs...`

**Exemplo React:**

```tsx
// pages/ResetPassword.tsx
import { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '@/services/api';

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const token = searchParams.get('token');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Validar se tem token
  if (!token) {
    return (
      <div className="text-center">
        <h2>Link inválido</h2>
        <p>O link de recuperação está incompleto ou inválido.</p>
        <a href="/forgot-password">Solicitar novo link</a>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validações
    if (password.length < 6) {
      setError('A senha deve ter no mínimo 6 caracteres.');
      return;
    }

    if (password !== confirmPassword) {
      setError('As senhas não conferem.');
      return;
    }

    setLoading(true);

    try {
      await api.post('/auth/reset-password', {
        token,
        new_password: password,
      });
      setSuccess(true);

      // Redirecionar para login após 3 segundos
      setTimeout(() => navigate('/login'), 3000);
    } catch (err: any) {
      if (err.response?.status === 400) {
        setError('Link expirado ou inválido. Solicite um novo link.');
      } else {
        setError('Erro ao redefinir senha. Tente novamente.');
      }
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="text-center">
        <h2>Senha alterada com sucesso!</h2>
        <p>Você será redirecionado para o login em instantes...</p>
        <a href="/login">Ir para o login</a>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>Criar nova senha</h2>
      <p>Digite sua nova senha abaixo.</p>

      <div>
        <label>Nova senha</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Mínimo 6 caracteres"
          minLength={6}
          required
        />
      </div>

      <div>
        <label>Confirmar senha</label>
        <input
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          placeholder="Digite novamente"
          required
        />
      </div>

      {error && <p className="error">{error}</p>}

      <button type="submit" disabled={loading}>
        {loading ? 'Salvando...' : 'Salvar nova senha'}
      </button>
    </form>
  );
}
```

---

### Passo 3: Configurar Rotas

```tsx
// App.tsx ou routes.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Login } from './pages/Login';
import { ForgotPassword } from './pages/ForgotPassword';
import { ResetPassword } from './pages/ResetPassword';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        {/* outras rotas */}
      </Routes>
    </BrowserRouter>
  );
}
```

---

### Passo 4: Adicionar Link na Tela de Login

```tsx
// Na tela de login, adicionar link para recuperação
<form onSubmit={handleLogin}>
  <input type="email" placeholder="Email" />
  <input type="password" placeholder="Senha" />

  <button type="submit">Entrar</button>

  <a href="/forgot-password">Esqueci minha senha</a>
</form>
```

---

## Formato do Email Recebido

O usuário receberá um email com o seguinte formato:

```
Assunto: Redefinição de Senha - Starke

────────────────────────────────────
         STARKE
   Sistema de Gestão Patrimonial
────────────────────────────────────

Olá, [Nome do Usuário]!

Recebemos uma solicitação para redefinir
a senha da sua conta. Clique no botão
abaixo para criar uma nova senha:

    [ Redefinir Minha Senha ]

Este link é válido por 1 hora. Se você
não solicitou a redefinição de senha,
ignore este email.

────────────────────────────────────
© 2025 Starke - Todos os direitos reservados
```

---

## Tratamento de Erros

### Erros Possíveis

| Código | Situação | Mensagem para o Usuário |
|--------|----------|-------------------------|
| 200 | Email enviado (ou não existe) | "Verifique seu email" |
| 400 | Token inválido/expirado | "Link expirado. Solicite um novo." |
| 422 | Senha muito curta | "A senha deve ter no mínimo 6 caracteres" |
| 500 | Erro no servidor | "Erro interno. Tente novamente." |

### Exemplo de Tratamento

```tsx
try {
  await api.post('/auth/reset-password', { token, new_password });
  // Sucesso
} catch (error) {
  if (error.response?.status === 400) {
    // Token expirado ou inválido
    showError('O link expirou ou é inválido. Solicite um novo link de recuperação.');
  } else if (error.response?.status === 422) {
    // Validação falhou
    const detail = error.response?.data?.detail;
    if (Array.isArray(detail)) {
      showError(detail[0]?.msg || 'Dados inválidos');
    }
  } else {
    // Erro genérico
    showError('Ocorreu um erro. Tente novamente mais tarde.');
  }
}
```

---

## Validações Recomendadas

### No Frontend (antes de enviar)

1. **Email:**
   - Formato válido de email
   - Campo obrigatório

2. **Nova Senha:**
   - Mínimo 6 caracteres
   - Confirmação deve ser igual
   - Recomendado: força da senha (maiúscula, número, especial)

### Exemplo de Validação de Força

```tsx
function getPasswordStrength(password: string) {
  let strength = 0;

  if (password.length >= 6) strength++;
  if (password.length >= 8) strength++;
  if (/[A-Z]/.test(password)) strength++;
  if (/[0-9]/.test(password)) strength++;
  if (/[^A-Za-z0-9]/.test(password)) strength++;

  if (strength <= 2) return { label: 'Fraca', color: 'red' };
  if (strength <= 3) return { label: 'Média', color: 'orange' };
  return { label: 'Forte', color: 'green' };
}
```

---

## Configuração do Backend

Para o envio de emails funcionar, o backend precisa das seguintes variáveis de ambiente:

```env
# URL do Frontend (para montar o link de reset)
FRONTEND_URL=https://app.starke.com.br

# Configurações SMTP
EMAIL_BACKEND=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=sistema@empresa.com
SMTP_PASSWORD=senha_app
EMAIL_FROM_ADDRESS=noreply@empresa.com
EMAIL_FROM_NAME=Starke
```

---

## Checklist de Implementação

- [ ] Criar página `/forgot-password`
- [ ] Criar página `/reset-password`
- [ ] Adicionar link "Esqueci minha senha" no login
- [ ] Configurar rotas no router
- [ ] Implementar validações de senha
- [ ] Testar fluxo completo
- [ ] Testar com token expirado
- [ ] Testar com email não cadastrado

---

## Testes Manuais

1. **Fluxo Feliz:**
   - Ir para `/forgot-password`
   - Inserir email válido cadastrado
   - Verificar email recebido
   - Clicar no link
   - Inserir nova senha
   - Verificar redirecionamento para login
   - Fazer login com nova senha

2. **Token Expirado:**
   - Solicitar reset
   - Aguardar 1+ hora (ou usar token modificado)
   - Tentar usar o link
   - Verificar mensagem de erro

3. **Email Não Cadastrado:**
   - Inserir email que não existe
   - Verificar que mostra mesma mensagem (sem revelar se existe)

---

*Última atualização: Dezembro 2025*

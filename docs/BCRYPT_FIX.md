# Correção do Erro de bcrypt no Docker/Portainer

## 🐛 Problema

Erro durante login no ambiente Docker/Portainer:

```
ValueError: password cannot be longer than 72 bytes, truncate manually if necessary
AttributeError: module 'bcrypt' has no attribute '__about__'
```

## 🔍 Causa

**Incompatibilidade entre bcrypt 5.x+ e passlib 1.7.4:**

- bcrypt 5.0.0 (lançado em 25/09/2025) removeu o atributo `__about__`
- passlib 1.7.4 depende deste atributo para detecção de backend
- passlib não é mais mantido (última atualização: 08/10/2020)

**Por que funciona local mas falha no Docker:**
- Local: bcrypt 3.2.2 (Python 3.9)
- Docker: bcrypt 5.x+ instalado via Poetry (Python 3.11)
- Sem `poetry.lock`: Builds não-determinísticos

## ✅ Correção Aplicada

### Arquivos Atualizados

**1. `pyproject.toml` (linha 21):**
```toml
bcrypt = ">=4.0.0,<5.0.0"
```

**2. `requirements.txt` (linha 12):**
```txt
bcrypt>=4.0.0,<5.0.0
```

## 🚀 Próximos Passos

### Opção 1: Usando o Script Automático (Recomendado)

Execute o script helper que gera o `poetry.lock` e faz rebuild:

```bash
./scripts/fix_bcrypt_docker.sh
```

### Opção 2: Passo a Passo Manual

#### 1. Gerar `poetry.lock` (requer Docker rodando)

```bash
docker run --rm \
  -v "$(pwd):/app" \
  -w /app \
  python:3.11-slim \
  sh -c "pip install poetry && poetry lock --no-update"
```

Ou, se tiver Python 3.11 localmente:

```bash
poetry lock --no-update
```

#### 2. Verificar Versões no Lock File

```bash
grep -A 5 'name = "bcrypt"' poetry.lock | grep "version"
# Deve mostrar: version = "4.x.x" (NÃO 5.x.x)
```

#### 3. Rebuild do Container Docker

```bash
# Limpar cache e rebuild
docker-compose -f docker-compose.portainer.yml build --no-cache

# Reiniciar containers
docker-compose -f docker-compose.portainer.yml up -d
```

#### 4. Testar Login

Acesse o Portainer e tente fazer login novamente.

## 📝 Commitar Mudanças

```bash
# Adicionar arquivos modificados
git add pyproject.toml requirements.txt scripts/fix_bcrypt_docker.sh BCRYPT_FIX.md

# Se poetry.lock foi gerado
git add poetry.lock

# Commit
git commit -m "fix: Pin bcrypt <5.0.0 for passlib 1.7.4 compatibility

- Add bcrypt version constraint in pyproject.toml and requirements.txt
- Create helper script for Docker rebuild
- Fix login error in Portainer environment

Resolves incompatibility with bcrypt 5.x+ and passlib 1.7.4"
```

## 🔧 Validação

Após rebuild, verificar logs do container:

```bash
# Ver logs do container
docker-compose -f docker-compose.portainer.yml logs starke

# Não deve aparecer erros de bcrypt
```

## 📚 Referências

- Issue bcrypt: https://github.com/pyca/bcrypt/issues/684
- passlib última versão: 1.7.4 (08/10/2020)
- bcrypt breaking change: v5.0.0 (25/09/2025)

## ⚠️ Solução de Longo Prazo

Considerar migração de passlib para bcrypt direto:
- passlib não é mais mantido
- Usar `bcrypt.hashpw()` e `bcrypt.checkpw()` diretamente
- Atualizar `src/starke/domain/services/auth_service.py`

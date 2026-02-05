# Funcionalidades a Remover - Starke Fluxo de Caixa

Este documento lista as funcionalidades que **NÃO são necessárias** para o sistema de Fluxo de Caixa e podem ser removidas.

---

## Resumo

| Categoria | Manter | Remover |
|-----------|--------|---------|
| **API - Rotas** | auth, developments, reports, scheduler, users, me | accounts, assets, audit, clients, documents, impersonation, institutions, liabilities, positions |
| **API - Services** | auth, cash_flow, contract, development, mega_sync, uau_sync, portfolio_calculator, ipca, permission | audit, currency, impersonation, ingestion |
| **API - Database** | models.py (core) | patrimony/* (toda a pasta) |
| **Front - Features** | auth, operacional/relatorios, operacional/empreendimentos, operacional/scheduler, operacional/configuracoes | cliente/*, operacional/ativos, operacional/auditoria, operacional/clientes, operacional/contas, operacional/passivos, operacional/posicoes, operacional/uploads, impersonation |

---

## API - O que REMOVER

### Rotas (`api/src/starke/api/v1/`)

| Pasta | Funcionalidade | Motivo para remover |
|-------|---------------|---------------------|
| `accounts/` | Contas bancárias | Patrimônio |
| `assets/` | Ativos financeiros | Patrimônio |
| `audit/` | Logs de auditoria | Patrimônio (opcional manter) |
| `clients/` | Clientes do patrimônio | Patrimônio |
| `documents/` | Upload de documentos | Patrimônio |
| `impersonation/` | Visualizar como cliente | Patrimônio |
| `institutions/` | Instituições financeiras | Patrimônio |
| `liabilities/` | Passivos | Patrimônio |
| `positions/` | Posições mensais | Patrimônio |

### Services (`api/src/starke/domain/services/`)

| Arquivo | Funcionalidade | Motivo para remover |
|---------|---------------|---------------------|
| `audit_service.py` | Auditoria | Patrimônio |
| `currency_service.py` | Conversão de moedas | Patrimônio |
| `impersonation_service.py` | Impersonação | Patrimônio |
| `ingestion_service.py` | Importação de planilhas | Patrimônio |

### Database - Patrimony (`api/src/starke/infrastructure/database/patrimony/`)

**Remover toda a pasta `patrimony/`:**

| Arquivo | Modelo | Motivo |
|---------|--------|--------|
| `account.py` | Account | Contas bancárias |
| `asset.py` | Asset | Ativos financeiros |
| `audit_log.py` | AuditLog | Logs de auditoria |
| `client.py` | Client | Clientes patrimônio |
| `document.py` | Document | Documentos |
| `import_history.py` | ImportHistory | Histórico importação |
| `institution.py` | Institution | Instituições |
| `liability.py` | Liability | Passivos |
| `monthly_position.py` | MonthlyPosition | Posições mensais |

### Outras pastas da API

| Pasta | Motivo |
|-------|--------|
| `api/api_samples/validacao_cliente/` | Testes de patrimônio |
| `api/docs/html/` | Dashboards de patrimônio |
| `api/uploads/` | Uploads de documentos |
| `api/validation_output/` | Outputs de validação |

---

## FRONT - O que REMOVER

### Features (`front/src/features/`)

| Pasta | Funcionalidade | Motivo |
|-------|---------------|--------|
| `cliente/` | **Toda a pasta** | Área do cliente (patrimônio) |
| `cliente/composicao/` | Composição de ativos | Patrimônio |
| `cliente/configuracoes/` | Config do cliente | Patrimônio |
| `cliente/documentos/` | Documentos do cliente | Patrimônio |
| `cliente/evolucao/` | Evolução patrimonial | Patrimônio |
| `cliente/passivos/` | Passivos do cliente | Patrimônio |
| `cliente/resumo/` | Dashboard do cliente | Patrimônio |
| `impersonation/` | **Toda a pasta** | Visualizar como cliente |

### Features Operacionais (`front/src/features/operacional/`)

| Pasta | Funcionalidade | Motivo |
|-------|---------------|--------|
| `ativos/` | Gestão de ativos | Patrimônio |
| `auditoria/` | Logs de auditoria | Patrimônio |
| `clientes/` | Gestão de clientes | Patrimônio |
| `contas/` | Contas e instituições | Patrimônio |
| `passivos/` | Gestão de passivos | Patrimônio |
| `posicoes/` | Posições mensais | Patrimônio |
| `uploads/` | Upload de documentos | Patrimônio |

### Layouts (`front/src/shared/components/layout/`)

| Arquivo | Motivo |
|---------|--------|
| `ClientLayout.tsx` | Layout área do cliente |

---

## API - O que MANTER

### Rotas essenciais para Fluxo de Caixa

| Pasta | Funcionalidade |
|-------|---------------|
| `auth/` | Autenticação |
| `developments/` | Empreendimentos e filiais |
| `reports/` | Relatórios de fluxo de caixa |
| `scheduler/` | Agendamento de sync |
| `users/` | Gestão de usuários |
| `me/` | Perfil do usuário logado |

### Services essenciais

| Arquivo | Funcionalidade |
|---------|---------------|
| `auth_service.py` | Autenticação |
| `cash_flow_service.py` | Cálculos de fluxo de caixa |
| `contract_service.py` | Contratos |
| `development_service.py` | Empreendimentos |
| `mega_sync_service.py` | Sync com Mega |
| `uau_sync_service.py` | Sync com UAU |
| `mega_transformer.py` | Transformação dados Mega |
| `uau_transformer.py` | Transformação dados UAU |
| `portfolio_calculator.py` | Cálculos de portfólio |
| `ipca_service.py` | Índices IPCA |
| `permission_service.py` | Permissões |
| `classe_financeira_mapper.py` | Mapeamento classes financeiras |

### Database - Modelos essenciais (em `models.py`)

| Modelo | Tabela | Uso |
|--------|--------|-----|
| `User` | users | Usuários do sistema |
| `Development` | empreendimentos | Empreendimentos |
| `Filial` | filiais | Filiais |
| `Contract` | contratos | Contratos |
| `CashIn` | entradas_caixa | Entradas de caixa |
| `CashOut` | saidas_caixa | Saídas de caixa |
| `PortfolioStats` | estatisticas_portfolio | Estatísticas |
| `Delinquency` | inadimplencia | Inadimplência |
| `FaturaPagar` | faturas_pagar | Faturas a pagar |
| `Run` | runs | Histórico de syncs |
| `RawAPIResponse` | raw_api_responses | Respostas brutas da API |

---

## FRONT - O que MANTER

### Features essenciais

| Pasta | Funcionalidade |
|-------|---------------|
| `auth/` | Login, logout, reset senha |
| `operacional/relatorios/` | Relatórios de fluxo de caixa |
| `operacional/empreendimentos/` | Lista de empreendimentos |
| `operacional/scheduler/` | Controle de sincronização |
| `operacional/configuracoes/` | Configurações e usuários |

### Shared Components

| Pasta | Motivo |
|-------|--------|
| `shared/components/ui/` | Componentes UI (manter todos) |
| `shared/components/common/` | Componentes comuns |
| `shared/components/layout/OperationalLayout.tsx` | Layout principal |
| `shared/services/api/` | Cliente API |
| `shared/hooks/` | Hooks utilitários |

---

## Migrations (Alembic)

Após remover as funcionalidades, será necessário:

1. Criar nova migration removendo tabelas de patrimônio
2. Ou criar banco do zero apenas com tabelas necessárias

### Tabelas a REMOVER do banco

```sql
-- Patrimônio
DROP TABLE IF EXISTS clients CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS institutions CASCADE;
DROP TABLE IF EXISTS assets CASCADE;
DROP TABLE IF EXISTS liabilities CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS monthly_positions CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS import_history CASCADE;

-- Outras (verificar se usa)
DROP TABLE IF EXISTS report_access_tokens CASCADE;
DROP TABLE IF EXISTS user_preferences CASCADE;
DROP TABLE IF EXISTS impersonation_logs CASCADE;
```

---

## Ordem sugerida de remoção

1. **Front** - Remover features não usadas
2. **API - Rotas** - Remover rotas não usadas
3. **API - Services** - Remover serviços não usados
4. **API - Database/Patrimony** - Remover modelos de patrimônio
5. **API - models.py** - Limpar modelos não usados
6. **Migrations** - Criar migration de limpeza
7. **Testes** - Remover testes das funcionalidades removidas
8. **Docs** - Remover documentação não relevante

---

## Arquivos de configuração a revisar

- `api/src/starke/api/v1/router.py` - Remover imports das rotas removidas
- `api/src/starke/domain/permissions/screens.py` - Remover telas de patrimônio
- `front/src/app/router.tsx` - Remover rotas do front
- `front/src/app/providers.tsx` - Verificar providers não usados

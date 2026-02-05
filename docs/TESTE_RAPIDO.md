# 🧪 Teste Rápido do Sistema

Guia para fazer um teste completo do sistema sem usar Google Sheets.

---

## ✅ Configuração Já Feita

O `.env` já está configurado com:

```bash
TEST_MODE=true
TEST_EMAIL_RECIPIENT=fernando.ferreira@brainitsolutions.com.br
```

Isso significa que:
- ✅ Não vai buscar destinatários do Google Sheets
- ✅ Vai enviar apenas para `fernando.ferreira@brainitsolutions.com.br`
- ✅ Perfeito para testes!

---

## 🚀 Executar Teste Simples

Execute o comando:

```bash
PYTHONPATH=/Users/fernandoferreira/Documents/projetos/atlas/starke/src:$PYTHONPATH python3 -m starke.cli test-simple
```

Ou se tiver Poetry funcionando:

```bash
poetry run starke test-simple
```

---

## 📊 O que o teste faz

1. **Cria dados de exemplo**:
   - Entradas: R$ 101.000 (Contratos Ativos + Recuperações)
   - Saídas: R$ 39.000 (OPEX + Financeiras)
   - Saldo: R$ 50.000 → R$ 112.000
   - Carteira: VP R$ 5M, 150 contratos, 142 ativos

2. **Gera relatório HTML** mobile-first responsivo

3. **Envia email** para `fernando.ferreira@brainitsolutions.com.br`

---

## 📧 Output Esperado

```
🧪 Executando teste simples do sistema...

📧 Email de teste: fernando.ferreira@brainitsolutions.com.br

📊 Criando dados de exemplo...
✅ Dados criados

📄 Gerando relatório HTML...
✅ Relatório gerado (8543 caracteres)

📧 Enviando email para fernando.ferreira@brainitsolutions.com.br...
✅ Email enviado com sucesso!

📬 Verifique sua caixa de entrada:
   fernando.ferreira@brainitsolutions.com.br

🎉 Teste concluído com sucesso!
```

---

## 📬 Verificar Email

1. Abra sua caixa de entrada: `fernando.ferreira@brainitsolutions.com.br`
2. Procure por: **"Teste - Fluxo de Caixa - DD/MM/YYYY"**
3. O email conterá:
   - Cards com resumo (Entradas, Saídas, Saldo, Fluxo Líquido)
   - Dados da Carteira (VP, LTV, Prazo Médio, Duration)
   - Tabela de Entradas detalhada
   - Tabela de Saídas detalhada
   - Análise de Saldo

---

## 🔧 Outros Comandos Úteis

### Ver configuração atual
```bash
PYTHONPATH=/Users/fernandoferreira/Documents/projetos/atlas/starke/src:$PYTHONPATH python3 -m starke.cli config
```

Output:
```
⚙️  Configuração Atual:

Environment:    development
Debug:          true
...
🧪 Test Mode:    True
Test Email:     fernando.ferreira@brainitsolutions.com.br
```

### Testar só o email (sem relatório)
```bash
PYTHONPATH=/Users/fernandoferreira/Documents/projetos/atlas/starke/src:$PYTHONPATH python3 -m starke.cli test-email fernando.ferreira@brainitsolutions.com.br
```

---

## 🚦 Troubleshooting

### Erro: "TEST_MODE não está habilitado"

**Solução**: Edite o `.env`:
```bash
TEST_MODE=true
TEST_EMAIL_RECIPIENT=fernando.ferreira@brainitsolutions.com.br
```

### Erro: "SMTP authentication failed"

**Solução**: Verifique as credenciais SMTP no `.env`:
```bash
SMTP_USERNAME=brainitsolutionscwb@gmail.com
SMTP_PASSWORD=joawodtkwkdwyweo
```

### Email não chegou

1. **Verifique spam/lixeira**
2. **Aguarde 1-2 minutos** (pode demorar)
3. **Verifique logs** para ver se foi enviado:
   ```bash
   # O comando mostrará se houve erro
   ```

### Erro: "ModuleNotFoundError"

**Solução**: Use o PYTHONPATH completo:
```bash
PYTHONPATH=/Users/fernandoferreira/Documents/projetos/atlas/starke/src:$PYTHONPATH python3 -m starke.cli test-simple
```

---

## 🔄 Desabilitar Modo Teste

Quando estiver pronto para usar Google Sheets em produção:

```bash
# Edite .env:
TEST_MODE=false
GOOGLE_SHEETS_USE_OAUTH=true
GOOGLE_SHEETS_SPREADSHEET_ID=seu_id_aqui
```

Depois autentique:
```bash
poetry run starke auth-sheets
```

---

## 📝 Resumo

**Comando principal**:
```bash
PYTHONPATH=/Users/fernandoferreira/Documents/projetos/atlas/starke/src:$PYTHONPATH \
python3 -m starke.cli test-simple
```

**O que esperar**:
- ✅ Criação de dados de exemplo
- ✅ Geração de HTML
- ✅ Envio de email
- ✅ Email na caixa de entrada em 1-2 minutos

**Próximos passos**:
- Verificar email recebido
- Testar em mobile/desktop
- Integrar com API Mega real
- Configurar Google Sheets

---

**Pronto para testar? Execute o comando e verifique seu email!** 📧

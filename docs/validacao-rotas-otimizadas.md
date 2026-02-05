# Validação de Rotas Otimizadas - FaturaReceber/Saldo

**Data:** 30 de Outubro de 2025
**Status:** ⏳ Aguardando Testes

---

## 🎯 Objetivo

Validar se a rota `/api/FinanceiroMovimentacao/FaturaReceber/Saldo` pode substituir o fluxo atual de `DadosParcelas` com ganho de performance e mantendo todos os dados necessários.

---

## 📋 Checklist de Validações

### ✅ Validações Obrigatórias (Bloqueia Implementação)

- [ ] **V1**: NumeroDocumento corresponde a cod_contrato
- [ ] **V2**: Retorna parcelas de múltiplas filiais/empreendimentos
- [ ] **V3**: Tem campo para identificar quando foi pago (DataBaixa)
- [ ] **V4**: Tem campo para categorizar (TipoParcela ou similar)
- [ ] **V5**: Volume de dados retornados é gerenciável (< 50MB)

### ⚠️ Validações Desejáveis (Não bloqueia, mas limita funcionalidade)

- [ ] **V6**: Tem campo StatusParcela ou Situacao
- [ ] **V7**: Expand adiciona campos extras úteis
- [ ] **V8**: Performance é realmente melhor que DadosParcelas

---

## 🧪 Testes a Executar

### **Teste 1: Rota Base (SEM expand)**

#### Comando
```bash
curl -X GET \
  "https://api.mega.com/api/FinanceiroMovimentacao/FaturaReceber/Saldo/2025-10-01/2025-10-31" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "tenantId: SEU_TENANT" \
  > teste1_base.json
```

#### Análise Necessária
```bash
# Ver estrutura do primeiro registro
cat teste1_base.json | jq '.[0]'

# Contar registros
cat teste1_base.json | jq 'length'

# Verificar campos disponíveis
cat teste1_base.json | jq '.[0] | keys'

# Verificar tipos de documento
cat teste1_base.json | jq '[.[].TipoDocumento] | unique'

# Verificar filiais diferentes
cat teste1_base.json | jq '[.[].Filial.Id] | unique | length'
```

#### Resultado Esperado
```json
{
  "Filial": {"Id": 4},
  "Agente": {"Codigo": 12536},
  "TipoDocumento": "CONTRATO",
  "NumeroDocumento": "6670",
  "NumeroParcela": "012",
  "DataVencimento": "20/10/2025",
  "ValorParcela": 166666.67,
  "SaldoAtual": 166666.67
}
```

#### Validações
- [ ] Retorna múltiplas filiais? (V2)
- [ ] NumeroDocumento parece ser código de contrato? (V1)
- [ ] Tamanho do JSON é aceitável? (V5)

---

### **Teste 2: Com Expand Básico**

#### Comando
```bash
curl -X GET \
  "https://api.mega.com/api/FinanceiroMovimentacao/FaturaReceber/Saldo/2025-10-01/2025-10-31?expand=centroCusto,projeto,situacao" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "tenantId: SEU_TENANT" \
  > teste2_expand_basico.json
```

#### Análise
```bash
# Comparar campos com teste 1
diff <(cat teste1_base.json | jq '.[0] | keys | sort') \
     <(cat teste2_expand_basico.json | jq '.[0] | keys | sort')

# Verificar se adicionou campos
cat teste2_expand_basico.json | jq '.[0] | keys' | grep -i "centro\|projeto\|situacao"
```

#### Validações
- [ ] Expand adicionou campos? (V7)
- [ ] Tem Situacao ou Status? (V6)

---

### **Teste 3: Com Expand Completo**

#### Comando
```bash
curl -X GET \
  "https://api.mega.com/api/FinanceiroMovimentacao/FaturaReceber/Saldo/2025-10-01/2025-10-31?expand=centroCusto,projeto,situacao,parcela,dataBaixa,tipoParcela,status,statusParcela" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "tenantId: SEU_TENANT" \
  > teste3_expand_completo.json
```

#### Análise
```bash
# Verificar TODOS os campos retornados
cat teste3_expand_completo.json | jq '.[0] | keys'

# Procurar campos críticos
cat teste3_expand_completo.json | jq '.[0]' | grep -i "baixa\|tipo\|situacao\|status"
```

#### Validações
- [ ] Tem DataBaixa ou DataPagamento? (V3 - CRÍTICO!)
- [ ] Tem TipoParcela ou campo similar? (V4 - CRÍTICO!)

---

### **Teste 4: Validar NumeroDocumento = cod_contrato**

#### Comando
```bash
# 1. Buscar contratos de um empreendimento conhecido
curl -X GET \
  "https://api.mega.com/api/Carteira/DadosContrato/IdEmpreendimento=1472" \
  -H "Authorization: Bearer SEU_TOKEN" \
  > teste4_contratos.json

# 2. Pegar um cod_contrato
cat teste4_contratos.json | jq '.[0].cod_contrato'
# Exemplo: 2547

# 3. Buscar parcelas desse contrato via DadosParcelas
curl -X GET \
  "https://api.mega.com/api/Carteira/DadosParcelas/IdContrato=2547" \
  -H "Authorization: Bearer SEU_TOKEN" \
  > teste4_parcelas_antigas.json

# 4. Buscar via FaturaReceber e filtrar por NumeroDocumento
cat teste1_base.json | jq '.[] | select(.NumeroDocumento == "2547")'
```

#### Validações
- [ ] NumeroDocumento em FaturaReceber = cod_contrato em DadosContrato? (V1 - CRÍTICO!)
- [ ] Mesmas parcelas aparecem em ambas rotas?

---

### **Teste 5: Comparar Dados - DadosParcelas vs FaturaReceber**

#### Comando
```bash
# Buscar mesmas parcelas pelas 2 rotas e comparar

# Via DadosParcelas
curl -X GET \
  "https://api.mega.com/api/Carteira/DadosParcelas/IdContrato=2547" \
  -H "Authorization: Bearer SEU_TOKEN" \
  > teste5_dados_parcelas.json

# Via FaturaReceber (filtrado)
cat teste3_expand_completo.json | jq '[.[] | select(.NumeroDocumento == "2547")]' > teste5_fatura_receber.json

# Comparar quantidade
echo "DadosParcelas: $(cat teste5_dados_parcelas.json | jq 'length')"
echo "FaturaReceber: $(cat teste5_fatura_receber.json | jq 'length')"

# Comparar valores
cat teste5_dados_parcelas.json | jq '[.[].vlr_pago] | add'
cat teste5_fatura_receber.json | jq '[.[].ValorParcela] | add'
```

#### Validações
- [ ] Quantidades batem?
- [ ] Valores totais batem?
- [ ] Mesmos números de parcela?

---

### **Teste 6: Performance**

#### Comando
```bash
# Medir tempo de execução

# DadosParcelas (50 contratos)
time for i in {1..50}; do
  curl -s "https://api.mega.com/api/Carteira/DadosParcelas/IdContrato=$i" \
    -H "Authorization: Bearer TOKEN" > /dev/null
done

# FaturaReceber (1 request)
time curl -s "https://api.mega.com/api/FinanceiroMovimentacao/FaturaReceber/Saldo/2025-10-01/2025-10-31" \
  -H "Authorization: Bearer TOKEN" > /dev/null
```

#### Validações
- [ ] FaturaReceber é mais rápido? (V8)
- [ ] Quanto tempo economiza?

---

## 📊 Matriz de Decisão

### **Cenário 1: ✅ Todos os Campos Disponíveis**

**Condições:**
- ✅ V1: NumeroDocumento = cod_contrato
- ✅ V3: Tem DataBaixa
- ✅ V4: Tem TipoParcela

**Decisão:** ✅ **MIGRAR para FaturaReceber**

**Ações:**
1. Implementar novo método no `mega_client.py`
2. Criar serviço de agregação otimizado
3. Migrar `cash_flow_service.py`
4. Deprecar uso de DadosParcelas para agregação

---

### **Cenário 2: ⚠️ Campos Parciais (Sem DataBaixa ou TipoParcela)**

**Condições:**
- ✅ V1: NumeroDocumento = cod_contrato
- ❌ V3: NÃO tem DataBaixa
- ❌ V4: NÃO tem TipoParcela

**Decisão:** ⚠️ **USAR COM LIMITAÇÕES**

**Limitações:**
- ❌ Não consegue calcular realizado no mês correto
- ❌ Não consegue categorizar (Ativos/Recuperações/Antecipações)
- ✅ Consegue apenas: previsto vs realizado (básico)

**Ações:**
1. Usar FaturaReceber APENAS para forecast (previsto)
2. Continuar usando DadosParcelas para actual (realizado) e categorização
3. Abordagem híbrida

---

### **Cenário 3: ❌ NumeroDocumento NÃO é cod_contrato**

**Condições:**
- ❌ V1: NumeroDocumento ≠ cod_contrato

**Decisão:** ❌ **NÃO MIGRAR**

**Ações:**
1. Manter DadosParcelas (atual)
2. Implementar cache para otimizar
3. Considerar agregação mensal no banco

---

## 📝 Template de Resultado

Após executar todos os testes, preencha:

```markdown
## Resultados dos Testes

**Data dos Testes:** ___/___/2025
**Executado por:** ___________

### Validações Obrigatórias

- [ ] V1: NumeroDocumento = cod_contrato
  - Resultado: ✅ SIM / ❌ NÃO
  - Observações: ___________

- [ ] V2: Múltiplas filiais/empreendimentos
  - Resultado: ✅ SIM / ❌ NÃO
  - Quantidade de filiais: ___
  - Observações: ___________

- [ ] V3: Campo DataBaixa disponível
  - Resultado: ✅ SIM / ❌ NÃO
  - Nome do campo: ___________
  - Observações: ___________

- [ ] V4: Campo TipoParcela disponível
  - Resultado: ✅ SIM / ❌ NÃO
  - Nome do campo: ___________
  - Observações: ___________

- [ ] V5: Volume de dados aceitável
  - Resultado: ✅ SIM / ❌ NÃO
  - Tamanho do JSON: ___ MB
  - Quantidade de registros: ___
  - Observações: ___________

### Validações Desejáveis

- [ ] V6: Campo Situacao/Status
  - Resultado: ✅ SIM / ❌ NÃO
  - Nome do campo: ___________

- [ ] V7: Expand adiciona campos
  - Resultado: ✅ SIM / ❌ NÃO
  - Campos adicionados: ___________

- [ ] V8: Performance melhor
  - Resultado: ✅ SIM / ❌ NÃO
  - Tempo DadosParcelas: ___ segundos
  - Tempo FaturaReceber: ___ segundos
  - Ganho: ____%

### Decisão Final

**Cenário Identificado:** Cenário ___

**Decisão:** ✅ MIGRAR / ⚠️ USAR COM LIMITAÇÕES / ❌ NÃO MIGRAR

**Justificativa:**
___________________________________________
___________________________________________
___________________________________________

**Próximas Ações:**
1. ___________________________________________
2. ___________________________________________
3. ___________________________________________
```

---

## 🚀 Próximos Passos

1. **Executar todos os 6 testes** listados acima
2. **Preencher o template** de resultados
3. **Analisar o cenário** identificado
4. **Tomar decisão** de implementação
5. **Documentar achados** para referência futura

---

## ⚠️ Observações Importantes

1. **NÃO altere código** antes de validar TODOS os testes
2. **Salve TODOS os JSONs** de teste para análise posterior
3. **Documente qualquer comportamento inesperado**
4. **Se tiver dúvidas**, refaça o teste antes de prosseguir

---

**Última Atualização:** 30 de Outubro de 2025

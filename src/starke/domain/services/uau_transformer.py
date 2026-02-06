"""Transform UAU API data to Starke domain models."""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class UAUDataTransformer:
    """Transform data from UAU API format to Starke domain models.

    UAU API returns schema as first record in arrays - this should be
    filtered by the API client before passing to transformer.

    Key mappings:
    - Empresa UAU = Empreendimento Starke
    - Obra UAU = Fase (aggregated by Empresa)
    """

    # ============================================
    # Development (Empresa -> Empreendimento)
    # ============================================

    def transform_empresa_to_development(self, empresa: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform UAU empresa to Starke Development format.

        In UAU, Empresa = Empreendimento.

        Args:
            empresa: Raw empresa data from UAU API
                - Codigo_emp: int
                - Desc_emp: string
                - CGC_emp: string (CNPJ)

        Returns:
            Dict with Development model fields
        """
        empresa_id = empresa.get("Codigo_emp")
        if not empresa_id:
            raise ValueError(f"Empresa missing Codigo_emp: {empresa}")

        empresa_nome = empresa.get("Desc_emp") or f"Empresa {empresa_id}"

        return {
            "external_id": int(empresa_id),  # Original ID from UAU API
            "name": empresa_nome,
            "is_active": False,  # Starts inactive, activated only if has importations
            "raw_data": empresa,
            "origem": "uau",
            "last_synced_at": datetime.utcnow(),
        }

    # ============================================
    # CashOut - Desembolso
    # ============================================

    # Offset to avoid ID collision between Mega and UAU
    UAU_FILIAL_ID_OFFSET = 1_000_000

    def transform_desembolso_to_cash_out(
        self,
        desembolsos: List[Dict[str, Any]],
        empresa_id: int,
        empresa_nome: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Transform UAU desembolso records to aggregated CashOut records.

        Aggregates by ref_month and categoria (Composicao).
        Creates separate records for orcamento (Projetado) and realizado (Pago).

        Args:
            desembolsos: List of desembolso records from UAU API
            empresa_id: Empresa ID (empreendimento_id)
            empresa_nome: Empresa name

        Returns:
            Dict keyed by "ref_month|categoria" with aggregated values:
            {
                "2024-01|C0023": {
                    "filial_id": empresa_id,
                    "filial_nome": empresa_nome,
                    "mes_referencia": "2024-01",
                    "categoria": "C0023",
                    "orcamento": 10000.0,
                    "realizado": 8000.0,
                    "origem": "uau"
                }
            }
        """
        aggregated: Dict[str, Dict[str, Any]] = {}

        for record in desembolsos:
            status = record.get("Status", "")
            if status not in ("Projetado", "Pagar", "Pago"):
                continue

            # Build ref_month from DtaRefAno and DtaRefMes
            ano = record.get("DtaRefAno")
            mes = record.get("DtaRefMes")

            if not ano or not mes:
                continue

            ref_month = f"{ano}-{mes:02d}" if isinstance(mes, int) else f"{ano}-{int(mes):02d}"

            # Use Composicao as categoria (or Item if Composicao is empty)
            categoria = record.get("Composicao") or record.get("Item") or "outros"

            # Get value
            valor = self._parse_decimal(record.get("Total", 0))
            if valor <= 0:
                continue

            # Create key for aggregation
            key = f"{ref_month}|{categoria}"

            if key not in aggregated:
                aggregated[key] = {
                    "filial_id": empresa_id,
                    "filial_nome": empresa_nome,
                    "mes_referencia": ref_month,
                    "categoria": categoria,
                    "orcamento": 0.0,
                    "realizado": 0.0,
                    "detalhes": {"records_count": 0},
                    "origem": "uau",
                }

            # Add to appropriate field based on status
            # Projetado e Pagar = orçado (previsto/pendente)
            # Pago = realizado
            if status in ("Projetado", "Pagar"):
                aggregated[key]["orcamento"] += float(valor)
            elif status == "Pago":
                aggregated[key]["realizado"] += float(valor)

            aggregated[key]["detalhes"]["records_count"] += 1

        return aggregated

    # ============================================
    # CashIn - Parcelas
    # ============================================

    def transform_parcela_a_receber_to_cash_in(
        self,
        parcela: Dict[str, Any],
        empresa_id: int,
        empresa_nome: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Transform UAU parcela a receber to Starke CashIn (forecast).

        Args:
            parcela: Raw parcela data from BuscarParcelasAReceber
                - Empresa_prc, Obra_Prc, NumVend_prc, NumParc_Prc
                - Data_Prc (due date)
                - Valor_Prc (value)
                - Tipo_Prc (type for category)
            empresa_id: Empresa ID
            empresa_nome: Empresa name

        Returns:
            CashIn dict with forecast value
        """
        # Extract due date
        dt_vencimento = self._parse_date(parcela.get("Data_Prc"))
        if not dt_vencimento:
            return None

        # Extract value
        valor = self._parse_decimal(parcela.get("Valor_Prc", 0))
        if valor <= 0:
            return None

        # Build ref_month from due date
        ref_month = dt_vencimento.strftime("%Y-%m")

        # Map Tipo_Prc to category
        tipo = parcela.get("Tipo_Prc", "")
        category = self._map_tipo_parcela_to_category(tipo)

        # Build origin_id for upsert
        num_venda = parcela.get("NumVend_prc", 0)
        num_parcela = parcela.get("NumParc_Prc", 0)
        obra = parcela.get("Obra_Prc", "")
        origin_id = f"uau_{empresa_id}_{obra}_{num_venda}_{num_parcela}_forecast"

        return {
            "empreendimento_id": empresa_id,
            "empreendimento_nome": empresa_nome,
            "ref_month": ref_month,
            "category": category,
            "forecast": float(valor),
            "actual": 0.0,
            "details": {
                "origin_id": origin_id,
                "tipo": "forecast",
                "vencimento": dt_vencimento.isoformat(),
                "num_venda": num_venda,
                "num_parcela": num_parcela,
                "obra": obra,
                "tipo_parcela": tipo,
                "cliente": parcela.get("nome_pes"),
            },
            "origem": "uau",
        }

    def transform_parcela_recebida_to_cash_in(
        self,
        parcela: Dict[str, Any],
        empresa_id: int,
        empresa_nome: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Transform UAU parcela recebida to Starke CashIn (actual).

        Args:
            parcela: Raw parcela data from BuscarParcelasRecebidas
                - Empresa_rec, Obra_Rec, NumVend_Rec, NumParc_Rec
                - Data_Rec (payment date)
                - ValorConf_Rec (confirmed value)
                - ParcType_Rec (type for category)
            empresa_id: Empresa ID
            empresa_nome: Empresa name

        Returns:
            CashIn dict with actual value
        """
        # Extract payment date
        dt_pagamento = self._parse_date(parcela.get("Data_Rec"))
        if not dt_pagamento:
            return None

        # Extract value
        valor = self._parse_decimal(parcela.get("ValorConf_Rec", 0))
        if valor <= 0:
            return None

        # Build ref_month from payment date
        ref_month = dt_pagamento.strftime("%Y-%m")

        # Map ParcType_Rec to category
        tipo = parcela.get("ParcType_Rec", "")
        category = self._map_tipo_parcela_to_category(tipo)

        # Build origin_id for upsert
        num_venda = parcela.get("NumVend_Rec", 0)
        num_parcela = parcela.get("NumParc_Rec", 0)
        obra = parcela.get("Obra_Rec", "")
        origin_id = f"uau_{empresa_id}_{obra}_{num_venda}_{num_parcela}_actual"

        return {
            "empreendimento_id": empresa_id,
            "empreendimento_nome": empresa_nome,
            "ref_month": ref_month,
            "category": category,
            "forecast": 0.0,
            "actual": float(valor),
            "details": {
                "origin_id": origin_id,
                "tipo": "actual",
                "pagamento": dt_pagamento.isoformat(),
                "vencimento": self._parse_date_str(parcela.get("DataVenci_Rec")),
                "num_venda": num_venda,
                "num_parcela": num_parcela,
                "obra": obra,
                "tipo_parcela": tipo,
                "juros": float(self._parse_decimal(parcela.get("VlJurosConf_Rec", 0))),
                "multa": float(self._parse_decimal(parcela.get("VlMultaConf_Rec", 0))),
            },
            "origem": "uau",
        }

    # ============================================
    # CashIn - ExportarVendas (novo método otimizado)
    # ============================================

    def transform_parcela_export_to_cash_in(
        self,
        parcela: Dict[str, Any],
        empresa_id: int,
        empresa_nome: str,
        obra: str,
        num_venda: int,
    ) -> List[Dict[str, Any]]:
        """
        Transform parcela from ExportarVendasXml to CashIn records.

        Handles both:
        - ParcelaRecebida = "0" → 1 record: forecast no mês do vencimento
        - ParcelaRecebida = "1" → 2 records:
            - forecast no mês do vencimento (o que era esperado receber)
            - actual no mês do pagamento (o que foi efetivamente recebido)

        NOTA: A API UAU zera o ValorPrincipal quando a parcela é paga,
        por isso usamos ValorPrincipalConfirmado como base do forecast
        para parcelas pagas.

        Args:
            parcela: Raw parcela data from ExportarVendasXml
                - ParcelaRecebida: "0" = aberta, "1" = paga
                - TipoParcela: tipo (E, S, M, etc)
                - NumeroParcela: número da parcela
                - DataVencimento: data de vencimento
                - DataRecebimento: data do pagamento (se paga)
                - ValorPrincipal: valor original (forecast, 0 se paga)
                - ValorPrincipalConfirmado: valor pago (actual)
                - ValorJurosAtrasoConfirmado: juros cobrados
                - ValorMultaConfirmado: multa cobrada
            empresa_id: Empresa/Empreendimento ID
            empresa_nome: Empresa name
            obra: Obra code
            num_venda: Número da venda

        Returns:
            List of CashIn dicts (1 for open, 2 for paid parcelas)
        """
        is_paga = parcela.get("ParcelaRecebida") == "1"
        num_parcela = self._safe_int(parcela.get("NumeroParcela")) or 0
        tipo = parcela.get("TipoParcela", "")
        category = self._map_tipo_parcela_to_category(tipo)

        if is_paga:
            dt_pagamento = self._parse_date(parcela.get("DataRecebimento"))
            if not dt_pagamento:
                return []

            valor_principal = self._parse_decimal(parcela.get("ValorPrincipalConfirmado", 0))
            if valor_principal <= 0:
                return []

            # Componentes adicionais do valor efetivamente recebido
            juros_atraso = self._parse_decimal(parcela.get("ValorJurosAtrasoConfirmado", 0))
            multa = self._parse_decimal(parcela.get("ValorMultaConfirmado", 0))
            juros_contrato = self._parse_decimal(parcela.get("ValorJurosContratoConfirmado", 0))
            acrescimo = self._parse_decimal(parcela.get("ValorAcrescimoConfirmado", 0))
            correcao = self._parse_decimal(parcela.get("ValorCorrecaoConfirmado", 0))
            correcao_atraso = self._parse_decimal(parcela.get("ValorCorrecaoAtrasoConfirmado", 0))
            desconto = self._parse_decimal(parcela.get("ValorDescontoConfirmado", 0))
            desconto_antecipacao = self._parse_decimal(parcela.get("ValorDescontoAdiantamentoConfirmado", 0))
            desconto_condicional = self._parse_decimal(parcela.get("ValorDescontoCondicionalConfirmado", 0))

            # Actual = principal + acréscimos - descontos
            valor_actual = (
                valor_principal
                + juros_atraso + multa + juros_contrato
                + acrescimo + correcao + correcao_atraso
                - desconto - desconto_antecipacao - desconto_condicional
            )

            dt_vencimento = self._parse_date(parcela.get("DataVencimento"))

            records = []

            # FORECAST - o que era esperado receber no mês do vencimento
            # Usa ValorPrincipalConfirmado (sem juros/multa/desconto) como valor base esperado
            if dt_vencimento:
                forecast_ref_month = dt_vencimento.strftime("%Y-%m")
                forecast_origin_id = f"uau_export_{empresa_id}_{obra}_{num_venda}_{num_parcela}_forecast"

                records.append({
                    "empreendimento_id": empresa_id,
                    "empreendimento_nome": empresa_nome,
                    "ref_month": forecast_ref_month,
                    "category": category,
                    "forecast": float(valor_principal),
                    "actual": 0.0,
                    "details": {
                        "origin_id": forecast_origin_id,
                        "tipo": "forecast",
                        "vencimento": dt_vencimento.isoformat(),
                        "pagamento": dt_pagamento.isoformat(),
                        "num_venda": num_venda,
                        "num_parcela": num_parcela,
                        "obra": obra,
                        "tipo_parcela": tipo,
                    },
                    "origem": "uau",
                })

            # ACTUAL - valor total efetivamente recebido (principal + juros + multa - descontos)
            actual_ref_month = dt_pagamento.strftime("%Y-%m")
            actual_origin_id = f"uau_export_{empresa_id}_{obra}_{num_venda}_{num_parcela}_actual"

            records.append({
                "empreendimento_id": empresa_id,
                "empreendimento_nome": empresa_nome,
                "ref_month": actual_ref_month,
                "category": category,
                "forecast": 0.0,
                "actual": float(valor_actual),
                "details": {
                    "origin_id": actual_origin_id,
                    "tipo": "actual",
                    "pagamento": dt_pagamento.isoformat(),
                    "vencimento": self._parse_date_str(parcela.get("DataVencimento")),
                    "num_venda": num_venda,
                    "num_parcela": num_parcela,
                    "obra": obra,
                    "tipo_parcela": tipo,
                    "principal": float(valor_principal),
                    "juros_atraso": float(juros_atraso),
                    "multa": float(multa),
                    "juros_contrato": float(juros_contrato),
                    "acrescimo": float(acrescimo),
                    "correcao": float(correcao),
                    "correcao_atraso": float(correcao_atraso),
                    "desconto": float(desconto),
                    "desconto_antecipacao": float(desconto_antecipacao),
                    "desconto_condicional": float(desconto_condicional),
                },
                "origem": "uau",
            })

            return records
        else:
            # FORECAST - parcela aberta
            dt_vencimento = self._parse_date(parcela.get("DataVencimento"))
            if not dt_vencimento:
                return []

            valor = self._parse_decimal(parcela.get("ValorPrincipal", 0))
            if valor <= 0:
                return []

            ref_month = dt_vencimento.strftime("%Y-%m")
            origin_id = f"uau_export_{empresa_id}_{obra}_{num_venda}_{num_parcela}_forecast"

            return [{
                "empreendimento_id": empresa_id,
                "empreendimento_nome": empresa_nome,
                "ref_month": ref_month,
                "category": category,
                "forecast": float(valor),
                "actual": 0.0,
                "details": {
                    "origin_id": origin_id,
                    "tipo": "forecast",
                    "vencimento": dt_vencimento.isoformat(),
                    "num_venda": num_venda,
                    "num_parcela": num_parcela,
                    "obra": obra,
                    "tipo_parcela": tipo,
                },
                "origem": "uau",
            }]

    def aggregate_cash_in(
        self,
        records: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate CashIn records by empreendimento_id, ref_month, category.

        Args:
            records: List of CashIn dicts

        Returns:
            Dict keyed by "emp_id|ref_month|category" with aggregated values
        """
        aggregated: Dict[str, Dict[str, Any]] = {}

        for record in records:
            if not record:
                continue

            emp_id = record["empreendimento_id"]
            ref_month = record["ref_month"]
            category = record["category"]
            key = f"{emp_id}|{ref_month}|{category}"

            if key not in aggregated:
                aggregated[key] = {
                    "empreendimento_id": emp_id,
                    "empreendimento_nome": record["empreendimento_nome"],
                    "ref_month": ref_month,
                    "category": category,
                    "forecast": 0.0,
                    "actual": 0.0,
                    "details": {"records_count": 0},
                    "origem": "uau",
                }

            aggregated[key]["forecast"] += record.get("forecast", 0.0)
            aggregated[key]["actual"] += record.get("actual", 0.0)
            aggregated[key]["details"]["records_count"] += 1

        return aggregated

    # ============================================
    # Portfolio Stats
    # ============================================

    def transform_parcelas_to_portfolio_stats(
        self,
        parcelas_vp: List[Dict[str, Any]],
        empresa_id: int,
        empresa_nome: str,
        ref_month: str,
    ) -> Dict[str, Any]:
        """
        Transform UAU parcelas with VP to Starke PortfolioStats.

        Uses ConsultarParcelasDaVenda response which has automatic VP calculation.

        Args:
            parcelas_vp: List of parcelas from ConsultarParcelasDaVenda
                - Principal_reaj (original value)
                - Valor_reaj (present value = VP)
                - Juros_reaj, Multa_reaj, Correcao_reaj
                - DataVenc_reaj (due date)
            empresa_id: Empresa ID
            empresa_nome: Empresa name
            ref_month: Reference month (YYYY-MM)

        Returns:
            PortfolioStats dict
        """
        total_vp = 0.0
        total_principal = 0.0
        total_juros = 0.0
        total_multa = 0.0
        total_correcao = 0.0
        total_parcelas = 0
        prazo_ponderado = 0.0

        hoje = datetime.now().date()

        for parcela in parcelas_vp:
            vp = float(self._parse_decimal(parcela.get("Valor_reaj", 0)))
            principal = float(self._parse_decimal(parcela.get("Principal_reaj", 0)))

            if vp <= 0:
                continue

            total_vp += vp
            total_principal += principal
            total_juros += float(self._parse_decimal(parcela.get("Juros_reaj", 0)))
            total_multa += float(self._parse_decimal(parcela.get("Multa_reaj", 0)))
            total_correcao += float(self._parse_decimal(parcela.get("Correcao_reaj", 0)))
            total_parcelas += 1

            # Calculate weighted average term
            dt_venc = self._parse_date(parcela.get("DataVenc_reaj"))
            if dt_venc:
                dias_ate_venc = max(0, (dt_venc - hoje).days)
                prazo_ponderado += vp * dias_ate_venc

        # Calculate prazo_medio (weighted average term in days)
        prazo_medio = prazo_ponderado / total_vp if total_vp > 0 else 0

        return {
            "empreendimento_id": empresa_id,
            "empreendimento_nome": empresa_nome,
            "ref_month": ref_month,
            "vp": total_vp,
            "ltv": 0.0,  # Not calculated from UAU data
            "prazo_medio": prazo_medio / 30,  # Convert to months
            "duration": prazo_medio / 365,  # Convert to years
            "total_contracts": 0,  # Would need separate query
            "active_contracts": 0,
            "details": {
                "total_parcelas": total_parcelas,
                "total_principal": total_principal,
                "total_juros": total_juros,
                "total_multa": total_multa,
                "total_correcao": total_correcao,
            },
            "origem": "uau",
        }

    # ============================================
    # Delinquency (Inadimplência)
    # ============================================

    # Bank compensation grace period (same as Mega: 3 days)
    GRACE_DAYS_COMPENSACAO = 3

    def transform_parcelas_export_to_delinquency(
        self,
        vendas: List[Dict[str, Any]],
        empresa_id: int,
        empresa_nome: str,
        ref_date: date,
    ) -> Dict[str, Any]:
        """
        Transform ExportarVendas parcelas to Starke Delinquency.

        Optimized method that processes parcelas directly from ExportarVendasXml,
        avoiding separate API calls. Handles both scenarios:

        1. Parcelas VENCIDAS NÃO PAGAS:
           - ParcelaRecebida = "0" AND DataVencimento < ref_date - grace_period
           - dias_atraso = ref_date - DataVencimento

        2. Parcelas PAGAS EM ATRASO:
           - ParcelaRecebida = "1" AND DataRecebimento > DataVencimento + grace_period
           - dias_atraso = DataRecebimento - DataVencimento

        Grace period: 3 days (bank compensation time)

        Args:
            vendas: List of vendas from ExportarVendasXml (with Parcelas embedded)
            empresa_id: Empresa ID
            empresa_nome: Empresa name
            ref_date: Reference date for calculation

        Returns:
            Delinquency dict with aging buckets
        """
        buckets = {
            "up_to_30": 0.0,
            "days_30_60": 0.0,
            "days_60_90": 0.0,
            "days_90_180": 0.0,
            "above_180": 0.0,
        }
        quantities = {
            "up_to_30": 0,
            "days_30_60": 0,
            "days_60_90": 0,
            "days_90_180": 0,
            "above_180": 0,
        }
        total = 0.0
        total_qty = 0
        parcelas_vencidas_nao_pagas = 0
        parcelas_pagas_atraso = 0

        for venda in vendas:
            # Skip cancelled vendas (StatusVenda = "1")
            if venda.get("StatusVenda") == "1":
                continue

            # Get parcelas from venda
            parcelas_data = venda.get("Parcelas", {})
            parcelas = parcelas_data.get("Parcela", [])

            # Normalize to list
            if isinstance(parcelas, dict):
                parcelas = [parcelas]

            for parcela in parcelas:
                is_paga = parcela.get("ParcelaRecebida") == "1"

                if is_paga:
                    # Parcela PAGA - 3 cenários possíveis (mesmo padrão do Mega):
                    dt_pagamento = self._parse_date(parcela.get("DataRecebimento"))
                    dt_venc = self._parse_date(parcela.get("DataVencimento"))

                    if not dt_pagamento or not dt_venc:
                        continue

                    # Skip parcelas com vencimento futuro em relação ao ref_date
                    if dt_venc > ref_date:
                        continue

                    if dt_pagamento <= ref_date:
                        # Cenário 2: Paga ANTES/DURANTE o mês de referência
                        # dias_atraso = data_pagamento - data_vencimento
                        dias_atraso = (dt_pagamento - dt_venc).days

                        # Skip if paid on time or within grace period
                        if dias_atraso <= self.GRACE_DAYS_COMPENSACAO:
                            continue

                        # Use confirmed value for paid parcels
                        valor = float(self._parse_decimal(parcela.get("ValorPrincipalConfirmado", 0)))
                        if valor <= 0:
                            continue

                        self._add_to_bucket(buckets, quantities, dias_atraso, valor)
                        total += valor
                        total_qty += 1
                        parcelas_pagas_atraso += 1
                    else:
                        # Cenário 3: Paga DEPOIS do mês de referência
                        # Nesse mês ela ainda não tinha sido paga, tratar como vencida não paga
                        dias_atraso = (ref_date - dt_venc).days

                        if dias_atraso <= self.GRACE_DAYS_COMPENSACAO:
                            continue

                        # Use ValorPrincipalConfirmado (ValorPrincipal é zerado quando paga)
                        valor = float(self._parse_decimal(parcela.get("ValorPrincipalConfirmado", 0)))
                        if valor <= 0:
                            continue

                        self._add_to_bucket(buckets, quantities, dias_atraso, valor)
                        total += valor
                        total_qty += 1
                        parcelas_vencidas_nao_pagas += 1

                else:
                    # Cenário 1: Parcela VENCIDA NÃO PAGA
                    dt_venc = self._parse_date(parcela.get("DataVencimento"))
                    if not dt_venc:
                        continue

                    # Skip future parcelas
                    if dt_venc > ref_date:
                        continue

                    # dias_atraso = ref_date - data_vencimento
                    dias_atraso = (ref_date - dt_venc).days

                    # Skip if within grace period
                    if dias_atraso <= self.GRACE_DAYS_COMPENSACAO:
                        continue

                    # Use principal value for unpaid parcels
                    valor = float(self._parse_decimal(parcela.get("ValorPrincipal", 0)))
                    if valor <= 0:
                        continue

                    self._add_to_bucket(buckets, quantities, dias_atraso, valor)
                    total += valor
                    total_qty += 1
                    parcelas_vencidas_nao_pagas += 1

        return {
            "empreendimento_id": empresa_id,
            "empreendimento_nome": empresa_nome,
            "ref_month": ref_date.strftime("%Y-%m"),
            "up_to_30": buckets["up_to_30"],
            "days_30_60": buckets["days_30_60"],
            "days_60_90": buckets["days_60_90"],
            "days_90_180": buckets["days_90_180"],
            "above_180": buckets["above_180"],
            "total": total,
            "details": {
                "calculation_date": ref_date.isoformat(),
                "grace_days": self.GRACE_DAYS_COMPENSACAO,
                "quantities": quantities,
                "total_parcelas": total_qty,
                "parcelas_vencidas_nao_pagas": parcelas_vencidas_nao_pagas,
                "parcelas_pagas_atraso": parcelas_pagas_atraso,
            },
            "origem": "uau",
        }

    def transform_parcelas_to_delinquency(
        self,
        parcelas_a_receber: List[Dict[str, Any]],
        parcelas_recebidas: List[Dict[str, Any]],
        empresa_id: int,
        empresa_nome: str,
        ref_date: date,
    ) -> Dict[str, Any]:
        """
        Transform UAU parcelas to Starke Delinquency.

        Calculates aging buckets from overdue parcelas (same logic as Mega):
        - Unpaid parcelas: dias_atraso = ref_date - data_vencimento
        - Paid late parcelas: dias_atraso = data_pagamento - data_vencimento
        - Grace period: 3 days (bank compensation time)

        Args:
            parcelas_a_receber: List of open parcelas from BuscarParcelasAReceber
                - Data_Prc (due date)
                - Valor_Prc (value)
                - Status_Prc (0 = open)
            parcelas_recebidas: List of paid parcelas from BuscarParcelasRecebidas
                - Data_Rec (payment date)
                - ValorConf_Rec (paid value)
                - DataVenc_Rec (due date)
            empresa_id: Empresa ID
            empresa_nome: Empresa name
            ref_date: Reference date for calculation

        Returns:
            Delinquency dict with aging buckets
        """
        buckets = {
            "up_to_30": 0.0,
            "days_30_60": 0.0,
            "days_60_90": 0.0,
            "days_90_180": 0.0,
            "above_180": 0.0,
        }
        quantities = {
            "up_to_30": 0,
            "days_30_60": 0,
            "days_60_90": 0,
            "days_90_180": 0,
            "above_180": 0,
        }
        total = 0.0
        total_qty = 0

        # Process UNPAID parcelas (parcelas a receber em aberto)
        for parcela in parcelas_a_receber:
            # Only consider open parcelas (Status_Prc = 0)
            status = parcela.get("Status_Prc")
            if status != 0:
                continue

            # Get due date
            dt_venc = self._parse_date(parcela.get("Data_Prc"))
            if not dt_venc:
                continue

            # Skip future parcelas
            if dt_venc > ref_date:
                continue

            # Calculate dias_atraso for unpaid: ref_date - data_vencimento
            dias_atraso = (ref_date - dt_venc).days

            # Skip if within grace period (bank compensation: 3 days)
            if dias_atraso < self.GRACE_DAYS_COMPENSACAO:
                continue

            # Get value
            valor = float(self._parse_decimal(parcela.get("Valor_Prc", 0)))
            if valor <= 0:
                continue

            # Classify into bucket
            self._add_to_bucket(buckets, quantities, dias_atraso, valor)
            total += valor
            total_qty += 1

        # Process PAID LATE parcelas (parcelas recebidas com atraso)
        for parcela in parcelas_recebidas:
            # Get payment date
            dt_pagamento = self._parse_date(parcela.get("Data_Rec"))
            if not dt_pagamento:
                continue

            # Only consider payments before/on ref_date
            if dt_pagamento > ref_date:
                continue

            # Get due date (field name is DataVenci_Rec)
            dt_venc = self._parse_date(parcela.get("DataVenci_Rec"))
            if not dt_venc:
                continue

            # Calculate dias_atraso for paid: data_pagamento - data_vencimento
            dias_atraso = (dt_pagamento - dt_venc).days

            # Skip if paid on time or within grace period
            if dias_atraso < self.GRACE_DAYS_COMPENSACAO:
                continue

            # Get value
            valor = float(self._parse_decimal(parcela.get("ValorConf_Rec", 0)))
            if valor <= 0:
                continue

            # Classify into bucket
            self._add_to_bucket(buckets, quantities, dias_atraso, valor)
            total += valor
            total_qty += 1

        return {
            "empreendimento_id": empresa_id,
            "empreendimento_nome": empresa_nome,
            "ref_month": ref_date.strftime("%Y-%m"),
            "up_to_30": buckets["up_to_30"],
            "days_30_60": buckets["days_30_60"],
            "days_60_90": buckets["days_60_90"],
            "days_90_180": buckets["days_90_180"],
            "above_180": buckets["above_180"],
            "total": total,
            "details": {
                "calculation_date": ref_date.isoformat(),
                "grace_days": self.GRACE_DAYS_COMPENSACAO,
                "quantities": quantities,
                "total_parcelas": total_qty,
            },
            "origem": "uau",
        }

    def _add_to_bucket(
        self,
        buckets: Dict[str, float],
        quantities: Dict[str, int],
        dias_atraso: int,
        valor: float,
    ) -> None:
        """Add value to appropriate aging bucket."""
        if dias_atraso <= 30:
            buckets["up_to_30"] += valor
            quantities["up_to_30"] += 1
        elif dias_atraso <= 60:
            buckets["days_30_60"] += valor
            quantities["days_30_60"] += 1
        elif dias_atraso <= 90:
            buckets["days_60_90"] += valor
            quantities["days_60_90"] += 1
        elif dias_atraso <= 180:
            buckets["days_90_180"] += valor
            quantities["days_90_180"] += 1
        else:
            buckets["above_180"] += valor
            quantities["above_180"] += 1

    # ============================================
    # Contract (Venda -> Contrato)
    # ============================================

    # StatusVenda mapping from UAU swagger
    STATUS_VENDA_MAPPING = {
        "0": "Normal",
        "1": "Cancelada",
        "2": "Alterada",
        "3": "Quitada",
        "4": "Em acerto",
    }

    def transform_venda_to_contract(
        self,
        venda: Dict[str, Any],
        empreendimento_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Transform UAU venda (ExportarVendasXml) to Starke Contract format.

        Args:
            venda: Raw venda data from ExportarVendasXml
                - Empresa, Obra, Numero (unique key)
                - DataDaVenda (signature date)
                - StatusVenda (0=Normal, 1=Cancelada, 2=Alterada, 3=Quitada, 4=Em acerto)
                - DataCancelamento (if cancelled)
                - Clientes.Cliente (client info)
                - Itens.Item (items for total value)
            empreendimento_id: Development ID in Starke

        Returns:
            Dict with Contract model fields
        """
        numero = venda.get("Numero")
        if not numero:
            logger.warning(f"Venda missing Numero: {venda}")
            return None

        obra = venda.get("Obra", "")
        empresa = venda.get("Empresa", "")

        # Parse dates
        data_assinatura = self._parse_date(venda.get("DataDaVenda"))
        data_cancelamento = self._parse_date(venda.get("DataCancelamento"))

        # Map status
        status_code = str(venda.get("StatusVenda", "0"))
        status = self.STATUS_VENDA_MAPPING.get(status_code, "Normal")

        # Get cliente principal (pode ser objeto ou array)
        cliente_cpf = None
        cliente_codigo = None
        clientes_data = venda.get("Clientes", {})
        clientes = clientes_data.get("Cliente", [])

        # Normalizar para lista
        if isinstance(clientes, dict):
            clientes = [clientes]

        # Pegar cliente principal (Principal = "1") ou primeiro
        for cliente in clientes:
            if cliente.get("Principal") == "1":
                cliente_cpf = cliente.get("CpfCnpjDoCliente")
                cliente_codigo = self._safe_int(cliente.get("CodigoCliente"))
                break
        else:
            # Se não achou principal, pega o primeiro
            if clientes:
                cliente_cpf = clientes[0].get("CpfCnpjDoCliente")
                cliente_codigo = self._safe_int(clientes[0].get("CodigoCliente"))

        # Calculate valor_contrato from Itens
        valor_contrato = Decimal("0")
        itens_data = venda.get("Itens", {})
        itens = itens_data.get("Item", [])

        # Normalizar para lista
        if isinstance(itens, dict):
            itens = [itens]

        for item in itens:
            preco = self._parse_decimal(item.get("Preco", 0))
            quantidade = self._parse_decimal(item.get("Quantidade", 1))
            valor_contrato += preco * quantidade

        return {
            "cod_contrato": int(numero),
            "empreendimento_id": empreendimento_id,
            "obra": obra,
            "origem": "uau",
            "status": status,
            "valor_contrato": valor_contrato,
            "data_assinatura": data_assinatura,
            "cliente_cpf": cliente_cpf,
            "cliente_codigo": cliente_codigo,
            "data_cancelamento": data_cancelamento,
            "raw_data": {
                "empresa": empresa,
                "obra": obra,
                "numero": numero,
                "status_code": status_code,
            },
            "last_synced_at": datetime.utcnow(),
        }

    def is_venda_finalizada(self, venda: Dict[str, Any]) -> bool:
        """
        Check if venda is in a finalized state (Cancelada or Quitada).

        Finalized vendas don't need to be re-synced as they won't change.

        Args:
            venda: Raw venda data or contract data

        Returns:
            True if venda is finalized (Cancelada=1 or Quitada=3)
        """
        status = str(venda.get("StatusVenda", venda.get("status", "0")))
        # Cancelada = 1, Quitada = 3
        return status in ("1", "3", "Cancelada", "Quitada")

    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int, returning None if not possible."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    # ============================================
    # Helper Methods
    # ============================================

    def _map_tipo_parcela_to_category(self, tipo: str) -> str:
        """Map UAU Tipo_Prc/ParcType_Rec to Starke category."""
        tipo = (tipo or "").upper().strip()

        # Common mappings based on typical UAU values
        mapping = {
            "E": "ativos",      # Entrada
            "M": "ativos",      # Mensal
            "P": "ativos",      # Periódica
            "I": "ativos",      # Intermediária
            "F": "ativos",      # Final
            "S": "ativos",      # Sinal
            "R": "recuperacoes",  # Renegociação
            "A": "antecipacoes",  # Antecipação
        }

        return mapping.get(tipo, "outras")

    def _parse_decimal(self, value: Any) -> Decimal:
        """Parse value to Decimal, handling None and various formats."""
        if value is None:
            return Decimal("0")

        if isinstance(value, Decimal):
            return value

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        if isinstance(value, str):
            cleaned = value.replace(",", "").replace(" ", "").strip()
            try:
                return Decimal(cleaned)
            except Exception:
                logger.warning(f"Could not parse decimal from: {value}")
                return Decimal("0")

        return Decimal("0")

    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse value to date, handling various formats."""
        if value is None:
            return None

        if isinstance(value, date):
            return value

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            # Try common formats
            formats = [
                "%Y-%m-%dT%H:%M:%S",      # ISO datetime
                "%Y-%m-%dT%H:%M:%S.%f",   # ISO datetime with microseconds
                "%Y-%m-%d",               # ISO date
                "%d/%m/%Y",               # Brazilian format
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue

            logger.warning(f"Could not parse date from: {value}")

        return None

    def _parse_date_str(self, value: Any) -> Optional[str]:
        """Parse value to date string in ISO format."""
        dt = self._parse_date(value)
        return dt.isoformat() if dt else None

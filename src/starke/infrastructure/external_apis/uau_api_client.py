"""UAU API Client (Globaltec/Senior) with authentication and error handling."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import httpx

from starke.core.config import get_settings

logger = logging.getLogger(__name__)


class UAUAPIError(Exception):
    """Base exception for UAU API errors."""

    pass


class UAUAuthenticationError(UAUAPIError):
    """Exception for authentication failures."""

    pass


class UAUAPIClient:
    """
    HTTP client for UAU API with dual-token authentication and retry logic.

    UAU API uses two tokens:
    - X-INTEGRATION-Authorization: Fixed integration token provided by client
    - Authorization: Session token obtained via login

    Features:
    - Dual-token authentication
    - Automatic session token refresh
    - Retry logic with exponential backoff
    - Schema filtering (first record is always schema definition)
    - Request/response logging
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        integration_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialize UAU API Client.

        Args:
            base_url: Base URL of UAU API (from env if not provided)
            integration_token: Fixed integration token (from env if not provided)
            username: API username (from env if not provided)
            password: API password (from env if not provided)
            timeout: Request timeout in seconds
        """
        settings = get_settings()

        self.base_url = base_url or settings.uau_api_url
        self.integration_token = integration_token or settings.uau_integration_token
        self.username = username or settings.uau_username
        self.password = password or settings.uau_password
        self.timeout = timeout or settings.uau_timeout
        self.max_retries = settings.uau_max_retries

        # Session token state
        self.session_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

        # HTTP client
        self.client = httpx.Client(timeout=self.timeout)

        # Cache for obras (avoid redundant API calls)
        self._obras_cache: Optional[List[Dict[str, Any]]] = None

        # Retry configuration
        self.retry_delay = 30  # seconds (fixed delay between retries)

        logger.info(f"UAU API Client initialized for {self.base_url}")

    def __enter__(self):
        """Context manager entry."""
        self.authenticate()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close HTTP client."""
        if self.client:
            self.client.close()

    # ============================================
    # Authentication
    # ============================================

    def authenticate(self, retry_count: int = 0) -> str:
        """
        Authenticate with UAU API and obtain session token.

        Uses dual-token authentication:
        - X-INTEGRATION-Authorization header with fixed integration token
        - Returns session token for Authorization header

        Args:
            retry_count: Current retry attempt (internal use)

        Returns:
            Session token

        Raises:
            UAUAuthenticationError: If authentication fails after all retries
        """
        # Ensure base_url ends with /
        base = self.base_url.rstrip("/") + "/"
        url = base + "Autenticador/AutenticarUsuario"

        headers = {
            "X-INTEGRATION-Authorization": self.integration_token,
            "Content-Type": "application/json",
        }

        payload = {"login": self.username, "senha": self.password}

        try:
            logger.info(f"Authenticating with UAU API as {self.username}")

            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            # UAU returns token directly as string
            self.session_token = response.text.strip().strip('"')

            if not self.session_token:
                raise UAUAuthenticationError("No session token in authentication response")

            # Token expires in 2 hours, set expiry to 115 minutes for safety
            self.token_expires_at = datetime.now() + timedelta(minutes=115)

            logger.info("Successfully authenticated with UAU API")
            return self.session_token

        except httpx.HTTPStatusError as e:
            # Retry for server errors (5xx)
            if e.response.status_code >= 500 and retry_count < self.max_retries:
                # Incremental backoff: 30s, 60s, 90s
                wait_time = self.retry_delay * (retry_count + 1)
                logger.warning(
                    f"UAU Authentication failed with {e.response.status_code}, "
                    f"retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})"
                )
                time.sleep(wait_time)
                return self.authenticate(retry_count + 1)

            logger.error(f"UAU Authentication failed: {e.response.status_code} - {e.response.text}")
            raise UAUAuthenticationError(f"Authentication failed: {e}")

        except httpx.RequestError as e:
            # Retry for network errors
            if retry_count < self.max_retries:
                # Incremental backoff: 30s, 60s, 90s
                wait_time = self.retry_delay * (retry_count + 1)
                logger.warning(
                    f"UAU Authentication network error, "
                    f"retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries}): {e}"
                )
                time.sleep(wait_time)
                return self.authenticate(retry_count + 1)

            logger.error(f"UAU Authentication error: {e}")
            raise UAUAuthenticationError(f"Authentication error: {e}")

        except Exception as e:
            logger.error(f"UAU Authentication error: {e}")
            raise UAUAuthenticationError(f"Authentication error: {e}")

    def ensure_authenticated(self) -> None:
        """Ensure client has valid session token."""
        if not self.session_token:
            self.authenticate()
            return

        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            logger.info("Session token expired, re-authenticating")
            self.authenticate()

    # ============================================
    # HTTP Methods
    # ============================================

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with both tokens."""
        return {
            "X-INTEGRATION-Authorization": self.integration_token,
            "Authorization": self.session_token,
            "Content-Type": "application/json",
        }

    def _filter_schema(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out schema definition from response.

        UAU API returns schema as first record in arrays.
        Schema records have type definitions like "System.Int32, mscorlib, ..."

        Args:
            data: Raw response data

        Returns:
            Data without schema record
        """
        if not data or not isinstance(data, list):
            return data

        if len(data) <= 1:
            return []

        # Check if first record looks like schema (has type definitions)
        first_record = data[0]
        if isinstance(first_record, dict):
            for value in first_record.values():
                if isinstance(value, str) and "System." in value and "mscorlib" in value:
                    return data[1:]  # Skip first record (schema)

        return data

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        filter_schema: bool = True,
    ) -> Any:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON body data
            retry_count: Current retry attempt
            filter_schema: Whether to filter schema from response

        Returns:
            Response JSON data (filtered)

        Raises:
            UAUAPIError: If request fails after all retries
        """
        self.ensure_authenticated()

        # Ensure correct URL construction
        base = self.base_url.rstrip("/") + "/"
        url = base + endpoint.lstrip("/")
        headers = self._get_headers()

        try:
            logger.debug(f"UAU {method} {url}")

            response = self.client.request(
                method=method, url=url, params=params, json=json_data, headers=headers
            )

            response.raise_for_status()

            if response.status_code == 204 or not response.content:
                return None

            data = response.json()

            # Filter schema if it's a list response
            if filter_schema and isinstance(data, list):
                data = self._filter_schema(data)

            logger.debug(f"UAU Response: {len(data) if isinstance(data, list) else 1} records")

            return data

        except httpx.HTTPStatusError as e:
            # Check if it's an authentication error
            if e.response.status_code in (401, 403):
                logger.warning("UAU Authentication error, refreshing token and retrying")
                self.authenticate()

                if retry_count < 1:
                    return self._make_request(method, endpoint, params, json_data, retry_count + 1, filter_schema)

            # Retry for server errors (5xx)
            if e.response.status_code >= 500 and retry_count < self.max_retries:
                # Incremental backoff: 30s, 60s, 90s
                wait_time = self.retry_delay * (retry_count + 1)
                logger.warning(
                    f"UAU Server error {e.response.status_code}, "
                    f"retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})"
                )
                time.sleep(wait_time)
                return self._make_request(method, endpoint, params, json_data, retry_count + 1, filter_schema)

            logger.error(f"UAU API request failed: {e.response.status_code} - {e.response.text}")
            raise UAUAPIError(f"API request failed: {e}")

        except httpx.RequestError as e:
            # Retry for network errors
            if retry_count < self.max_retries:
                # Incremental backoff: 30s, 60s, 90s
                wait_time = self.retry_delay * (retry_count + 1)
                logger.warning(f"UAU Network error, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
                return self._make_request(method, endpoint, params, json_data, retry_count + 1, filter_schema)

            logger.error(f"UAU Network error: {e}")
            raise UAUAPIError(f"Network error: {e}")

        except Exception as e:
            logger.error(f"UAU Unexpected error: {e}")
            raise UAUAPIError(f"Unexpected error: {e}")

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make GET request."""
        return self._make_request("GET", endpoint, params=params)

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Any:
        """Make POST request."""
        return self._make_request("POST", endpoint, json_data=json_data or {})

    # ============================================
    # Empresas (Companies = Empreendimentos)
    # ============================================

    def get_empresas(self) -> List[Dict[str, Any]]:
        """
        Get list of active empresas (companies).

        In UAU, Empresa = Empreendimento in Starke.

        Returns:
            List of empresas with fields:
            - Codigo_emp: int (ID)
            - Desc_emp: string (Name)
            - CGC_emp: string (CNPJ)
        """
        data = self.post("/Empresa/ObterEmpresasAtivas")
        return data if isinstance(data, list) else []

    # ============================================
    # Obras (Projects = Phases)
    # ============================================

    def get_obras(self) -> List[Dict[str, Any]]:
        """
        Get list of active obras (projects).

        In UAU, Obra = Phase of Empreendimento (group by Empresa).
        Results are cached for the session to avoid redundant API calls.

        Returns:
            List of obras with fields:
            - Cod_obr: string (Code)
            - Empresa_obr: int (FK to empresa)
            - Descr_obr: string (Name)
            - Status_obr: int (0 = active)
            - DtIni_obr: datetime (Start date)
        """
        # Return cached data if available
        if self._obras_cache is not None:
            logger.debug(f"Using cached obras ({len(self._obras_cache)} records)")
            return self._obras_cache

        data = self.post("/Obras/ObterObrasAtivas")
        self._obras_cache = data if isinstance(data, list) else []
        logger.info(f"Cached {len(self._obras_cache)} obras")
        return self._obras_cache

    def get_obras_by_empresa(self, empresa_id: int) -> List[Dict[str, Any]]:
        """
        Get obras filtered by empresa.

        Args:
            empresa_id: Empresa ID

        Returns:
            List of obras for the empresa
        """
        all_obras = self.get_obras()
        # Ensure empresa_id is int for comparison (API returns Empresa_obr as int)
        empresa_id_int = int(empresa_id)
        return [o for o in all_obras if o.get("Empresa_obr") == empresa_id_int]

    # ============================================
    # CashOut - Desembolso (Disbursements)
    # ============================================

    def get_desembolso(
        self,
        empresa: int,
        obra: str,
        mes_inicial: str,
        mes_final: str,
    ) -> List[Dict[str, Any]]:
        """
        Get disbursement planning data (CashOut).

        Returns budget, pending, and paid records.

        Args:
            empresa: Empresa ID
            obra: Obra code (e.g., "JVL00")
            mes_inicial: Start month in "MM/YYYY" format
            mes_final: End month in "MM/YYYY" format

        Returns:
            List of desembolso records with fields:
            - Status: "Projetado" | "Pagar" | "Pago"
            - Empresa, Obra, Contrato, Produto
            - Composicao, Item, Insumo (for categorization)
            - DtaRef, DtaRefMes, DtaRefAno (reference date)
            - Total, Acrescimo, Desconto, TotalLiq, TotalBruto
        """
        payload = {
            "Empresa": empresa,
            "Obra": obra,
            "MesInicial": mes_inicial,
            "MesFinal": mes_final,
        }

        data = self.post("/Planejamento/ConsultarDesembolsoPlanejamento", json_data=payload)
        return data if isinstance(data, list) else []

    def get_desembolso_empresa(
        self,
        empresa: int,
        mes_inicial: str,
        mes_final: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all disbursement data for an empresa (all obras).

        Args:
            empresa: Empresa ID
            mes_inicial: Start month in "MM/YYYY" format
            mes_final: End month in "MM/YYYY" format

        Returns:
            Combined list of desembolso records from all obras
        """
        obras = self.get_obras_by_empresa(empresa)
        all_data = []

        for obra in obras:
            obra_code = obra.get("Cod_obr")
            if obra_code:
                try:
                    data = self.get_desembolso(empresa, obra_code, mes_inicial, mes_final)
                    all_data.extend(data)
                except UAUAPIError as e:
                    logger.warning(f"Failed to get desembolso for obra {obra_code}: {e}")

        return all_data

    # ============================================
    # CashIn - Vendas e Parcelas (Sales and Installments)
    # ============================================

    def get_vendas_por_periodo(
        self,
        empresas_obras: List[Dict[str, Any]],
        data_inicio: str,
        data_fim: str,
        status_venda: Optional[str] = None,
    ) -> List[str]:
        """
        Get sales keys for a period.

        Args:
            empresas_obras: List of {"codigoEmpresa": int, "codigoObra": str}
            data_inicio: Start date in "YYYY-MM-DD" format
            data_fim: End date in "YYYY-MM-DD" format
            status_venda: Optional filter - "0" = Normal, "1" = Cancelled, "3" = Paid off
                          If None, returns all statuses

        Returns:
            List of sale keys in format "EMPRESA-OBRA/NUMVENDA" (e.g., "00093-JVA16/00006")
        """
        payload = {
            "data_inicio": f"{data_inicio}T00:00:00",
            "data_fim": f"{data_fim}T00:00:00",
            "listaEmpresaObra": empresas_obras,
        }

        if status_venda is not None:
            payload["statusVenda"] = status_venda

        data = self.post("/Venda/RetornaChavesVendasPorPeriodo", json_data=payload)

        # Response is a comma-separated string or list
        if isinstance(data, str):
            return [v.strip() for v in data.split(",") if v.strip()]
        elif isinstance(data, list):
            return data
        return []

    def get_parcelas_a_receber(
        self,
        empresa: int,
        obra: str,
        num_ven: int,
    ) -> List[Dict[str, Any]]:
        """
        Get installments to receive (CashIn forecast + delinquency).

        Args:
            empresa: Empresa ID
            obra: Obra code
            num_ven: Sale number

        Returns:
            List of parcelas with fields:
            - Empresa_prc, Obra_Prc, NumVend_prc, NumParc_Prc
            - Data_Prc (due date for ref_month)
            - Valor_Prc (forecast value)
            - Status_Prc (0 = open)
            - Tipo_Prc (type for categorization)
            - Cliente_Prc, nome_pes (client info)
        """
        payload = {
            "empresa": empresa,
            "obra": obra,
            "num_ven": num_ven,
        }

        data = self.post("/Venda/BuscarParcelasAReceber", json_data=payload)
        return data if isinstance(data, list) else []

    def get_parcelas_recebidas(
        self,
        empresa: int,
        obra: str,
        num_ven: int,
    ) -> List[Dict[str, Any]]:
        """
        Get received installments (CashIn actual).

        Note: Response has wrapper {"Recebidas": [...]}

        Args:
            empresa: Empresa ID
            obra: Obra code
            num_ven: Sale number

        Returns:
            List of parcelas with fields:
            - Empresa_rec, Obra_Rec, NumVend_Rec, NumParc_Rec
            - Data_Rec (payment date for ref_month)
            - ValorConf_Rec (actual value received)
            - Status_Rec (1 = confirmed)
            - ParcType_Rec (type for categorization)
        """
        payload = {
            "empresa": empresa,
            "obra": obra,
            "num_ven": num_ven,
        }

        # Use filter_schema=False because response has wrapper structure [{"Recebidas": [...]}]
        # The outer array has only 1 element which would be incorrectly filtered out
        data = self._make_request(
            "POST",
            "/Venda/BuscarParcelasRecebidas",
            json_data=payload,
            filter_schema=False,
        )

        # Handle wrapper structure: [{"Recebidas": [schema, data1, data2, ...]}]
        if isinstance(data, list) and len(data) > 0:
            first = data[0]
            if isinstance(first, dict) and "Recebidas" in first:
                recebidas = first["Recebidas"]
                if isinstance(recebidas, list):
                    return self._filter_schema(recebidas)

        return data if isinstance(data, list) else []

    def get_parcelas_venda_vp(
        self,
        empresa: int,
        obra: str,
        num_venda: int,
        data_calculo: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get sale installments with present value (VP) calculation.

        This endpoint automatically calculates present value with interest/fines.

        Args:
            empresa: Empresa ID
            obra: Obra code
            num_venda: Sale number
            data_calculo: Calculation date in "YYYY-MM-DD" format (default: today)

        Returns:
            List of parcelas with VP fields:
            - Principal_reaj (original value)
            - Valor_reaj (present value = VP)
            - Juros_reaj (calculated interest)
            - Multa_reaj (fine)
            - Correcao_reaj (monetary correction)
            - DataVenc_reaj (due date)
        """
        if not data_calculo:
            data_calculo = datetime.now().strftime("%Y-%m-%d")

        payload = {
            "empresa": empresa,
            "obra": obra,
            "num_venda": num_venda,
            "data_calculo": f"{data_calculo}T00:00:00",
            "boleto_antecipado": False,
        }

        data = self.post("/Venda/ConsultarParcelasDaVenda", json_data=payload)
        return data if isinstance(data, list) else []

    def exportar_vendas(
        self,
        vendas: List[Dict[str, Any]],
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Export sales (contracts) with full cadastral data.

        This endpoint returns complete sale data including:
        - Sale details (number, date, status, value)
        - Client information (code, CPF/CNPJ)
        - Items (products, prices, quantities)
        - Installments (parcelas) with payment status

        Args:
            vendas: List of sale keys {"Empresa": int, "Obra": str, "Venda": int}
            data_inicio: Optional start date filter (YYYY-MM-DD)
            data_fim: Optional end date filter (YYYY-MM-DD)

        Returns:
            Dict with XML-like structure:
            {
                "Vendas": {
                    "Venda": {  # or list of Vendas
                        "Empresa": "93",
                        "Obra": "JVA16",
                        "Numero": "8",
                        "DataDaVenda": "2021-04-23",
                        "StatusVenda": "1",  # 0=Normal, 1=Cancelada, 3=Quitada
                        "Clientes": {"Cliente": {...}},
                        "Itens": {"Item": {...}},
                        "Parcelas": {"Parcela": [...]}
                    }
                }
            }
        """
        payload: Dict[str, Any] = {
            "dados_vendas": {}
        }

        if vendas:
            payload["dados_vendas"]["listaVendas"] = vendas

        if data_inicio:
            payload["dados_vendas"]["dataInicio"] = f"{data_inicio}T00:00:00"

        if data_fim:
            payload["dados_vendas"]["dataFim"] = f"{data_fim}T23:59:59"

        # This endpoint returns XML-like structure, not array
        data = self._make_request(
            "POST",
            "/Venda/ExportarVendasXml",
            json_data=payload,
            filter_schema=False,
        )

        return data if isinstance(data, dict) else {}

    def exportar_vendas_por_periodo(
        self,
        empresa: int,
        data_inicio: str,
        data_fim: str,
        exclude_vendas: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        """
        Export all sales for an empresa in a period.

        Uses RetornaChavesVendasPorPeriodo to get sale keys, then ExportarVendasXml
        to get full data. Optionally excludes vendas already in cache (cancelled/paid off).

        Args:
            empresa: Empresa ID
            data_inicio: Start date (YYYY-MM-DD)
            data_fim: End date (YYYY-MM-DD)
            exclude_vendas: Optional set of venda keys to exclude (empresa, obra, numero)

        Returns:
            List of sale dicts with full data
        """
        # Get obras for empresa
        obras = self.get_obras_by_empresa(empresa)
        if not obras:
            logger.warning(f"No obras found for empresa {empresa}")
            return []

        # Get all venda keys for empresa
        empresas_obras = [
            {"codigoEmpresa": empresa, "codigoObra": o.get("Cod_obr")}
            for o in obras if o.get("Cod_obr")
        ]

        venda_keys = self.get_vendas_por_periodo(
            empresas_obras, data_inicio, data_fim
        )

        if not venda_keys:
            logger.info(f"No vendas found for empresa {empresa} in period")
            return []

        logger.info(f"Found {len(venda_keys)} vendas for empresa {empresa}")

        # Parse keys and filter excluded
        vendas_to_fetch = []
        for key in venda_keys:
            parsed = self._parse_venda_key(key)
            if not parsed:
                continue

            emp, obra, num = parsed

            # Skip if in exclude list
            if exclude_vendas and (emp, obra, num) in exclude_vendas:
                continue

            vendas_to_fetch.append({
                "Empresa": emp,
                "Obra": obra,
                "Venda": num
            })

        if not vendas_to_fetch:
            logger.info("All vendas already cached, nothing to fetch")
            return []

        logger.info(f"Fetching {len(vendas_to_fetch)} vendas (excluded {len(venda_keys) - len(vendas_to_fetch)} cached)")

        # Fetch in batches (optimized via benchmark - see docs/uau/benchmark_exportar_vendas.md)
        all_vendas = []
        batch_size = 15

        for i in range(0, len(vendas_to_fetch), batch_size):
            batch = vendas_to_fetch[i:i + batch_size]
            try:
                result = self.exportar_vendas(batch)
                vendas_data = self._extract_vendas_from_export(result)
                all_vendas.extend(vendas_data)
            except UAUAPIError as e:
                logger.error(f"Error fetching batch {i//batch_size + 1}: {e}")

        return all_vendas

    def _extract_vendas_from_export(self, export_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract vendas list from ExportarVendasXml response.

        Response can be:
        - {"Vendas": {"Venda": {...}}} - single venda
        - {"Vendas": {"Venda": [...]}} - multiple vendas

        Returns:
            List of venda dicts
        """
        if not export_result:
            return []

        vendas = export_result.get("Vendas", {})
        if not vendas:
            return []

        venda_data = vendas.get("Venda")
        if not venda_data:
            return []

        # Single venda or list
        if isinstance(venda_data, dict):
            return [venda_data]
        elif isinstance(venda_data, list):
            return venda_data

        return []

    # ============================================
    # Convenience Methods
    # ============================================

    def _parse_venda_key(self, venda_key: str) -> Optional[Tuple[int, str, int]]:
        """
        Parse venda key into components.

        Args:
            venda_key: Key in format "00093-JVA16/00006"

        Returns:
            Tuple of (empresa, obra, num_ven) or None if invalid
        """
        try:
            parts = venda_key.split("/")
            if len(parts) != 2:
                return None

            emp_obra = parts[0]  # "00093-JVA16"
            num_ven = int(parts[1])  # 6

            emp_obra_parts = emp_obra.split("-")
            if len(emp_obra_parts) != 2:
                return None

            venda_empresa = int(emp_obra_parts[0])
            venda_obra = emp_obra_parts[1]

            return (venda_empresa, venda_obra, num_ven)
        except Exception:
            return None

    def _fetch_parcelas_for_venda(
        self, venda_key: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetch parcelas a receber and recebidas for a single venda.

        Args:
            venda_key: Venda key in format "00093-JVA16/00006"

        Returns:
            Tuple of (parcelas_a_receber, parcelas_recebidas)
        """
        parsed = self._parse_venda_key(venda_key)
        if not parsed:
            return ([], [])

        venda_empresa, venda_obra, num_ven = parsed

        a_receber = []
        recebidas = []

        try:
            a_receber = self.get_parcelas_a_receber(venda_empresa, venda_obra, num_ven)
        except Exception as e:
            logger.warning(f"Failed to get parcelas_a_receber for {venda_key}: {e}")

        try:
            recebidas = self.get_parcelas_recebidas(venda_empresa, venda_obra, num_ven)
        except Exception as e:
            logger.warning(f"Failed to get parcelas_recebidas for {venda_key}: {e}")

        return (a_receber, recebidas)

    def get_all_parcelas_empresa(
        self,
        empresa: int,
        data_inicio: str,
        data_fim: str,
        max_workers: Optional[int] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all parcelas (forecast and actual) for an empresa using parallel requests.

        IMPORTANT: This method fetches ALL vendas (regardless of creation date)
        because parcelas from old vendas may have payments in the current period.
        We also fetch all venda statuses (Normal, Cancelled, Paid off) because
        they may have relevant parcelas.

        Args:
            empresa: Empresa ID
            data_inicio: Start date in "YYYY-MM-DD" format (used for filtering parcelas, not vendas)
            data_fim: End date in "YYYY-MM-DD" format (used for filtering parcelas, not vendas)
            max_workers: Number of parallel threads (default from UAU_MAX_WORKERS env var, or 5)

        Returns:
            Dict with:
            - "a_receber": List of parcelas a receber (forecast)
            - "recebidas": List of parcelas recebidas (actual)
        """
        # Use settings default if not provided
        if max_workers is None:
            settings = get_settings()
            max_workers = settings.uau_max_workers

        # Get all obras for empresa
        obras = self.get_obras_by_empresa(empresa)

        # Build list of empresa/obra pairs
        empresas_obras = [
            {"codigoEmpresa": empresa, "codigoObra": o.get("Cod_obr")}
            for o in obras if o.get("Cod_obr")
        ]

        if not empresas_obras:
            return {"a_receber": [], "recebidas": []}

        # Get ALL vendas - use a very old start date and no status filter
        all_vendas_keys = self.get_vendas_por_periodo(
            empresas_obras,
            data_inicio="2000-01-01",  # Fetch all historical vendas
            data_fim=data_fim,
            status_venda=None,  # No filter - get all statuses
        )

        total_vendas = len(all_vendas_keys)
        logger.info(f"Found {total_vendas} total vendas for empresa {empresa}. Starting parallel fetch with {max_workers} workers...")

        all_a_receber = []
        all_recebidas = []
        processed = 0
        errors = 0

        # Use ThreadPoolExecutor for parallel requests
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_venda = {
                executor.submit(self._fetch_parcelas_for_venda, venda_key): venda_key
                for venda_key in all_vendas_keys
            }

            # Process results as they complete
            for future in as_completed(future_to_venda):
                venda_key = future_to_venda[future]
                processed += 1

                try:
                    a_receber, recebidas = future.result()
                    all_a_receber.extend(a_receber)
                    all_recebidas.extend(recebidas)
                except Exception as e:
                    errors += 1
                    logger.warning(f"Failed to process venda {venda_key}: {e}")

                # Log progress every 100 vendas
                if processed % 100 == 0:
                    logger.info(
                        f"Progress: {processed}/{total_vendas} vendas processed "
                        f"({processed * 100 // total_vendas}%) - "
                        f"a_receber: {len(all_a_receber)}, recebidas: {len(all_recebidas)}, errors: {errors}"
                    )

        logger.info(
            f"Completed: {processed} vendas processed - "
            f"a_receber: {len(all_a_receber)}, recebidas: {len(all_recebidas)}, errors: {errors}"
        )

        return {
            "a_receber": all_a_receber,
            "recebidas": all_recebidas,
        }

    def _fetch_vp_for_venda(
        self, venda_key: str, data_calculo: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch VP parcelas for a single venda.

        Args:
            venda_key: Venda key in format "00093-JVA16/00006"
            data_calculo: Calculation date in "YYYY-MM-DD" format

        Returns:
            List of parcelas with VP
        """
        parsed = self._parse_venda_key(venda_key)
        if not parsed:
            return []

        venda_empresa, venda_obra, num_ven = parsed

        try:
            return self.get_parcelas_venda_vp(venda_empresa, venda_obra, num_ven, data_calculo)
        except Exception as e:
            logger.warning(f"Failed to get VP for {venda_key}: {e}")
            return []

    def get_all_parcelas_vp_empresa(
        self,
        empresa: int,
        data_calculo: str,
        max_workers: Optional[int] = None,
        vendas_com_parcelas_a_receber: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all parcelas with VP for an empresa using parallel requests.

        Args:
            empresa: Empresa ID
            data_calculo: Calculation date in "YYYY-MM-DD" format
            max_workers: Number of parallel threads (default from UAU_MAX_WORKERS env var, or 5)
            vendas_com_parcelas_a_receber: Optional set of venda keys that have parcelas a receber.
                If provided, only these vendas will be queried for VP (optimization).
                Format: {(empresa, obra, num_venda), ...}

        Returns:
            List of parcelas with VP fields (Valor_reaj, Principal_reaj, etc.)
        """
        # Use settings default if not provided
        if max_workers is None:
            settings = get_settings()
            max_workers = settings.uau_max_workers

        # If we have a pre-filtered list of vendas with parcelas, use it directly
        if vendas_com_parcelas_a_receber:
            # Convert tuples (empresa, obra, num_venda) to string format "XXXXX-OBRA/YYYYY"
            all_vendas_keys = []
            for venda_tuple in vendas_com_parcelas_a_receber:
                empresa_id, obra, num_venda = venda_tuple
                # Format: "00002-JVA01/00123"
                venda_key = f"{int(empresa_id):05d}-{obra}/{int(num_venda):05d}"
                all_vendas_keys.append(venda_key)
            total_vendas = len(all_vendas_keys)
            logger.info(f"Using cached list: {total_vendas} vendas with parcelas a receber for VP calculation")
        else:
            # Get all obras for empresa
            obras = self.get_obras_by_empresa(empresa)

            # Build list of empresa/obra pairs
            empresas_obras = [
                {"codigoEmpresa": empresa, "codigoObra": o.get("Cod_obr")}
                for o in obras if o.get("Cod_obr")
            ]

            if not empresas_obras:
                return []

            # Get ALL vendas
            all_vendas_keys = self.get_vendas_por_periodo(
                empresas_obras,
                data_inicio="2000-01-01",
                data_fim=data_calculo,
                status_venda=None,
            )
            total_vendas = len(all_vendas_keys)

        logger.info(f"Found {total_vendas} vendas for VP calculation. Starting parallel fetch with {max_workers} workers...")

        all_parcelas_vp = []
        processed = 0
        errors = 0

        # Use ThreadPoolExecutor for parallel requests
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_venda = {
                executor.submit(self._fetch_vp_for_venda, venda_key, data_calculo): venda_key
                for venda_key in all_vendas_keys
            }

            # Process results as they complete
            for future in as_completed(future_to_venda):
                venda_key = future_to_venda[future]
                processed += 1

                try:
                    parcelas = future.result()
                    all_parcelas_vp.extend(parcelas)
                except Exception as e:
                    errors += 1
                    logger.warning(f"Failed to process VP for venda {venda_key}: {e}")

                # Log progress every 100 vendas
                if processed % 100 == 0:
                    logger.info(
                        f"VP Progress: {processed}/{total_vendas} vendas "
                        f"({processed * 100 // total_vendas}%) - "
                        f"parcelas: {len(all_parcelas_vp)}, errors: {errors}"
                    )

        logger.info(
            f"VP Completed: {processed} vendas processed - "
            f"parcelas: {len(all_parcelas_vp)}, errors: {errors}"
        )

        return all_parcelas_vp

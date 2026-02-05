"""Enhanced Mega API Client with authentication and error handling."""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx

from starke.core.config_loader import get_mega_config

logger = logging.getLogger(__name__)


class MegaAPIError(Exception):
    """Base exception for Mega API errors."""

    pass


class MegaAuthenticationError(MegaAPIError):
    """Exception for authentication failures."""

    pass


class MegaAPIClient:
    """
    HTTP client for Mega API with authentication and retry logic.

    Features:
    - Automatic authentication and token refresh
    - Retry logic with exponential backoff
    - Request/response logging
    - Error handling
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        tenant_id: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialize Mega API Client.

        Args:
            base_url: Base URL of Mega API (from env if not provided)
            username: API username (from env if not provided)
            password: API password (from env if not provided)
            tenant_id: Tenant ID for MegaCloud (from env if not provided)
            timeout: Request timeout in seconds
        """
        # Load configuration
        self.config = get_mega_config()

        # API configuration
        self.base_url = base_url or self._get_env_var("MEGA_API_URL")
        self.username = username or self._get_env_var("MEGA_API_USERNAME")
        self.password = password or self._get_env_var("MEGA_API_PASSWORD")
        self.tenant_id = tenant_id or self._get_env_var("MEGA_API_TENANT_ID")
        self.timeout = timeout or self.config.get_timeout_api_segundos()

        # Authentication state
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

        # HTTP client
        self.client = httpx.Client(timeout=self.timeout)

        # Retry configuration
        self.max_retries = self.config.get_max_retries()
        self.retry_delay = self.config.get_retry_delay_segundos()

        logger.info(f"Mega API Client initialized for {self.base_url}")

    def _get_env_var(self, var_name: str) -> str:
        """Get environment variable or raise error."""
        import os

        value = os.getenv(var_name)
        if not value:
            raise ValueError(
                f"Environment variable {var_name} not set. "
                f"Please set it in .env file or environment."
            )
        return value

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

    def authenticate(self) -> None:
        """
        Authenticate with Mega API and obtain access token.

        Raises:
            MegaAuthenticationError: If authentication fails
        """
        url = urljoin(self.base_url, "/api/Auth/SignIn")

        payload = {"userName": self.username, "password": self.password}

        # Add required headers for MegaCloud
        headers = {
            "tenantId": self.tenant_id,
            "grantType": "Api"
        }

        try:
            logger.info(f"Authenticating with Mega API as {self.username}")

            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()

            self.access_token = data.get("accessToken") or data.get("access_token")
            self.refresh_token = data.get("refreshToken") or data.get("refresh_token")

            if not self.access_token:
                raise MegaAuthenticationError("No access token in authentication response")

            # Token expires in 2 hours, set expiry to 115 minutes for safety
            self.token_expires_at = datetime.now() + timedelta(minutes=115)

            logger.info("Successfully authenticated with Mega API")

        except httpx.HTTPStatusError as e:
            logger.error(f"Authentication failed: {e.response.status_code} - {e.response.text}")
            raise MegaAuthenticationError(f"Authentication failed: {e}")
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise MegaAuthenticationError(f"Authentication error: {e}")

    def refresh_access_token(self) -> None:
        """
        Refresh access token using refresh token.

        Raises:
            MegaAuthenticationError: If token refresh fails
        """
        if not self.refresh_token:
            logger.warning("No refresh token available, re-authenticating")
            self.authenticate()
            return

        url = urljoin(self.base_url, "/api/autenticacao/AtualizarToken")

        payload = {"refreshToken": self.refresh_token}

        try:
            logger.info("Refreshing Mega API access token")

            response = self.client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()

            self.access_token = data.get("accessToken") or data.get("access_token")

            if not self.access_token:
                raise MegaAuthenticationError("No access token in refresh response")

            self.token_expires_at = datetime.now() + timedelta(minutes=55)

            logger.info("Successfully refreshed access token")

        except httpx.HTTPStatusError as e:
            logger.warning(f"Token refresh failed, re-authenticating: {e}")
            self.authenticate()
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            self.authenticate()

    def ensure_authenticated(self) -> None:
        """Ensure client has valid access token."""
        if not self.access_token:
            self.authenticate()
            return

        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            self.refresh_access_token()

    # ============================================
    # HTTP Methods
    # ============================================

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> Any:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/api/globalestruturas/Empreendimentos")
            params: Query parameters
            json_data: JSON body data
            retry_count: Current retry attempt

        Returns:
            Response JSON data

        Raises:
            MegaAPIError: If request fails after all retries
        """
        self.ensure_authenticated()

        url = urljoin(self.base_url, endpoint)

        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            if self.config.should_log_api_calls():
                logger.debug(f"{method} {url} params={params}")

            response = self.client.request(
                method=method, url=url, params=params, json=json_data, headers=headers
            )

            response.raise_for_status()

            # Check if response has content
            if response.status_code == 204 or not response.content:
                return None

            data = response.json()

            if self.config.should_log_api_calls():
                logger.debug(f"Response: {len(str(data))} bytes")

            return data

        except httpx.HTTPStatusError as e:
            # Check if it's an authentication error
            if e.response.status_code in (401, 403):
                logger.warning("Authentication error, refreshing token and retrying")
                self.refresh_access_token()

                if retry_count < 1:  # Retry once with new token
                    return self._make_request(method, endpoint, params, json_data, retry_count + 1)

            # Retry for rate limiting (429 Too Many Requests)
            if e.response.status_code == 429 and retry_count < self.max_retries:
                # Longer wait for rate limiting: 30s, 60s, 90s
                wait_time = 30 * (retry_count + 1)
                logger.warning(
                    f"Rate limited (429), waiting {wait_time}s "
                    f"(attempt {retry_count + 1}/{self.max_retries})"
                )
                time.sleep(wait_time)
                return self._make_request(method, endpoint, params, json_data, retry_count + 1)

            # Retry for server errors (5xx)
            if e.response.status_code >= 500 and retry_count < self.max_retries:
                wait_time = self.retry_delay * (2**retry_count)  # Exponential backoff
                logger.warning(
                    f"Server error {e.response.status_code}, "
                    f"retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})"
                )
                time.sleep(wait_time)
                return self._make_request(method, endpoint, params, json_data, retry_count + 1)

            logger.error(f"API request failed: {e.response.status_code} - {e.response.text}")
            raise MegaAPIError(f"API request failed: {e}")

        except httpx.RequestError as e:
            # Retry for network errors
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2**retry_count)
                logger.warning(
                    f"Network error, retrying in {wait_time}s "
                    f"(attempt {retry_count + 1}/{self.max_retries}): {e}"
                )
                time.sleep(wait_time)
                return self._make_request(method, endpoint, params, json_data, retry_count + 1)

            logger.error(f"Network error: {e}")
            raise MegaAPIError(f"Network error: {e}")

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise MegaAPIError(f"Unexpected error: {e}")

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make GET request."""
        return self._make_request("GET", endpoint, params=params)

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Any:
        """Make POST request."""
        return self._make_request("POST", endpoint, json_data=json_data)

    # ============================================
    # Empreendimentos (Developments)
    # ============================================

    def get_empreendimentos(
        self,
        filial: Optional[int] = None,
        organizacao: Optional[int] = None,
        expand: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get list of empreendimentos (developments).

        Args:
            filial: Optional filial code filter
            organizacao: Optional organization code filter
            expand: Optional expand parameter (e.g., "projeto,centrocusto")

        Returns:
            List of empreendimentos
        """
        if filial is not None:
            endpoint = "/api/globalestruturas/Empreendimentos/Filial"
            params = {"filial": filial}
            if organizacao is not None:
                params["organizacao"] = organizacao
            if expand:
                params["expand"] = expand
        else:
            endpoint = "/api/globalestruturas/Empreendimentos"
            params = {}
            if expand:
                params["expand"] = expand

        data = self.get(endpoint, params=params)
        return data if isinstance(data, list) else []

    def get_empreendimento(self, empreendimento_id: str, expand: Optional[str] = None) -> Dict[str, Any]:
        """
        Get specific empreendimento by ID.

        Args:
            empreendimento_id: Encrypted empreendimento ID
            expand: Optional expand parameter

        Returns:
            Empreendimento data
        """
        endpoint = f"/api/globalestruturas/Empreendimentos/{empreendimento_id}"
        params = {"expand": expand} if expand else None
        return self.get(endpoint, params=params)

    # ============================================
    # Contratos (Contracts)
    # ============================================

    def get_contratos(self, empreendimento_id: str) -> List[Dict[str, Any]]:
        """
        Get contracts for an empreendimento using encrypted ID.

        Args:
            empreendimento_id: Encrypted empreendimento ID

        Returns:
            List of contracts
        """
        endpoint = f"/api/Carteira/Contratos/{empreendimento_id}"
        data = self.get(endpoint)
        return data if isinstance(data, list) else []

    def get_contratos_by_development_id(self, development_id: int) -> List[Dict[str, Any]]:
        """
        Get contracts for an empreendimento using numeric development ID.

        This is the preferred method for fetching contracts as it uses the numeric
        'codigo' field from empreendimentos instead of encrypted IDs.

        Args:
            development_id: Numeric development ID (e.g., 24905)

        Returns:
            List of contracts

        Example:
            >>> client.get_contratos_by_development_id(24905)
            [{"cod_contrato": "123", ...}, ...]
        """
        endpoint = f"/api/Carteira/DadosContrato/IdEmpreendimento={development_id}"
        data = self.get(endpoint)
        return data if isinstance(data, list) else []

    def get_all_contratos(self) -> List[Dict[str, Any]]:
        """
        Get ALL contracts across all developments (optimization for bulk operations).

        This is more efficient than calling get_contratos_by_development_id()
        for each development individually. Uses IdEmpreendimento=0 to fetch all.

        Returns:
            List of ALL contracts

        Example:
            >>> client.get_all_contratos()
            [{"cod_contrato": "123", "empreendimento_id": 24905, ...}, ...]
        """
        logger.info("Fetching ALL contracts from Mega API (IdEmpreendimento=0)")
        return self.get_contratos_by_development_id(0)

    def get_contrato(self, contrato_id: str) -> Dict[str, Any]:
        """
        Get specific contract details.

        Args:
            contrato_id: Encrypted contract ID

        Returns:
            Contract data
        """
        endpoint = f"/api/Carteira/Contratos/Dados/{contrato_id}"
        return self.get(endpoint)

    # ============================================
    # Parcelas (Installments)
    # ============================================

    def get_parcelas(self, contrato_id: str) -> List[Dict[str, Any]]:
        """
        Get installments for a contract using encrypted ID.

        Args:
            contrato_id: Encrypted contract ID

        Returns:
            List of installments
        """
        endpoint = f"/api/Carteira/Parcelas/{contrato_id}"
        data = self.get(endpoint)
        return data if isinstance(data, list) else []

    def get_parcelas_by_contract_id(self, contract_id: int) -> List[Dict[str, Any]]:
        """
        Get installments for a contract using numeric contract ID.

        This is the preferred method for fetching parcelas as it uses the numeric
        'cod_contrato' field instead of encrypted IDs.

        Args:
            contract_id: Numeric contract ID (e.g., 11530)

        Returns:
            List of installments

        Example:
            >>> client.get_parcelas_by_contract_id(11530)
            [{"cod_parcela": "4577971", ...}, ...]
        """
        endpoint = f"/api/Carteira/DadosParcelas/IdContrato={contract_id}"
        data = self.get(endpoint)
        return data if isinstance(data, list) else []

    # ============================================
    # Contas a Pagar (Accounts Payable)
    # ============================================

    def get_faturas_pagar(
        self,
        vencto_inicial: str,
        vencto_final: str,
        filial: Optional[int] = None,
        expand: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get accounts payable invoices.

        Args:
            vencto_inicial: Start date (YYYY-MM-DD)
            vencto_final: End date (YYYY-MM-DD)
            filial: Optional filial filter
            expand: Optional expand parameter

        Returns:
            List of invoices
        """
        if filial is not None:
            endpoint = f"/api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/{filial}/{vencto_inicial}/{vencto_final}"
        else:
            endpoint = f"/api/FinanceiroMovimentacao/FaturaPagar/Saldo/{vencto_inicial}/{vencto_final}"

        params = {"expand": expand} if expand else None
        data = self.get(endpoint, params=params)
        return data if isinstance(data, list) else []

    # ============================================
    # Contas a Receber (Accounts Receivable)
    # ============================================

    def get_faturas_receber(
        self,
        vencto_inicial: str,
        vencto_final: str,
        filial: Optional[int] = None,
        expand: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get accounts receivable invoices.

        Args:
            vencto_inicial: Start date (YYYY-MM-DD)
            vencto_final: End date (YYYY-MM-DD)
            filial: Optional filial filter
            expand: Optional expand parameter

        Returns:
            List of invoices
        """
        if filial is not None:
            endpoint = f"/api/FinanceiroMovimentacao/FaturaReceber/Saldo/Filial/{filial}/{vencto_inicial}/{vencto_final}"
        else:
            endpoint = f"/api/FinanceiroMovimentacao/FaturaReceber/Saldo/{vencto_inicial}/{vencto_final}"

        params = {"expand": expand} if expand else None
        data = self.get(endpoint, params=params)
        return data if isinstance(data, list) else []

    # ============================================
    # Saldos Contábeis (Accounting Balances)
    # ============================================

    def get_saldo_centro_custo(
        self,
        filial: str,
        data_inicial: str,
        data_final: str,
        expand: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get accounting balances by cost center.

        Args:
            filial: Filial code or CNPJ
            data_inicial: Start date (YYYY-MM-DD)
            data_final: End date (YYYY-MM-DD)
            expand: Optional expand parameter (e.g., "CentroCusto,Conta")

        Returns:
            List of balances
        """
        endpoint = "/api/lancamento/Saldo/centroCusto"
        params = {
            "Filial": filial,
            "DataInicial": data_inicial,
            "DataFinal": data_final,
        }
        if expand:
            params["Expand"] = expand

        data = self.get(endpoint, params=params)
        return data if isinstance(data, list) else []

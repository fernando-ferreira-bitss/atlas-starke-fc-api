"""Mega ERP API Client with retry and rate limiting."""

from datetime import datetime
from typing import Any, Optional, Union

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from starke.core.config import get_settings
from starke.core.date_helpers import utc_now
from starke.core.logging import get_logger

logger = get_logger(__name__)


class MegaAPIError(Exception):
    """Base exception for Mega API errors."""

    pass


class MegaAPIClient:
    """Client for Mega ERP Carteira API with authentication and retry logic."""

    def __init__(self) -> None:
        """Initialize Mega API client."""
        self.settings = get_settings()
        self.base_url = self.settings.mega_api_url.rstrip("/")
        self.tenant_id = self.settings.mega_api_tenant_id
        self.username = self.settings.mega_api_username
        self.password = self.settings.mega_api_password
        self.timeout = self.settings.mega_api_timeout

        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )

        # Token management
        self._access_token: Optional[str] = None
        self._token_expiration: Optional[datetime] = None
        self._refresh_token: Optional[str] = None

        logger.info("Mega API client initialized", base_url=self.base_url)

    def _authenticate(self) -> None:
        """Authenticate with Mega API and get access token."""
        logger.info("Authenticating with Mega API")

        try:
            response = self.client.post(
                "/api/Auth/SignIn",
                headers={
                    "tenantId": self.tenant_id,
                    "grantType": "Api",
                },
                json={
                    "userName": self.username,
                    "password": self.password,
                },
            )
            response.raise_for_status()

            data = response.json()
            self._access_token = data.get("accessToken")
            self._refresh_token = data.get("refreshToken")

            # Parse expiration time
            expiration_str = data.get("expirationToken")
            if expiration_str:
                # Handle microseconds with varying precision (API can return 5-7 digits, Python supports 6)
                # Remove 'Z' suffix
                expiration_str = expiration_str.replace("Z", "")

                # Split date/time from timezone offset
                if "+" in expiration_str:
                    dt_part, tz_part = expiration_str.rsplit("+", 1)
                    tz_part = "+" + tz_part
                elif expiration_str.count("-") > 2:  # Has timezone offset with -
                    dt_part, tz_part = expiration_str.rsplit("-", 1)
                    tz_part = "-" + tz_part
                else:
                    dt_part = expiration_str
                    tz_part = ""

                # Normalize microseconds to 6 digits
                if "." in dt_part:
                    base, microsec = dt_part.rsplit(".", 1)
                    # Pad or truncate to exactly 6 digits
                    if len(microsec) < 6:
                        microsec = microsec.ljust(6, "0")
                    elif len(microsec) > 6:
                        microsec = microsec[:6]
                    dt_part = f"{base}.{microsec}"

                expiration_str = dt_part + tz_part
                self._token_expiration = datetime.fromisoformat(expiration_str)

            logger.info("Authentication successful",
                       token_expires=self._token_expiration.isoformat() if self._token_expiration else None)

        except httpx.HTTPStatusError as e:
            logger.error("Authentication failed", status_code=e.response.status_code, error=str(e))
            raise MegaAPIError(f"Authentication failed: {e}") from e
        except Exception as e:
            logger.error("Authentication error", error=str(e))
            raise MegaAPIError(f"Authentication error: {e}") from e

    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token."""
        # Check if we need to authenticate or refresh
        if not self._access_token:
            self._authenticate()
        elif self._token_expiration:
            # Compare with timezone-aware datetime
            now = utc_now()
            if now >= self._token_expiration:
                logger.info("Token expired, re-authenticating")
                self._authenticate()

        # Update client headers with token
        if self._access_token:
            self.client.headers["Authorization"] = f"Bearer {self._access_token}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Union[dict[str, Any], list[Any]]:
        """Make HTTP request with retry logic."""
        # Ensure we have a valid token
        self._ensure_authenticated()

        url = f"{endpoint}" if endpoint.startswith("/") else f"/{endpoint}"

        logger.debug(
            "Making API request",
            method=method,
            endpoint=url,
            has_params="params" in kwargs,
            has_json="json" in kwargs,
        )

        try:
            response = self.client.request(method, url, **kwargs)
            response.raise_for_status()

            # Handle different response types
            if response.status_code == 204:
                logger.warning("API returned 204 No Content", endpoint=url)
                return []

            data = response.json()
            logger.info(
                "API request successful",
                method=method,
                endpoint=url,
                status_code=response.status_code,
            )
            return data

        except httpx.HTTPStatusError as e:
            # Handle rate limiting (429) with retry
            if e.response.status_code == 429:
                retry_count = kwargs.get("_retry_count", 0)
                if retry_count < 3:
                    wait_time = 30 * (retry_count + 1)  # 30s, 60s, 90s
                    logger.warning(
                        "Rate limited (429), waiting before retry",
                        method=method,
                        endpoint=url,
                        wait_time=wait_time,
                        attempt=retry_count + 1,
                    )
                    import time
                    time.sleep(wait_time)
                    kwargs["_retry_count"] = retry_count + 1
                    return self._request(method, endpoint, **kwargs)

            logger.error(
                "API request failed",
                method=method,
                endpoint=url,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise MegaAPIError(f"API request failed: {e}") from e

        except httpx.RequestError as e:
            logger.error(
                "Network error during API request",
                method=method,
                endpoint=url,
                error=str(e),
            )
            raise

    def get_empreendimentos(
        self, filial: Optional[int] = None, organizacao: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """
        Get all empreendimentos (projects).

        Args:
            filial: Branch code (optional)
            organizacao: Organization code (optional)

        Returns:
            List of empreendimento data
        """
        endpoint = "/api/globalestruturas/Empreendimentos"
        params = {}
        if filial is not None:
            params["filial"] = filial
        if organizacao is not None:
            params["organizacao"] = organizacao

        result = self._request("GET", endpoint, params=params)

        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_contratos_by_empreendimento(self, empreendimento_id: int) -> list[dict[str, Any]]:
        """
        Get all contracts for a specific empreendimento.

        Args:
            empreendimento_id: ID of the empreendimento

        Returns:
            List of contract data
        """
        endpoint = f"/api/Carteira/DadosContrato/IdEmpreendimento={empreendimento_id}"
        result = self._request("GET", endpoint)

        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_contrato_by_id(self, contrato_id: int) -> dict[str, Any]:
        """
        Get contract data by ID.

        Args:
            contrato_id: ID of the contract

        Returns:
            Contract data
        """
        endpoint = f"/api/Carteira/DadosContrato/IdContrato={contrato_id}"
        result = self._request("GET", endpoint)

        if isinstance(result, list):
            return result[0] if result else {}
        return result

    def get_parcelas_by_contrato(self, contrato_id: int) -> list[dict[str, Any]]:
        """
        Get all installments for a specific contract.

        Args:
            contrato_id: ID of the contract

        Returns:
            List of installment data
        """
        endpoint = f"/api/Carteira/DadosParcelas/IdContrato={contrato_id}"
        result = self._request("GET", endpoint)

        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_participantes_by_empreendimento(
        self, empreendimento_id: int
    ) -> list[dict[str, Any]]:
        """
        Get all participants for a specific empreendimento.

        Args:
            empreendimento_id: ID of the empreendimento

        Returns:
            List of participant data
        """
        endpoint = f"/api/Carteira/DadosParticipantes/IdEmpreendimento={empreendimento_id}"
        result = self._request("GET", endpoint)

        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_renegociacoes_by_contrato(self, contrato_id: int) -> list[dict[str, Any]]:
        """
        Get all renegotiations for a specific contract.

        Args:
            contrato_id: ID of the contract

        Returns:
            List of renegotiation data
        """
        endpoint = f"/api/Carteira/DadosRenegociacoes/IdContrato={contrato_id}"
        result = self._request("GET", endpoint)

        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_despesas(self, data_inicio: str, data_fim: str) -> list[dict[str, Any]]:
        """
        Get ALL despesas (contas a pagar) for all filiais in date range.

        This method fetches despesas from all filiais at once, which is more efficient
        than calling get_despesas_by_filial multiple times.

        Args:
            data_inicio: Start date in YYYY-MM-DD format
            data_fim: End date in YYYY-MM-DD format

        Returns:
            List of despesas data from all filiais

        Note:
            The API endpoint returns parcelas with SaldoAtual field:
            - SaldoAtual = 0: Paid (use for actual)
            - SaldoAtual > 0: Unpaid (use for forecast)

            To filter by empreendimento, use Agente.Codigo which corresponds to cod_contrato.
        """
        endpoint = f"/api/FinanceiroMovimentacao/FaturaPagar/Saldo/{data_inicio}/{data_fim}"

        result = self._request("GET", endpoint)

        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_receitas(self, data_inicio: str, data_fim: str) -> list[dict[str, Any]]:
        """
        Get ALL receitas (contas a receber) for all filiais in date range.

        This method fetches receitas from all filiais at once.

        Args:
            data_inicio: Start date in YYYY-MM-DD format
            data_fim: End date in YYYY-MM-DD format

        Returns:
            List of receitas data from all filiais

        Note:
            To filter by empreendimento, use Agente.Codigo which corresponds to cod_contrato.
        """
        endpoint = f"/api/FinanceiroMovimentacao/FaturaReceber/Saldo/{data_inicio}/{data_fim}"

        result = self._request("GET", endpoint)

        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_despesas_by_filial(
        self, filial_id: int, data_inicio: str, data_fim: str
    ) -> list[dict[str, Any]]:
        """
        Get all despesas (contas a pagar) for a specific filial and date range.

        DEPRECATED: Use get_despesas() instead, which fetches from all filiais at once.

        Args:
            filial_id: ID of the filial (empreendimento)
            data_inicio: Start date in YYYY-MM-DD format
            data_fim: End date in YYYY-MM-DD format

        Returns:
            List of despesas data

        Note:
            The API endpoint returns parcelas with SaldoAtual field:
            - SaldoAtual = 0: Paid (use for actual)
            - SaldoAtual > 0: Unpaid (use for forecast)
        """
        endpoint = (
            f"/api/FinanceiroMovimentacao/FaturaPagar/Saldo/Filial/"
            f"{filial_id}/{data_inicio}/{data_fim}"
        )

        # Request with expand parameter to get classe financeira and other details
        params = {"expand": "classeFinanceira,centroCusto,projeto"}

        result = self._request("GET", endpoint, params=params)

        if isinstance(result, list):
            return result
        return [result] if result else []

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
        logger.info("Mega API client closed")

    def __enter__(self) -> "MegaAPIClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

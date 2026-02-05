"""BCB PTAX quotation client for fetching currency exchange rates."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

import httpx

from starke.core.logging import get_logger

logger = get_logger(__name__)


class BCBQuotationClient:
    """Client for BCB PTAX API to fetch currency exchange rates.

    Uses the OLINDA API from Banco Central do Brasil to get official
    PTAX quotations (selling rates) for USD, EUR and other currencies.

    API Documentation:
    https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/documentacao
    """

    BASE_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"

    # Supported currencies (BCB symbols)
    SUPPORTED_CURRENCIES = {"USD", "EUR"}

    def __init__(self) -> None:
        """Initialize BCB quotation client."""
        # Cache: {currency_YYYY-MM-DD: Decimal}
        self._cache: dict[str, Decimal] = {}
        # Track when current day's quote was fetched (for TTL)
        self._current_day_fetch_time: dict[str, datetime] = {}
        # Cache TTL for current day quotes (1 hour)
        self._current_day_ttl = timedelta(hours=1)

    def _get_cache_key(self, currency: str, ref_date: date) -> str:
        """Generate cache key for a currency/date pair."""
        return f"{currency}_{ref_date.isoformat()}"

    def _is_cache_valid(self, currency: str, ref_date: date) -> bool:
        """Check if cached value is still valid.

        Past dates: always valid (quotes don't change)
        Current date: valid for TTL period
        """
        cache_key = self._get_cache_key(currency, ref_date)

        if cache_key not in self._cache:
            return False

        # Past dates are always valid
        if ref_date < date.today():
            return True

        # Current date: check TTL
        fetch_time = self._current_day_fetch_time.get(cache_key)
        if fetch_time and datetime.now() - fetch_time < self._current_day_ttl:
            return True

        return False

    def _format_date_for_api(self, ref_date: date) -> str:
        """Format date for BCB API (MM-DD-YYYY)."""
        return ref_date.strftime("%m-%d-%Y")

    def _find_last_business_day(self, ref_date: date) -> date:
        """Find last business day on or before ref_date.

        BCB doesn't publish quotes on weekends/holidays.
        This goes back up to 7 days to find a quote.
        """
        current = ref_date
        for _ in range(7):
            # Skip weekends (Saturday=5, Sunday=6)
            if current.weekday() < 5:
                return current
            current -= timedelta(days=1)
        return ref_date

    def get_quotation(
        self,
        currency: str,
        ref_date: Optional[date] = None
    ) -> Optional[Decimal]:
        """Get selling quotation (PTAX) for a currency on a specific date.

        Args:
            currency: Currency code (USD, EUR)
            ref_date: Reference date (defaults to today)

        Returns:
            Exchange rate (BRL per 1 unit of foreign currency)
            or None if not available
        """
        if ref_date is None:
            ref_date = date.today()

        if currency not in self.SUPPORTED_CURRENCIES:
            logger.warning(
                "Unsupported currency requested",
                currency=currency,
                supported=list(self.SUPPORTED_CURRENCIES),
            )
            return None

        # Check cache
        if self._is_cache_valid(currency, ref_date):
            cache_key = self._get_cache_key(currency, ref_date)
            logger.debug(
                "Using cached quotation",
                currency=currency,
                date=ref_date.isoformat(),
                rate=float(self._cache[cache_key]),
            )
            return self._cache[cache_key]

        # Try to fetch quote for the date
        quote = self._fetch_quotation_from_api(currency, ref_date)

        # If no quote (weekend/holiday), try previous days
        if quote is None:
            business_day = self._find_last_business_day(ref_date)
            if business_day != ref_date:
                logger.debug(
                    "No quote for date, trying previous business day",
                    original_date=ref_date.isoformat(),
                    business_day=business_day.isoformat(),
                )
                quote = self._fetch_quotation_from_api(currency, business_day)

        if quote is not None:
            # Cache the result
            cache_key = self._get_cache_key(currency, ref_date)
            self._cache[cache_key] = quote

            # Track fetch time for current day
            if ref_date >= date.today():
                self._current_day_fetch_time[cache_key] = datetime.now()

        return quote

    def _fetch_quotation_from_api(
        self,
        currency: str,
        ref_date: date
    ) -> Optional[Decimal]:
        """Fetch quotation from BCB API for a specific date.

        Args:
            currency: Currency code
            ref_date: Reference date

        Returns:
            Selling rate or None if not available
        """
        # Build URL for CotacaoMoedaDia endpoint
        formatted_date = self._format_date_for_api(ref_date)
        url = (
            f"{self.BASE_URL}/CotacaoMoedaDia(moeda=@moeda,dataCotacao=@dataCotacao)"
            f"?@moeda='{currency}'&@dataCotacao='{formatted_date}'"
            f"&$format=json&$select=cotacaoVenda,dataHoraCotacao"
        )

        logger.debug(
            "Fetching quotation from BCB API",
            currency=currency,
            date=ref_date.isoformat(),
            url=url,
        )

        try:
            response = httpx.get(url, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            # Response format: {"value": [{"cotacaoVenda": 6.15, "dataHoraCotacao": "..."}]}
            values = data.get("value", [])

            if not values:
                logger.debug(
                    "No quotation found for date",
                    currency=currency,
                    date=ref_date.isoformat(),
                )
                return None

            # Get the last quote of the day (most recent)
            last_quote = values[-1]
            rate = Decimal(str(last_quote["cotacaoVenda"]))

            logger.info(
                "Fetched quotation successfully",
                currency=currency,
                date=ref_date.isoformat(),
                rate=float(rate),
            )

            return rate

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error fetching quotation",
                currency=currency,
                date=ref_date.isoformat(),
                status_code=e.response.status_code,
                error=str(e),
            )
            return None

        except Exception as e:
            logger.error(
                "Failed to fetch quotation from BCB",
                currency=currency,
                date=ref_date.isoformat(),
                error=str(e),
            )
            return None

    def get_quotations_period(
        self,
        currency: str,
        start_date: date,
        end_date: date
    ) -> dict[date, Decimal]:
        """Get quotations for a date range.

        Useful for historical data when calculating evolution charts.

        Args:
            currency: Currency code (USD, EUR)
            start_date: Start date of period
            end_date: End date of period

        Returns:
            Dictionary {date: rate} with available quotations
        """
        if currency not in self.SUPPORTED_CURRENCIES:
            logger.warning(
                "Unsupported currency for period query",
                currency=currency,
            )
            return {}

        # Build URL for CotacaoMoedaPeriodo endpoint
        start_formatted = self._format_date_for_api(start_date)
        end_formatted = self._format_date_for_api(end_date)

        url = (
            f"{self.BASE_URL}/CotacaoMoedaPeriodo(moeda=@moeda,"
            f"dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
            f"?@moeda='{currency}'"
            f"&@dataInicial='{start_formatted}'"
            f"&@dataFinalCotacao='{end_formatted}'"
            f"&$format=json&$select=cotacaoVenda,dataHoraCotacao"
        )

        logger.info(
            "Fetching quotations for period from BCB API",
            currency=currency,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        try:
            response = httpx.get(url, timeout=60.0)
            response.raise_for_status()
            data = response.json()

            values = data.get("value", [])

            if not values:
                logger.warning(
                    "No quotations found for period",
                    currency=currency,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                )
                return {}

            # Group by date and take last quote of each day
            quotes_by_date: dict[date, Decimal] = {}

            for item in values:
                # Parse datetime: "2025-12-09 13:08:14.955"
                dt_str = item["dataHoraCotacao"]
                dt = datetime.fromisoformat(dt_str.replace(" ", "T"))
                quote_date = dt.date()

                rate = Decimal(str(item["cotacaoVenda"]))

                # Keep latest quote for each date
                quotes_by_date[quote_date] = rate

                # Also cache individual quotes
                cache_key = self._get_cache_key(currency, quote_date)
                self._cache[cache_key] = rate

            logger.info(
                "Fetched quotations for period successfully",
                currency=currency,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                num_quotes=len(quotes_by_date),
            )

            return quotes_by_date

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error fetching period quotations",
                currency=currency,
                status_code=e.response.status_code,
                error=str(e),
            )
            return {}

        except Exception as e:
            logger.error(
                "Failed to fetch period quotations from BCB",
                currency=currency,
                error=str(e),
            )
            return {}

    def get_quotation_for_month(
        self,
        currency: str,
        year: int,
        month: int
    ) -> Optional[Decimal]:
        """Get quotation for the last day of a specific month.

        Useful for calculating historical positions at month-end.

        Args:
            currency: Currency code
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Exchange rate for month-end or None
        """
        # Get last day of month
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        return self.get_quotation(currency, last_day)

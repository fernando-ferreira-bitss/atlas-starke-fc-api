"""IPCA service for calculating inflation-adjusted values."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import httpx

from starke.core.logging import get_logger

logger = get_logger(__name__)


class IPCAService:
    """Service for fetching IPCA data and calculating accumulated inflation."""

    BCB_API_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json"

    def __init__(self) -> None:
        """Initialize IPCA service."""
        self._cache: dict[str, Decimal] = {}  # Cache: {YYYY-MM: ipca_value}
        self._all_data_fetched = False

    def fetch_all_ipca_data(self) -> dict[str, Decimal]:
        """Fetch ALL IPCA data from BCB API (no date filters).

        This fetches all historical IPCA data and caches it.
        Should be called once at the beginning of processing.

        Returns:
            Dictionary with {YYYY-MM: ipca_percentage}
        """
        # If already fetched, return cached data
        if self._all_data_fetched and self._cache:
            logger.debug("Using cached IPCA data", num_months=len(self._cache))
            return self._cache

        logger.info("Fetching all IPCA data from BCB")

        try:
            response = httpx.get(self.BCB_API_URL, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            # Parse response: [{"data": "01/01/2020", "valor": "0.28"}, ...]
            for item in data:
                # Parse date DD/MM/YYYY to get YYYY-MM
                dt = datetime.strptime(item["data"], "%d/%m/%Y")
                month_key = dt.strftime("%Y-%m")

                # Convert to Decimal
                ipca_value = Decimal(item["valor"])
                self._cache[month_key] = ipca_value

            self._all_data_fetched = True

            logger.info(
                "Fetched all IPCA data successfully",
                num_months=len(self._cache),
            )

            return self._cache

        except Exception as e:
            logger.error(
                "Failed to fetch IPCA data from BCB",
                error=str(e),
            )
            raise

    def fetch_ipca_data(self, start_date: date, end_date: Optional[date] = None) -> dict[str, Decimal]:
        """Fetch IPCA data for a specific date range.

        This will fetch all data if not already cached, then filter by date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to today)

        Returns:
            Dictionary with {YYYY-MM: ipca_percentage} for the specified range
        """
        if end_date is None:
            end_date = date.today()

        # Fetch all data if not already fetched
        if not self._all_data_fetched:
            self.fetch_all_ipca_data()

        # Filter by date range
        start_key = start_date.strftime("%Y-%m")
        end_key = end_date.strftime("%Y-%m")

        filtered_data = {
            month_key: ipca_value
            for month_key, ipca_value in self._cache.items()
            if start_key <= month_key <= end_key
        }

        logger.debug(
            "Filtered IPCA data by date range",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            num_months=len(filtered_data),
        )

        return filtered_data
            
    def calculate_accumulated_ipca(self, start_date: date, end_date: Optional[date] = None) -> Decimal:
        """Calculate accumulated IPCA between two dates.
        
        Formula: accumulated = [(1 + ipca1/100) * (1 + ipca2/100) * ... - 1] * 100
        
        Args:
            start_date: Start date
            end_date: End date (defaults to today)
            
        Returns:
            Accumulated IPCA percentage
        """
        if end_date is None:
            end_date = date.today()
            
        # Fetch IPCA data
        ipca_data = self.fetch_ipca_data(start_date, end_date)
        
        if not ipca_data:
            logger.warning(
                "No IPCA data available for period",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            return Decimal("0")
        
        # Calculate accumulated IPCA using compound formula
        accumulated = Decimal("1")
        for month_key in sorted(ipca_data.keys()):
            ipca_monthly = ipca_data[month_key]
            accumulated *= (Decimal("1") + ipca_monthly / Decimal("100"))
            
        # Convert back to percentage: (accumulated - 1) * 100
        accumulated_percentage = (accumulated - Decimal("1")) * Decimal("100")
        
        logger.info(
            "Calculated accumulated IPCA",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            accumulated_percentage=float(accumulated_percentage),
        )
        
        return accumulated_percentage
        
    def calculate_ipca_adjusted_value(
        self, 
        original_value: Decimal, 
        start_date: date,
        end_date: Optional[date] = None
    ) -> Decimal:
        """Calculate IPCA-adjusted value.
        
        Args:
            original_value: Original value
            start_date: Reference date of original value
            end_date: Target date (defaults to today)
            
        Returns:
            IPCA-adjusted value
        """
        accumulated_ipca = self.calculate_accumulated_ipca(start_date, end_date)
        
        # adjusted_value = original_value * (1 + accumulated_ipca/100)
        adjusted_value = original_value * (Decimal("1") + accumulated_ipca / Decimal("100"))
        
        logger.debug(
            "Calculated IPCA-adjusted value",
            original_value=float(original_value),
            accumulated_ipca=float(accumulated_ipca),
            adjusted_value=float(adjusted_value),
        )
        
        return adjusted_value

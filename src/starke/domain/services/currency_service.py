"""Currency conversion service using BCB PTAX quotations."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from starke.core.logging import get_logger
from starke.infrastructure.external_apis.bcb_quotation_client import BCBQuotationClient

logger = get_logger(__name__)


class CurrencyService:
    """Service for converting values between currencies using BCB PTAX rates.

    Supports conversions between BRL, USD, and EUR using official
    Banco Central do Brasil quotations.

    Conversion logic:
    - BRL → USD: value / USD quotation
    - BRL → EUR: value / EUR quotation
    - USD → BRL: value * USD quotation
    - EUR → BRL: value * EUR quotation
    - USD → EUR: value * USD quotation / EUR quotation
    - EUR → USD: value * EUR quotation / USD quotation
    """

    # Precision for monetary calculations (2 decimal places)
    PRECISION = Decimal("0.01")

    def __init__(self, quotation_client: Optional[BCBQuotationClient] = None) -> None:
        """Initialize currency service.

        Args:
            quotation_client: BCB quotation client instance (creates new if None)
        """
        self.client = quotation_client or BCBQuotationClient()

    def convert(
        self,
        value: Decimal,
        from_currency: str,
        to_currency: str,
        ref_date: Optional[date] = None,
    ) -> Optional[Decimal]:
        """Convert a value between currencies.

        Args:
            value: Amount to convert
            from_currency: Source currency (BRL, USD, EUR)
            to_currency: Target currency (BRL, USD, EUR)
            ref_date: Reference date for quotation (defaults to today)

        Returns:
            Converted value or None if conversion failed
        """
        # No conversion needed
        if from_currency == to_currency:
            return value

        if ref_date is None:
            ref_date = date.today()

        logger.debug(
            "Converting currency",
            value=float(value),
            from_currency=from_currency,
            to_currency=to_currency,
            ref_date=ref_date.isoformat(),
        )

        # Handle conversions involving BRL
        if from_currency == "BRL":
            return self._convert_from_brl(value, to_currency, ref_date)
        elif to_currency == "BRL":
            return self._convert_to_brl(value, from_currency, ref_date)
        else:
            # Cross-currency conversion (e.g., USD → EUR)
            return self._convert_cross(value, from_currency, to_currency, ref_date)

    def _convert_from_brl(
        self,
        value: Decimal,
        to_currency: str,
        ref_date: date
    ) -> Optional[Decimal]:
        """Convert from BRL to foreign currency.

        Formula: result = value / quotation
        Example: R$ 100 / 5.5 = USD 18.18
        """
        quotation = self.client.get_quotation(to_currency, ref_date)

        if quotation is None or quotation == 0:
            logger.warning(
                "Could not get quotation for conversion from BRL",
                to_currency=to_currency,
                ref_date=ref_date.isoformat(),
            )
            return None

        result = value / quotation
        result = result.quantize(self.PRECISION, rounding=ROUND_HALF_UP)

        logger.debug(
            "Converted from BRL",
            original=float(value),
            to_currency=to_currency,
            quotation=float(quotation),
            result=float(result),
        )

        return result

    def _convert_to_brl(
        self,
        value: Decimal,
        from_currency: str,
        ref_date: date
    ) -> Optional[Decimal]:
        """Convert from foreign currency to BRL.

        Formula: result = value * quotation
        Example: USD 100 * 5.5 = R$ 550.00
        """
        quotation = self.client.get_quotation(from_currency, ref_date)

        if quotation is None:
            logger.warning(
                "Could not get quotation for conversion to BRL",
                from_currency=from_currency,
                ref_date=ref_date.isoformat(),
            )
            return None

        result = value * quotation
        result = result.quantize(self.PRECISION, rounding=ROUND_HALF_UP)

        logger.debug(
            "Converted to BRL",
            original=float(value),
            from_currency=from_currency,
            quotation=float(quotation),
            result=float(result),
        )

        return result

    def _convert_cross(
        self,
        value: Decimal,
        from_currency: str,
        to_currency: str,
        ref_date: date
    ) -> Optional[Decimal]:
        """Convert between two foreign currencies (via BRL).

        Formula: result = value * from_quotation / to_quotation
        Example: USD 100 → EUR: 100 * 5.5 / 6.0 = EUR 91.67
        """
        from_quotation = self.client.get_quotation(from_currency, ref_date)
        to_quotation = self.client.get_quotation(to_currency, ref_date)

        if from_quotation is None or to_quotation is None or to_quotation == 0:
            logger.warning(
                "Could not get quotations for cross conversion",
                from_currency=from_currency,
                to_currency=to_currency,
                ref_date=ref_date.isoformat(),
            )
            return None

        result = value * from_quotation / to_quotation
        result = result.quantize(self.PRECISION, rounding=ROUND_HALF_UP)

        logger.debug(
            "Converted cross currency",
            original=float(value),
            from_currency=from_currency,
            to_currency=to_currency,
            from_quotation=float(from_quotation),
            to_quotation=float(to_quotation),
            result=float(result),
        )

        return result

    def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        ref_date: Optional[date] = None,
    ) -> Optional[Decimal]:
        """Get exchange rate between two currencies.

        Args:
            from_currency: Source currency
            to_currency: Target currency
            ref_date: Reference date (defaults to today)

        Returns:
            Exchange rate (1 unit of from_currency = X units of to_currency)
        """
        if from_currency == to_currency:
            return Decimal("1")

        if ref_date is None:
            ref_date = date.today()

        # Use convert with value=1 to get the rate
        rate = self.convert(Decimal("1"), from_currency, to_currency, ref_date)

        if rate is not None:
            # Return with more precision for rate display
            rate = rate.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        return rate

    def convert_dict_values(
        self,
        data: dict,
        value_fields: list[str],
        from_currency: str,
        to_currency: str,
        ref_date: Optional[date] = None,
    ) -> dict:
        """Convert monetary values in a dictionary.

        Useful for converting response data inline.

        Args:
            data: Dictionary with monetary values
            value_fields: List of field names to convert
            from_currency: Source currency
            to_currency: Target currency
            ref_date: Reference date

        Returns:
            New dictionary with converted values
        """
        if from_currency == to_currency:
            return data

        result = data.copy()

        for field in value_fields:
            if field in result and result[field] is not None:
                original = result[field]
                if isinstance(original, (int, float)):
                    original = Decimal(str(original))
                elif not isinstance(original, Decimal):
                    continue

                converted = self.convert(original, from_currency, to_currency, ref_date)
                if converted is not None:
                    result[field] = float(converted)

        return result

    def convert_list_values(
        self,
        items: list[dict],
        value_fields: list[str],
        currency_field: str,
        target_currency: str,
        ref_date: Optional[date] = None,
        date_field: Optional[str] = None,
    ) -> list[dict]:
        """Convert monetary values in a list of items.

        Each item can have its own source currency and optionally
        its own reference date.

        Args:
            items: List of dictionaries with monetary values
            value_fields: Field names to convert
            currency_field: Field containing source currency
            target_currency: Target currency for all items
            ref_date: Default reference date (used if date_field is None)
            date_field: Field containing item-specific date (for historical data)

        Returns:
            New list with converted values and original values preserved
        """
        result = []

        for item in items:
            new_item = item.copy()
            from_currency = item.get(currency_field, "BRL")

            # Get reference date (item-specific or default)
            item_date = ref_date
            if date_field and date_field in item:
                item_date_val = item[date_field]
                if isinstance(item_date_val, str):
                    try:
                        item_date = date.fromisoformat(item_date_val[:10])
                    except ValueError:
                        pass
                elif isinstance(item_date_val, date):
                    item_date = item_date_val

            # Convert each value field
            for field in value_fields:
                if field in new_item and new_item[field] is not None:
                    original = new_item[field]
                    if isinstance(original, (int, float)):
                        original = Decimal(str(original))
                    elif not isinstance(original, Decimal):
                        continue

                    # Store original value
                    new_item[f"original_{field}"] = float(original)
                    new_item[f"original_{field}_currency"] = from_currency

                    # Convert to target currency
                    converted = self.convert(
                        original, from_currency, target_currency, item_date
                    )
                    if converted is not None:
                        new_item[field] = float(converted)

            result.append(new_item)

        return result

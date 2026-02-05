"""Date and period helpers for cash flow reporting."""

from datetime import date, timedelta
from typing import Literal

PeriodType = Literal["mensal", "trimestral", "anual"]


def normalize_ref_date(ref_date: date) -> date:
    """
    Normalize ref_date to first day of month.

    This ensures consistency across the system, as we always store
    monthly data using the first day of the month as the reference.

    Args:
        ref_date: Any date in the month

    Returns:
        First day of the month (YYYY-MM-01)

    Examples:
        >>> normalize_ref_date(date(2024, 12, 15))
        date(2024, 12, 1)
        >>> normalize_ref_date(date(2024, 12, 1))
        date(2024, 12, 1)
    """
    return ref_date.replace(day=1)


def get_quarter_start_month(month: int) -> int:
    """
    Get the first month of the quarter for a given month.

    Args:
        month: Month number (1-12)

    Returns:
        First month of the quarter (1, 4, 7, or 10)

    Examples:
        >>> get_quarter_start_month(12)  # Q4
        10
        >>> get_quarter_start_month(5)   # Q2
        4
    """
    return ((month - 1) // 3) * 3 + 1


def get_quarter_number(month: int) -> int:
    """
    Get the quarter number for a given month.

    Args:
        month: Month number (1-12)

    Returns:
        Quarter number (1-4)

    Examples:
        >>> get_quarter_number(12)
        4
        >>> get_quarter_number(3)
        1
    """
    return ((month - 1) // 3) + 1


def generate_period_dates(period_type: PeriodType, ref_date: date) -> list[date]:
    """
    Generate list of ref_dates for aggregation based on period type.

    All returned dates are normalized to the first day of the month.

    Args:
        period_type: Type of period ("mensal", "trimestral", "anual")
        ref_date: Reference date (any day in the target period)

    Returns:
        List of ref_dates to query (all as first day of month)

    Examples:
        >>> ref = date(2024, 12, 15)
        >>> generate_period_dates("mensal", ref)
        [date(2024, 12, 1)]

        >>> generate_period_dates("trimestral", ref)  # Q4
        [date(2024, 10, 1), date(2024, 11, 1), date(2024, 12, 1)]

        >>> generate_period_dates("anual", ref)
        [date(2024, 1, 1), date(2024, 2, 1), ..., date(2024, 12, 1)]
    """
    ref_date = normalize_ref_date(ref_date)

    if period_type == "mensal":
        return [ref_date]

    elif period_type == "trimestral":
        # Get quarter start month
        quarter_start = get_quarter_start_month(ref_date.month)
        return [
            ref_date.replace(month=quarter_start, day=1),
            ref_date.replace(month=quarter_start + 1, day=1),
            ref_date.replace(month=quarter_start + 2, day=1),
        ]

    elif period_type == "anual":
        # Return all 12 months of the year
        return [ref_date.replace(month=m, day=1) for m in range(1, 13)]

    else:
        raise ValueError(f"Invalid period_type: {period_type}. Must be 'mensal', 'trimestral', or 'anual'")


def format_period_label(period_type: PeriodType, ref_date: date, lang: str = "pt") -> str:
    """
    Format a period label for display.

    Args:
        period_type: Type of period ("mensal", "trimestral", "anual")
        ref_date: Reference date
        lang: Language for month names ("pt" or "en")

    Returns:
        Formatted period label

    Examples:
        >>> format_period_label("mensal", date(2024, 12, 1))
        'Dez/2024'
        >>> format_period_label("trimestral", date(2024, 12, 1))
        'Q4/2024'
        >>> format_period_label("anual", date(2024, 12, 1))
        '2024'
    """
    ref_date = normalize_ref_date(ref_date)

    if period_type == "mensal":
        if lang == "pt":
            month_names = [
                "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                "Jul", "Ago", "Set", "Out", "Nov", "Dez"
            ]
            return f"{month_names[ref_date.month - 1]}/{ref_date.year}"
        else:
            return ref_date.strftime("%b/%Y")

    elif period_type == "trimestral":
        quarter = get_quarter_number(ref_date.month)
        return f"Q{quarter}/{ref_date.year}"

    elif period_type == "anual":
        return str(ref_date.year)

    else:
        raise ValueError(f"Invalid period_type: {period_type}")


def get_previous_period(period_type: PeriodType, ref_date: date) -> date:
    """
    Get the reference date for the previous period.

    Args:
        period_type: Type of period ("mensal", "trimestral", "anual")
        ref_date: Current reference date

    Returns:
        Reference date for previous period (first day of month)

    Examples:
        >>> get_previous_period("mensal", date(2024, 12, 1))
        date(2024, 11, 1)
        >>> get_previous_period("trimestral", date(2024, 12, 1))  # Q4 -> Q3
        date(2024, 9, 1)
        >>> get_previous_period("anual", date(2024, 12, 1))
        date(2023, 12, 1)
    """
    ref_date = normalize_ref_date(ref_date)

    if period_type == "mensal":
        # Go back one month
        if ref_date.month == 1:
            return date(ref_date.year - 1, 12, 1)
        else:
            return ref_date.replace(month=ref_date.month - 1)

    elif period_type == "trimestral":
        # Go back 3 months
        month = ref_date.month - 3
        year = ref_date.year
        if month < 1:
            month += 12
            year -= 1
        return date(year, month, 1)

    elif period_type == "anual":
        # Go back one year
        return ref_date.replace(year=ref_date.year - 1)

    else:
        raise ValueError(f"Invalid period_type: {period_type}")


def get_last_n_periods(period_type: PeriodType, ref_date: date, n: int = 12) -> list[date]:
    """
    Get the last N periods including the current one.

    Args:
        period_type: Type of period ("mensal", "trimestral", "anual")
        ref_date: Current reference date
        n: Number of periods to retrieve

    Returns:
        List of reference dates (oldest first, newest last)

    Examples:
        >>> get_last_n_periods("mensal", date(2024, 3, 1), n=3)
        [date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1)]

        >>> get_last_n_periods("trimestral", date(2024, 12, 1), n=4)
        [date(2024, 3, 1), date(2024, 6, 1), date(2024, 9, 1), date(2024, 12, 1)]
    """
    ref_date = normalize_ref_date(ref_date)
    periods = [ref_date]

    current = ref_date
    for _ in range(n - 1):
        current = get_previous_period(period_type, current)
        periods.insert(0, current)

    return periods


def get_months_between(start_date: date, end_date: date) -> list[date]:
    """
    Get all months between two dates (inclusive).

    Args:
        start_date: Start date (any day in the month)
        end_date: End date (any day in the month)

    Returns:
        List of reference dates (first day of each month), oldest to newest

    Examples:
        >>> get_months_between(date(2024, 10, 15), date(2024, 12, 20))
        [date(2024, 10, 1), date(2024, 11, 1), date(2024, 12, 1)]

        >>> get_months_between(date(2024, 12, 1), date(2025, 2, 1))
        [date(2024, 12, 1), date(2025, 1, 1), date(2025, 2, 1)]
    """
    start_date = normalize_ref_date(start_date)
    end_date = normalize_ref_date(end_date)

    # Ensure start is before or equal to end
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    months = []
    current = start_date

    while current <= end_date:
        months.append(current)
        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return months

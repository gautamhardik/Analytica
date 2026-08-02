"""
Analytica — Shared Utility Functions
Formatters, calculators, and helpers used across services.
"""


def format_currency(value: float, symbol: str = "R$") -> str:
    """Format a numeric value as Brazilian Real currency string."""
    if abs(value) >= 1_000_000:
        return f"{symbol} {value / 1_000_000:,.2f}M"
    if abs(value) >= 1_000:
        return f"{symbol} {value / 1_000:,.1f}K"
    return f"{symbol} {value:,.2f}"


def format_number(value: int | float) -> str:
    """Format a number with thousand separators."""
    if isinstance(value, float):
        return f"{value:,.2f}"
    return f"{value:,}"


def calc_growth_pct(current: float, previous: float) -> float | None:
    """Calculate percentage growth between two periods."""
    if previous is None or previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 2)


def determine_trend(change_pct: float | None) -> str:
    """Return trend direction string from a percentage change."""
    if change_pct is None:
        return "neutral"
    if change_pct > 0:
        return "up"
    if change_pct < 0:
        return "down"
    return "neutral"


def safe_float(value) -> float:
    """Safely convert a database value to float."""
    if value is None:
        return 0.0
    return float(value)


def safe_int(value) -> int:
    """Safely convert a database value to int."""
    if value is None:
        return 0
    return int(value)

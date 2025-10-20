from __future__ import annotations

from typing import Union

Number = Union[int, float]


def _format_compact(value: float) -> str:
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    if absolute >= 1_000_000:
        scaled = absolute / 1_000_000
        suffix = "M"
    elif absolute >= 1_000:
        scaled = absolute / 1_000
        suffix = "K"
    else:
        scaled = absolute
        suffix = ""
    decimals = 1
    if scaled < 1:
        decimals = 3
        if scaled < 0.1:
            decimals = 4
        if scaled < 0.01:
            decimals = 5
    formatted = f"{scaled:.{decimals}f}"
    return f"{sign}{formatted}{suffix}"


def format_plain(value: Number) -> str:
    """Format a numeric value with a mandatory decimal separator."""

    return _format_compact(float(value))


def format_currency(value: Number, symbol: str = "$") -> str:
    """Format currency with a compact suffix and trailing symbol."""

    return f"{format_plain(value)}{symbol}"


def format_rate(value: Number, symbol: str = "$") -> str:
    """Format a per-second income rate with the currency symbol."""

    return f"{format_currency(value, symbol)}/s"

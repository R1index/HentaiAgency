"""Centralised economy tuning for the idol agency bot."""

from __future__ import annotations

from decimal import Decimal, getcontext
from typing import Any, Optional, Sequence, Tuple

# Experience math can grow extremely large (levels up to 9999) so we bump the
# decimal precision high enough to retain accurate arithmetic even for very high
# level requirements.
getcontext().prec = 11000

# Probability weights for each rarity. Values are percentages that add up to 100.
RARITY_WEIGHTS: Sequence[Tuple[str, int]] = (
    ("N", 50),
    ("R", 25),
    ("SR", 15),
    ("SSR", 8),
    ("UR", 2),
)

# Scouting economy.
GACHA_COST: int = 500
DUP_CASHBACK: float = 0.50

# Progression tuning.
LEVEL_INCOME_GROWTH: float = 0.05
MAX_GIRL_LEVEL: int = 9999
_XP_BASE = Decimal(10)
_XP_DISPLAY_SMALL_CAP = Decimal("1000000")


def xp_to_decimal(value: Any) -> Decimal:
    """Convert persisted XP values into a high precision Decimal."""

    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal(0)
    return Decimal(str(value))


def xp_to_storage(value: Decimal) -> str:
    """Serialise a Decimal XP value for SQLite storage."""

    normalised = value.normalize() if value else Decimal(0)
    if not normalised:
        return "0"
    magnitude = abs(normalised)
    if magnitude.adjusted() > 18:
        return str(normalised)
    text = format(normalised, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def format_xp(value: Decimal) -> str:
    """Render XP values compactly, handling gigantic magnitudes gracefully."""

    if not value:
        return "0"
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    if magnitude < _XP_DISPLAY_SMALL_CAP:
        rendered = format(magnitude.normalize(), "f")
        if "." in rendered:
            rendered = rendered.rstrip("0").rstrip(".")
        if not rendered:
            rendered = "0"
    else:
        rendered = format(magnitude.normalize(), ".4E").replace("E+", "e+").replace("E-", "e-")
    return f"{sign}{rendered}"


def level_xp_required(level: int) -> Optional[Decimal]:
    """Return the XP required to reach the next level, or ``None`` if capped."""

    if level >= MAX_GIRL_LEVEL:
        return None
    if level < 1:
        level = 1
    shift = max(0, level - 1)
    requirement = _XP_BASE * Decimal(1 << shift)
    return requirement

# Live game loop tuning.
FANS_GAIN_PER_POP: float = 0.025
PASSIVE_PER_FAN_PER_SEC: float = 0.00025
STAM_DOWN_SEC_PER_1: float = 12.0
STAM_UP_SEC_PER_1: float = 4.0


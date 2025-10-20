"""Centralised economy tuning for the idol agency bot."""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

# Probability weights for each rarity. Values are percentages that add up to 100.
RARITY_WEIGHTS: Sequence[Tuple[str, int]] = (
    ("N", 50),
    ("R", 25),
    ("SR", 15),
    ("SSR", 8),
    ("UR", 2),
)

# Scouting economy.
GACHA_COST: int = 1250
DUP_CASHBACK: float = 0.45

# Progression tuning.
LEVEL_INCOME_GROWTH: float = 0.05
MAX_GIRL_LEVEL: int = 4


def level_xp_required(level: int) -> Optional[float]:
    """Return the XP required to reach the next level, or ``None`` if capped."""

    if level >= MAX_GIRL_LEVEL:
        return None
    if level < 1:
        level = 1
    base = 10
    return float(base * (2 ** (level - 1)))

# Live game loop tuning.
FANS_GAIN_PER_POP: float = 0.025
PASSIVE_PER_FAN_PER_SEC: float = 0.00025
STAM_DOWN_SEC_PER_1: float = 12.0
STAM_UP_SEC_PER_1: float = 4.0


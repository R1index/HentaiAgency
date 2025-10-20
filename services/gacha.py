import random
from typing import Dict, Any, List, Tuple
from db.database import db
from models.girl_pool import load_pool

RARITY_POOL = [
    ("N",   40),
    ("R",   30),
    ("SR",  20),
    ("SSR",  9),
    ("UR",   1),
]

GACHA_COST = 500
DUP_CASHBACK = 0.5

def rarity_roll() -> str:
    r = random.uniform(0, 100)
    acc = 0
    for code, w in RARITY_POOL:
        acc += w
        if r <= acc:
            return code
    return RARITY_POOL[-1][0]

def pick_by_rarity(pool: List[Dict[str, Any]], rarity: str) -> Dict[str, Any]:
    candidates = [g for g in pool if g["rarity"] == rarity] or pool
    return random.choice(candidates)

def rarity_emoji(r: str) -> str:
    mapping = {"N":"⭐", "R":"⭐⭐", "SR":"⭐⭐⭐", "SSR":"⭐⭐⭐⭐", "UR":"⭐⭐⭐⭐⭐"}
    return mapping.get(r, r)

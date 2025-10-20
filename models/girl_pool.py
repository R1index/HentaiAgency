from typing import List, Dict, Any, Optional
import json

ALLOWED_RARITIES = {"N","R","SR","SSR","UR"}

def validate_entry(e: Dict[str, Any]) -> Optional[str]:
    req = ["name", "rarity", "income", "popularity", "specialty"]
    for k in req:
        if k not in e:
            return f"Missing field '{k}'"
    if e["rarity"] not in ALLOWED_RARITIES:
        return "Invalid rarity"
    try:
        float(e["income"]); float(e["popularity"])
    except Exception:
        return "Income/Popularity must be numbers"
    return None

def load_pool(path: str) -> (List[Dict[str, Any]], Optional[str]):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
        cleaned = []
        for e in data:
            err = validate_entry(e)
            if err:
                return [], f"Invalid entry for name='{e.get('name','?')}': {err}"
            cleaned.append({
                "name": e["name"],
                "rarity": e["rarity"],
                "income": float(e["income"]),
                "popularity": float(e["popularity"]),
                "specialty": e["specialty"],
                "image_url": e.get("image_url"),
            })
        return cleaned, None
    except FileNotFoundError:
        return [], "girls.json not found"
    except Exception as ex:
        return [], f"Error loading JSON: {ex}"

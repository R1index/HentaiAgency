from typing import List, Dict, Any, Optional
import json
from pathlib import Path

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

def _resolve_image(e: Dict[str, Any], base_dir: Path, warnings: List[str]) -> tuple[Optional[str], Optional[str]]:
    raw = e.get("image") or e.get("image_path") or e.get("image_url")
    if raw is None:
        return None, None
    raw_str = str(raw).strip()
    if not raw_str:
        return None, None
    lower = raw_str.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        return raw_str, None
    candidate = Path(raw_str)
    if not candidate.is_absolute():
        candidate = (base_dir / candidate).resolve()
    if not candidate.exists():
        warnings.append(f"Image file not found for '{e.get('name', '?')}': {candidate}")
    return None, str(candidate)


def load_pool(path: str) -> (List[Dict[str, Any]], Optional[str]):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
        base_dir = Path(path).resolve().parent
        cleaned = []
        warnings: List[str] = []
        for e in data:
            err = validate_entry(e)
            if err:
                return [], f"Invalid entry for name='{e.get('name','?')}': {err}"
            image_url, image_path = _resolve_image(e, base_dir, warnings)
            cleaned.append({
                "name": e["name"],
                "rarity": e["rarity"],
                "income": float(e["income"]),
                "popularity": float(e["popularity"]),
                "specialty": e["specialty"],
                "image_url": image_url,
                "image_path": image_path,
            })
        warn_text = None
        if warnings:
            # Preserve order but drop duplicates
            seen = []
            for msg in warnings:
                if msg not in seen:
                    seen.append(msg)
            warn_text = "\n".join(seen)
        return cleaned, warn_text
    except FileNotFoundError:
        return [], "girls.json not found"
    except Exception as ex:
        return [], f"Error loading JSON: {ex}"

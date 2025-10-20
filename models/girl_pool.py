from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path

ALLOWED_RARITIES = {"N", "R", "SR", "SSR", "UR"}


def validate_entry(e: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    name = str(e.get("name", "")).strip()
    if not name:
        errors.append("Missing field 'name'")
    else:
        e["name"] = name

    rarity_raw = str(e.get("rarity", "")).strip().upper()
    if not rarity_raw:
        errors.append("Missing field 'rarity'")
    elif rarity_raw not in ALLOWED_RARITIES:
        errors.append(f"Invalid rarity '{rarity_raw}'")
    else:
        e["rarity"] = rarity_raw

    for field in ("income", "popularity"):
        raw_value = e.get(field)
        try:
            number = float(raw_value)
        except (TypeError, ValueError):
            errors.append(f"{field.title()} must be a number")
            continue
        if number < 0:
            errors.append(f"{field.title()} must be non-negative")
        else:
            e[field] = number

    specialty = str(e.get("specialty", "")).strip()
    if not specialty:
        e["specialty"] = "-"
    else:
        e["specialty"] = specialty

    return errors

def _resolve_image(
    e: Dict[str, Any], base_dir: Path, warnings: List[str]
) -> tuple[Optional[str], Optional[str]]:
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
    env_root = os.getenv("GIRLS_IMAGE_ROOT")
    search_roots: List[Path] = []
    if env_root:
        search_roots.append(Path(env_root).expanduser())
    default_folder = (base_dir / "girls_images").resolve()
    if default_folder not in search_roots:
        search_roots.append(default_folder)
    if base_dir not in search_roots:
        search_roots.append(base_dir)

    resolved: Optional[Path] = None
    if candidate.is_absolute():
        resolved = candidate
        if not resolved.exists():
            warnings.append(
                f"Image file not found for '{e.get('name', '?')}': {resolved}"
            )
        return None, str(resolved)

    for root in search_roots:
        attempt = (root / candidate).resolve()
        if attempt.exists():
            resolved = attempt
            break

    if resolved is None:
        # Prefer the first search root as the intended destination
        target_root = search_roots[0] if search_roots else base_dir
        resolved = (target_root / candidate).resolve()
        warnings.append(
            f"Image file not found for '{e.get('name', '?')}': {resolved}"
        )

    return None, str(resolved)


def load_pool(path: str) -> (List[Dict[str, Any]], Optional[str]):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
        base_dir = Path(path).resolve().parent
        cleaned = []
        warnings: List[str] = []
        for idx, entry in enumerate(data):
            entry_dict = dict(entry)
            problems = validate_entry(entry_dict)
            if problems:
                label = entry_dict.get("name") or f"entry #{idx + 1}"
                warnings.append(
                    f"Skipped '{label}': " + "; ".join(problems)
                )
                continue
            image_url, image_path = _resolve_image(entry_dict, base_dir, warnings)
            cleaned.append({
                "name": entry_dict["name"],
                "rarity": entry_dict["rarity"],
                "income": float(entry_dict["income"]),
                "popularity": float(entry_dict["popularity"]),
                "specialty": entry_dict.get("specialty", "-"),
                "image_url": image_url,
                "image_path": image_path,
            })
        warn_text = None
        if warnings:
            # Preserve order but drop duplicates
            seen: List[str] = []
            for msg in warnings:
                if msg not in seen:
                    seen.append(msg)
            warn_text = "\n".join(seen)
        return cleaned, warn_text
    except FileNotFoundError:
        return [], "girls.json not found"
    except Exception as ex:
        return [], f"Error loading JSON: {ex}"

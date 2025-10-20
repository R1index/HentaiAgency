from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from services.image_paths import allowed_roots, is_within_allowed

ALLOWED_RARITIES: Sequence[str] = ("N", "R", "SR", "SSR", "UR")


def _coerce_float(value: Any, default: float, warnings: List[str], context: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        warnings.append(f"{context} is invalid; defaulting to {default}")
        return default


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
    candidate = Path(raw_str).expanduser()
    base_dir_resolved = base_dir.resolve()
    search_roots: List[Path] = allowed_roots(
        base_dir_resolved / "girls_images", base_dir_resolved
    )

    if candidate.is_absolute():
        resolved = candidate.resolve()
        if not is_within_allowed(resolved, search_roots):
            warnings.append(
                f"Image path for '{e.get('name', '?')}' outside allowed directories: {resolved}"
            )
            return None, None
        if not resolved.exists():
            warnings.append(
                f"Image file not found for '{e.get('name', '?')}': {resolved}"
            )
            return None, None
        return None, str(resolved)

    for root in search_roots:
        attempt = (root / candidate).resolve()
        if not is_within_allowed(attempt, search_roots):
            continue
        if attempt.exists():
            return None, str(attempt)

    target_root = search_roots[0] if search_roots else base_dir_resolved
    fallback = (target_root / candidate).resolve()
    warnings.append(
        f"Image file not found for '{e.get('name', '?')}': {fallback}"
    )
    return None, None


def _normalise_entry(
    raw: Any, base_dir: Path, warnings: List[str], index: int
) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        warnings.append(f"Skipping entry #{index + 1}: expected object, got {type(raw).__name__}")
        return None

    name = str(raw.get("name", "")).strip()
    if not name:
        warnings.append(f"Skipping entry #{index + 1}: missing name")
        return None

    rarity = str(raw.get("rarity", "N")).strip().upper()
    if rarity not in ALLOWED_RARITIES:
        warnings.append(f"{name}: invalid rarity '{raw.get('rarity')}', defaulting to 'N'")
        rarity = "N"

    income = _coerce_float(raw.get("income"), 5.0, warnings, f"{name}: income")
    popularity = _coerce_float(raw.get("popularity"), 100.0, warnings, f"{name}: popularity")
    specialty = str(raw.get("specialty") or "-").strip() or "-"
    image_url, image_path = _resolve_image(raw, base_dir, warnings)

    return {
        "name": name,
        "rarity": rarity,
        "income": income,
        "popularity": popularity,
        "specialty": specialty,
        "image_url": image_url,
        "image_path": image_path,
    }


def _dedupe(entries: Sequence[Dict[str, Any]], warnings: List[str]) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for entry in entries:
        name = entry["name"]
        if name in seen:
            warnings.append(f"Duplicate entry for '{name}' encountered; using the last value")
        else:
            order.append(name)
        seen[name] = entry
    return [seen[name] for name in order]


def load_pool(path: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return [], "girls.json not found"
    except Exception as ex:  # pragma: no cover - defensive guard
        return [], f"Error loading JSON: {ex}"

    if not isinstance(data, list):
        return [], "girls.json root must be a list of entries"

    base_dir = Path(path).resolve().parent
    warnings: List[str] = []
    normalised: List[Dict[str, Any]] = []
    for idx, raw in enumerate(data):
        entry = _normalise_entry(raw, base_dir, warnings, idx)
        if entry:
            normalised.append(entry)

    cleaned = _dedupe(normalised, warnings)

    warn_text = None
    if warnings:
        seen_messages: List[str] = []
        for msg in warnings:
            if msg not in seen_messages:
                seen_messages.append(msg)
        warn_text = "\n".join(seen_messages)

    return cleaned, warn_text


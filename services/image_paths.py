"""Utilities for validating local image paths.

These helpers centralise the logic for resolving roster image references while
ensuring the bot only ever touches files inside the configured asset
directories.  Keeping the validation rules in one place makes it harder to
accidentally reintroduce path traversal vulnerabilities in the different
consumers (pool loader, roster UI, gacha flow).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Sequence


def _normalise_roots(roots: Iterable[Path]) -> List[Path]:
    """Return a deduplicated list of absolute, normalised directories."""

    normalised: List[Path] = []
    for root in roots:
        resolved = Path(root).expanduser().resolve()
        if resolved not in normalised:
            normalised.append(resolved)
    return normalised


def allowed_roots(*extra_roots: Path) -> List[Path]:
    """Collect the directories that may legitimately contain girl images."""

    roots: List[Path] = []
    env_root = os.getenv("GIRLS_IMAGE_ROOT")
    if env_root:
        roots.append(Path(env_root))

    roots.append(Path("data/girls_images"))
    roots.append(Path("data"))

    for root in extra_roots:
        roots.append(root)

    return _normalise_roots(roots)


def is_within_allowed(path: Path, roots: Sequence[Path]) -> bool:
    """Return ``True`` when ``path`` lives inside one of ``roots``."""

    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False

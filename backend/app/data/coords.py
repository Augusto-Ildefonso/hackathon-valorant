"""Game coordinates -> minimap coordinates (0..1). Owner: Stream A.

Catalog transform (axes are swapped): `u = y * xMultiplier + xScalarToAdd`, `v = x * yMultiplier + yScalarToAdd`,
where `u` is the horizontal and `v` the vertical position on the minimap image (0..1, y down).
Out-of-bounds points (players outside the playable area, e.g. x < -10000) and maps without a transform
(Abyss, Summit) return `None` / NaN.
"""
from __future__ import annotations

import numpy as np

from .catalog import get_catalog

MARGIN = 0.02  # tolerance around 0..1 before a point counts as outside the map
X_OUTLIER = -10_000  # raw game x below this is never on the map


def to_minimap(map_name: str, x: float, y: float) -> tuple[float, float] | None:
    t = get_catalog().transform(map_name)
    if t is None or x is None or y is None or x < X_OUTLIER:
        return None
    u, v = y * t.x_mult + t.x_add, x * t.y_mult + t.y_add
    if not (-MARGIN <= u <= 1 + MARGIN and -MARGIN <= v <= 1 + MARGIN):
        return None
    return float(min(max(u, 0.0), 1.0)), float(min(max(v, 0.0), 1.0))


def to_minimap_arrays(map_name: str, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Vectorized version; invalid points become NaN in both outputs."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    t = get_catalog().transform(map_name)
    if t is None:
        return np.full_like(x, np.nan), np.full_like(y, np.nan)
    u, v = y * t.x_mult + t.x_add, x * t.y_mult + t.y_add
    bad = ~((u >= -MARGIN) & (u <= 1 + MARGIN) & (v >= -MARGIN) & (v <= 1 + MARGIN)) | (x < X_OUTLIER)
    u, v = np.clip(u, 0, 1), np.clip(v, 0, 1)
    u[bad], v[bad] = np.nan, np.nan
    return u, v

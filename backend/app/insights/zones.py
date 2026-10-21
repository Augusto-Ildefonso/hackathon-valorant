"""Blind-spot blobs from the heatmap layers (python port of the frontend `findZones`). Owner: Stream D."""
from __future__ import annotations

from dataclasses import dataclass

from ..schemas.map import HeatLayer
from . import thresholds as T


@dataclass(frozen=True)
class Zone:
    x0: float
    y0: float
    x1: float
    y1: float
    weight: float

    @property
    def center(self) -> tuple[float, float]:
        return (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2

    def contains(self, u: float, v: float) -> bool:
        return self.x0 <= u <= self.x1 and self.y0 <= v <= self.y1


def find_zones(layer: HeatLayer, threshold: float = T.ZONE_THRESHOLD, min_cells: int = T.ZONE_MIN_CELLS, top: int = 3) -> list[Zone]:
    """Connected blobs of cells above `threshold`, as bounding boxes in 0..1 (x right, y down), strongest first."""
    g, n = layer.grid, len(layer.grid)
    seen = [[False] * n for _ in range(n)]
    zones: list[Zone] = []
    for r in range(n):
        for c in range(n):
            if seen[r][c] or g[r][c] < threshold:
                continue
            stack, seen[r][c] = [(r, c)], True
            cells, weight, r0, r1, c0, c1 = 0, 0.0, r, r, c, c
            while stack:
                y, x = stack.pop()
                cells += 1
                weight += g[y][x]
                r0, r1, c0, c1 = min(r0, y), max(r1, y), min(c0, x), max(c1, x)
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < n and 0 <= nx < n and not seen[ny][nx] and g[ny][nx] >= threshold:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            if cells >= min_cells:
                zones.append(Zone(c0 / n, r0 / n, (c1 + 1) / n, (r1 + 1) / n, weight))
    return sorted(zones, key=lambda z: -z.weight)[:top]

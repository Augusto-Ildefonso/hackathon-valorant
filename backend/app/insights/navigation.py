"""Walkable-floor routing on the minimap (Stream D): drawn routes follow corridors instead of crossing walls.

The catalog minimap is a clean floor plan: opaque pixels are walkable floor, transparent ones are walls or outside. We
turn it into a coarse grid (`N` x `N`), measure each cell's clearance from the nearest wall, and route between waypoints
with A* (cost grows near walls, so paths run through the middle of corridors). Waypoints that fall inside a wall (a
centroid of two corridors) are snapped to the nearest floor first. The result is simplified by line of sight, so every
straight segment that is drawn stays on floor. Maps without a minimap (Abyss, Summit) or unreachable pairs return the
input untouched. Only the supplied catalog image is used.
"""
from __future__ import annotations

import heapq
from functools import lru_cache

import numpy as np
from PIL import Image

from ..data.catalog import get_catalog
from ..deps import CATALOG_DIR

N = 256                # grid resolution (cell = 4 px of the 1024 px minimap)
MAX_CLEAR = 4          # clearance is measured up to this many cells
WALL_COST = 3.0        # extra cost multiplier right next to a wall
SNAP_RADIUS = 24       # cells searched to move a waypoint out of a wall

Pt = tuple[float, float]
_STEPS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


class Grid:
    def __init__(self, floor: np.ndarray):
        self.floor = floor
        self.clear = self._clearance(floor)

    @staticmethod
    def _clearance(floor: np.ndarray) -> np.ndarray:
        """Steps (4-neighbour) to the nearest wall cell, capped at MAX_CLEAR; 0 on walls."""
        clear = np.zeros(floor.shape, dtype=np.int8)
        cur = floor.copy()
        for k in range(1, MAX_CLEAR + 1):
            clear[cur] = k
            nxt = cur.copy()
            nxt[1:, :] &= cur[:-1, :]
            nxt[:-1, :] &= cur[1:, :]
            nxt[:, 1:] &= cur[:, :-1]
            nxt[:, :-1] &= cur[:, 1:]
            nxt[0, :] = nxt[-1, :] = False
            nxt[:, 0] = nxt[:, -1] = False
            cur = nxt
        return clear

    def cell(self, p: Pt) -> tuple[int, int]:
        return min(max(int(p[1] * N), 0), N - 1), min(max(int(p[0] * N), 0), N - 1)  # (row, col)

    def snap(self, p: Pt) -> tuple[int, int] | None:
        r, c = self.cell(p)
        if self.clear[r, c] >= 2:
            return r, c
        best, best_d = None, 1e9
        for dr in range(-SNAP_RADIUS, SNAP_RADIUS + 1):
            for dc in range(-SNAP_RADIUS, SNAP_RADIUS + 1):
                rr, cc = r + dr, c + dc
                if 0 <= rr < N and 0 <= cc < N and self.clear[rr, cc] >= 2:
                    d = dr * dr + dc * dc
                    if d < best_d:
                        best, best_d = (rr, cc), d
        return best

    def astar(self, a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]] | None:
        if a == b:
            return [a]
        clear = self.clear
        g = {a: 0.0}
        prev: dict[tuple[int, int], tuple[int, int]] = {}
        heap = [(0.0, a)]
        done: set[tuple[int, int]] = set()
        while heap:
            _, cur = heapq.heappop(heap)
            if cur in done:
                continue
            if cur == b:
                path = [cur]
                while cur in prev:
                    cur = prev[cur]
                    path.append(cur)
                return path[::-1]
            done.add(cur)
            for dr, dc in _STEPS:
                nr, nc = cur[0] + dr, cur[1] + dc
                if not (0 <= nr < N and 0 <= nc < N) or clear[nr, nc] < 1:
                    continue
                if dr and dc and (clear[cur[0] + dr, cur[1]] < 1 or clear[cur[0], cur[1] + dc] < 1):
                    continue  # no cutting wall corners
                step = 1.4142 if dr and dc else 1.0
                near = max(0, MAX_CLEAR - int(clear[nr, nc])) / MAX_CLEAR  # 0 in open floor, up to 0.75 by a wall
                cost = g[cur] + step * (1 + WALL_COST * near)
                if cost < g.get((nr, nc), 1e18):
                    g[(nr, nc)] = cost
                    prev[(nr, nc)] = cur
                    h = max(abs(nr - b[0]), abs(nc - b[1])) + 0.4142 * min(abs(nr - b[0]), abs(nc - b[1]))
                    heapq.heappush(heap, (cost + h, (nr, nc)))
        return None

    def visible(self, a: tuple[int, int], b: tuple[int, int]) -> bool:
        """A straight segment between two cells stays on floor (clearance >= 1 at every sample)."""
        n = max(abs(a[0] - b[0]), abs(a[1] - b[1])) * 2 or 1
        for i in range(n + 1):
            t = i / n
            r, c = round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t)
            if self.clear[r, c] < 1:
                return False
        return True


@lru_cache(maxsize=None)
def grid(map_name: str) -> Grid | None:
    t = get_catalog().transform(map_name)
    if t is None:
        return None
    path = CATALOG_DIR / "Maps" / f"{t.id}.png"
    try:
        alpha = np.asarray(Image.open(path).convert("RGBA"))[:, :, 3] > 128
    except OSError:
        return None
    k = alpha.shape[0] // N
    floor = alpha[: N * k, : N * k].reshape(N, k, N, k).mean(axis=(1, 3)) >= 0.5
    return Grid(floor)


def _to_pt(cell: tuple[int, int]) -> Pt:
    return (cell[1] + 0.5) / N, (cell[0] + 0.5) / N


def route(map_name: str, points: list[Pt]) -> list[Pt]:
    """Waypoints through `points` that follow walkable floor. Falls back to `points` when it cannot."""
    g = grid(map_name)
    if g is None or len(points) < 2:
        return points
    cells = [g.snap(p) for p in points]
    if any(c is None for c in cells):
        return points
    path: list[tuple[int, int]] = []
    for a, b in zip(cells, cells[1:]):
        seg = g.astar(a, b)
        if seg is None:
            return points
        path += seg if not path else seg[1:]
    # line-of-sight simplification: keep the furthest visible cell each time
    keep = [path[0]]
    i = 0
    while i < len(path) - 1:
        j = len(path) - 1
        while j > i + 1 and not g.visible(path[i], path[j]):
            j -= 1
        keep.append(path[j])
        i = j
    out = [_to_pt(c) for c in keep]
    # keep the exact end points when they were already on floor (the plant point, a hold)
    for idx, p in ((0, points[0]), (-1, points[-1])):
        r, c = g.cell(p)
        if g.clear[r, c] >= 1:
            out[idx] = (min(max(p[0], 0.0), 1.0), min(max(p[1], 0.0), 1.0))
    return out


def snap_point(map_name: str, p: Pt) -> Pt:
    """Move a marker that falls inside a wall to the nearest floor (unchanged when already on floor)."""
    g = grid(map_name)
    if g is None:
        return p
    r, c = g.cell(p)
    if g.clear[r, c] >= 1:
        return p
    cell = g.snap(p)
    return _to_pt(cell) if cell else p

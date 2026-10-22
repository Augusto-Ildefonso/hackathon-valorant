"""Walkable-floor routing (Stream D): drawn routes must not cross walls."""
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.data.catalog import get_catalog
from app.deps import CATALOG_DIR
from app.insights import navigation as nav
from app.main import app

client = TestClient(app)


def _floor_image(map_name: str) -> np.ndarray:
    t = get_catalog().transform(map_name)
    return np.asarray(Image.open(CATALOG_DIR / "Maps" / f"{t.id}.png").convert("RGBA"))[:, :, 3] > 128


def _segment_on_floor(floor: np.ndarray, a, b, tolerance_px: int = 6) -> bool:
    """Every sample of the segment is floor, or within `tolerance_px` of floor (outline pixels, grid rounding)."""
    size = floor.shape[0]
    n = int(np.hypot(b[0] - a[0], b[1] - a[1]) * size) * 2 + 1
    for i in range(n + 1):
        x, y = a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n
        c, r = min(int(x * size), size - 1), min(int(y * size), size - 1)
        window = floor[max(r - tolerance_px, 0): r + tolerance_px + 1, max(c - tolerance_px, 0): c + tolerance_px + 1]
        if not window.any():
            return False
    return True


def test_clearance_and_astar_on_a_synthetic_grid():
    floor = np.zeros((nav.N, nav.N), dtype=bool)
    floor[100:140, 20:236] = True   # a long corridor
    floor[100:236, 20:60] = True    # turning south at the west end
    g = nav.Grid(floor)
    a, b = g.snap((0.9, 0.5)), g.snap((0.15, 0.85))
    path = g.astar(a, b)
    assert path and all(floor[r, c] for r, c in path)
    # a straight line between the ends would cut through the wall block; the path has to turn
    assert not g.visible(a, b)


def test_waypoint_inside_a_wall_is_snapped_to_floor():
    floor = np.zeros((nav.N, nav.N), dtype=bool)
    floor[50:200, 50:200] = True
    g = nav.Grid(floor)
    cell = g.snap((0.15, 0.15))  # inside the wall margin, a few cells from floor
    assert cell is not None and floor[cell] and g.clear[cell] >= 2
    assert g.snap((0.02, 0.02)) is None  # too far from any floor: left alone by the callers


def test_maps_without_a_minimap_are_returned_untouched():
    pts = [(0.2, 0.2), (0.8, 0.8)]
    assert nav.route("Abyss", pts) == pts and nav.snap_point("Abyss", (0.5, 0.5)) == (0.5, 0.5)


@pytest.mark.parametrize("map_name", ["Ascent", "Haven", "Lotus", "Split"])
def test_real_plans_do_not_cross_walls(full_store, map_name):
    teams = full_store.matches[full_store.matches.map_name == map_name]
    counts = (teams.team_a.value_counts().add(teams.team_b.value_counts(), fill_value=0)).sort_values(ascending=False)
    a, b = counts.index[0], counts.index[1]
    r = client.post("/api/plan", json={"team_a": a, "team_b": b, "map": map_name, "perspective": "a"})
    assert r.status_code == 200
    floor = _floor_image(map_name)
    checked = 0
    for rnd in r.json()["rounds"]:
        for rt in (rnd.get("map_plan") or {}).get("routes", []):
            pts = [(p["x"], p["y"]) for p in rt["points"]]
            for p, q in zip(pts, pts[1:]):
                assert _segment_on_floor(floor, p, q), f"{map_name} R{rnd['number']} {rt['label']}: {p} -> {q} crosses a wall"
                checked += 1
    assert checked > 0

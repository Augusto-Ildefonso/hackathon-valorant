"""Images for the printable plan (Stream D): the document names an image slot ("enemy:B", "agents", "buy:5"), this module
fills it from the supplied catalog and the plan's own data. Nothing here invents data: icons come from `public_catalog/`,
the minimap is the catalog floor plan, the route is the plan's enemy route.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from ..data.catalog import get_catalog
from ..data.coords import to_minimap
from ..data.store import Store
from ..deps import CATALOG_DIR
from ..schemas.plan import PlanResponse

_THUMB = re.compile(r"/api/thumb/(Characters|Weapons|Maps)/([A-Za-z0-9_\-]+)")
MAP_BG = (27, 31, 42)        # dark card behind the transparent floor plan and icons
ROUTE = (255, 181, 71)       # amber, like the app's enemy route
SITE = (255, 59, 82)         # accent red for site markers
SIZE = 720


def catalog_file(url: str | None) -> Path | None:
    """File behind a `/api/thumb/<folder>/<stem>?w=..` url of the catalog."""
    m = _THUMB.search(url or "")
    if not m:
        return None
    p = CATALOG_DIR / m.group(1) / f"{m.group(2)}.png"
    return p if p.exists() else None


@dataclass
class Strip:
    """A row of small icons with a label under each (agents, a round's weapons)."""

    items: list[tuple[Path, str]]


@dataclass
class Picture:
    data: bytes  # PNG
    width: int
    height: int


def plant_points(full: Store, map_name: str) -> dict[str, tuple[float, float]]:
    r = full.rounds.merge(full.matches[["match_id", "map_name"]], on="match_id")
    r = r[(r.map_name == map_name) & r.planter.notna()]
    out = {}
    for site, g in r.groupby("plant_site"):
        p = to_minimap(map_name, float(g.plant_x.mean()), float(g.plant_y.mean()))
        if p is not None:
            out[str(site)] = p
    return out


def _floor_plan(map_name: str) -> Image.Image | None:
    t = get_catalog().transform(map_name)
    if t is None:
        return None
    path = CATALOG_DIR / "Maps" / f"{t.id}.png"
    if not path.exists():
        return None
    fg = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", fg.size, MAP_BG + (255,))
    bg.alpha_composite(fg)
    return bg.convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)


def _png(im: Image.Image) -> Picture:
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return Picture(buf.getvalue(), im.width, im.height)


def _site_marker(d: ImageDraw.ImageDraw, p: tuple[float, float], label: str) -> None:
    x, y, r = p[0] * SIZE, p[1] * SIZE, 20
    d.rounded_rectangle((x - r, y - r, x + r, y + r), radius=6, fill=SITE)
    d.text((x - 5, y - 7), label, fill=(255, 255, 255))


def overview(map_name: str, plants: dict[str, tuple[float, float]]) -> Picture | None:
    im = _floor_plan(map_name)
    if im is None:
        return None
    d = ImageDraw.Draw(im)
    for site, p in plants.items():
        _site_marker(d, p, site)
    return _png(im)


def enemy_route(map_name: str, route: list[tuple[float, float]], plants: dict[str, tuple[float, float]]) -> Picture | None:
    im = _floor_plan(map_name)
    if im is None or len(route) < 2:
        return None
    d = ImageDraw.Draw(im)
    pts = [(x * SIZE, y * SIZE) for x, y in route]
    d.line(pts, fill=ROUTE, width=7, joint="curve")
    for x, y in pts[:-1]:
        d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=ROUTE)
    (x0, y0), (x1, y1) = pts[-2], pts[-1]  # arrow head on the last segment
    import math

    ang = math.atan2(y1 - y0, x1 - x0)
    tip = (x1, y1)
    left = (x1 - 22 * math.cos(ang - 0.45), y1 - 22 * math.sin(ang - 0.45))
    right = (x1 - 22 * math.cos(ang + 0.45), y1 - 22 * math.sin(ang + 0.45))
    d.polygon([tip, left, right], fill=ROUTE)
    for site, p in plants.items():
        _site_marker(d, p, site)
    return _png(im)


class ImageBank:
    """Which image slots exist for a plan and how to fill them."""

    def __init__(self, plan: PlanResponse, full: Store | None):
        self.plan = plan
        self.plants = plant_points(full, plan.map.name) if full is not None and plan.map.has_minimap else {}
        self.refs: dict[str, str] = {}  # slot -> what it shows (given to the LLM)
        self._routes: dict[str, list[tuple[float, float]]] = {}
        self._build()

    def _build(self) -> None:
        p = self.plan
        if p.map.has_minimap:
            if self.plants:
                self.refs["map:overview"] = f"minimapa de {p.map.name} com os sites marcados"
            best: dict[str, tuple[int, list[tuple[float, float]]]] = {}
            for r in p.rounds:
                mv = r.enemy_probable_strategy
                if mv.site and len(mv.route) >= 2 and mv.evidence.sample_size > best.get(mv.site, (0, []))[0]:
                    best[mv.site] = (mv.evidence.sample_size, [(q.x, q.y) for q in mv.route])
            for site, (_, route) in best.items():
                self._routes[site] = route
                self.refs[f"enemy:{site}"] = f"minimapa com o caminho provável do adversário rumo ao site {site}"
        if any(catalog_file(a.agent.icon_url) for a in p.agents):
            self.refs["agents"] = "retratos dos agentes recomendados"
        for a in p.agents:
            if a.agent.name and catalog_file(a.agent.icon_url):
                self.refs[f"agent:{a.agent.name}"] = f"retrato do agente {a.agent.name}"
        for r in p.rounds:
            if any(b.weapon and catalog_file(b.weapon.icon_url) for b in r.buy):
                self.refs[f"buy:{r.number}"] = f"armas da compra do round {r.number}"

    def resolve(self, ref: str) -> Picture | Strip | None:
        p = self.plan
        if ref not in self.refs:
            return None
        if ref == "map:overview":
            return overview(p.map.name, self.plants)
        if ref.startswith("enemy:"):
            return enemy_route(p.map.name, self._routes[ref.split(":", 1)[1]], self.plants)
        if ref == "agents":
            return Strip([(f, a.agent.name or "Agente desconhecido") for a in p.agents if (f := catalog_file(a.agent.icon_url))])
        if ref.startswith("agent:"):
            name = ref.split(":", 1)[1]
            return Strip([(f, name) for a in p.agents if a.agent.name == name and (f := catalog_file(a.agent.icon_url))][:1])
        if ref.startswith("buy:"):
            n = int(ref.split(":", 1)[1])
            r = next(x for x in p.rounds if x.number == n)
            counts: dict[str, list] = {}
            for b in r.buy:
                if b.weapon and (f := catalog_file(b.weapon.icon_url)):
                    c = counts.setdefault(b.weapon.id, [f, b.weapon.name or "Arma desconhecida", 0])
                    c[2] += 1
            return Strip([(f, f"{name} x{k}" if k > 1 else name) for f, name, k in counts.values()])
        return None

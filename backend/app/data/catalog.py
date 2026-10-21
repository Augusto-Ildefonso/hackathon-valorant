"""Public catalog lookups (agents, weapons, maps) with an explicit "unknown" fallback. Owner: Stream A.

The catalog is older than the matches: some agent/weapon IDs and every armor ID have no name. Those resolve to
`name=None` (the UI shows "Agente/Arma desconhecido(a)"); we never invent a name. IDs in match data are lower-case,
catalog IDs and image file names are upper-case: lookups normalize, URLs keep the file-name case.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import orjson

from ..deps import CATALOG_DIR
from ..schemas.common import AgentRef, MapRef, WeaponRef

# matchInfo.mapId codename -> public name (1:1 across all files; also in CLAUDE.md)
MAP_NAMES = {"Ascent": "Ascent", "Jam": "Lotus", "Triad": "Haven", "Bonsai": "Split", "Juliett": "Sunset",
             "Infinity": "Abyss", "Plummet": "Summit", "Foxtrot": "Breeze", "Pitt": "Pearl", "Canyon": "Fracture"}
CODENAMES = {v: k for k, v in MAP_NAMES.items()}


@dataclass(frozen=True)
class MapTransform:
    id: str
    x_mult: float
    x_add: float
    y_mult: float
    y_add: float

    @property
    def usable(self) -> bool:
        return not (self.x_mult == 0 and self.y_mult == 0)


class Catalog:
    def __init__(self, raw: dict):
        name = lambda item: item["name"].get("en-US") or next(iter(item["name"].values()))  # noqa: E731
        self._agents = {c["id"].lower(): (c["id"], name(c)) for c in raw["characters"]}
        self._weapons = {w["id"].lower(): (w["id"], name(w)) for w in raw["weapons"]}
        self._maps = {
            name(m): MapTransform(m["id"], m["xMultiplier"], m["xScalarToAdd"], m["yMultiplier"], m["yScalarToAdd"])
            for m in raw["maps"]
        }

    # ---- refs for API payloads ----
    def agent(self, agent_id: str | None) -> AgentRef | None:
        if not agent_id:
            return None
        hit = self._agents.get(agent_id.lower())
        if not hit:
            return AgentRef(id=agent_id, name=None, name_inferred=False, icon_url=None)
        cid, nm = hit
        return AgentRef(id=agent_id, name=nm, icon_url=f"/api/thumb/Characters/{cid}?w=96")

    def weapon(self, weapon_id: str | None) -> WeaponRef | None:
        if not weapon_id:
            return None
        hit = self._weapons.get(weapon_id.lower())
        if not hit:
            return WeaponRef(id=weapon_id, name=None, name_inferred=False, icon_url=None)
        wid, nm = hit
        return WeaponRef(id=weapon_id, name=nm, icon_url=f"/api/thumb/Weapons/{wid}?w=160")

    def map_ref(self, public_name: str) -> MapRef:
        t = self._maps.get(public_name)
        has = bool(t and t.usable)
        return MapRef(codename=CODENAMES.get(public_name, public_name), name=public_name, has_minimap=has,
                      minimap_url=f"/assets/Maps/{t.id}.png" if has else None,
                      thumb_url=f"/api/thumb/Maps/{t.id}_listview?w=120" if has else None)

    def transform(self, public_name: str) -> MapTransform | None:
        t = self._maps.get(public_name)
        return t if t and t.usable else None

    def agent_name(self, agent_id: str | None) -> str | None:
        hit = self._agents.get((agent_id or "").lower())
        return hit[1] if hit else None

    def weapon_name(self, weapon_id: str | None) -> str | None:
        hit = self._weapons.get((weapon_id or "").lower())
        return hit[1] if hit else None


@lru_cache
def get_catalog() -> Catalog:
    return Catalog(orjson.loads((CATALOG_DIR / "PublicContentCatalog.json").read_bytes()))

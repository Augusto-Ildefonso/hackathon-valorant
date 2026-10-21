"""Static game metadata used by the Action Plan: the in-game class of each agent and the armor-id convention.

Both are public game facts, not match data. They are NOT in the catalog (which only has names), so they live here and
are documented in `.claude/plans/mvp-plan.md`. Unknown agents get no role label (never guessed).
"""
from __future__ import annotations

AGENT_CLASS = {
    "jett": "duelist", "reyna": "duelist", "raze": "duelist", "phoenix": "duelist", "yoru": "duelist", "neon": "duelist",
    "iso": "duelist", "waylay": "duelist",
    "sova": "iniciador", "breach": "iniciador", "skye": "iniciador", "kay/o": "iniciador", "fade": "iniciador",
    "gekko": "iniciador", "tejo": "iniciador",
    "brimstone": "controlador", "omen": "controlador", "viper": "controlador", "astra": "controlador",
    "harbor": "controlador", "clove": "controlador",
    "sage": "sentinela", "cypher": "sentinela", "killjoy": "sentinela", "chamber": "sentinela", "deadlock": "sentinela",
    "vyse": "sentinela", "veto": "sentinela",
}


def agent_class(name: str | None) -> str | None:
    return AGENT_CLASS.get((name or "").lower())


# Armor ids have no names in the catalog. Ordering inferred from the loadout value on rounds with the same rifle
# (heavy ~ +1000 credits more than light): see "Armor inference" in the plan. Anything else is reported as light.
ARMOR_LEVEL = {
    "822bcab2-40a2-324e-c137-e09195ad7692": "heavy",
    "4dec83d5-4902-9ab3-bed6-a7a390761157": "light",
    "b1b9086d-41bd-a516-5d29-e3b34a6f1644": "light",
}


def armor_level(armor_id: str | None) -> str:
    if not isinstance(armor_id, str):
        return "none"
    return ARMOR_LEVEL.get(armor_id.lower(), "light")

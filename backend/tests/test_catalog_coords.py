import numpy as np

from app.data.catalog import MAP_NAMES, get_catalog
from app.data.coords import to_minimap, to_minimap_arrays

cat = get_catalog()


def test_known_and_unknown_agent():
    jett = next(a for a, (_, n) in cat._agents.items() if n == "Jett")
    assert cat.agent(jett).name == "Jett" and cat.agent(jett).icon_url.startswith("/assets/Characters/")
    unknown = cat.agent("efba5359-0000-0000-0000-000000000000")
    assert unknown.name is None and unknown.icon_url is None and not unknown.name_inferred
    assert cat.agent(None) is None


def test_unknown_weapon_has_no_invented_name():
    w = cat.weapon("410b2e0b-0000-0000-0000-000000000000")
    assert w.name is None and w.icon_url is None


def test_map_refs():
    assert cat.map_ref("Lotus").has_minimap and cat.map_ref("Lotus").codename == "Jam"
    for name in ("Abyss", "Summit"):
        ref = cat.map_ref(name)
        assert not ref.has_minimap and ref.minimap_url is None
    assert set(MAP_NAMES.values()) == {"Ascent", "Lotus", "Haven", "Split", "Sunset", "Abyss", "Summit", "Breeze", "Pearl", "Fracture"}


def test_to_minimap_rules():
    assert to_minimap("Abyss", 0, 0) is None  # no transform
    assert to_minimap("Ascent", -50_000, 0) is None  # outlier
    assert to_minimap("Ascent", 5356, -7114) is not None
    u, v = to_minimap_arrays("Ascent", np.array([5356, -50_000]), np.array([-7114, 0]))
    assert not np.isnan(u[0]) and np.isnan(u[1]) and np.isnan(v[1])


def test_plants_land_on_the_map(full_store):
    s = full_store
    r = s.rounds.merge(s.matches[["match_id", "map_name"]], on="match_id")
    for name in ("Ascent", "Lotus", "Haven", "Split"):
        p = r[(r.map_name == name) & r.planter.notna()]
        u, _ = to_minimap_arrays(name, p.plant_x.to_numpy(), p.plant_y.to_numpy())
        assert np.isnan(u).mean() < 0.02, name  # visual check saved in docs/coords-check.png

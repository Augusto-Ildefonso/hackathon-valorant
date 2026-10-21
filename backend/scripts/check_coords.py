"""Visual check of the coordinate transform: plant positions per site on the minimaps.

Run from the repo root: backend/.venv/bin/python backend/scripts/check_coords.py [Map ...]
Writes docs/coords-check.png. Sites should form tight clusters on the real bombsites.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.data.catalog import get_catalog  # noqa: E402
from app.data.coords import to_minimap_arrays  # noqa: E402
from app.data.loader import load_store  # noqa: E402

SIZE = 512
COLORS = {"A": (255, 59, 82), "B": (46, 230, 208), "C": (255, 181, 71)}


def main(maps: list[str]):
    store = load_store()
    cat = get_catalog()
    tiles = []
    for name in maps:
        ref = cat.map_ref(name)
        img = Image.open(ROOT / ref.minimap_url.replace("/assets/", "public_catalog/")).convert("RGB").resize((SIZE, SIZE))
        d = ImageDraw.Draw(img)
        r = store.rounds.merge(store.matches[["match_id", "map_name"]], on="match_id")
        r = r[(r.map_name == name) & r.planter.notna()]
        u, v = to_minimap_arrays(name, r.plant_x.to_numpy(), r.plant_y.to_numpy())
        for ui, vi, site in zip(u, v, r.plant_site):
            if ui == ui:
                px, py = ui * SIZE, vi * SIZE
                d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=COLORS.get(site, (255, 255, 255)))
        d.text((8, 8), f"{name}  n={len(r)}", fill=(255, 255, 255))
        tiles.append(img)
    cols = 2
    rows = (len(tiles) + 1) // 2
    sheet = Image.new("RGB", (cols * SIZE, rows * SIZE))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * SIZE, (i // cols) * SIZE))
    out = ROOT / "docs" / "coords-check.png"
    out.parent.mkdir(exist_ok=True)
    sheet.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1:] or ["Ascent", "Lotus", "Haven", "Split"])

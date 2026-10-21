"""Small cached thumbnails of catalog images (the originals are ~1024px / 850 KB, too heavy for list icons).

`GET /api/thumb/{folder}/{stem}?w=96` -> PNG scaled to width `w` (never upscaled), cached under `.cache/thumbs/`.
Owner: Stream A (added by Stream E for the agent/weapon/map pictures in lists).
"""
import re

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from PIL import Image

from ..deps import CATALOG_DIR, REPO_ROOT

router = APIRouter(prefix="/api", tags=["assets"])
FOLDERS = {"Characters", "Weapons", "Maps"}
STEM = re.compile(r"^[A-Za-z0-9_\-]+$")
CACHE = REPO_ROOT / ".cache" / "thumbs"


@router.get("/thumb/{folder}/{stem}")
def thumb(folder: str, stem: str, w: int = Query(96, ge=16, le=512)):
    src = CATALOG_DIR / folder / f"{stem}.png"
    if folder not in FOLDERS or not STEM.match(stem) or not src.exists():
        raise HTTPException(404, "Unknown image")
    out = CACHE / f"{folder}-{stem}-{w}.png"
    if not out.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        im = Image.open(src).convert("RGBA")
        if im.width > w:
            im = im.resize((w, max(1, round(im.height * w / im.width))), Image.LANCZOS)
        im.save(out, optimize=True)
    return FileResponse(out, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})

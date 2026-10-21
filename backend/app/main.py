"""App wiring. Owner: Stream A (others request router registration via a one-line PR)."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .deps import CATALOG_DIR
from .routers import maps, matches, meta, plan, players, teams

app = FastAPI(title="Hackathon Valorant API", version="0.1.0")

for module in (meta, players, teams, maps, matches, plan):
    app.include_router(module.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


if CATALOG_DIR.exists():
    app.mount("/assets", StaticFiles(directory=CATALOG_DIR), name="assets")

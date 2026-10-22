"""App wiring. Owner: Stream A (others request router registration via a one-line PR)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .deps import CATALOG_DIR, get_store
from .routers import assets, chat, maps, matches, meta, plan, players, teams

@asynccontextmanager
async def lifespan(_: FastAPI):
    get_store()  # load (or read the disk cache of) every JSON in data/ before serving
    yield


app = FastAPI(title="VaváGym API", version="0.1.0", lifespan=lifespan)

for module in (meta, players, teams, maps, matches, plan, chat, assets):
    app.include_router(module.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


if CATALOG_DIR.exists():
    app.mount("/assets", StaticFiles(directory=CATALOG_DIR), name="assets")

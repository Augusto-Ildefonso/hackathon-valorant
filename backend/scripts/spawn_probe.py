"""Probe (exploratory): Action Plan round routes computed in-process (no server). Run from the repo root."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

d = TestClient(app).post("/api/plan", json={"team_a": "UFMT Turuna", "team_b": "Azure Bears Black", "map": "Ascent", "perspective": "a"}).json()
r = d["rounds"][4]
for rt in r["map_plan"]["routes"]:
    print(rt["kind"], rt["label"], [(round(p["x"], 2), round(p["y"], 2)) for p in rt["points"]])

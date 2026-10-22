"""Write the printable plan PDF for a matchup (no server needed). Usage, from the repo root:

    backend/.venv/bin/python backend/scripts/make_report.py <out.pdf> [--ai] [team_a] [team_b] [map]

`--ai` lets the LLM write the document (needs GEMINI_API_KEY); without it the deterministic document is produced.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
out = Path(args[0])
a, b, m = (args[1:4] + ["UFMT Turuna", "Azure Bears Black", "Ascent"][len(args[1:4]):])
r = TestClient(app).post("/api/plan/report", json={"team_a": a, "team_b": b, "map": m, "perspective": "a", "use_llm": "--ai" in sys.argv}, timeout=600)
print(r.status_code, r.headers.get("content-type"), "source:", r.headers.get("x-report-source"), "note:", r.headers.get("x-report-note"), len(r.content), "bytes")
if r.status_code == 200:
    out.write_bytes(r.content)
else:
    print(r.text[:600])

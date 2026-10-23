"""Lists the Gemini/Gemma model ids the configured key can call (never prints the key): `python scripts/list_models.py [filter]`."""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.insights import llm  # noqa: E402  (loads .env)

needle = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
r = httpx.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": llm.api_key(), "pageSize": 200}, timeout=30)
r.raise_for_status()
for m in r.json().get("models", []):
    name = m["name"].removeprefix("models/")
    if needle in name.lower() and "generateContent" in m.get("supportedGenerationMethods", []):
        print(name, "|", m.get("displayName"))

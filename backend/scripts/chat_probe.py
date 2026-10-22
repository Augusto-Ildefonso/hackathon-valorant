"""Prints how the chat answers a few sentences on the real data: `python scripts/chat_probe.py ["sentence" ...]`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.chat.understand import names  # noqa: E402
from app.main import app  # noqa: E402

nm = names()
team = nm.teams[0]
other = nm.teams[1]
player = nm.players[0][1]
mp = nm.maps[0]
sentences = sys.argv[1:] or [
    f"informações do jogador {player}", f"detalhes do mapa {mp}", f"plano contra o time {other} no mapa {mp}",
    f"plano do {team} contra {other} em {mp.lower()}", "resumo do campeonato", f"como está o time {team}?", "quais os melhores jogadores?",
    f"ultima partida do {team}", "oi", "jogador xyzabc", f"mapa {mp[:-1]}",
]
with TestClient(app) as c:
    for s in sentences:
        r = c.post("/api/chat", json={"message": s})
        j = r.json()
        kinds = [b["type"] for b in j.get("blocks", [])] if r.status_code == 200 else r.text[:300]
        print(f"{s!r:70} -> {r.status_code} {j.get('intent')} {kinds} {j.get('dashboard')}")

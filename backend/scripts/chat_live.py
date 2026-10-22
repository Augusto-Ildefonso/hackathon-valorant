"""Live check of the chat's AI parts against the running API (needs GEMINI_API_KEY): `python scripts/chat_live.py`."""
import json
import time
import urllib.request

API = "http://localhost:8000"


def post(path, body):
    req = urllib.request.Request(API + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


for q in ["me conta como anda aquele time do Azure Bears preto, se vale a pena enfrentar", "quem manda bem em Haven por aqui?", "como será que o chadu joga"]:
    t = time.time()
    r = post("/api/chat", {"message": q})
    print(f"\n{q!r}\n  -> intent={r['intent']} source={r['source']} dashboard={r['dashboard'] and r['dashboard']['path'][:40]} ({time.time() - t:.1f}s)")
    if r["can_summarize"]:
        t = time.time()
        s = post("/api/chat/summary", {"intent": r["intent"], "blocks": r["blocks"]})
        print(f"  summary ({time.time() - t:.1f}s): {s['text']!r} note={s['note']}")

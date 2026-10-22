"""Dev probe: what the model wrote for the printable plan vs what the validation kept (uses the disk cache)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.deps import get_store  # noqa: E402
from app.insights import llm, report  # noqa: E402
from app.insights.action_plan import build_plan  # noqa: E402
from app.insights.report_images import ImageBank  # noqa: E402
from app.schemas import PlanRequest  # noqa: E402

full = get_store()
plan = build_plan(full, PlanRequest(team_a="UFMT Turuna", team_b="Azure Bears Black", map="Ascent"))
bank = ImageBank(plan, full)
data, err, hit = llm.generate_json(report.SYSTEM, json.dumps(report._packet(plan, bank), ensure_ascii=False))
print("error:", err, "cached:", hit)
secs = data.get("sections", []) if data else []
words = sum(len(str(b.get("text", "")).split()) + sum(len(i.split()) for i in b.get("items", [])) for s in secs for b in s.get("blocks", []))
print("sections:", len(secs), "words written:", words)
allowed, total = report._allowed_numbers(plan), plan.rounds_per_half * 2
for s in secs:
    for b in s.get("blocks", []):
        texts = [b["text"]] if b.get("type") == "paragraph" else b.get("items", []) if b.get("type") == "bullets" else []
        for t in texts:
            if report._clean(t, report.MAX_PARAGRAPH if b["type"] == "paragraph" else report.MAX_BULLET, allowed, total) is None:
                extra = llm.numbers_in(t) - allowed
                why = "stats" if llm.recites_stats(t) else "reader" if llm.addresses_reader(t) else f"numbers {sorted(extra)}" if extra else "length/refs"
                print(f"DROPPED ({why}): {t[:140]}")
blocks, dropped = report.validate_sections(data, plan, bank)
print("kept blocks:", len(blocks), "dropped:", dropped)

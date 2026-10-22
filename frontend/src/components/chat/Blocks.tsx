// Renders the typed blocks of a chat answer with the existing UI components. Owner: Stream G.
import { useState } from "react";
import { downloadPlanPdf } from "@/api/client";
import type { ChatBlock } from "@/api/types";
import { InsightCard } from "@/components/ui/InsightList";

const title = "font-display text-xs font-semibold uppercase leading-4 tracking-[0.96px] text-fg-muted";

function PdfButton({ request }: { request: object }) {
  const [state, setState] = useState<{ busy: boolean; error?: string }>({ busy: false });
  const go = async () => {
    setState({ busy: true });
    try {
      await downloadPlanPdf({ ...request, use_llm: true });
      setState({ busy: false });
    } catch (e) {
      setState({ busy: false, error: String(e) });
    }
  };
  return (
    <div className="flex items-center gap-3">
      <button onClick={go} disabled={state.busy} className="rounded-sm border border-border bg-surface-raised px-4 py-2 text-sm font-medium text-fg-secondary hover:text-fg disabled:opacity-50">
        {state.busy ? "Gerando PDF…" : "Baixar plano em PDF"}
      </button>
      {state.error && <span role="alert" className="text-xs text-accent">{state.error}</span>}
    </div>
  );
}

export function Blocks({ blocks, onSend }: { blocks: ChatBlock[]; onSend: (text: string) => void }) {
  return (
    <div className="flex flex-col gap-3">
      {blocks.map((b, i) => {
        switch (b.type) {
          case "text":
            return <p key={i} className="text-sm leading-6 text-fg">{b.text}</p>;
          case "warning":
            return <p key={i} className="rounded-sm border border-amber bg-tint-amber px-3 py-2 text-sm text-amber">{b.text}</p>;
          case "stats":
            return (
              <div key={i} className="flex flex-col gap-2">
                {b.title && <p className={title}>{b.title}</p>}
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  {b.items.map((s) => (
                    <div key={s.label} className="flex flex-col gap-1 rounded-md border border-border bg-surface-raised p-3">
                      <span className={title}>{s.label}</span>
                      <span className="font-display text-2xl font-bold text-fg">{s.value}</span>
                      <span className="text-[11px] text-fg-muted">
                        {s.sample_size != null && `n = ${s.sample_size}`}
                        {s.low_sample && <span className="ml-1 text-amber">⚠ amostra pequena</span>}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          case "insights":
            return (
              <div key={i} className="flex flex-col gap-2">
                <p className={title}>{b.title}</p>
                {b.items.map((it) => <InsightCard key={it.id} insight={it} />)}
              </div>
            );
          case "table":
            return (
              <div key={i} className="flex flex-col gap-2 overflow-x-auto">
                {b.title && <p className={title}>{b.title}</p>}
                <table className="w-full text-left text-sm">
                  <thead><tr>{b.columns.map((c) => <th key={c} className={`${title} border-b border-border py-2 pr-4`}>{c}</th>)}</tr></thead>
                  <tbody>
                    {b.rows.map((r, ri) => (
                      <tr key={ri}>{r.map((c, ci) => <td key={ci} className="border-b border-border py-2 pr-4 text-fg">{c}</td>)}</tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          case "choices":
            return (
              <div key={i} className="flex flex-col gap-2">
                <p className="text-sm text-fg">{b.prompt}</p>
                <div className="flex flex-wrap gap-2">
                  {b.options.map((o) => (
                    <button key={o.send} onClick={() => onSend(o.send)} className="rounded-sm border border-border bg-surface px-3 py-2 text-sm font-medium text-fg-secondary hover:border-border-strong hover:text-fg">{o.label}</button>
                  ))}
                </div>
              </div>
            );
          case "plan_summary":
            return (
              <div key={i} className="flex flex-col gap-3">
                <p className={title}>{b.title}</p>
                {b.rounds.map((r) => (
                  <div key={r.number} className="flex flex-col gap-1 rounded-md border border-border bg-surface-raised p-3">
                    <p className="font-display text-sm font-semibold text-fg">Round {r.number} · {r.side} · {r.round_type}</p>
                    <p className="text-sm text-fg">{r.summary_pt}</p>
                    <p className="text-xs text-fg-muted">{r.buy_pt}</p>
                  </div>
                ))}
                {b.weak_points.length > 0 && <p className={title}>Pontos fracos do adversário</p>}
                {b.weak_points.map((w) => <InsightCard key={w.id} insight={w} />)}
                <PdfButton request={b.pdf_request} />
              </div>
            );
        }
      })}
    </div>
  );
}

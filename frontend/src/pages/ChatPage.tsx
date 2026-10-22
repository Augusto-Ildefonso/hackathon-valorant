// Início: chat that triggers the existing analyses and shows them in a readable way (Stream G). No Figma frame exists for
// it, so it reuses the design tokens and components of the other screens (deviation recorded in the plan).
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import { useLeaderboards, useMaps } from "@/api/hooks";
import type { ChatContext, ChatResponse } from "@/api/types";
import { Blocks } from "@/components/chat/Blocks";
import { FilterChip } from "@/components/ui/FilterChip";
import { PageHeader } from "@/components/ui/PageHeader";

type Msg = { id: number; role: "user"; text: string } | { id: number; role: "bot"; response?: ChatResponse; error?: string; summary?: string; summarizing?: boolean };
const KEY = "vavagym.chat";

function load(): { msgs: Msg[]; ctx: ChatContext } {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) ?? "") as { msgs: Msg[]; ctx: ChatContext };
  } catch {
    return { msgs: [], ctx: {} };
  }
}

export default function ChatPage() {
  const initial = useRef(load()).current;
  const [msgs, setMsgs] = useState<Msg[]>(initial.msgs);
  const [ctx, setCtx] = useState<ChatContext>(initial.ctx);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | undefined>();
  const [hideTips, setHideTips] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const board = useLeaderboards();
  const maps = useMaps();

  useEffect(() => {
    try {
      sessionStorage.setItem(KEY, JSON.stringify({ msgs: msgs.filter((m) => m.role === "user" || m.response), ctx }));
    } catch { /* storage unavailable: the conversation just is not kept across pages */ }
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [msgs, ctx]);

  const player = board.data?.players.kd[0]?.player.riot_id;
  const teams = board.data?.teams.win_rate ?? [];
  const map = maps.data?.items.slice().sort((a, b) => b.matches - a.matches)[0]?.map.name;
  const tips = [
    player && `Informações do jogador ${player}`,
    map && `Detalhes do mapa ${map}`,
    teams.length > 1 && map && `Plano do ${teams[0].team.name} contra o ${teams[1].team.name} no mapa ${map}`,
    "Resumo do campeonato",
  ].filter(Boolean) as string[];

  const send = async (raw: string) => {
    const message = raw.trim();
    if (!message || busy) return;
    const id = Date.now();
    setBusy(true);
    setProblem(undefined);
    try {
      const r = await api<ChatResponse>("/api/chat", { body: { message, context: ctx } });
      if (r.problem) {  // missing or unknown data: like an invalid form field, the question is not sent and stays in the box
        setText(message);
        setProblem(r.problem);
        return;
      }
      setText("");
      setMsgs((m) => [...m, { id, role: "user", text: message }]);
      setCtx(r.context);
      setMsgs((m) => [...m, { id: id + 1, role: "bot", response: r, summarizing: r.can_summarize }]);
      if (r.can_summarize) {  // the answer is already on screen; the optional AI paragraph arrives when (and if) it is ready
        api<{ text: string | null; note: string | null }>("/api/chat/summary", { body: { intent: r.intent, blocks: r.blocks } })
          .then((s) => setMsgs((m) => m.map((x) => (x.id === id + 1 && x.role === "bot" ? { ...x, summary: s.text ?? undefined, summarizing: false } : x))))
          .catch(() => setMsgs((m) => m.map((x) => (x.id === id + 1 && x.role === "bot" ? { ...x, summarizing: false } : x))));
      }
    } catch (e) {
      setMsgs((m) => [...m, { id, role: "user", text: message }, { id: id + 1, role: "bot", error: String(e) }]);
      setText("");
    } finally {
      setBusy(false);
    }
  };

  const reset = () => { setMsgs([]); setCtx({}); };

  return (
    <div className="mx-auto flex w-full max-w-[860px] flex-col gap-6">
      <PageHeader
        title="Pergunte ao VaváGym"
        subtitle="Peça informações de um jogador, time, mapa ou campeonato, ou um plano contra um adversário. Cada resposta vem das mesmas análises do dashboard."
        actions={msgs.length > 0 ? <button onClick={reset} className="rounded-sm border border-border px-3 py-2 text-sm text-fg-secondary hover:text-fg">Nova conversa</button> : undefined}
      />

      <div className="flex flex-col gap-4" aria-live="polite">
        {msgs.length === 0 && (
          <p className="rounded-md border border-border bg-surface p-5 text-sm leading-6 text-fg-secondary">
            Escreva uma pergunta abaixo. Também é possível navegar direto pelo menu lateral: o chat é só um atalho.
          </p>
        )}
        {msgs.map((m) =>
          m.role === "user" ? (
            <div key={m.id} className="self-end rounded-md bg-surface-accent px-4 py-3 text-sm text-fg">{m.text}</div>
          ) : (
            <div key={m.id} className="flex flex-col gap-4 rounded-md border border-border bg-surface p-5">
              {m.error ? <p role="alert" className="text-sm text-accent">Não consegui responder agora: {m.error}</p> : m.response && (
                <>
                  {(m.summary || m.summarizing) && (
                    <p className="rounded-sm border border-border bg-surface-raised px-4 py-3 text-sm leading-6 text-fg">
                      <span className="mr-2 rounded-sm bg-tint-violet px-2 text-[11px] font-medium leading-[14px] text-violet" title="Escrito por IA a partir dos fatos abaixo">IA</span>
                      {m.summary ?? <span className="text-fg-muted">Escrevendo o resumo…</span>}
                    </p>
                  )}
                  <Blocks blocks={m.response.blocks} onSend={send} />
                  {m.response.note && <p className="text-xs text-fg-muted">{m.response.note}</p>}
                  {m.response.dashboard && (
                    <div>
                      <Link to={m.response.dashboard.path} className="inline-block rounded-sm bg-accent px-5 py-3 font-display text-xs font-semibold uppercase tracking-[0.96px] text-on-accent hover:bg-accent-hover">
                        {m.response.dashboard.label} →
                      </Link>
                    </div>
                  )}
                </>
              )}
            </div>
          ),
        )}
        {busy && <p className="text-sm text-fg-muted">Analisando…</p>}
        <div ref={end} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); void send(text); }} className="sticky bottom-0 flex flex-col gap-3 bg-bg-app pb-2 pt-2">
        <div className="flex gap-3">
          <input
            value={text}
            onChange={(e) => { setText(e.target.value); setProblem(undefined); }}
            aria-label="Pergunta"
            aria-invalid={problem ? true : undefined}
            aria-describedby={problem ? "chat-problem" : undefined}
            placeholder="Ex.: plano do time A contra o time B no mapa Ascent"
            className={`min-w-0 flex-1 rounded-sm border bg-surface px-4 py-3 text-sm text-fg placeholder:text-fg-muted ${problem ? "border-accent" : "border-border"}`}
          />
          <button type="submit" disabled={busy || !text.trim()} className="shrink-0 rounded-sm bg-accent px-6 py-3 font-display text-xs font-semibold uppercase tracking-[0.96px] text-on-accent hover:bg-accent-hover disabled:opacity-50">
            Enviar
          </button>
        </div>
        {problem && <p id="chat-problem" role="alert" className="text-sm text-accent">{problem}</p>}
        {!hideTips && msgs.length === 0 && tips.length > 0 && (  // shortcuts only help before the first question
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] text-fg-muted">Sugestões (opcional)</span>
            {tips.map((t) => <FilterChip key={t} onClick={() => void send(t)}>{t}</FilterChip>)}
            <button type="button" onClick={() => setHideTips(true)} className="text-[11px] text-fg-muted hover:text-fg" aria-label="Ocultar sugestões">ocultar</button>
          </div>
        )}
      </form>
    </div>
  );
}

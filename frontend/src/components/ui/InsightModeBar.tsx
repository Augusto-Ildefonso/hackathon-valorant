// Figma "AI mode bar" (Player 48:552, Team 48:560, Map 48:568, Match 48:576): "INSIGHTS POR  [Regras] [Análise por IA]  caption".
// Switches the insight panels of a page between the fixed rules and the AI analysis (same computed facts, every number
// validated by the backend). Owner: Stream D. The rules stay on screen while the slow AI answer loads.
import { usePlanCapabilities } from "@/api/hooks";
import type { InsightMode } from "@/api/types";
import { FilterChip } from "./FilterChip";

export interface InsightModeBarProps {
  mode: InsightMode;
  onChange: (m: InsightMode) => void;
  /** The AI request is in flight. */
  loading: boolean;
  /** `insights_source` of the data on screen: "rules" while in AI mode means the backend fell back to the rules. */
  source?: InsightMode;
}

export function InsightModeBar({ mode, onChange, loading, source }: InsightModeBarProps) {
  const caps = usePlanCapabilities();
  const available = Boolean(caps.data?.llm);
  const fellBack = mode === "llm" && !loading && source !== "llm";
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <span className="font-display text-xs font-semibold uppercase tracking-[0.96px] text-fg-muted">Insights por</span>
        <FilterChip on={mode === "rules"} onClick={() => onChange("rules")}>Regras</FilterChip>
        <FilterChip
          on={mode === "llm"}
          disabled={!available}
          onClick={() => onChange("llm")}
          title={available ? "Análise por IA sobre os mesmos fatos calculados; cada número é validado" : "Desativada neste ambiente (defina VAVAGYM_LLM=1 e GEMINI_API_KEY no arquivo .env do servidor)"}
          className={available ? "" : "cursor-not-allowed opacity-50"}
        >
          {loading ? "Gerando análise…" : "Análise por IA"}
        </FilterChip>
        <span className="ml-auto text-[11px] text-fg-muted">Regras: limiares fixos, instantâneas · IA: mesmos fatos, números validados, 20 s a 2 min</span>
      </div>
      {loading && <p className="text-xs leading-4 text-cyan">Gerando a análise por IA… pode levar de 20 s a 2 minutos; os insights por regras continuam na tela.</p>}
      {fellBack && <p className="text-xs leading-4 text-amber">A análise por IA não ficou disponível agora (cota ou falha do modelo): mostrando os insights por regras.</p>}
      {mode === "llm" && !loading && source === "llm" && <p className="text-[11px] leading-[14px] text-fg-muted">Análise por IA a partir dos fatos calculados (valores, amostras e referências vêm do código). Insights marcados com IA podem repetir ideias das regras.</p>}
    </div>
  );
}

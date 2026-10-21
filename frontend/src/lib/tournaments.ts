// Tournament / phase options for the filters, built from /api/meta. Owner: Stream E.
import type { MetaResponse } from "@/api/types";

export interface Option {
  value: string; // "" = all, "RUSH2", or "UNIVAVA/Classificat" (phase prefix)
  label: string;
}

const short = (s: string) => s.replace("Series ", "");

/** "Classificatória 1..4" -> one option "Univavá · Classif. 1–4"; other phases keep their own name. */
export function tournamentOptions(meta: MetaResponse | undefined): Option[] {
  const out: Option[] = [{ value: "", label: "Todos" }];
  for (const t of meta?.tournaments ?? []) {
    if (!t.phases.length) {
      out.push({ value: t.id, label: short(t.name) });
      continue;
    }
    const groups = new Map<string, number[]>();
    for (const p of t.phases) {
      const m = p.match(/^(.*?)\s*(\d+)$/);
      const base = m ? m[1] : p;
      groups.set(base, [...(groups.get(base) ?? []), ...(m ? [Number(m[2])] : [])]);
    }
    for (const [base, nums] of groups) {
      const label = base.replace("Classificatória", "Classif.");
      out.push({
        value: `${t.id}/${base}`,
        label: nums.length > 1 ? `${t.name} · ${label} ${Math.min(...nums)}–${Math.max(...nums)}` : `${t.name} · ${label}`,
      });
    }
  }
  return out;
}

const MONTHS = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];

/** "Tudo" plus one option per month between the first and last match date. */
export function periodOptions(meta: MetaResponse | undefined): Option[] {
  const out: Option[] = [{ value: "", label: "Tudo" }];
  if (!meta) return out;
  const [y0, m0] = meta.date_from.split("-").map(Number);
  const [y1, m1] = meta.date_to.split("-").map(Number);
  for (let y = y0, m = m0; y < y1 || (y === y1 && m <= m1); m === 12 ? (y++, (m = 1)) : m++) {
    out.push({ value: `${y}-${String(m).padStart(2, "0")}`, label: `${MONTHS[m - 1]} ${y}` });
  }
  return out;
}

/** Short tournament label used in match tables: "Univavá · Grupos", "Rush Inclusivo". */
export function tournamentLabel(tournament: string, phase: string | null): string {
  const base = short(tournament);
  if (!phase) return base;
  return `${base} · ${phase.replace("Fase de ", "").replace("Classificatória", "Classif.")}`;
}

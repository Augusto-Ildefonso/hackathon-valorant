// Shared formatting + pt-BR labels. Added by Stream B (used by Player/Team pages; others may reuse).
import type { RoleName, RoundType, Stat } from "@/api/types";

export const ROUND_TYPE_PT: Record<RoundType, string> = {
  pistol: "Pistol",
  eco: "Eco",
  semi_eco: "Semi-eco",
  force: "Force",
  full_buy: "Full buy",
};

export const ROLE_PT: Record<RoleName, string> = {
  entry: "Entry Fragger",
  lurker: "Lurker",
  igl: "IGL",
  support: "Suporte",
  anchor: "Anchor",
  flex: "Flex",
};

export const SIGNAL_PT: Record<string, string> = {
  first_duel_share: "rounds com duelo de abertura",
  early_kill_share: "kills nos primeiros 30 s",
  late_kill_share: "kills após 60 s",
  isolation: "isolamento do time",
  assists_per_round: "assistências por round",
  casts_per_round: "habilidades por round",
  defense_site_presence: "presença no bombsite na defesa",
  agent_variety: "variedade de agentes",
};

const nf = (digits: number) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits });

export const num = (v: number | null | undefined, digits = 2) => (v == null ? "—" : nf(digits).format(v));
export const pct = (v: number | null | undefined, digits = 0) => (v == null ? "—" : `${nf(digits).format(v * 100)}%`);
export const statPct = (s: Stat, digits = 0) => pct(s.value, digits);
export const statNum = (s: Stat, digits = 2) => num(s.value, digits);
export const seconds = (ms: number | null | undefined) => (ms == null ? "—" : `${nf(1).format(ms / 1000)} s`);
export const dateBR = (iso: string) => iso.split("-").reverse().join("/");

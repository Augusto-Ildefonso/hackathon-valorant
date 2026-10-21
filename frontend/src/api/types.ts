// Mirrors backend/app/schemas/*.py. Owner: Stream E. Keep in sync in the same PR as any schema change.

// ---- common ----
export type Side = "attack" | "defense";
export type InsightKind = "strength" | "weakness" | "tip" | "strategy";
export type RoundType = "pistol" | "eco" | "semi_eco" | "force" | "full_buy";
export type RoleName = "entry" | "lurker" | "igl" | "support" | "anchor" | "flex";
export type Site = "A" | "B" | "C";

export interface Point { x: number; y: number }
export interface Stat { value: number | null; sample_size: number; low_sample: boolean }
export interface Evidence { metric: string; value: number; baseline?: number | null; sample_size: number; unit?: string | null }
export interface Insight { id: string; kind: InsightKind; text_pt: string; evidence: Evidence; low_sample: boolean }
export interface AgentRef { id: string; name: string | null; name_inferred: boolean; icon_url: string | null }
export interface WeaponRef { id: string; name: string | null; name_inferred: boolean; icon_url: string | null }
export interface MapRef { codename: string; name: string; has_minimap: boolean; minimap_url: string | null }
export interface TeamRef { name: string }
export interface PlayerRef { puuid: string; riot_id: string }
export interface MatchSide { team: TeamRef; score: number }
export interface MatchListItem {
  match_id: string; tournament: string; phase: string | null; date: string; map: MapRef;
  team_a: MatchSide; team_b: MatchSide; winner: "a" | "b"; duration_ms: number;
}
export interface Signal { name: string; value: number; sample_size: number }
export interface RoleScore { role: RoleName; score: number; confidence: number; inferred: boolean; signals: Signal[] }

// ---- meta ----
export interface Kpis { matches: number; rounds: number; kills: number; players: number; teams: number; tournaments: number }
export interface TournamentInfo { id: string; name: string; phases: string[]; matches: number }
export interface MetaResponse { kpis: Kpis; date_from: string; date_to: string; tournaments: TournamentInfo[]; maps: MapRef[] }
export interface PlayerHit { player: PlayerRef; team: TeamRef | null; matches: number }
export interface TeamHit { team: TeamRef; matches: number }
export interface MapHit { map: MapRef }
export interface SearchResponse { query: string; players: PlayerHit[]; teams: TeamHit[]; maps: MapHit[] }
export interface PlayerLeaderRow {
  rank: number; player: PlayerRef; team: TeamRef | null; value: number; matches: number; rounds: number; low_sample: boolean;
  kd?: number | null; adr?: number | null; hs_pct?: number | null; first_kills?: number | null;
}
export interface TeamLeaderRow {
  rank: number; team: TeamRef; value: number; matches: number; rounds: number; low_sample: boolean;
  wins?: number | null; losses?: number | null;
}
export interface LeaderboardsResponse {
  players: Record<"kd" | "adr" | "hs_pct" | "first_kills", PlayerLeaderRow[]>;
  teams: Record<"win_rate" | "round_win_rate", TeamLeaderRow[]>;
}

// ---- player ----
export interface Multikills { k2: number; k3: number; k4: number; k5: number }
export interface PlayerStats {
  matches: number; rounds: number; kills: number; deaths: number; assists: number;
  kd: Stat; adr: Stat; hs_pct: Stat; first_kill_rate: Stat; first_death_rate: Stat; opening_duel_win_pct: Stat;
  clutches: number; multikills: Multikills;
  shots: number; first_kills: number; first_deaths: number; traded_deaths: number;
}
export interface WeaponPerformance {
  weapon: WeaponRef; buy_type: RoundType | null; rounds: number; round_win_rate: Stat; kills: number;
  kd: Stat; hs_pct: Stat; damage_per_round: Stat;
}
export interface MapPerformance { map: MapRef; matches: number; kills: number; deaths: number; kd: Stat }
export interface AgentPerformance { agent: AgentRef; matches: number; kd: Stat; adr: Stat; win_rate: Stat }
export interface PlayerProfile {
  player: PlayerRef; teams: TeamRef[]; favorite_agent: AgentRef | null; roles: RoleScore[]; stats: PlayerStats;
  weapons: WeaponPerformance[]; by_map: MapPerformance[]; agents: AgentPerformance[]; insights: Insight[];
}

// ---- team ----
export interface TeamListItem { team: TeamRef; matches: number; win_rate: Stat; round_win_rate: Stat; last_match_date: string }
export interface TeamListResponse { items: TeamListItem[] }
export interface RosterMember { player: PlayerRef; matches: number; top_role: RoleScore | null; kd?: number | null; adr?: number | null }
export interface TeamRecord {
  matches: number; series: number; wins: number; losses: number;
  round_win_rate: Stat; attack_win_rate: Stat; defense_win_rate: Stat;
}
export interface TrendPoint { match_id: string; date: string; round_diff: number; map_name?: string | null }
export interface TeamMapPerformance { map: MapRef; matches: number; win_rate: Stat; attack_win_rate: Stat; defense_win_rate: Stat }
export interface TeamEconomy {
  win_rate_by_round_type: Record<RoundType, Stat>; pistol_win_rate: Stat; plant_site_preference: Partial<Record<Site, Stat>>;
  avg_time_to_plant_ms: Stat; post_plant_win_rate: Stat; retake_success_rate: Stat;
}
export interface RoleCount { role: RoleName; count: number }
export interface TeamProfile {
  team: TeamRef; roster: RosterMember[]; record: TeamRecord; matches: MatchListItem[]; trend: TrendPoint[];
  by_map: TeamMapPerformance[]; economy: TeamEconomy; role_composition: RoleCount[]; insights: Insight[];
}

// ---- map ----
export interface MapListItem { map: MapRef; matches: number; rounds: number; attack_win_rate: Stat }
export interface MapListResponse { items: MapListItem[] }
export interface UsageRow { id: string; name: string | null; icon_url: string | null; picks: number; share: number }
export interface SiteStats { site: Site; plants: number; plant_rate: Stat; defuse_rate: Stat; retake_rate: Stat }
export interface PlantPoint { site: Site; point: Point }
export interface MapProfile {
  map: MapRef; matches: number; rounds: number; attack_win_rate: Stat; defense_win_rate: Stat;
  classification: "attack" | "defense" | "balanced"; top_agents: UsageRow[]; top_weapons: UsageRow[];
  sites: SiteStats[]; plants: PlantPoint[]; insights: Insight[];
}
export interface HeatLayer { grid: number[][]; max_count: number }
export interface HeatmapResponse {
  map: MapRef; side: Side | "both"; grid_size: number; has_data: boolean;
  kills: HeatLayer | null; deaths: HeatLayer | null; danger: HeatLayer | null; uncovered: HeatLayer | null;
  plants: PlantPoint[]; agents_used: AgentRef[]; weapons_used: WeaponRef[];
}

// ---- match ----
export interface MatchListResponse { items: MatchListItem[]; total: number }
export interface RoundEconomy { team_a_type: RoundType; team_b_type: RoundType; team_a_loadout: number; team_b_loadout: number }
export interface RoundSummary {
  number: number; half: 1 | 2 | "ot"; winner: "a" | "b"; team_a_side: Side;
  result: "eliminated" | "defused" | "detonated" | "timer"; ceremony: string | null; plant_site: Site | null;
  planted: boolean; defused: boolean; economy: RoundEconomy;
}
export interface ScoreboardRow {
  player: PlayerRef; team: "a" | "b"; agent: AgentRef; kills: number; deaths: number; assists: number;
  adr: Stat; hs_pct: Stat; first_kills: number; score: number;
}
export interface MatchReport {
  match_id: string; tournament: string; phase: string | null; date: string; map: MapRef; duration_ms: number;
  team_a: MatchSide; team_b: MatchSide; winner: "a" | "b"; mvp: PlayerRef | null; rounds: RoundSummary[];
  scoreboard: ScoreboardRow[]; insights_a: Insight[]; insights_b: Insight[];
}
export interface ReplayPlayer {
  puuid: string; riot_id: string; team: "a" | "b"; agent: AgentRef | null; pos: Point | null; view_radians: number | null;
}
export interface KillEvent {
  id: string; round: number; time_ms: number; killer: ReplayPlayer; victim: ReplayPlayer; assistants: PlayerRef[];
  weapon: WeaponRef | null; damage_type: "weapon" | "ability" | "bomb" | "fall" | "melee" | "crush" | "unknown";
  headshot: boolean | null; others_alive: ReplayPlayer[];
}
export interface KillsResponse { match_id: string; map: MapRef; has_minimap: boolean; kills: KillEvent[]; teams: Record<"a" | "b", TeamRef> }

// ---- plan ----
export interface PlanRequest {
  team_a: string; team_b: string; map: string; perspective: "a" | "b"; rounds_per_half: number; starting_side: Side;
}
export interface AgentRecommendation { agent: AgentRef; role: string | null; reason_pt: string; evidence: Stat }
export interface OpponentSummary {
  team: TeamRef; matches_on_map: number; preferred_site: Site | null; avg_time_to_plant_ms: Stat;
  attack_win_rate: Stat; defense_win_rate: Stat; pistol_win_rate: Stat; eco_win_rate: Stat; insights: Insight[];
}
export interface ProjectedEconomy { team_credits: number; enemy_credits: number; reasoning_pt: string }
export interface BuyItem { role: string; weapon: WeaponRef | null; armor: "none" | "light" | "heavy"; reason_pt: string }
export interface RoundStrategy { summary_pt: string; site: Site | null; timing: string | null; steps_pt: string[] }
export interface EnemyMove { summary_pt: string; site: Site | null; route: Point[]; evidence: Stat }
export interface ContingencyOutcome { round_type: RoundType; summary_pt: string }
export interface Contingency { if_previous_won: ContingencyOutcome; if_previous_lost: ContingencyOutcome }
export interface RoundPlan {
  number: number; half: 1 | 2; side: Side; round_type: RoundType; base_scenario_result: "win" | "loss";
  win_probability: Stat; projected_economy: ProjectedEconomy; buy: BuyItem[]; strategy: RoundStrategy;
  enemy_weak_points: Insight[]; enemy_probable_strategy: EnemyMove; contingency: Contingency; insights: Insight[];
}
export interface PlanResponse {
  team_a: TeamRef; team_b: TeamRef; perspective: "a" | "b"; map: MapRef; rounds_per_half: number;
  starting_side: Side; agents: AgentRecommendation[]; opponent: OpponentSummary; rounds: RoundPlan[]; narrative_pt: string | null;
}

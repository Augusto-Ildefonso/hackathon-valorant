// Layered minimap renderer. Owner: Stream C. The PROPS BELOW ARE FROZEN in Phase 0 (B and D reuse this component);
// Stream C may replace the body (pan/zoom, view cones, richer layers) but not break the props.
// Stream E additions (props unchanged): extra heat colors (green, violet), square plant markers with the site letter.
import { useEffect, useRef } from "react";
import type { HeatLayer, MapRef, Point } from "@/api/types";
import { EmptyState } from "@/components/ui/EmptyState";

export type PointKind = "kill" | "death" | "plant" | "player";

export interface MinimapPoint {
  point: Point;
  kind: PointKind;
  team?: "a" | "b";
  label?: string;
  /** Looking direction in radians (draws a view cone when set). */
  viewRadians?: number | null;
}

export interface MinimapProps {
  map: MapRef;
  /** Rendered size in px (square). Default 640. */
  size?: number;
  /** Heat layers drawn first (bottom to top). */
  heat?: Array<{ layer: HeatLayer; color?: "red" | "cyan" | "amber" | "green" | "violet"; opacity?: number }>;
  points?: MinimapPoint[];
  /** Killer -> victim trajectories. `dashed` / `color` are optional additions (Stream E). */
  lines?: Array<{ from: Point; to: Point; team?: "a" | "b"; dashed?: boolean; color?: string }>;
  /** Routes (e.g. probable enemy path in the Action Plan). */
  routes?: Array<{ points: Point[]; color?: string }>;
  onPointClick?: (index: number) => void;
}

const TEAM_A = "#2ee6d0"; // Figma Match Report: team A cyan, team B amber
const TEAM_B = "#ffb547";
const HEAT_RGB = { red: "255,59,82", cyan: "46,230,208", amber: "255,181,71", green: "61,220,132", violet: "160,123,255" } as const;

export function MinimapCanvas({ map, size = 640, heat = [], points = [], lines = [], routes = [] }: MinimapProps) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const ctx = ref.current?.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, size, size);
    for (const { layer, color = "red", opacity = 0.7 } of heat) {
      const n = layer.grid.length;
      const cell = size / n;
      layer.grid.forEach((row, r) =>
        row.forEach((v, c) => {
          if (v <= 0) return;
          ctx.fillStyle = `rgba(${HEAT_RGB[color]},${Math.min(1, v) * opacity})`;
          ctx.fillRect(c * cell, r * cell, cell, cell);
        }),
      );
    }
    for (const l of lines) {
      ctx.strokeStyle = l.color ?? (l.team === "b" ? TEAM_B : l.team === "a" ? TEAM_A : "#ff3b52");
      ctx.lineWidth = 2;
      ctx.setLineDash(l.dashed ? [6, 5] : []);
      ctx.beginPath();
      ctx.moveTo(l.from.x * size, l.from.y * size);
      ctx.lineTo(l.to.x * size, l.to.y * size);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.lineWidth = 1;
    }
    for (const r of routes) {
      ctx.strokeStyle = r.color ?? "#ffb547";
      ctx.lineWidth = 2;
      ctx.beginPath();
      r.points.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x * size, p.y * size) : ctx.lineTo(p.x * size, p.y * size)));
      ctx.stroke();
      ctx.lineWidth = 1;
    }
    for (const p of points) {
      const x = p.point.x * size, y = p.point.y * size;
      if (p.kind === "plant") {
        ctx.fillStyle = "#ffb547";
        ctx.beginPath();
        ctx.roundRect(x - 13, y - 13, 26, 26, 3);
        ctx.fill();
        ctx.fillStyle = "#0a0d12";
        ctx.font = "600 14px 'Chakra Petch', sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(p.label ?? "", x, y + 1);
        continue;
      }
      const color = p.team === "b" ? TEAM_B : p.team === "a" ? TEAM_A : "#ff3b52";
      if (p.kind === "death") {  // victim: red square with a cross
        ctx.fillStyle = "#ff3b52";
        ctx.fillRect(x - 11, y - 11, 22, 22);
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x - 5, y - 5); ctx.lineTo(x + 5, y + 5);
        ctx.moveTo(x + 5, y - 5); ctx.lineTo(x - 5, y + 5);
        ctx.stroke();
        ctx.lineWidth = 1;
      } else {
        if (p.viewRadians != null) {  // view cone: game angle t -> minimap direction (sin t, -cos t), verified on real kills
          const a = Math.atan2(-Math.cos(p.viewRadians), Math.sin(p.viewRadians)), half = Math.PI / 6, len = 55;
          ctx.fillStyle = `${color}40`;
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.arc(x, y, len, a - half, a + half);
          ctx.closePath();
          ctx.fill();
        }
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, p.kind === "kill" ? 9 : p.kind === "player" ? 6 : 4, 0, Math.PI * 2);
        ctx.fill();
        if (p.kind === "kill") {  // killer: white ring
          ctx.strokeStyle = "#fff";
          ctx.lineWidth = 2;
          ctx.stroke();
          ctx.lineWidth = 1;
        }
      }
      if (p.label) {
        ctx.fillStyle = p.kind === "death" ? "#ff6475" : "#f1eee8";
        ctx.font = "11px Inter, sans-serif";
        ctx.textAlign = "left";
        ctx.textBaseline = "alphabetic";
        ctx.fillText(p.label, x + 14, y + 4);
      }
    }
  }, [heat, points, lines, routes, size]);

  if (!map.has_minimap || !map.minimap_url) {
    return (
      <EmptyState
        title={`Sem minimapa para ${map.name}`}
        message="Este mapa não tem minimapa no catálogo; as estatísticas que não dependem de posição continuam disponíveis."
      />
    );
  }
  return (
    <div className="relative border border-border bg-black" style={{ width: size, height: size }}>
      <img src={map.minimap_url} alt={`Minimapa de ${map.name}`} width={size} height={size} className="absolute inset-0" />
      <canvas ref={ref} width={size} height={size} className="absolute inset-0" />
    </div>
  );
}

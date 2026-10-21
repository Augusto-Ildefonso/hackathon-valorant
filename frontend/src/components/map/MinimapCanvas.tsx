// Layered minimap renderer. Owner: Stream C. The PROPS BELOW ARE FROZEN in Phase 0 (B and D reuse this component);
// Stream C may replace the body (pan/zoom, view cones, richer layers) but not break the props.
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
  heat?: Array<{ layer: HeatLayer; color?: "red" | "cyan" | "amber"; opacity?: number }>;
  points?: MinimapPoint[];
  /** Killer -> victim trajectories. */
  lines?: Array<{ from: Point; to: Point; team?: "a" | "b" }>;
  /** Routes (e.g. probable enemy path in the Action Plan). */
  routes?: Array<{ points: Point[]; color?: string }>;
  onPointClick?: (index: number) => void;
}

const HEAT_RGB = { red: "255,59,82", cyan: "46,230,208", amber: "255,181,71" } as const;

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
          ctx.fillStyle = `rgba(${HEAT_RGB[color]},${v * opacity})`;
          ctx.fillRect(c * cell, r * cell, cell, cell);
        }),
      );
    }
    for (const l of lines) {
      ctx.strokeStyle = l.team === "b" ? "#5b8def" : "#ff3b52";
      ctx.beginPath();
      ctx.moveTo(l.from.x * size, l.from.y * size);
      ctx.lineTo(l.to.x * size, l.to.y * size);
      ctx.stroke();
    }
    for (const r of routes) {
      ctx.strokeStyle = r.color ?? "#ffb547";
      ctx.beginPath();
      r.points.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x * size, p.y * size) : ctx.lineTo(p.x * size, p.y * size)));
      ctx.stroke();
    }
    for (const p of points) {
      ctx.fillStyle = p.kind === "plant" ? "#ffb547" : p.team === "b" ? "#5b8def" : "#ff3b52";
      ctx.beginPath();
      ctx.arc(p.point.x * size, p.point.y * size, 5, 0, Math.PI * 2);
      ctx.fill();
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
    <div className="relative" style={{ width: size, height: size }}>
      <img src={map.minimap_url} alt={`Minimapa de ${map.name}`} width={size} height={size} className="absolute inset-0" />
      <canvas ref={ref} width={size} height={size} className="absolute inset-0" />
    </div>
  );
}

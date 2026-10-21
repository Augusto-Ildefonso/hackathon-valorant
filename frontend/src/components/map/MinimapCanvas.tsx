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
  /** Routes (e.g. probable enemy path in the Action Plan). Stream D additions: arrow head, dashes, width and a label
   *  (`leader`: the label goes to a tidy column on the right joined to the route start by a thin line). */
  routes?: Array<{ points: Point[]; color?: string; arrow?: boolean; dashed?: boolean; width?: number; label?: string; leader?: boolean }>;
  /** Dashed translucent boxes with a label (Action Plan zones): `box` = [x0, y0, x1, y1] in 0..1. */
  boxes?: Array<{ box: number[]; color: string; label?: string; below?: boolean }>;
  onPointClick?: (index: number) => void;
  /** Optional (Stream C): draws dashed, labelled boxes ("DESCOBERTA n") around the strongest blobs of this layer. */
  zoneLayer?: HeatLayer | null;
}

/** Connected blobs of cells above `threshold` -> bounding boxes in 0..1, strongest first. */
export function findZones(layer: HeatLayer, threshold = 0.3, minCells = 5, max = 3) {
  const g = layer.grid, n = g.length;
  const seen = Array.from({ length: n }, () => new Array<boolean>(n).fill(false));
  const zones: Array<{ x0: number; y0: number; x1: number; y1: number; weight: number }> = [];
  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      if (seen[r][c] || g[r][c] < threshold) continue;
      const stack = [[r, c]];
      seen[r][c] = true;
      let cells = 0, weight = 0, r0 = r, r1 = r, c0 = c, c1 = c;
      while (stack.length) {
        const [y, x] = stack.pop()!;
        cells++; weight += g[y][x];
        r0 = Math.min(r0, y); r1 = Math.max(r1, y); c0 = Math.min(c0, x); c1 = Math.max(c1, x);
        for (const [dy, dx] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const ny = y + dy, nx = x + dx;
          if (ny >= 0 && ny < n && nx >= 0 && nx < n && !seen[ny][nx] && g[ny][nx] >= threshold) { seen[ny][nx] = true; stack.push([ny, nx]); }
        }
      }
      if (cells >= minCells) zones.push({ x0: c0 / n, y0: r0 / n, x1: (c1 + 1) / n, y1: (r1 + 1) / n, weight });
    }
  }
  return zones.sort((a, b) => b.weight - a.weight).slice(0, max);
}

const TEAM_A = "#2ee6d0"; // Figma Match Report: team A cyan, team B amber
const TEAM_B = "#ffb547";
const HEAT_RGB = { red: "255,59,82", cyan: "46,230,208", amber: "255,181,71", green: "61,220,132", violet: "160,123,255" } as const;

/** Small dark label with a coloured outline (readable over any part of the minimap). Returns its width. */
function pill(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, color: string): number {
  ctx.font = "500 10px Inter, sans-serif";
  const w = ctx.measureText(text).width + 12, h = 16;
  ctx.fillStyle = "rgba(7,9,13,0.82)";
  ctx.strokeStyle = color;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, 3);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = color;
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.fillText(text, x + 6, y + h / 2 + 0.5);
  return w;
}

function arrowHead(ctx: CanvasRenderingContext2D, a: Point, b: Point, size: number, color: string) {
  const ang = Math.atan2(b.y - a.y, b.x - a.x);
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(b.x * size, b.y * size);
  ctx.lineTo(b.x * size - 11 * Math.cos(ang - 0.45), b.y * size - 11 * Math.sin(ang - 0.45));
  ctx.lineTo(b.x * size - 11 * Math.cos(ang + 0.45), b.y * size - 11 * Math.sin(ang + 0.45));
  ctx.closePath();
  ctx.fill();
}

export function MinimapCanvas({ map, size = 640, heat = [], points = [], lines = [], routes = [], boxes = [], zoneLayer = null }: MinimapProps) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const ctx = ref.current?.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, size, size);
    for (const { layer, color = "red", opacity = 0.7 } of heat) {
      // draw the n x n grid into a tiny canvas, then scale it up smoothed and blurred (no visible blocks)
      const n = layer.grid.length;
      // The max-normalized grid is dominated by a few hot cells; rescale to its 95th percentile and apply a gamma
      // curve so medium-density areas are visible too.
      const vals = layer.grid.flat().filter((v) => v > 0).sort((a, b) => a - b);
      const p95 = vals.length ? vals[Math.floor(vals.length * 0.95)] || 1 : 1;
      const off = document.createElement("canvas");
      off.width = off.height = n;
      const octx = off.getContext("2d")!;
      layer.grid.forEach((row, r) =>
        row.forEach((v, c) => {
          if (v <= 0) return;
          const a = Math.pow(Math.min(1, v / p95), 0.8) * opacity;
          octx.fillStyle = `rgba(${HEAT_RGB[color]},${a})`;
          octx.fillRect(c, r, 1, 1);
        }),
      );
      ctx.save();
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = "high";
      ctx.filter = `blur(${Math.max(2, size / 150)}px)`;
      ctx.drawImage(off, 0, 0, size, size);
      ctx.restore();
    }
    if (zoneLayer) {
      findZones(zoneLayer).forEach((z, i) => {
        const x = z.x0 * size, y = z.y0 * size, w = (z.x1 - z.x0) * size, h = (z.y1 - z.y0) * size;
        ctx.strokeStyle = "#2ee6d0";
        ctx.lineWidth = 1.5;
        ctx.setLineDash([6, 4]);
        ctx.strokeRect(x, y, w, h);
        ctx.setLineDash([]);
        ctx.fillStyle = "#2ee6d0";
        ctx.font = "600 10px 'Chakra Petch', sans-serif";
        ctx.textAlign = "left";
        ctx.textBaseline = "top";
        ctx.fillText(`DESCOBERTA ${i + 1}`, x + 6, y + 5);
        ctx.lineWidth = 1;
      });
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
    for (const b of boxes) {  // zones under the routes
      const [x0, y0, x1, y1] = b.box;
      ctx.fillStyle = `${b.color}1f`;
      ctx.fillRect(x0 * size, y0 * size, (x1 - x0) * size, (y1 - y0) * size);
      ctx.strokeStyle = b.color;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 4]);
      ctx.strokeRect(x0 * size, y0 * size, (x1 - x0) * size, (y1 - y0) * size);
      ctx.setLineDash([]);
      ctx.lineWidth = 1;
    }
    for (const r of routes) {
      const color = r.color ?? "#ffb547";
      ctx.strokeStyle = color;
      ctx.lineWidth = r.width ?? 2;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.setLineDash(r.dashed ? [7, 5] : []);
      ctx.beginPath();
      r.points.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x * size, p.y * size) : ctx.lineTo(p.x * size, p.y * size)));
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.lineWidth = 1;
      if (r.arrow && r.points.length > 1) arrowHead(ctx, r.points[r.points.length - 2], r.points[r.points.length - 1], size, color);
    }
    // route labels: leader labels share a column on the right of the arrow starts, the others sit next to their start
    const leaders = routes.filter((r) => r.label && r.leader && r.points.length).sort((a, b) => a.points[0].y - b.points[0].y);
    if (leaders.length) {
      ctx.font = "500 10px Inter, sans-serif";
      const widest = Math.max(...leaders.map((r) => ctx.measureText(r.label!).width + 12));
      const colX = Math.min(Math.max(...leaders.map((r) => r.points[0].x * size)) + 50, size - widest - 4);
      let y = Math.max(4, leaders[0].points[0].y * size - 30);
      for (const r of leaders) {
        const color = r.color ?? "#2ee6d0";
        ctx.strokeStyle = `${color}8c`;
        ctx.beginPath();
        ctx.moveTo(r.points[0].x * size, r.points[0].y * size);
        ctx.lineTo(colX, y + 8);
        ctx.stroke();
        pill(ctx, r.label!, colX, y, color);
        y += 24;
      }
    }
    for (const r of routes) {
      if (r.label && !r.leader && r.points.length) pill(ctx, r.label, r.points[0].x * size + 6, Math.max(2, r.points[0].y * size - 22), r.color ?? "#ffb547");
    }
    for (const b of boxes) {
      if (b.label) {
        ctx.font = "500 10px Inter, sans-serif";
        const w = ctx.measureText(b.label).width + 12;
        const y = b.below ? Math.min(b.box[3] * size + 4, size - 18) : Math.max(2, b.box[1] * size - 22);
        pill(ctx, b.label, Math.max(2, Math.min(b.box[0] * size, size - w - 2)), y, b.color);
      }
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
  }, [heat, points, lines, routes, boxes, size, zoneLayer]);

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
      <img
        src={map.minimap_url}
        alt={`Minimapa de ${map.name}`}
        width={size}
        height={size}
        className="absolute inset-0"
        style={heat.length ? { filter: "brightness(0.55)" } : undefined} /* dim the map so the heat stands out */
      />
      <canvas ref={ref} width={size} height={size} className="absolute inset-0" />
    </div>
  );
}

// Catalog pictures next to names (Figma: agents 24px tile, weapons ~40x16 silhouette, maps 44x20 banner). Owner: Stream E.
// URLs come from the API (small cached thumbnails); unknown items or failed loads show a neutral "?" tile.
// Props of AgentIcon/WeaponIcon are frozen; MapIcon and CatalogIcon are additions.
import { useState } from "react";
import type { AgentRef, MapRef, WeaponRef } from "@/api/types";

type Kind = "agent" | "weapon" | "map";

const RADIUS = { agent: "rounded-sm", weapon: "", map: "rounded-sm" } as const;

/** Generic picture slot. `url` null/failed => neutral tile with "?". */
export function CatalogIcon({ url, name, kind, w, h }: { url?: string | null; name: string; kind: Kind; w: number; h: number }) {
  const [failed, setFailed] = useState(false);
  const base = `shrink-0 ${RADIUS[kind]}`;
  if (!url || failed) {
    return (
      <span style={{ width: w, height: h }} className={`${base} inline-flex items-center justify-center bg-surface-raised text-[10px] text-fg-muted`} title={name} aria-label={name}>
        {kind === "weapon" ? "" : "?"}
      </span>
    );
  }
  return (
    <img
      src={url}
      alt={name}
      title={name}
      width={w}
      height={h}
      loading="lazy"
      onError={() => setFailed(true)}
      style={{ width: w, height: h, ...(kind === "weapon" ? { filter: "brightness(2.4) contrast(1.1)" } : {}) }}
      className={`${base} ${kind === "weapon" ? "object-contain" : "bg-surface-raised object-cover"}`}
    />
  );
}

interface IconProps {
  size?: number;
  showName?: boolean;
}

export function AgentIcon({ agent, size = 24, showName = false }: IconProps & { agent: AgentRef | null }) {
  const name = agent?.name ?? "Agente desconhecido";
  return (
    <span className="inline-flex items-center gap-2" title={agent?.name_inferred ? `${name} (inferido)` : name}>
      <CatalogIcon url={agent?.icon_url} name={name} kind="agent" w={size} h={size} />
      {showName && <span className="truncate">{name}</span>}
    </span>
  );
}

/** `size` is the picture height; the width follows the silhouette ratio (2.5:1). */
export function WeaponIcon({ weapon, size = 16, showName = false }: IconProps & { weapon: WeaponRef | null }) {
  const name = weapon?.name ?? "Arma desconhecida";
  return (
    <span className="inline-flex items-center gap-2" title={weapon?.name_inferred ? `${name} (inferido)` : name}>
      <CatalogIcon url={weapon?.icon_url} name={name} kind="weapon" w={Math.round(size * 2.5)} h={size} />
      {showName && <span className="truncate">{name}</span>}
    </span>
  );
}

export function MapIcon({ map, w = 44, h = 20, showName = false }: { map: MapRef; w?: number; h?: number; showName?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2" title={map.name}>
      <CatalogIcon url={map.thumb_url} name={map.name} kind="map" w={w} h={h} />
      {showName && <span className="truncate">{map.name}</span>}
    </span>
  );
}

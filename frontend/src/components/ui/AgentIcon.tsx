// Agent / weapon icons from the catalog (URLs come from the API). Owner: Stream E. Props are frozen.
import type { AgentRef, WeaponRef } from "@/api/types";

interface IconProps {
  size?: number;
  showName?: boolean;
}

export function AgentIcon({ agent, size = 32, showName = false }: IconProps & { agent: AgentRef | null }) {
  const name = agent?.name ?? "Agente desconhecido";
  return (
    <span className="inline-flex items-center gap-2" title={agent?.name_inferred ? `${name} (inferido)` : name}>
      {agent?.icon_url ? (
        <img src={agent.icon_url} alt={name} width={size} height={size} className="rounded-sm bg-surface-raised" />
      ) : (
        <span style={{ width: size, height: size }} className="inline-flex items-center justify-center rounded-sm bg-surface-raised text-fg-muted">?</span>
      )}
      {showName && <span className="text-sm">{name}</span>}
    </span>
  );
}

export function WeaponIcon({ weapon, size = 32, showName = false }: IconProps & { weapon: WeaponRef | null }) {
  const name = weapon?.name ?? "Arma desconhecida";
  return (
    <span className="inline-flex items-center gap-2" title={weapon?.name_inferred ? `${name} (inferido)` : name}>
      {weapon?.icon_url ? (
        <img src={weapon.icon_url} alt={name} height={size} style={{ height: size }} className="bg-transparent" />
      ) : (
        <span style={{ height: size }} className="inline-flex items-center px-2 text-fg-muted">?</span>
      )}
      {showName && <span className="text-sm">{name}</span>}
    </span>
  );
}

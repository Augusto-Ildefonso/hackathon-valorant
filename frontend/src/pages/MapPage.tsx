// Stub. Owner: Stream C.
import { useParams } from "react-router-dom";
import { useHeatmap, useMap } from "@/api/hooks";
import { MinimapCanvas } from "@/components/map/MinimapCanvas";
import { PageHeader } from "@/components/ui/PageHeader";

export default function MapPage() {
  const { mapName = "" } = useParams();
  const { data, isLoading, error } = useMap(mapName);
  const heat = useHeatmap(mapName);
  return (
    <>
      <PageHeader title={data?.map.name ?? mapName} subtitle="Perfil do mapa (em construção)" />
      {isLoading && <p className="text-fg-muted">Carregando…</p>}
      {error && <p className="text-accent">Erro: {String(error)}</p>}
      {data && (
        <MinimapCanvas
          map={data.map}
          size={480}
          heat={heat.data?.deaths ? [{ layer: heat.data.deaths, color: "red" }] : []}
          points={data.plants.map((p) => ({ point: p.point, kind: "plant" as const, label: p.site }))}
        />
      )}
    </>
  );
}

import { useEffect, useState } from "react";
import { buildCapability, getCapabilityGraph, listDocuments } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import type { CapabilityEntityType, CapabilityGraphResponse, DocumentRead } from "../api/types";
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  Select,
  SkeletonList,
  StatCard,
} from "../components/kit";
import { AIProcessing } from "../components/kit";
import { Award, Users, Briefcase, Wrench, Landmark, Layers, type LucideIcon } from "lucide-react";

const ENTITY_TYPES: CapabilityEntityType[] = ["certification", "employee", "project", "equipment", "financial_record"];

const BUILD_STAGES = ["Reading document…", "Extracting structured entities…", "Validating confidence…", "Saving to capability library…"];

export default function Capabilities() {
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [graph, setGraph] = useState<CapabilityGraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [building, setBuilding] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<Record<string, CapabilityEntityType>>({});
  const { notify } = useToast();

  const refresh = async () => {
    setLoading(true);
    try {
      const [docs, capGraph] = await Promise.all([listDocuments(), getCapabilityGraph()]);
      setDocuments(docs);
      setGraph(capGraph);
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleBuild = async (documentId: string, fileName: string) => {
    const entityType = selectedType[documentId] ?? ENTITY_TYPES[0];
    setBuilding(documentId);
    try {
      await buildCapability(documentId, entityType);
      notify("success", `Capabilities extracted from ${fileName}.`);
      await refresh();
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setBuilding(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Capability Library</h1>
        <p className="text-sm text-muted-foreground mt-1">
          AI-extracted certifications, personnel, projects, equipment, and financials.
        </p>
      </div>

      <Card>
        <CardHeader title="Build Capabilities" description="Run extraction on an uploaded document" />
        <CardBody>
          {loading ? (
            <SkeletonList rows={2} />
          ) : documents.length === 0 ? (
            <EmptyState icon={Layers} title="No documents yet" description="Upload a document on the Documents page first." />
          ) : building ? (
            <AIProcessing stages={BUILD_STAGES} />
          ) : (
            <ul className="divide-y divide-border -mx-6">
              {documents.map((d) => (
                <li key={d.id} className="px-6 py-3 flex flex-wrap items-center justify-between gap-3">
                  <span className="text-sm font-medium truncate min-w-0">{d.file_name}</span>
                  <div className="flex items-center gap-2 shrink-0 flex-wrap">
                    <Select
                      value={selectedType[d.id] ?? ENTITY_TYPES[0]}
                      onChange={(e) =>
                        setSelectedType((prev) => ({ ...prev, [d.id]: e.target.value as CapabilityEntityType }))
                      }
                      className="!py-1.5 text-xs"
                    >
                      {ENTITY_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t.replace(/_/g, " ")}
                        </option>
                      ))}
                    </Select>
                    <Button size="sm" onClick={() => handleBuild(d.id, d.file_name)}>
                      Build Capabilities
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-surface border border-border rounded-lg p-5 h-24" />
          ))}
        </div>
      ) : graph ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Total" value={graph.summary.total_entities} icon={<Layers size={16} />} tone="primary" />
            <StatCard label="Current" value={graph.summary.total_current} icon={<Award size={16} />} tone="success" />
            <StatCard label="Stale" value={graph.summary.total_stale} icon={<Wrench size={16} />} tone="warning" />
            <StatCard label="Expired" value={graph.summary.total_expired} icon={<Landmark size={16} />} tone="danger" />
          </div>

          <EntitySection icon={Award} title="Certifications" empty={graph.certifications.length === 0}>
            {graph.certifications.map((c) => (
              <li key={c.id} className="py-3 text-sm flex items-center justify-between">
                <span>
                  {c.certification_name}
                  {c.issuing_authority && <span className="text-muted-foreground"> — {c.issuing_authority}</span>}
                </span>
                <Badge value={c.freshness_status} />
              </li>
            ))}
          </EntitySection>

          <EntitySection icon={Users} title="Employees" empty={graph.employees.length === 0}>
            {graph.employees.map((e) => (
              <li key={e.id} className="py-3 text-sm">
                <div className="flex items-center justify-between">
                  <span>
                    {e.name}
                    {e.position && <span className="text-muted-foreground"> — {e.position}</span>}
                  </span>
                  <Badge value={e.freshness_status} />
                </div>
                {e.skills && <p className="text-xs text-muted-foreground mt-1">{e.skills.join(" · ")}</p>}
              </li>
            ))}
          </EntitySection>

          <EntitySection icon={Briefcase} title="Projects" empty={graph.projects.length === 0}>
            {graph.projects.map((p) => (
              <li key={p.id} className="py-3 text-sm flex items-center justify-between">
                <span>
                  {p.client ?? "Unnamed client"}
                  {p.industry && <span className="text-muted-foreground"> — {p.industry}</span>}
                </span>
                <Badge value={p.freshness_status} />
              </li>
            ))}
          </EntitySection>

          <EntitySection icon={Wrench} title="Equipment" empty={graph.equipment.length === 0}>
            {graph.equipment.map((eq) => (
              <li key={eq.id} className="py-3 text-sm flex items-center justify-between">
                <span>{eq.equipment_name}</span>
                <Badge value={eq.freshness_status} />
              </li>
            ))}
          </EntitySection>

          <EntitySection icon={Landmark} title="Financial Records" empty={graph.financial_records.length === 0}>
            {graph.financial_records.map((f) => (
              <li key={f.id} className="py-3 text-sm flex items-center justify-between">
                <span>{f.financial_year ?? "—"}</span>
                <Badge value={f.freshness_status} />
              </li>
            ))}
          </EntitySection>
        </>
      ) : null}
    </div>
  );
}

function EntitySection({
  icon: Icon,
  title,
  empty,
  children,
}: {
  icon: LucideIcon;
  title: string;
  empty: boolean;
  children: React.ReactNode;
}) {
  if (empty) return null;
  return (
    <Card>
      <CardHeader title={<span className="flex items-center gap-2"><Icon size={14} className="text-muted-foreground" />{title}</span>} />
      <CardBody className="!py-1">
        <ul className="divide-y divide-border">{children}</ul>
      </CardBody>
    </Card>
  );
}

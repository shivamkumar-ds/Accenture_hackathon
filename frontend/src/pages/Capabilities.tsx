import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { buildCapability, deleteCapability, getCapabilityGraph, listDocuments } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";
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
import { Award, Users, Briefcase, Wrench, Landmark, Layers, Trash2, type LucideIcon } from "lucide-react";

const ENTITY_TYPES: CapabilityEntityType[] = ["certification", "employee", "project", "equipment", "financial_record"];

const BUILD_STAGES = ["Reading document…", "Extracting structured entities…", "Validating confidence…", "Saving to capability library…"];

export default function Capabilities() {
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [graph, setGraph] = useState<CapabilityGraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [building, setBuilding] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<Record<string, CapabilityEntityType>>({});
  const { notify } = useToast();
  const { user } = useAuth();
  // DELETE /capabilities/{id} is admin-only server-side (require_administrator)
  // -- hiding the button for non-admins avoids a confusing 403 on click,
  // it's not a real access-control boundary (the backend still enforces it).
  const canDeleteCapabilities = user?.role === "administrator";

  // One document, one-time capability: a document that already has a live
  // (non-removed) capability entity built from it, regardless of type,
  // can't be built again until that entity is deleted (backend enforces
  // this with a 409; this Set drives the matching UI state so the Build
  // button doesn't even offer an action that will just fail).
  const builtDocumentIds = useMemo(() => {
    if (!graph) return new Set<string>();
    const allEntities = [
      ...graph.certifications,
      ...graph.employees,
      ...graph.projects,
      ...graph.equipment,
      ...graph.financial_records,
    ];
    return new Set(allEntities.filter((e) => e.source_document_id).map((e) => e.source_document_id as string));
  }, [graph]);

  // Real preview text per document -- one document produces exactly one
  // capability entity (the "one document, one-time" rule above), so this
  // isn't pulling multiple separate records; it's the entity's own real
  // multi-value fields (an employee's skills, a project's similarity
  // tags) plus its name/label, so a document with only a single-value
  // entity (certification/equipment/financial record) honestly shows
  // just the one line rather than inventing extra items.
  const previewsByDocument = useMemo(() => {
    const map = new Map<string, string[]>();
    if (!graph) return map;
    const add = (docId: string | null, items: (string | null | undefined)[]) => {
      if (!docId) return;
      map.set(docId, items.filter((v): v is string => Boolean(v && v.trim())));
    };
    graph.certifications.forEach((c) => add(c.source_document_id, [c.certification_name, c.issuing_authority]));
    graph.employees.forEach((e) => add(e.source_document_id, [e.name, ...(e.skills ?? [])]));
    graph.projects.forEach((p) => add(p.source_document_id, [p.client ?? "Unnamed client", ...(p.similarity_tags ?? [])]));
    graph.equipment.forEach((eq) => add(eq.source_document_id, [eq.equipment_name]));
    graph.financial_records.forEach((f) => add(f.source_document_id, [f.financial_year ? `FY ${f.financial_year}` : null]));
    return map;
  }, [graph]);

  const refresh = async () => {
    setLoading(true);
    try {
      const [docs, capGraph] = await Promise.all([listDocuments(), getCapabilityGraph()]);
      // Capability Library only builds from company documents (certifications,
      // resumes, project/equipment/financial records) -- tender documents go
      // through a separate upload flow (document_type "tender", set only by
      // TenderUpload.tsx/tender_service.upload_tender) and were never meant
      // to be extractable as capability evidence. listDocuments() returns
      // every company document with no type filter, so this page has to
      // exclude tenders itself.
      setDocuments(docs.filter((d) => d.document_type !== "tender"));
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

  const handleRemoveCapability = async (entityId: string, label: string) => {
    if (!confirm(`Delete "${label}" from the capability library? Any mission currently citing it as evidence will be re-evaluated.`)) {
      return;
    }
    setRemovingId(entityId);
    try {
      await deleteCapability(entityId);
      notify("success", `"${label}" removed.`);
      await refresh();
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setRemovingId(null);
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
            <EmptyState
              icon={Layers}
              title="No documents yet"
              description="Upload a document on the Documents page first."
              action={
                <Link to="/documents" className="text-sm font-medium text-primary hover:underline">
                  Go to Documents →
                </Link>
              }
            />
          ) : building ? (
            <AIProcessing stages={BUILD_STAGES} />
          ) : (
            <ul className="divide-y divide-border -mx-6">
              {documents.map((d) => {
                // One document, one-time capability -- once this document
                // has a live capability entity, Build is replaced with a
                // status hint instead of an action that would just 409.
                // Deleting the entity below (Certifications/Employees/etc.
                // section) frees the document up to be rebuilt.
                const alreadyBuilt = builtDocumentIds.has(d.id);
                const preview = previewsByDocument.get(d.id) ?? [];
                const shown = preview.slice(0, 4);
                const extra = preview.length - shown.length;
                return (
                  <li key={d.id} className="px-6 py-3 flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <span className="text-sm font-medium truncate block">{d.file_name}</span>
                      {alreadyBuilt && shown.length > 0 && (
                        <ul className="mt-1.5 space-y-0.5">
                          {shown.map((item, i) => (
                            <li key={i} className="text-xs text-muted-foreground truncate">
                              • {item}
                            </li>
                          ))}
                          {extra > 0 && <li className="text-xs text-muted-foreground/70">+{extra} more</li>}
                        </ul>
                      )}
                    </div>
                    {alreadyBuilt ? (
                      <span className="text-xs text-muted-foreground shrink-0">
                        Capabilities built — delete below to rebuild
                      </span>
                    ) : (
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
                    )}
                  </li>
                );
              })}
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
              <li key={c.id} className="py-3 text-sm flex items-center justify-between gap-3">
                <span className="min-w-0 truncate">
                  {c.certification_name}
                  {c.issuing_authority && <span className="text-muted-foreground"> — {c.issuing_authority}</span>}
                </span>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge value={c.freshness_status} />
                  {canDeleteCapabilities && (
                    <DeleteEntityButton
                      loading={removingId === c.id}
                      onClick={() => handleRemoveCapability(c.id, c.certification_name)}
                    />
                  )}
                </div>
              </li>
            ))}
          </EntitySection>

          <EntitySection icon={Users} title="Employees" empty={graph.employees.length === 0}>
            {graph.employees.map((e) => (
              <li key={e.id} className="py-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="min-w-0 truncate">
                    {e.name}
                    {e.position && <span className="text-muted-foreground"> — {e.position}</span>}
                  </span>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge value={e.freshness_status} />
                    {canDeleteCapabilities && (
                      <DeleteEntityButton loading={removingId === e.id} onClick={() => handleRemoveCapability(e.id, e.name)} />
                    )}
                  </div>
                </div>
                {e.skills && <p className="text-xs text-muted-foreground mt-1">{e.skills.join(" · ")}</p>}
              </li>
            ))}
          </EntitySection>

          <EntitySection icon={Briefcase} title="Projects" empty={graph.projects.length === 0}>
            {graph.projects.map((p) => (
              <li key={p.id} className="py-3 text-sm flex items-center justify-between gap-3">
                <span className="min-w-0 truncate">
                  {p.client ?? "Unnamed client"}
                  {p.industry && <span className="text-muted-foreground"> — {p.industry}</span>}
                </span>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge value={p.freshness_status} />
                  {canDeleteCapabilities && (
                    <DeleteEntityButton
                      loading={removingId === p.id}
                      onClick={() => handleRemoveCapability(p.id, p.client ?? "Unnamed client")}
                    />
                  )}
                </div>
              </li>
            ))}
          </EntitySection>

          <EntitySection icon={Wrench} title="Equipment" empty={graph.equipment.length === 0}>
            {graph.equipment.map((eq) => (
              <li key={eq.id} className="py-3 text-sm flex items-center justify-between gap-3">
                <span className="min-w-0 truncate">{eq.equipment_name}</span>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge value={eq.freshness_status} />
                  {canDeleteCapabilities && (
                    <DeleteEntityButton
                      loading={removingId === eq.id}
                      onClick={() => handleRemoveCapability(eq.id, eq.equipment_name)}
                    />
                  )}
                </div>
              </li>
            ))}
          </EntitySection>

          <EntitySection icon={Landmark} title="Financial Records" empty={graph.financial_records.length === 0}>
            {graph.financial_records.map((f) => (
              <li key={f.id} className="py-3 text-sm flex items-center justify-between gap-3">
                <span className="min-w-0 truncate">{f.financial_year ?? "—"}</span>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge value={f.freshness_status} />
                  {canDeleteCapabilities && (
                    <DeleteEntityButton
                      loading={removingId === f.id}
                      onClick={() => handleRemoveCapability(f.id, `${f.financial_year ?? "record"} financial record`)}
                    />
                  )}
                </div>
              </li>
            ))}
          </EntitySection>
        </>
      ) : null}
    </div>
  );
}

function DeleteEntityButton({ onClick, loading }: { onClick: () => void; loading: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="w-6 h-6 rounded-md flex items-center justify-center text-muted-foreground hover:bg-danger-soft hover:text-danger transition-colors disabled:opacity-50"
      aria-label="Delete capability entry"
    >
      <Trash2 size={13} />
    </button>
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

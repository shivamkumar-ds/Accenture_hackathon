import { useEffect, useMemo, useState } from "react";
import { deleteDocument, listDocuments, uploadDocument } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import type { DocumentRead } from "../api/types";
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  Dropzone,
  EmptyState,
  LiveClock,
  Select,
  SearchInput,
  SkeletonList,
  StatCard,
} from "../components/kit";
import { CheckCircle2, Clock3, FileStack, Trash2, XCircle } from "lucide-react";

const DOCUMENT_TYPES = [
  "certification",
  "employee_resume",
  "project_record",
  "equipment_record",
  "financial_record",
  "other",
];

export default function Documents() {
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState(DOCUMENT_TYPES[0]);
  const [query, setQuery] = useState("");
  const [lastSynced, setLastSynced] = useState<Date | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const { notify } = useToast();

  const refresh = async () => {
    setLoading(true);
    try {
      // This page is "Company Documents" specifically (see the header copy
      // below) -- tender documents (document_type "tender", uploaded via
      // the separate New Tender flow) aren't company capability evidence
      // and shouldn't appear here, same reasoning as the Capability
      // Library's own document list. listDocuments() has no type filter,
      // so it's applied client-side.
      const docs = await listDocuments();
      setDocuments(docs.filter((d) => d.document_type !== "tender"));
      setLastSynced(new Date());
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

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    try {
      await uploadDocument(file, documentType);
      notify("success", `${file.name} uploaded successfully.`);
      setFile(null);
      await refresh();
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (documentId: string, fileName: string) => {
    if (!confirm(`Delete "${fileName}"? This removes the file and can't be undone.`)) return;
    setDeletingId(documentId);
    try {
      await deleteDocument(documentId);
      notify("success", `"${fileName}" deleted.`);
      await refresh();
    } catch (err) {
      // 409 here means an active tender or a built capability still
      // references this document -- extractErrorMessage() surfaces the
      // backend's exact reason (e.g. "delete the tender first").
      notify("error", extractErrorMessage(err));
    } finally {
      setDeletingId(null);
    }
  };

  const filtered = useMemo(
    () => documents.filter((d) => d.file_name.toLowerCase().includes(query.toLowerCase())),
    [documents, query]
  );

  const counts = useMemo(
    () => ({
      completed: documents.filter((d) => d.processing_status === "completed").length,
      pending: documents.filter((d) => d.processing_status === "pending" || d.processing_status === "processing").length,
      failed: documents.filter((d) => d.processing_status === "failed").length,
    }),
    [documents]
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Company Documents</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Upload certifications, resumes, and project records to build your capability library.
        </p>
      </div>

      {!loading && documents.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard label="Total" value={documents.length} icon={<FileStack size={16} />} tone="neutral" />
          <StatCard label="Completed" value={counts.completed} icon={<CheckCircle2 size={16} />} tone="success" />
          <StatCard label="Pending" value={counts.pending} icon={<Clock3 size={16} />} tone="warning" />
          <StatCard label="Failed" value={counts.failed} icon={<XCircle size={16} />} tone={counts.failed > 0 ? "warning" : "neutral"} />
        </div>
      )}

      <Card>
        <CardHeader title="Upload Document" />
        <CardBody>
          <form onSubmit={handleUpload} className="flex flex-col sm:flex-row sm:items-end gap-4">
            <div className="sm:w-56 shrink-0">
              <Select label="Document Type" className="h-11" value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
                {DOCUMENT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.replace(/_/g, " ")}
                  </option>
                ))}
              </Select>
            </div>
            <div className="flex-1 min-w-0">
              <Dropzone compact file={file} onFileSelected={setFile} className="h-11" />
            </div>
            <Button type="submit" loading={uploading} disabled={!file} size="lg" className="w-full sm:w-auto shrink-0">
              Upload Document
            </Button>
          </form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Uploaded Documents"
          description={
            lastSynced ? (
              <span className="inline-flex items-center gap-1">
                Synced as of <LiveClock showDate={false} className="text-xs" />
              </span>
            ) : undefined
          }
          action={<SearchInput value={query} onChange={setQuery} placeholder="Search documents…" />}
        />
        <CardBody className="!px-0 sm:!px-6">
          {loading ? (
            <div className="px-6">
              <SkeletonList rows={4} />
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={FileStack}
              title={documents.length === 0 ? "No documents yet" : "No matches"}
              description={
                documents.length === 0
                  ? "Upload your first document above to get started."
                  : "Try a different search term."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[640px]">
                <thead>
                  <tr className="text-left text-xs text-muted-foreground uppercase tracking-wide border-b border-border">
                    <th className="py-2 px-6 font-medium">File</th>
                    <th className="py-2 px-6 font-medium">Type</th>
                    <th className="py-2 px-6 font-medium">Status</th>
                    <th className="py-2 px-6 font-medium">Uploaded</th>
                    <th className="py-2 px-6 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filtered.map((d) => (
                    <tr key={d.id} className="hover:bg-surface-hover transition-colors">
                      <td className="py-3 px-6 font-medium">{d.file_name}</td>
                      <td className="py-3 px-6 text-muted-foreground">{d.document_type.replace(/_/g, " ")}</td>
                      <td className="py-3 px-6">
                        <Badge value={d.processing_status} />
                      </td>
                      <td className="py-3 px-6 text-muted-foreground tabular-nums whitespace-nowrap">
                        {new Date(d.upload_time).toLocaleString()}
                      </td>
                      <td className="py-3 px-6">
                        <div className="flex justify-end">
                          <button
                            type="button"
                            onClick={() => handleDelete(d.id, d.file_name)}
                            disabled={deletingId === d.id}
                            className="w-7 h-7 rounded-md flex items-center justify-center text-muted-foreground hover:bg-danger-soft hover:text-danger transition-colors disabled:opacity-50"
                            aria-label={`Delete ${d.file_name}`}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

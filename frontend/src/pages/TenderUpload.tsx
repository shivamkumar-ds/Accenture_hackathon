import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { addTenderDocument, extractTenderMetadata, uploadTender } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import { Button, Card, CardBody, CardHeader, Combobox, Dropzone, Input } from "../components/kit";
import { TENDER_CATEGORIES } from "../lib/tenderCategories";
import { FileText, Plus, X } from "lucide-react";
import { cn } from "../lib/cn";

// Additional tender documents (technical bid detail, financial BOQ,
// supporting annexures) -- the same set the backend's multi-document
// Tender support (Bug #007) already accepts via storage.ALLOWED_EXTENSIONS
// for tender uploads. Intentionally narrower here than the full backend
// allowlist (which also covers .docx/.png/.jpg for other document types) --
// a real tender's supporting files are PDFs and spreadsheets, not images.
const ADDITIONAL_FILE_EXTENSIONS = [".pdf", ".xls", ".xlsx"];
const ADDITIONAL_FILE_ACCEPT = ADDITIONAL_FILE_EXTENSIONS.join(",");

function fileExtension(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot === -1 ? "" : name.slice(dot).toLowerCase();
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Compact file-preview row -- shared by the primary document (once
// selected) and every additional document row, so both look like the
// same "this file is attached" affordance rather than two different
// visual languages. `bare` drops the row's own border/radius/background
// for use inside a single divided list container (additional documents);
// without it, the row is a standalone bordered card (primary document).
function FileRow({
  file,
  onRemove,
  disabled,
  bare = false,
}: {
  file: File;
  onRemove: () => void;
  disabled?: boolean;
  bare?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-2.5 px-3 py-2.5",
        !bare && "rounded-lg border border-border bg-muted/60"
      )}
    >
      <div className="w-6 h-6 rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0">
        <FileText size={12} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium truncate">{file.name}</p>
      </div>
      <span className="text-[11px] text-muted-foreground shrink-0 tabular-nums">{formatBytes(file.size)}</span>
      <button
        type="button"
        onClick={onRemove}
        disabled={disabled}
        className="text-muted-foreground hover:text-danger transition shrink-0 disabled:opacity-50"
        aria-label={`Remove ${file.name}`}
      >
        <X size={14} />
      </button>
    </div>
  );
}

export default function TenderUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [additionalFiles, setAdditionalFiles] = useState<File[]>([]);
  const [additionalFilesError, setAdditionalFilesError] = useState<string | null>(null);
  const [tenderName, setTenderName] = useState("");
  const [organization, setOrganization] = useState("");
  const [category, setCategory] = useState("");
  const [closingDate, setClosingDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [extracting, setExtracting] = useState(false);
  const { notify } = useToast();
  const navigate = useNavigate();
  const additionalFileInputRef = useRef<HTMLInputElement>(null);

  // All five primary fields are mandatory -- the Upload Tender button
  // stays disabled until every one of them is filled in. Additional
  // documents are always optional -- a single-PDF tender must keep
  // working exactly as before this feature existed.
  const isComplete = Boolean(file && tenderName.trim() && organization.trim() && category && closingDate);

  // Best-effort prefill from the primary PDF's own text -- heuristic-only,
  // never overwrites anything the user already typed, and silently no-ops
  // on failure (this is a convenience, not a required step).
  const handleFileSelected = (selected: File | null) => {
    setFile(selected);
    if (!selected) return;
    setExtracting(true);
    extractTenderMetadata(selected)
      .then((guess) => {
        setTenderName((prev) => prev || guess.tender_name || "");
        setOrganization((prev) => prev || guess.organization || "");
        setClosingDate((prev) => prev || guess.closing_date || "");
      })
      .catch(() => {
        // Non-fatal: form stays blank/editable, upload flow is unaffected.
      })
      .finally(() => setExtracting(false));
  };

  // Validates and appends newly picked additional files -- rejects
  // unsupported extensions with a clear inline error (rather than letting
  // them reach the backend and fail there) and skips filenames already
  // selected (primary or additional) rather than silently double-adding
  // the same file twice.
  const handleAdditionalFilesPicked = (picked: FileList | null) => {
    if (!picked || picked.length === 0) return;
    const existingNames = new Set([file?.name, ...additionalFiles.map((f) => f.name)].filter(Boolean));
    const accepted: File[] = [];
    const rejectedType: string[] = [];
    const rejectedDuplicate: string[] = [];

    for (const picked_file of Array.from(picked)) {
      if (!ADDITIONAL_FILE_EXTENSIONS.includes(fileExtension(picked_file.name))) {
        rejectedType.push(picked_file.name);
        continue;
      }
      if (existingNames.has(picked_file.name)) {
        rejectedDuplicate.push(picked_file.name);
        continue;
      }
      existingNames.add(picked_file.name);
      accepted.push(picked_file);
    }

    if (accepted.length > 0) {
      setAdditionalFiles((prev) => [...prev, ...accepted]);
    }
    if (rejectedType.length > 0) {
      setAdditionalFilesError(
        `Unsupported file type: ${rejectedType.join(", ")}. Supported formats: PDF, XLS, XLSX.`
      );
    } else if (rejectedDuplicate.length > 0) {
      setAdditionalFilesError(`Already selected: ${rejectedDuplicate.join(", ")}.`);
    } else {
      setAdditionalFilesError(null);
    }
  };

  const handleRemoveAdditionalFile = (name: string) => {
    setAdditionalFiles((prev) => prev.filter((f) => f.name !== name));
    setAdditionalFilesError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isComplete || !file) return;
    setLoading(true);
    setUploadStatus(`Uploading ${file.name}…`);
    try {
      const res = await uploadTender(file, {
        tender_name: tenderName || undefined,
        organization: organization || undefined,
        category: category || undefined,
        closing_date: closingDate || undefined,
      });
      if (!res.tender_id) {
        notify("error", "Tender uploaded, but the response didn't include a tender_id. Check the /api/v1/tenders/upload response shape.");
        return;
      }

      // Additional documents (multi-document Tender support, Bug #007) --
      // attached one at a time to the same tender_id via the existing
      // POST /tenders/{id}/documents endpoint. Document role (main /
      // technical / financial / annexure) is inferred server-side from
      // the filename -- reusing the same convention the backend already
      // established, not re-implemented here.
      const failedUploads: string[] = [];
      for (let i = 0; i < additionalFiles.length; i++) {
        const additionalFile = additionalFiles[i];
        setUploadStatus(`Uploading ${additionalFile.name} (${i + 1} of ${additionalFiles.length})…`);
        try {
          await addTenderDocument(res.tender_id, additionalFile);
        } catch (err) {
          failedUploads.push(`${additionalFile.name} (${extractErrorMessage(err)})`);
        }
      }

      if (failedUploads.length > 0) {
        // Honest partial-success reporting -- the Tender and its primary
        // document exist and are usable, but NOT every requested document
        // made it in. Never silently claim full success here.
        notify(
          "error",
          `Tender created, but ${failedUploads.length} additional document(s) failed to upload: ${failedUploads.join("; ")}. ` +
            "You can retry from the Tender Workspace."
        );
      } else if (additionalFiles.length > 0) {
        notify("success", `Tender uploaded with ${additionalFiles.length + 1} documents. Go to Tender Workspace to run full analysis.`);
      } else {
        notify("success", "Tender uploaded. Go to Tender Workspace to run full analysis.");
      }
      navigate("/missions");
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setLoading(false);
      setUploadStatus(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Upload Tender</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Upload the tender document set — the AI will extract every requirement automatically.
        </p>
      </div>
      <Card>
        <CardHeader title="Tender Details" />
        <CardBody className="px-5 py-4">
          <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
            <div className="space-y-3.5">
              <Input
                label="Tender Name"
                required
                value={tenderName}
                onChange={(e) => setTenderName(e.target.value)}
                placeholder={extracting ? "Reading PDF…" : undefined}
              />
              <Input
                label="Organization"
                required
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                placeholder={extracting ? "Reading PDF…" : undefined}
              />
              <div className="grid grid-cols-2 gap-3">
                <Combobox
                  label="Category"
                  value={category}
                  onChange={setCategory}
                  options={TENDER_CATEGORIES}
                  placeholder="Select category"
                  searchPlaceholder="Search categories…"
                />
                <Input
                  label="Closing Date"
                  type="date"
                  required
                  value={closingDate}
                  onChange={(e) => setClosingDate(e.target.value)}
                />
              </div>
              <Button type="submit" loading={loading} disabled={!isComplete} className="w-full" size="lg">
                Upload Tender
              </Button>
              {loading && uploadStatus && (
                <p className="text-xs text-muted-foreground text-center -mt-2">{uploadStatus}</p>
              )}
            </div>
            <div className="space-y-3.5">
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5">
                  Primary Tender Document
                </p>
                {file ? (
                  <FileRow file={file} onRemove={() => handleFileSelected(null)} disabled={loading} />
                ) : (
                  <Dropzone file={null} onFileSelected={handleFileSelected} hint="Tender PDF, up to 50MB" compact />
                )}
              </div>

              {/* Additional Tender Documents -- multi-document Tender
                  support (Bug #007). A real tender is rarely a single
                  PDF: this lets the user attach every relevant file (e.g.
                  a technical bid spreadsheet, a financial BOQ) in the same
                  flow that creates the Tender, rather than requiring a
                  separate trip to Tender Workspace afterward. */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Additional Tender Documents
                  </p>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    icon={<Plus size={14} />}
                    onClick={() => additionalFileInputRef.current?.click()}
                  >
                    Add Tender File
                  </Button>
                  <input
                    ref={additionalFileInputRef}
                    type="file"
                    multiple
                    accept={ADDITIONAL_FILE_ACCEPT}
                    className="hidden"
                    onChange={(e) => {
                      handleAdditionalFilesPicked(e.target.files);
                      e.target.value = "";
                    }}
                  />
                </div>

                {additionalFilesError && (
                  <p className="text-xs text-danger mb-1.5">{additionalFilesError}</p>
                )}

                {additionalFiles.length > 0 ? (
                  <div className="rounded-lg border border-border divide-y divide-border overflow-hidden">
                    {additionalFiles.map((f) => (
                      <FileRow
                        key={f.name}
                        file={f}
                        onRemove={() => handleRemoveAdditionalFile(f.name)}
                        disabled={loading}
                        bare
                      />
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    Optional — attach technical bid details, BOQ, or other supporting files (PDF, XLS, XLSX).
                  </p>
                )}
              </div>
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}

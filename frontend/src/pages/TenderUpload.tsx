import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { extractTenderMetadata, uploadTender } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import { Button, Card, CardBody, CardHeader, Dropzone, Input } from "../components/kit";

export default function TenderUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [tenderName, setTenderName] = useState("");
  const [organization, setOrganization] = useState("");
  const [closingDate, setClosingDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const { notify } = useToast();
  const navigate = useNavigate();

  // Best-effort prefill from the PDF's own text -- heuristic-only, never
  // overwrites anything the user already typed, and silently no-ops on
  // failure (this is a convenience, not a required step).
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    try {
      const res = await uploadTender(file, {
        tender_name: tenderName || undefined,
        organization: organization || undefined,
        closing_date: closingDate || undefined,
      });
      if (!res.tender_id) {
        notify("error", "Tender uploaded, but the response didn't include a tender_id. Check the /api/v1/tenders/upload response shape.");
        return;
      }
      notify("success", "Tender uploaded. Go to Tender Workspace to run full analysis.");
      navigate("/missions");
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Upload Tender</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Upload the tender document — the AI will extract every requirement automatically.
        </p>
      </div>
      <Card>
        <CardHeader title="Tender Details" />
        <CardBody>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="space-y-4">
              <Input
                label="Tender Name (optional)"
                value={tenderName}
                onChange={(e) => setTenderName(e.target.value)}
                placeholder={extracting ? "Reading PDF…" : undefined}
              />
              <Input
                label="Organization (optional)"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                placeholder={extracting ? "Reading PDF…" : undefined}
              />
              <Input
                label="Closing Date (optional)"
                type="date"
                value={closingDate}
                onChange={(e) => setClosingDate(e.target.value)}
              />
              <Button type="submit" loading={loading} disabled={!file} className="w-full" size="lg">
                Upload Tender
              </Button>
            </div>
            <div>
              <Dropzone file={file} onFileSelected={handleFileSelected} hint="Tender PDF, up to 50MB" className="h-full min-h-[280px]" />
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}

import { useCallback, useRef, useState } from "react";
import { FileText, UploadCloud, X } from "lucide-react";
import { cn } from "../../lib/cn";

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function Dropzone({
  file,
  onFileSelected,
  accept = "application/pdf",
  hint = "PDF, up to 50MB",
  className,
  compact = false,
}: {
  file: File | null;
  onFileSelected: (file: File | null) => void;
  accept?: string;
  hint?: string;
  className?: string;
  compact?: boolean;
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const dropped = e.dataTransfer.files?.[0];
      if (dropped) onFileSelected(dropped);
    },
    [onFileSelected]
  );

  if (file) {
    return (
      <div
        className={cn(
          "flex items-center gap-3 rounded-lg border border-border bg-muted/60",
          compact ? "px-3" : "px-4 py-3",
          className
        )}
      >
        <div className={cn("rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0", compact ? "w-7 h-7" : "w-9 h-9")}>
          <FileText size={compact ? 13 : 16} />
        </div>
        <div className="min-w-0 flex-1">
          <p className={cn("font-medium truncate", compact ? "text-xs" : "text-sm")}>{file.name}</p>
          {!compact && <p className="text-xs text-muted-foreground">{formatBytes(file.size)}</p>}
        </div>
        <button
          type="button"
          onClick={() => onFileSelected(null)}
          className="text-muted-foreground hover:text-danger transition shrink-0"
        >
          <X size={compact ? 14 : 16} />
        </button>
      </div>
    );
  }

  // Compact mode packs the whole control onto a single row -- icon, copy,
  // and hint inline -- so it can sit flush next to a <Select> and a
  // <Button> of the same height instead of towering over them as its own
  // block. Used where the surrounding form is itself a single-line row
  // (e.g. Documents' Upload Document form); the full drag-and-drop square
  // is kept as the default everywhere else (e.g. New Tender).
  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={cn(
        compact
          ? "flex items-center gap-2 rounded-lg border-2 border-dashed px-4 cursor-pointer transition-colors"
          : "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center cursor-pointer transition-colors",
        dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-surface-hover",
        className
      )}
    >
      {compact ? (
        <>
          <div className={cn("w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition", dragging ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground")}>
            <UploadCloud size={13} />
          </div>
          <p className="text-sm truncate">
            <span className="text-primary font-medium">Click to upload</span>{" "}
            <span className="text-muted-foreground">or drag and drop · {hint}</span>
          </p>
        </>
      ) : (
        <>
          <div className={cn("w-10 h-10 rounded-full flex items-center justify-center transition", dragging ? "bg-primary text-primary-foreground animate-pulse-ring" : "bg-muted text-muted-foreground")}>
            <UploadCloud size={18} />
          </div>
          <p className="text-sm font-medium">
            <span className="text-primary">Click to upload</span> or drag and drop
          </p>
          <p className="text-xs text-muted-foreground">{hint}</p>
        </>
      )}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => onFileSelected(e.target.files?.[0] ?? null)}
      />
    </div>
  );
}

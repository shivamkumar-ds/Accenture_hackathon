import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from "lucide-react";

type ToastVariant = "success" | "error" | "info";

interface Toast {
  id: number;
  variant: ToastVariant;
  message: string;
}

interface ToastContextValue {
  notify: (variant: ToastVariant, message: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

const variantConfig: Record<ToastVariant, { icon: typeof CheckCircle2; classes: string }> = {
  success: { icon: CheckCircle2, classes: "border-success/30 bg-success-soft text-success" },
  error: { icon: XCircle, classes: "border-danger/30 bg-danger-soft text-danger" },
  info: { icon: Info, classes: "border-info/30 bg-info-soft text-info" },
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const notify = useCallback((variant: ToastVariant, message: string) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, variant, message }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 5000);
  }, []);

  const dismiss = (id: number) => setToasts((prev) => prev.filter((t) => t.id !== id));

  return (
    <ToastContext.Provider value={{ notify }}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 w-full max-w-sm">
        {toasts.map((t) => {
          const cfg = variantConfig[t.variant];
          const Icon = cfg.icon;
          return (
            <div
              key={t.id}
              className={`animate-fade-in flex items-start gap-3 rounded-lg border px-4 py-3 shadow-elevated backdrop-blur-sm ${cfg.classes}`}
            >
              <Icon size={18} className="shrink-0 mt-0.5" />
              <p className="text-sm leading-snug flex-1">{t.message}</p>
              <button onClick={() => dismiss(t.id)} className="opacity-60 hover:opacity-100 transition">
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export function AlertTriangleIcon() {
  return <AlertTriangle size={18} />;
}

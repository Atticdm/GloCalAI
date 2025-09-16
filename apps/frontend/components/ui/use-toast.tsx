import * as React from "react";
import { Toast, ToastDescription, ToastProvider, ToastTitle, ToastViewport } from "@/components/ui/toast";

export type ToastMessage = {
  title: string;
  description?: string;
  id?: string;
};

interface ToastContextValue {
  toast: (message: ToastMessage) => void;
}

const ToastContext = React.createContext<ToastContextValue | undefined>(undefined);

export function ToastManager({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = React.useState<ToastMessage[]>([]);

  const toast = React.useCallback((message: ToastMessage) => {
    setMessages((current) => [...current, { ...message, id: crypto.randomUUID() }]);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      <ToastProvider>
        {children}
        <ToastViewport />
        {messages.map((item) => (
          <Toast key={item.id} onOpenChange={(open) => !open && setMessages((current) => current.filter((m) => m.id !== item.id))}>
            <div className="grid gap-1 pr-4">
              <ToastTitle>{item.title}</ToastTitle>
              {item.description ? <ToastDescription>{item.description}</ToastDescription> : null}
            </div>
          </Toast>
        ))}
      </ToastProvider>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastManager");
  }
  return ctx.toast;
}

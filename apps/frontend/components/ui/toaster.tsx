import { ToastManager } from "@/components/ui/use-toast";

export function Toaster({ children }: { children: React.ReactNode }) {
  return <ToastManager>{children}</ToastManager>;
}

import { cn } from "@/lib/utils";

export function Badge({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center rounded-full bg-slate-800 px-2 py-1 text-xs text-slate-200", className)}>
      {children}
    </span>
  );
}

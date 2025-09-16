"use client";

import { Loader2 } from "lucide-react";

import { LoginForm } from "@/components/dashboard/login-form";
import { useAuth } from "@/hooks/use-auth";

export function AuthBoundary({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-slate-400">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Checking session...
      </div>
    );
  }
  if (!token) {
    return <LoginForm />;
  }
  return <>{children}</>;
}

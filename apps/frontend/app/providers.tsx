"use client";

import * as React from "react";

import { AuthProvider } from "@/hooks/use-auth";
import { Toaster } from "@/components/ui/toaster";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <Toaster>{children}</Toaster>
    </AuthProvider>
  );
}

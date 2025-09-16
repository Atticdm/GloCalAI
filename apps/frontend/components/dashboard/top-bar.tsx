"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";

export function TopBar() {
  const { user, logout } = useAuth();
  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2 text-lg font-semibold">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand/20 text-brand">GA</span>
          <span>Glocal Ads AI</span>
        </Link>
        {user ? (
          <div className="flex items-center gap-4 text-sm text-slate-300">
            <div className="text-right">
              <div className="font-medium text-slate-100">{user.email}</div>
              <div className="text-xs text-slate-400 uppercase">{user.role}</div>
            </div>
            <Button variant="outline" size="sm" onClick={logout}>
              Logout
            </Button>
          </div>
        ) : null}
      </div>
    </header>
  );
}

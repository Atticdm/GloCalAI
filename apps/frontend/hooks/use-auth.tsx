"use client";

import * as React from "react";

import { apiClient, setAuthToken } from "@/lib/api-client";

export interface UserProfile {
  id: string;
  email: string;
  role: string;
}

interface AuthContextValue {
  token: string | null;
  user: UserProfile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEY = "glocal-auth-token";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = React.useState<string | null>(null);
  const [user, setUser] = React.useState<UserProfile | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const saved = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
    if (saved) {
      setToken(saved);
      setAuthToken(saved);
      refreshProfile(saved).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const refreshProfile = React.useCallback(async (authToken: string) => {
    try {
      setAuthToken(authToken);
      const response = await apiClient.get<UserProfile>("/me");
      setUser(response.data);
    } catch {
      setToken(null);
      setUser(null);
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  const login = React.useCallback(
    async (email: string, password: string) => {
      const response = await apiClient.post<{ token: string }>("/auth/sign-in", { email, password });
      const authToken = response.data.token;
      setToken(authToken);
      setAuthToken(authToken);
      window.localStorage.setItem(STORAGE_KEY, authToken);
      await refreshProfile(authToken);
    },
    [refreshProfile]
  );

  const logout = React.useCallback(() => {
    setToken(null);
    setUser(null);
    setAuthToken(null);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  const value = React.useMemo(
    () => ({ token, user, loading, login, logout }),
    [token, user, loading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = React.useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}

"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { insforge } from "@/lib/insforge";

export interface AuthUser {
  id: string;
  email?: string;
  name?: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, name?: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// InsForge methods return { data, error }; surface the error message to the caller.
function unwrapError(error: unknown): never {
  const message =
    (error as { message?: string })?.message ?? "Something went wrong.";
  throw new Error(message);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const { data } = await insforge.auth.getCurrentUser();
      setUser((data?.user as AuthUser) ?? null);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const { error } = await insforge.auth.signInWithPassword({ email, password });
      if (error) unwrapError(error);
      await refresh();
    },
    [refresh],
  );

  const signUp = useCallback(
    async (email: string, password: string, name?: string) => {
      const { error } = await insforge.auth.signUp({ email, password, name });
      if (error) unwrapError(error);
      await refresh();
    },
    [refresh],
  );

  const signOut = useCallback(async () => {
    await insforge.auth.signOut();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

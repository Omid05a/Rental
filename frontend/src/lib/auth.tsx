"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { ApiError, apiFetch } from "@/lib/api";

export type VerificationStatus =
  | "not_submitted"
  | "pending"
  | "approved"
  | "rejected";

export type User = {
  id: number;
  phone: string;
  first_name: string;
  last_name: string;
  verification_status: VerificationStatus;
  rejection_reason: string;
};

type Tokens = { access: string; refresh: string };

type AuthContextValue = {
  user: User | null;
  ready: boolean;
  signIn: (tokens: Tokens, user: User) => void;
  signOut: () => void;
  updateUser: (user: User) => void;
  authFetch: <T>(path: string, options?: RequestInit) => Promise<T>;
};

const STORAGE_KEY = "rental.tokens";

function readTokens(): Tokens | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Tokens) : null;
  } catch {
    return null;
  }
}

function writeTokens(tokens: Tokens | null) {
  try {
    if (tokens) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // Storage can be unavailable (private mode); the session is then in-memory only.
  }
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const tokensRef = useRef<Tokens | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const signOut = useCallback(() => {
    tokensRef.current = null;
    writeTokens(null);
    setUser(null);
  }, []);

  const signIn = useCallback((tokens: Tokens, nextUser: User) => {
    tokensRef.current = tokens;
    writeTokens(tokens);
    setUser(nextUser);
  }, []);

  const authFetch = useCallback(
    async <T,>(path: string, options: RequestInit = {}): Promise<T> => {
      const tokens = tokensRef.current;
      if (!tokens) {
        throw new ApiError(401, null);
      }

      try {
        return await apiFetch<T>(path, options, tokens.access);
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401) {
          throw error;
        }
      }

      // The access token expired: refresh it once and retry the request.
      try {
        const refreshed = await apiFetch<{ access: string; refresh?: string }>(
          "/auth/token/refresh/",
          { method: "POST", body: JSON.stringify({ refresh: tokens.refresh }) },
        );
        const next = {
          access: refreshed.access,
          refresh: refreshed.refresh ?? tokens.refresh,
        };
        tokensRef.current = next;
        writeTokens(next);
        return await apiFetch<T>(path, options, next.access);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          signOut();
        }
        throw error;
      }
    },
    [signOut],
  );

  useEffect(() => {
    async function restoreSession() {
      const stored = readTokens();
      if (stored) {
        tokensRef.current = stored;
        try {
          setUser(await authFetch<User>("/me/"));
        } catch {
          // Invalid sessions are cleared by authFetch; network errors keep the tokens.
        }
      }
      setReady(true);
    }
    void restoreSession();
  }, [authFetch]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, ready, signIn, signOut, updateUser: setUser, authFetch }),
    [user, ready, signIn, signOut, authFetch],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}

/** Redirects to the login page when there is no signed-in user. */
export function useRequireAuth() {
  const auth = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (auth.ready && !auth.user) {
      router.replace("/login");
    }
  }, [auth.ready, auth.user, router]);

  return auth;
}
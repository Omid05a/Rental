"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { useAuth } from "@/lib/auth";

type UnreadValue = {
  count: number;
  setCount: (count: number) => void;
  refresh: () => Promise<void>;
};

const POLL_MS = 30_000;

const UnreadContext = createContext<UnreadValue>({
  count: 0,
  setCount: () => undefined,
  refresh: async () => undefined,
});

/**
 * Polls the unread notification count while a user is signed in. The same
 * request makes the server create time-based reminders, so reminders appear
 * while the app is open.
 */
export function UnreadProvider({ children }: { children: ReactNode }) {
  const { user, ready, authFetch } = useAuth();
  const [count, setCount] = useState(0);
  const signedIn = ready && !!user;

  const refresh = useCallback(async () => {
    try {
      const data = await authFetch<{ count: number }>(
        "/notifications/unread-count/",
      );
      setCount(data.count);
    } catch {
      // Keep the previous value when the request fails.
    }
  }, [authFetch]);

  useEffect(() => {
    if (!signedIn) return;
    let active = true;

    const tick = () => {
      if (document.visibilityState === "hidden") return;
      authFetch<{ count: number }>("/notifications/unread-count/")
        .then((data) => {
          if (active) setCount(data.count);
        })
        .catch(() => undefined);
    };

    const first = setTimeout(tick, 0);
    const timer = setInterval(tick, POLL_MS);
    return () => {
      active = false;
      clearTimeout(first);
      clearInterval(timer);
    };
  }, [signedIn, authFetch]);

  const value = useMemo<UnreadValue>(
    () => ({ count: signedIn ? count : 0, setCount, refresh }),
    [signedIn, count, refresh],
  );

  return (
    <UnreadContext.Provider value={value}>{children}</UnreadContext.Provider>
  );
}

export function useUnread(): UnreadValue {
  return useContext(UnreadContext);
}
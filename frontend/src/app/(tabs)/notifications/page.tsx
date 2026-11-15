"use client";

import {
  Bell,
  CalendarClock,
  Car,
  Route,
  ShieldCheck,
  Star,
  TriangleAlert,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useUnread } from "@/components/unread-provider";
import { PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
import { useRequireAuth } from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";
import { formatJalaliDateTime } from "@/lib/jalali";
import type {
  AppNotification,
  NotificationKind,
  NotificationList,
} from "@/lib/social";

const ICONS: Record<NotificationKind, LucideIcon> = {
  verification: ShieldCheck,
  vehicle: Car,
  booking: CalendarClock,
  trip: Route,
  payment: Wallet,
  damage: TriangleAlert,
  review: Star,
  reminder: Bell,
};

const relativeFormat = new Intl.RelativeTimeFormat("fa", { numeric: "auto" });

function timeAgo(value: string, nowMs: number) {
  const diff = (new Date(value).getTime() - nowMs) / 1000;
  const abs = Math.abs(diff);
  if (abs < 60) return "همین الان";
  if (abs < 3600) return relativeFormat.format(Math.round(diff / 60), "minute");
  if (abs < 86400) return relativeFormat.format(Math.round(diff / 3600), "hour");
  if (abs < 7 * 86400) {
    return relativeFormat.format(Math.round(diff / 86400), "day");
  }
  return formatJalaliDateTime(value);
}

type Result = { items: AppNotification[]; error: string | null };

export default function NotificationsPage() {
  const router = useRouter();
  const { user, ready, authFetch } = useRequireAuth();
  const { count, setCount } = useUnread();

  const [result, setResult] = useState<Result | null>(null);
  const [now] = useState(() => Date.now());
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!ready || !user) return;
    let active = true;
    authFetch<NotificationList>("/notifications/?limit=50")
      .then((data) => {
        if (!active) return;
        setResult({ items: data.results, error: null });
        setCount(data.unread_count);
      })
      .catch((err) => {
        if (active) setResult({ items: [], error: getErrorMessage(err) });
      });
    return () => {
      active = false;
    };
  }, [ready, user, authFetch, setCount]);

  async function markAll() {
    setBusy(true);
    try {
      await authFetch("/notifications/read/", {
        method: "POST",
        body: JSON.stringify({ all: true }),
      });
      setResult((current) =>
        current
          ? {
              ...current,
              items: current.items.map((item) => ({ ...item, is_read: true })),
            }
          : current,
      );
      setCount(0);
    } catch (err) {
      setResult((current) =>
        current ? { ...current, error: getErrorMessage(err) } : current,
      );
    } finally {
      setBusy(false);
    }
  }

  function open(item: AppNotification) {
    if (!item.is_read) {
      authFetch("/notifications/read/", {
        method: "POST",
        body: JSON.stringify({ ids: [item.id] }),
      }).catch(() => undefined);
      setResult((current) =>
        current
          ? {
              ...current,
              items: current.items.map((entry) =>
                entry.id === item.id ? { ...entry, is_read: true } : entry,
              ),
            }
          : current,
      );
      setCount(Math.max(0, count - 1));
    }
    if (item.link) router.push(item.link);
  }

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  const items = result?.items ?? [];

  return (
    <PageShell>
      <header className="flex items-center justify-between gap-3 px-6 pb-4 pt-12">
        <h1 className="text-xl font-bold">اعلان‌ها</h1>
        {count > 0 ? (
          <Button
            variant="outline"
            disabled={busy}
            onClick={markAll}
            className="h-9 rounded-full border-border bg-card px-4 text-xs"
          >
            خواندن همه
          </Button>
        ) : null}
      </header>

      <main className="flex flex-1 flex-col gap-3 px-6 pb-10">
        {result?.error ? (
          <p role="alert" className="px-2 text-sm text-destructive">
            {result.error}
          </p>
        ) : null}

        {!result ? (
          <p className="text-center text-sm text-muted-foreground">
            در حال بارگذاری…
          </p>
        ) : null}

        {result && !result.error && items.length === 0 ? (
          <div className="rounded-3xl bg-card p-8 text-center text-sm text-muted-foreground">
            هنوز اعلانی ندارید.
          </div>
        ) : null}

        <ul className="flex flex-col gap-2">
          {items.map((item) => {
            const Icon = ICONS[item.kind] ?? Bell;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => open(item)}
                  className={`flex w-full items-start gap-3 rounded-3xl p-4 text-start ${
                    item.is_read ? "bg-card" : "bg-card ring-1 ring-primary/60"
                  }`}
                >
                  <span
                    className={`flex size-10 shrink-0 items-center justify-center rounded-full ${
                      item.is_read
                        ? "bg-secondary text-muted-foreground"
                        : "bg-primary/15 text-primary"
                    }`}
                  >
                    <Icon className="size-5" />
                  </span>
                  <span className="flex min-w-0 flex-1 flex-col gap-1">
                    <span className="flex items-center justify-between gap-3">
                      <strong className="text-sm">{item.title}</strong>
                      {!item.is_read ? (
                        <span className="size-2 shrink-0 rounded-full bg-primary" />
                      ) : null}
                    </span>
                    {item.body ? (
                      <span className="text-xs leading-relaxed text-muted-foreground">
                        {item.body}
                      </span>
                    ) : null}
                    <span className="text-[11px] text-muted-foreground">
                      {timeAgo(item.created_at, now)}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </main>
    </PageShell>
  );
}
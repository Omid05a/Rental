"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type CSSProperties } from "react";

import { PageShell } from "@/components/page-shell";
import { useRequireAuth } from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";
import { formatPriceShort, formatToman, toFa } from "@/lib/format";
import {
  JALALI_MONTHS,
  formatJalaliDateTime,
  jalaliYearMonth,
} from "@/lib/jalali";
import type { Earnings, EarningsItem } from "@/lib/social";

type Result = { data: Earnings | null; error: string | null };

type MonthSlot = { jy: number; jm: number; net: number };

// Staggered entrance delay index (see .stagger in globals.css)
function stagger(index: number): CSSProperties {
  return { "--i": index } as CSSProperties;
}

function buildMonths(items: EarningsItem[], now: Date): MonthSlot[] {
  let { jy, jm } = jalaliYearMonth(now);
  const slots: MonthSlot[] = [];
  for (let i = 0; i < 6; i++) {
    slots.unshift({ jy, jm, net: 0 });
    jm -= 1;
    if (jm === 0) {
      jm = 12;
      jy -= 1;
    }
  }
  for (const item of items) {
    const { jy: itemYear, jm: itemMonth } = jalaliYearMonth(item.date);
    const slot = slots.find((s) => s.jy === itemYear && s.jm === itemMonth);
    if (slot) slot.net += item.net;
  }
  return slots;
}

function Stat({
  label,
  value,
  index,
  strong = false,
}: {
  label: string;
  value: string;
  index: number;
  strong?: boolean;
}) {
  return (
    <div
      className={`stagger flex flex-col gap-1 rounded-3xl p-4 ${
        strong ? "bg-primary text-primary-foreground" : "bg-card"
      }`}
      style={stagger(index)}
    >
      <span className={`text-xs ${strong ? "opacity-70" : "text-muted-foreground"}`}>
        {label}
      </span>
      <span className="text-lg font-bold">{value}</span>
    </div>
  );
}

function EarningsSkeleton() {
  return (
    <div className="flex flex-col gap-5" aria-hidden="true">
      <div className="skeleton h-20 rounded-3xl" />
      <div className="grid grid-cols-2 gap-3">
        <div className="skeleton h-20 rounded-3xl" />
        <div className="skeleton h-20 rounded-3xl" />
        <div className="skeleton h-20 rounded-3xl" />
        <div className="skeleton h-20 rounded-3xl" />
      </div>
      <div className="skeleton h-56 rounded-3xl" />
    </div>
  );
}

export default function EarningsPage() {
  const router = useRouter();
  const { user, ready, authFetch } = useRequireAuth();
  const [result, setResult] = useState<Result | null>(null);
  const [now] = useState(() => new Date());
  const [grown, setGrown] = useState(false);

  useEffect(() => {
    if (!ready || !user) return;
    let active = true;
    authFetch<Earnings>("/earnings/")
      .then((data) => {
        if (active) setResult({ data, error: null });
      })
      .catch((err) => {
        if (active) setResult({ data: null, error: getErrorMessage(err) });
      });
    return () => {
      active = false;
    };
  }, [ready, user, authFetch]);

  const data = result?.data ?? null;
  const months = useMemo(
    () => buildMonths(data?.items ?? [], now),
    [data, now],
  );

  // Let the chart bars grow from zero once the data has rendered
  useEffect(() => {
    if (!data) return;
    const frame = requestAnimationFrame(() => setGrown(true));
    return () => cancelAnimationFrame(frame);
  }, [data]);

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  const max = Math.max(...months.map((month) => month.net), 1);

  return (
    <PageShell>
      <header className="flex items-center gap-3 px-6 pb-4 pt-12">
        <button
          type="button"
          onClick={() => router.push("/profile")}
          aria-label="بازگشت"
          className="press flex size-10 items-center justify-center rounded-full bg-card hover:bg-accent"
        >
          <ArrowRight className="size-5" />
        </button>
        <h1 className="text-xl font-bold">گزارش درآمد</h1>
      </header>

      <main className="flex flex-1 flex-col gap-5 px-6 pb-10">
        {result?.error ? (
          <p
            role="alert"
            className="animate-fade-up px-2 text-sm text-destructive"
          >
            {result.error}
          </p>
        ) : null}

        {!result ? <EarningsSkeleton /> : null}

        {data ? (
          <>
            <Stat
              label="درآمد خالص"
              value={formatToman(data.total_net)}
              index={0}
              strong
            />

            <div className="grid grid-cols-2 gap-3">
              <Stat
                label="درآمد ناخالص"
                value={formatToman(data.total_gross)}
                index={1}
              />
              <Stat
                label="کارمزد رنتال"
                value={formatToman(data.total_fees)}
                index={2}
              />
              <Stat label="تعداد سفرها" value={toFa(data.trips)} index={3} />
              <Stat
                label="رزروهای پیش‌رو (ناخالص)"
                value={formatToman(data.pending_gross)}
                index={4}
              />
            </div>

            <section
              className="stagger rounded-3xl bg-card p-5"
              style={stagger(5)}
            >
              <h2 className="font-semibold">درآمد خالص ماهانه</h2>
              <div className="mt-4 flex h-36 items-end gap-2">
                {months.map((month, index) => (
                  <div
                    key={`${month.jy}-${month.jm}`}
                    className="flex h-full flex-1 items-end"
                  >
                    <div
                      className="w-full rounded-t-lg bg-primary"
                      style={{
                        height: grown
                          ? `${
                              month.net > 0
                                ? Math.max(6, (month.net / max) * 100)
                                : 2
                            }%`
                          : "2%",
                        opacity: month.net > 0 ? 1 : 0.25,
                        transition: "height 700ms var(--ease-out)",
                        transitionDelay: `${index * 70}ms`,
                      }}
                    />
                  </div>
                ))}
              </div>
              <div className="mt-2 flex gap-2">
                {months.map((month) => (
                  <div
                    key={`${month.jy}-${month.jm}`}
                    className="flex-1 text-center text-[10px] text-muted-foreground"
                  >
                    <p>{JALALI_MONTHS[month.jm - 1]}</p>
                    <p className="text-foreground">
                      {month.net > 0 ? formatPriceShort(month.net) : "—"}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            {data.by_vehicle.length > 0 ? (
              <section
                className="stagger rounded-3xl bg-card px-5 py-3"
                style={stagger(6)}
              >
                <h2 className="py-2 font-semibold">به تفکیک وسیله</h2>
                <ul className="divide-y divide-border">
                  {data.by_vehicle.map((row) => (
                    <li
                      key={row.vehicle_id}
                      className="flex items-center justify-between gap-4 py-3 text-sm"
                    >
                      <span className="min-w-0">
                        <span className="block truncate font-medium">
                          {row.title}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {toFa(row.trips)} سفر
                        </span>
                      </span>
                      <span className="shrink-0 font-bold">
                        {formatToman(row.net)}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            <section
              className="stagger flex flex-col gap-2"
              style={stagger(7)}
            >
              <h2 className="px-2 font-semibold">تراکنش‌های درآمدی</h2>
              {data.items.length === 0 ? (
                <p className="rounded-3xl bg-card p-6 text-center text-sm text-muted-foreground">
                  هنوز درآمدی ثبت نشده است. بعد از پایان اولین سفر، اینجا
                  نمایش داده می‌شود.
                </p>
              ) : null}
              <ul className="flex flex-col gap-2">
                {data.items.map((item, index) => (
                  <li
                    key={`${item.booking_id}-${item.kind}`}
                    className="stagger"
                    style={stagger(Math.min(index, 8))}
                  >
                    <Link
                      href={`/bookings/${item.booking_id}`}
                      className="press flex items-center justify-between gap-3 rounded-2xl bg-card px-4 py-3 hover:bg-accent"
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium">
                          {item.vehicle_title}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {item.kind === "trip" ? "سفر" : "کارمزد لغو رزرو"} ·{" "}
                          {formatJalaliDateTime(item.date)}
                        </span>
                      </span>
                      <span className="shrink-0 text-end">
                        <span className="block text-sm font-bold text-green-400">
                          {formatToman(item.net)}
                        </span>
                        <span className="text-[11px] text-muted-foreground">
                          ناخالص {formatPriceShort(item.gross)}
                        </span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          </>
        ) : null}
      </main>
    </PageShell>
  );
}
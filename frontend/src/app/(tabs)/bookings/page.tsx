"use client";

import { Bike, Car } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { PageShell } from "@/components/page-shell";
import { useRequireAuth } from "@/lib/auth";
import { BOOKING_STATUS, type Booking } from "@/lib/bookings";
import { getErrorMessage } from "@/lib/errors";
import { formatToman } from "@/lib/format";
import { formatJalaliDateTime } from "@/lib/jalali";

type Role = "renter" | "owner";

type ListResult = {
  role: Role;
  items: Booking[];
  error: string | null;
};

const NO_ITEMS: Booking[] = [];

const TABS: { value: Role; label: string }[] = [
  { value: "renter", label: "سفرهای من" },
  { value: "owner", label: "رزروهای وسایل من" },
];

export default function BookingsPage() {
  const { user, ready, authFetch } = useRequireAuth();
  const [role, setRole] = useState<Role>("renter");
  const [result, setResult] = useState<ListResult | null>(null);

  useEffect(() => {
    if (!ready || !user) return;
    let active = true;
    authFetch<Booking[]>(`/bookings/?role=${role}`)
      .then((items) => {
        if (active) setResult({ role, items, error: null });
      })
      .catch((err) => {
        if (active) {
          setResult({ role, items: NO_ITEMS, error: getErrorMessage(err) });
        }
      });
    return () => {
      active = false;
    };
  }, [ready, user, role, authFetch]);

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  const loading = result?.role !== role;
  const items = result?.items ?? NO_ITEMS;

  return (
    <PageShell>
      <header className="px-6 pb-4 pt-12">
        <h1 className="text-xl font-bold">رزروها</h1>
        <div role="tablist" className="mt-4 flex gap-2">
          {TABS.map((tab) => (
            <button
              key={tab.value}
              type="button"
              role="tab"
              aria-selected={role === tab.value}
              onClick={() => setRole(tab.value)}
              className={`h-10 flex-1 rounded-full px-3 text-sm font-medium ${
                role === tab.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-card"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      <main className="flex flex-1 flex-col gap-3 px-6 pb-10">
        {result?.error ? (
          <p role="alert" className="px-2 text-sm text-destructive">
            {result.error}
          </p>
        ) : null}

        {loading ? (
          <p className="text-center text-sm text-muted-foreground">
            در حال بارگذاری…
          </p>
        ) : null}

        {!loading && !result?.error && items.length === 0 ? (
          <div className="rounded-3xl bg-card p-8 text-center text-sm text-muted-foreground">
            {role === "renter"
              ? "هنوز رزروی انجام نداده‌اید. از بخش جستجو یک وسیله پیدا کنید."
              : "هنوز کسی وسایل شما را رزرو نکرده است."}
          </div>
        ) : null}

        <ul className="flex flex-col gap-3">
          {items.map((booking) => {
            const status = BOOKING_STATUS[booking.status];
            const Icon = booking.vehicle.kind === "bike" ? Bike : Car;
            return (
              <li key={booking.id}>
                <Link
                  href={`/bookings/${booking.id}`}
                  className="flex items-center gap-4 rounded-3xl bg-card p-3"
                >
                  <div className="flex size-20 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-secondary text-muted-foreground">
                    {booking.vehicle.cover ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={booking.vehicle.cover}
                        alt=""
                        className="size-full object-cover"
                      />
                    ) : (
                      <Icon className="size-8" />
                    )}
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col gap-1">
                    <h2 className="truncate font-semibold">
                      {booking.vehicle.title}
                    </h2>
                    <p className="text-xs text-muted-foreground">
                      {formatJalaliDateTime(booking.start_at)}
                    </p>
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className={`rounded-full px-3 py-0.5 text-xs font-medium ${status.className}`}
                      >
                        {status.label}
                      </span>
                      <span className="text-sm font-bold text-primary">
                        {formatToman(booking.rental_amount)}
                      </span>
                    </div>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      </main>
    </PageShell>
  );
}
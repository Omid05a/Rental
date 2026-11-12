"use client";

import { ArrowRight, Bike, Car, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
import { useRequireAuth } from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";
import { formatToman } from "@/lib/format";
import { APPROVAL, type Vehicle } from "@/lib/vehicles";

export default function MyVehiclesPage() {
  const router = useRouter();
  const { user, ready, authFetch } = useRequireAuth();

  const [vehicles, setVehicles] = useState<Vehicle[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready || !user) return;
    authFetch<Vehicle[]>("/my/vehicles/")
      .then(setVehicles)
      .catch((err) => setError(getErrorMessage(err)));
  }, [ready, user, authFetch]);

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  const verified = user.verification_status === "approved";

  return (
    <PageShell>
      <header className="flex items-center gap-3 px-6 pb-4 pt-12">
        <button
          type="button"
          onClick={() => router.push("/profile")}
          aria-label="بازگشت"
          className="flex size-10 items-center justify-center rounded-full bg-card"
        >
          <ArrowRight className="size-5" />
        </button>
        <h1 className="text-xl font-bold">وسایل من</h1>
      </header>

      <main className="flex flex-1 flex-col gap-4 px-6 pb-10">
        {!verified ? (
          <div className="flex flex-col gap-3 rounded-3xl bg-card p-5">
            <p className="text-sm leading-relaxed text-muted-foreground">
              برای ثبت وسیله، ابتدا باید هویت شما تأیید شود.
            </p>
            <Button
              onClick={() => router.push("/verification")}
              className="h-12 rounded-full font-bold"
            >
              ارسال مدارک
            </Button>
          </div>
        ) : null}

        {error ? (
          <p role="alert" className="px-2 text-sm text-destructive">
            {error}
          </p>
        ) : null}

        {!vehicles && !error ? (
          <p className="text-center text-sm text-muted-foreground">
            در حال بارگذاری…
          </p>
        ) : null}

        {vehicles && vehicles.length === 0 ? (
          <div className="flex flex-col items-center gap-3 rounded-3xl bg-card p-8 text-center">
            <Car className="size-10 text-primary" />
            <p className="text-sm text-muted-foreground">
              هنوز وسیله‌ای ثبت نکرده‌اید.
            </p>
          </div>
        ) : null}

        <ul className="flex flex-col gap-3">
          {vehicles?.map((vehicle) => {
            const status = APPROVAL[vehicle.approval_status];
            const cover = vehicle.photos[0]?.image;
            const Icon = vehicle.kind === "bike" ? Bike : Car;
            return (
              <li key={vehicle.id}>
                <Link
                  href={`/vehicles/mine/${vehicle.id}`}
                  className="flex items-center gap-4 rounded-3xl bg-card p-3"
                >
                  <div className="flex size-20 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-secondary text-muted-foreground">
                    {cover ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={cover}
                        alt=""
                        className="size-full object-cover"
                      />
                    ) : (
                      <Icon className="size-8" />
                    )}
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col gap-1">
                    <h2 className="truncate font-semibold">{vehicle.title}</h2>
                    <p className="text-sm text-muted-foreground">
                      {formatToman(vehicle.price_per_hour)} / ساعت
                    </p>
                    <span
                      className={`w-fit rounded-full px-3 py-0.5 text-xs font-medium ${status.className}`}
                    >
                      {status.label}
                    </span>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>

        {verified ? (
          <Button
            onClick={() => router.push("/vehicles/new")}
            className="mt-auto h-14 rounded-full text-base font-bold"
          >
            <Plus className="size-5" />
            ثبت وسیله جدید
          </Button>
        ) : null}
      </main>
    </PageShell>
  );
}
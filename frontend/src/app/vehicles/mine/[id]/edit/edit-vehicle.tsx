"use client";

import { ArrowRight } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageShell } from "@/components/page-shell";
import { VehicleForm } from "@/components/vehicle-form";
import { useRequireAuth } from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";
import type { Vehicle } from "@/lib/vehicles";

export default function EditVehicle() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const { user, ready, authFetch } = useRequireAuth();

  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready || !user) return;
    let active = true;
    authFetch<Vehicle>(`/my/vehicles/${id}/`)
      .then((data) => {
        if (active) setVehicle(data);
      })
      .catch((err) => {
        if (active) setError(getErrorMessage(err));
      });
    return () => {
      active = false;
    };
  }, [ready, user, id, authFetch]);

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  return (
    <PageShell>
      <header className="flex items-center gap-3 px-6 pb-4 pt-12">
        <button
          type="button"
          onClick={() => router.push(`/vehicles/mine/${id}`)}
          aria-label="بازگشت"
          className="press flex size-10 items-center justify-center rounded-full bg-card hover:bg-accent"
        >
          <ArrowRight className="size-5" />
        </button>
        <h1 className="text-xl font-bold">ویرایش وسیله</h1>
      </header>

      <main className="flex flex-1 flex-col px-6 pb-10">
        {error ? (
          <p
            role="alert"
            className="animate-fade-up px-2 text-sm text-destructive"
          >
            {error}
          </p>
        ) : null}

        {!vehicle && !error ? (
          <div className="flex flex-col gap-4" aria-hidden="true">
            <div className="skeleton h-14 rounded-full" />
            <div className="skeleton h-14 rounded-full" />
            <div className="skeleton h-14 rounded-full" />
            <div className="skeleton h-28 rounded-3xl" />
          </div>
        ) : null}

        {vehicle ? (
          <div className="animate-fade-up">
            <VehicleForm
              key={vehicle.id}
              vehicle={vehicle}
              onSaved={() => router.replace(`/vehicles/mine/${id}`)}
            />
          </div>
        ) : null}
      </main>
    </PageShell>
  );
}
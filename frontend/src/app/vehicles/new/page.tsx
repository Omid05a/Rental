"use client";

import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";

import { PageShell } from "@/components/page-shell";
import { VehicleForm } from "@/components/vehicle-form";
import { Button } from "@/components/ui/button";
import { useRequireAuth } from "@/lib/auth";

export default function NewVehiclePage() {
  const router = useRouter();
  const { user, ready } = useRequireAuth();

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  return (
    <PageShell>
      <header className="flex items-center gap-3 px-6 pb-4 pt-12">
        <button
          type="button"
          onClick={() => router.push("/vehicles/mine")}
          aria-label="بازگشت"
          className="press flex size-10 items-center justify-center rounded-full bg-card hover:bg-accent"
        >
          <ArrowRight className="size-5" />
        </button>
        <h1 className="text-xl font-bold">ثبت وسیله جدید</h1>
      </header>

      <main className="animate-fade-up flex flex-1 flex-col px-6 pb-10">
        {user.verification_status !== "approved" ? (
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
        ) : (
          <VehicleForm
            onSaved={(vehicle) => router.replace(`/vehicles/mine/${vehicle.id}`)}
          />
        )}
      </main>
    </PageShell>
  );
}
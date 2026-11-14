"use client";

import { ArrowRight, Printer } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
import { useRequireAuth } from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";
import { KIND_LABEL, type Vehicle } from "@/lib/vehicles";

type SheetData = { vehicle: Vehicle; code: string };

export default function QrSheet() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const { user, ready, authFetch } = useRequireAuth();

  const [data, setData] = useState<SheetData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready || !user) return;
    let active = true;
    Promise.all([
      authFetch<Vehicle>(`/my/vehicles/${id}/`),
      authFetch<{ qr_code: string }>(`/my/vehicles/${id}/qr/`),
    ])
      .then(([vehicle, qr]) => {
        if (active) setData({ vehicle, code: qr.qr_code });
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
      <header className="flex items-center gap-3 px-6 pb-4 pt-12 print:hidden">
        <button
          type="button"
          onClick={() => router.push(`/vehicles/mine/${id}`)}
          aria-label="بازگشت"
          className="flex size-10 items-center justify-center rounded-full bg-card"
        >
          <ArrowRight className="size-5" />
        </button>
        <h1 className="text-xl font-bold">QR وسیله</h1>
      </header>

      <main className="flex flex-1 flex-col gap-5 px-6 pb-10">
        {error ? (
          <p role="alert" className="px-2 text-sm text-destructive">
            {error}
          </p>
        ) : null}

        {!data && !error ? (
          <p className="text-center text-sm text-muted-foreground print:hidden">
            در حال بارگذاری…
          </p>
        ) : null}

        {data ? (
          <>
            <section className="mx-auto w-full max-w-xs rounded-3xl bg-white p-6 text-center text-black">
              <p
                className="text-lg font-semibold tracking-[0.18em]"
                style={{ fontFamily: "Poppins, system-ui, sans-serif" }}
              >
                RENTAL
              </p>

              <div className="mx-auto mt-4 w-fit rounded-xl bg-white p-2">
                <QRCodeSVG
                  value={data.code}
                  size={220}
                  level="M"
                  bgColor="#ffffff"
                  fgColor="#000000"
                />
              </div>

              <h2 className="mt-4 font-bold">{data.vehicle.title}</h2>
              <p className="mt-1 text-xs text-neutral-600">
                {KIND_LABEL[data.vehicle.kind]} · {data.vehicle.brand}{" "}
                {data.vehicle.model_name}
              </p>
              <p
                dir="ltr"
                className="mt-3 break-all text-xs tracking-wide text-neutral-700"
              >
                {data.code}
              </p>
              <p className="mt-3 text-xs leading-relaxed text-neutral-600">
                برای باز کردن قفل، این کد را در اپ رنتال اسکن کنید.
              </p>
            </section>

            <div className="flex flex-col gap-3 print:hidden">
              <Button
                onClick={() => window.print()}
                className="h-14 rounded-full text-base font-bold"
              >
                <Printer className="size-5" />
                چاپ برچسب
              </Button>
              <p className="px-2 text-sm leading-relaxed text-muted-foreground">
                برچسب را چاپ کنید و روی وسیله بچسبانید (مثلاً پشت شیشه جلوی
                خودرو یا روی بدنه دوچرخه). اسکن این کد به‌تنهایی چیزی را باز
                نمی‌کند: برای شروع سفر، رزرو فعال و نزدیک بودن به وسیله هم لازم
                است.
              </p>
            </div>
          </>
        ) : null}
      </main>
    </PageShell>
  );
}
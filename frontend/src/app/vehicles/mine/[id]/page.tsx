"use client";

import { ArrowRight, ImagePlus, Trash2 } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type ChangeEvent } from "react";

import { PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
import { useRequireAuth } from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";
import { formatToman, toFa } from "@/lib/format";
import {
  APPROVAL,
  FUEL_LABEL,
  KIND_LABEL,
  TRANSMISSION_LABEL,
  type Vehicle,
} from "@/lib/vehicles";

const MAX_PHOTOS = 6;
const MAX_BYTES = 5 * 1024 * 1024;

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-end font-medium">{value}</dd>
    </div>
  );
}

export default function ManageVehiclePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const { user, ready, authFetch } = useRequireAuth();

  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [uploading, setUploading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setVehicle(await authFetch<Vehicle>(`/my/vehicles/${id}/`));
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [authFetch, id]);

  useEffect(() => {
    if (ready && user) {
      void load();
    }
  }, [ready, user, load]);

  async function handleFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (!vehicle || files.length === 0) return;

    const slots = MAX_PHOTOS - vehicle.photos.length;
    const selected = files.slice(0, slots);
    if (files.length > slots) {
      setError(`حداکثر ${toFa(MAX_PHOTOS)} عکس مجاز است.`);
    } else {
      setError(null);
    }

    setUploading(true);
    try {
      for (const file of selected) {
        if (file.size > MAX_BYTES) {
          setError("حجم هر عکس باید کمتر از ۵ مگابایت باشد.");
          continue;
        }
        const body = new FormData();
        body.append("image", file);
        await authFetch(`/my/vehicles/${id}/photos/`, { method: "POST", body });
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setUploading(false);
      await load();
    }
  }

  async function deletePhoto(photoId: number) {
    setBusy(true);
    setError(null);
    try {
      await authFetch(`/my/vehicles/${id}/photos/${photoId}/`, {
        method: "DELETE",
      });
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive() {
    if (!vehicle) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await authFetch<Vehicle>(`/my/vehicles/${id}/`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !vehicle.is_active }),
      });
      setVehicle(updated);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  const status = vehicle ? APPROVAL[vehicle.approval_status] : null;
  const isCar = vehicle?.kind === "car";

  return (
    <PageShell>
      <header className="flex items-center gap-3 px-6 pb-4 pt-12">
        <button
          type="button"
          onClick={() => router.push("/vehicles/mine")}
          aria-label="بازگشت"
          className="flex size-10 items-center justify-center rounded-full bg-card"
        >
          <ArrowRight className="size-5" />
        </button>
        <h1 className="truncate text-xl font-bold">
          {vehicle?.title ?? "مدیریت وسیله"}
        </h1>
      </header>

      <main className="flex flex-1 flex-col gap-5 px-6 pb-10">
        {error ? (
          <p role="alert" className="px-2 text-sm text-destructive">
            {error}
          </p>
        ) : null}

        {!vehicle && !error ? (
          <p className="text-center text-sm text-muted-foreground">
            در حال بارگذاری…
          </p>
        ) : null}

        {vehicle && status ? (
          <>
            <section className="flex flex-col gap-3 rounded-3xl bg-card p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-semibold">وضعیت</h2>
                <span
                  className={`rounded-full px-3 py-0.5 text-xs font-medium ${status.className}`}
                >
                  {status.label}
                </span>
              </div>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {status.hint}
              </p>
              {vehicle.approval_status === "rejected" &&
              vehicle.rejection_reason ? (
                <p className="rounded-2xl bg-red-500/10 p-3 text-sm text-red-400">
                  دلیل: {vehicle.rejection_reason}
                </p>
              ) : null}
              {vehicle.approval_status === "approved" ? (
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={toggleActive}
                  className="h-12 rounded-full border-border bg-secondary font-medium"
                >
                  {vehicle.is_active
                    ? "غیرفعال کردن (عدم نمایش در جستجو)"
                    : "فعال کردن"}
                </Button>
              ) : null}
            </section>

            <section className="flex flex-col gap-3">
              <div className="flex items-center justify-between px-2">
                <h2 className="font-semibold">عکس‌ها</h2>
                <span className="text-xs text-muted-foreground">
                  {toFa(vehicle.photos.length)} از {toFa(MAX_PHOTOS)}
                </span>
              </div>

              {vehicle.photos.length === 0 ? (
                <p className="px-2 text-sm text-muted-foreground">
                  حداقل یک عکس واضح از وسیله اضافه کنید.
                </p>
              ) : null}

              <ul className="grid grid-cols-3 gap-2">
                {vehicle.photos.map((photo) => (
                  <li
                    key={photo.id}
                    className="relative aspect-square overflow-hidden rounded-2xl bg-card"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={photo.image}
                      alt=""
                      className="size-full object-cover"
                    />
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => deletePhoto(photo.id)}
                      aria-label="حذف عکس"
                      className="absolute end-1.5 top-1.5 flex size-8 items-center justify-center rounded-full bg-black/60 text-white"
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </li>
                ))}
              </ul>

              {vehicle.photos.length < MAX_PHOTOS ? (
                <label
                  className={`flex h-14 cursor-pointer items-center justify-center gap-2 rounded-full bg-primary font-bold text-primary-foreground ${
                    uploading ? "pointer-events-none opacity-60" : ""
                  }`}
                >
                  <ImagePlus className="size-5" />
                  {uploading ? "در حال ارسال…" : "افزودن عکس"}
                  <input
                    type="file"
                    multiple
                    accept="image/jpeg,image/png,image/webp"
                    className="sr-only"
                    disabled={uploading}
                    onChange={handleFiles}
                  />
                </label>
              ) : null}
            </section>

            <section className="rounded-3xl bg-card px-5 py-3">
              <dl className="divide-y divide-border">
                <Row label="نوع" value={KIND_LABEL[vehicle.kind]} />
                <Row
                  label="برند و مدل"
                  value={`${vehicle.brand} ${vehicle.model_name}`}
                />
                {vehicle.year ? (
                  <Row label="سال ساخت" value={toFa(vehicle.year)} />
                ) : null}
                {isCar && vehicle.transmission ? (
                  <Row
                    label="گیربکس"
                    value={TRANSMISSION_LABEL[vehicle.transmission]}
                  />
                ) : null}
                {isCar && vehicle.fuel_type ? (
                  <Row label="سوخت" value={FUEL_LABEL[vehicle.fuel_type]} />
                ) : null}
                {isCar && vehicle.seats ? (
                  <Row label="تعداد صندلی" value={toFa(vehicle.seats)} />
                ) : null}
                <Row
                  label="قیمت ساعتی"
                  value={formatToman(vehicle.price_per_hour)}
                />
                <Row
                  label="قیمت روزانه"
                  value={formatToman(vehicle.price_per_day)}
                />
                <Row label="سپرده" value={formatToman(vehicle.deposit)} />
                {isCar && vehicle.daily_km_limit ? (
                  <Row
                    label="سقف کیلومتر روزانه"
                    value={toFa(vehicle.daily_km_limit)}
                  />
                ) : null}
                <Row label="آدرس" value={vehicle.address} />
              </dl>
            </section>
          </>
        ) : null}
      </main>
    </PageShell>
  );
}
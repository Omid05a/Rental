"use client";

import { ArrowRight } from "lucide-react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import {
  DigitsInput,
  Field,
  INPUT_CLASS,
  SegmentedControl,
} from "@/components/form-bits";
import type { LatLng } from "@/components/map/location-picker";
import { PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";
import { formatToman } from "@/lib/format";
import {
  FUEL_LABEL,
  KIND_LABEL,
  TRANSMISSION_LABEL,
  type FuelType,
  type Transmission,
  type Vehicle,
  type VehicleKind,
} from "@/lib/vehicles";

// Leaflet needs the browser, so the map is loaded on the client only.
const LocationPicker = dynamic(
  () => import("@/components/map/location-picker"),
  {
    ssr: false,
    loading: () => <div className="h-72 animate-pulse rounded-3xl bg-card" />,
  },
);

type FormState = {
  kind: VehicleKind;
  title: string;
  brand: string;
  model_name: string;
  year: string;
  description: string;
  transmission: Transmission;
  fuel_type: FuelType;
  seats: string;
  insurance_expiry: string;
  price_per_hour: string;
  price_per_day: string;
  deposit: string;
  daily_km_limit: string;
  min_fuel_percent: string;
  address: string;
};

const INITIAL: FormState = {
  kind: "car",
  title: "",
  brand: "",
  model_name: "",
  year: "",
  description: "",
  transmission: "automatic",
  fuel_type: "gasoline",
  seats: "5",
  insurance_expiry: "",
  price_per_hour: "",
  price_per_day: "",
  deposit: "",
  daily_km_limit: "",
  min_fuel_percent: "25",
  address: "",
};

function todayIso() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function toNumberOrNull(value: string) {
  return value ? Number(value) : null;
}

function validate(form: FormState, point: LatLng | null) {
  const errors: Record<string, string> = {};
  const hourly = Number(form.price_per_hour);
  const daily = Number(form.price_per_day);

  if (form.title.trim().length < 3) {
    errors.title = "عنوان آگهی را وارد کنید (حداقل ۳ حرف).";
  }
  if (!form.brand.trim()) errors.brand = "برند را وارد کنید.";
  if (!form.model_name.trim()) errors.model_name = "مدل را وارد کنید.";
  if (form.year && (Number(form.year) < 1950 || Number(form.year) > 2100)) {
    errors.year = "سال ساخت معتبر نیست.";
  }
  if (!hourly) errors.price_per_hour = "قیمت ساعتی را وارد کنید.";
  if (!daily) {
    errors.price_per_day = "قیمت روزانه را وارد کنید.";
  } else if (hourly && daily > hourly * 24) {
    errors.price_per_day =
      "قیمت روزانه نمی‌تواند بیشتر از ۲۴ برابر قیمت ساعتی باشد.";
  }

  if (form.kind === "car") {
    const seats = Number(form.seats);
    if (!seats || seats < 1 || seats > 12) {
      errors.seats = "تعداد صندلی باید بین ۱ تا ۱۲ باشد.";
    }
    if (!form.insurance_expiry) {
      errors.insurance_expiry = "تاریخ انقضای بیمه شخص ثالث را وارد کنید.";
    } else if (form.insurance_expiry < todayIso()) {
      errors.insurance_expiry = "بیمه‌نامه منقضی شده است.";
    }
    if (form.min_fuel_percent && Number(form.min_fuel_percent) > 100) {
      errors.min_fuel_percent = "عدد باید بین ۰ تا ۱۰۰ باشد.";
    }
  }

  if (!point) errors.location = "محل تحویل را روی نقشه مشخص کنید.";
  if (!form.address.trim()) errors.address = "آدرس محل تحویل را وارد کنید.";
  return errors;
}

function serverFieldErrors(error: unknown) {
  const result: Record<string, string> = {};
  if (error instanceof ApiError && error.data && typeof error.data === "object") {
    for (const key of Object.keys(error.data as object)) {
      if (key !== "detail" && key !== "code") {
        result[key] = "مقدار واردشده معتبر نیست.";
      }
    }
  }
  return result;
}

export default function NewVehiclePage() {
  const router = useRouter();
  const { user, ready, authFetch } = useRequireAuth();

  const [form, setForm] = useState<FormState>(INITIAL);
  const [point, setPoint] = useState<LatLng | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((previous) => ({ ...previous, [key]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);

    const found = validate(form, point);
    setErrors(found);
    if (Object.keys(found).length > 0 || !point) {
      setFormError("لطفاً موارد مشخص‌شده را اصلاح کنید.");
      return;
    }

    const carOnly =
      form.kind === "car"
        ? {
            transmission: form.transmission,
            fuel_type: form.fuel_type,
            seats: Number(form.seats),
            insurance_expiry: form.insurance_expiry,
            daily_km_limit: toNumberOrNull(form.daily_km_limit),
            min_fuel_percent: toNumberOrNull(form.min_fuel_percent),
          }
        : {};

    const payload = {
      kind: form.kind,
      title: form.title.trim(),
      brand: form.brand.trim(),
      model_name: form.model_name.trim(),
      year: toNumberOrNull(form.year),
      description: form.description.trim(),
      price_per_hour: Number(form.price_per_hour),
      price_per_day: Number(form.price_per_day),
      deposit: Number(form.deposit || 0),
      latitude: point.lat,
      longitude: point.lng,
      address: form.address.trim(),
      ...carOnly,
    };

    setSubmitting(true);
    try {
      const created = await authFetch<Vehicle>("/my/vehicles/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      router.replace(`/vehicles/mine/${created.id}`);
    } catch (err) {
      setErrors(serverFieldErrors(err));
      setFormError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  const isCar = form.kind === "car";

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
        <h1 className="text-xl font-bold">ثبت وسیله جدید</h1>
      </header>

      <main className="flex flex-1 flex-col px-6 pb-10">
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
          <form onSubmit={handleSubmit} className="flex flex-col gap-6">
            <Field label="نوع وسیله">
              <SegmentedControl
                label="نوع وسیله"
                value={form.kind}
                onChange={(value) => set("kind", value)}
                options={[
                  { value: "car", label: KIND_LABEL.car },
                  { value: "bike", label: KIND_LABEL.bike },
                ]}
              />
            </Field>

            <Field label="عنوان آگهی" htmlFor="title" error={errors.title}>
              <Input
                id="title"
                className={INPUT_CLASS}
                placeholder={isCar ? "مثلاً: پژو ۲۰۶ تیپ ۵" : "مثلاً: دوچرخه شهری"}
                value={form.title}
                onChange={(event) => set("title", event.target.value)}
              />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="برند" htmlFor="brand" error={errors.brand}>
                <Input
                  id="brand"
                  className={INPUT_CLASS}
                  value={form.brand}
                  onChange={(event) => set("brand", event.target.value)}
                />
              </Field>
              <Field label="مدل" htmlFor="model_name" error={errors.model_name}>
                <Input
                  id="model_name"
                  className={INPUT_CLASS}
                  value={form.model_name}
                  onChange={(event) => set("model_name", event.target.value)}
                />
              </Field>
            </div>

            <Field
              label="سال ساخت (اختیاری)"
              htmlFor="year"
              error={errors.year}
            >
              <DigitsInput
                id="year"
                maxLength={4}
                placeholder="مثلاً ۲۰۱۸"
                value={form.year}
                onChange={(value) => set("year", value)}
              />
            </Field>

            <Field label="توضیحات (اختیاری)" htmlFor="description">
              <Textarea
                id="description"
                className="min-h-28 rounded-3xl border-0 bg-card p-4 text-base"
                value={form.description}
                onChange={(event) => set("description", event.target.value)}
              />
            </Field>

            {isCar ? (
              <>
                <Field label="گیربکس">
                  <SegmentedControl
                    label="گیربکس"
                    value={form.transmission}
                    onChange={(value) => set("transmission", value)}
                    options={(
                      Object.keys(TRANSMISSION_LABEL) as Transmission[]
                    ).map((value) => ({
                      value,
                      label: TRANSMISSION_LABEL[value],
                    }))}
                  />
                </Field>

                <Field label="نوع سوخت">
                  <SegmentedControl
                    label="نوع سوخت"
                    value={form.fuel_type}
                    onChange={(value) => set("fuel_type", value)}
                    options={(Object.keys(FUEL_LABEL) as FuelType[]).map(
                      (value) => ({ value, label: FUEL_LABEL[value] }),
                    )}
                  />
                </Field>

                <div className="grid grid-cols-2 gap-3">
                  <Field label="تعداد صندلی" htmlFor="seats" error={errors.seats}>
                    <DigitsInput
                      id="seats"
                      maxLength={2}
                      value={form.seats}
                      onChange={(value) => set("seats", value)}
                    />
                  </Field>
                  <Field
                    label="انقضای بیمه شخص ثالث"
                    htmlFor="insurance_expiry"
                    error={errors.insurance_expiry}
                  >
                    <Input
                      id="insurance_expiry"
                      type="date"
                      dir="ltr"
                      style={{ colorScheme: "dark" }}
                      className={INPUT_CLASS}
                      value={form.insurance_expiry}
                      onChange={(event) =>
                        set("insurance_expiry", event.target.value)
                      }
                    />
                  </Field>
                </div>
              </>
            ) : null}

            <Field
              label="قیمت هر ساعت (تومان)"
              htmlFor="price_per_hour"
              error={errors.price_per_hour}
              hint={
                form.price_per_hour
                  ? formatToman(Number(form.price_per_hour))
                  : undefined
              }
            >
              <DigitsInput
                id="price_per_hour"
                value={form.price_per_hour}
                onChange={(value) => set("price_per_hour", value)}
              />
            </Field>

            <Field
              label="قیمت هر روز (تومان)"
              htmlFor="price_per_day"
              error={errors.price_per_day}
              hint={
                form.price_per_day
                  ? formatToman(Number(form.price_per_day))
                  : "معمولاً کمتر از ۲۴ برابر قیمت ساعتی است."
              }
            >
              <DigitsInput
                id="price_per_day"
                value={form.price_per_day}
                onChange={(value) => set("price_per_day", value)}
              />
            </Field>

            <Field
              label="مبلغ سپرده (تومان، اختیاری)"
              htmlFor="deposit"
              error={errors.deposit}
              hint={
                form.deposit ? formatToman(Number(form.deposit)) : undefined
              }
            >
              <DigitsInput
                id="deposit"
                value={form.deposit}
                onChange={(value) => set("deposit", value)}
              />
            </Field>

            {isCar ? (
              <div className="grid grid-cols-2 gap-3">
                <Field
                  label="سقف کیلومتر روزانه"
                  htmlFor="daily_km_limit"
                  error={errors.daily_km_limit}
                >
                  <DigitsInput
                    id="daily_km_limit"
                    placeholder="مثلاً ۲۵۰"
                    value={form.daily_km_limit}
                    onChange={(value) => set("daily_km_limit", value)}
                  />
                </Field>
                <Field
                  label="حداقل بنزین (درصد)"
                  htmlFor="min_fuel_percent"
                  error={errors.min_fuel_percent}
                >
                  <DigitsInput
                    id="min_fuel_percent"
                    maxLength={3}
                    value={form.min_fuel_percent}
                    onChange={(value) => set("min_fuel_percent", value)}
                  />
                </Field>
              </div>
            ) : null}

            <Field
              label="محل تحویل"
              error={errors.location}
              hint="روی نقشه ضربه بزنید یا نشانگر را بکشید. وسیله باید در پایان سفر به همین محل برگردد."
            >
              <LocationPicker value={point} onChange={setPoint} />
            </Field>

            <Field label="آدرس محل تحویل" htmlFor="address" error={errors.address}>
              <Input
                id="address"
                className={INPUT_CLASS}
                placeholder="مثلاً: میدان ولیعصر، کوچه ..."
                value={form.address}
                onChange={(event) => set("address", event.target.value)}
              />
            </Field>

            {formError ? (
              <p role="alert" className="px-2 text-sm text-destructive">
                {formError}
              </p>
            ) : null}

            <Button
              type="submit"
              disabled={submitting}
              className="h-14 w-full rounded-full text-base font-bold"
            >
              {submitting ? "در حال ثبت…" : "ثبت وسیله"}
            </Button>
            <p className="text-center text-xs text-muted-foreground">
              بعد از ثبت، عکس‌ها را اضافه می‌کنید و وسیله برای تأیید بررسی می‌شود.
            </p>
          </form>
        )}
      </main>
    </PageShell>
  );
}
"use client";

import { LoaderCircle } from "lucide-react";
import dynamic from "next/dynamic";
import { useMemo, useState, type FormEvent } from "react";

import { JalaliDatePicker } from "@/components/booking-pickers";
import {
  DigitsInput,
  Field,
  INPUT_CLASS,
  SegmentedControl,
} from "@/components/form-bits";
import type { LatLng } from "@/components/map/location-picker";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";
import { formatToman } from "@/lib/format";
import { buildDayWindow, formatJalaliDate } from "@/lib/jalali";
import {
  FUEL_LABEL,
  KIND_LABEL,
  TRANSMISSION_LABEL,
  YEAR_MAX,
  YEAR_MIN,
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
    loading: () => <div className="skeleton h-72 rounded-3xl" />,
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

function initialState(vehicle?: Vehicle): FormState {
  if (!vehicle) return INITIAL;
  return {
    kind: vehicle.kind,
    title: vehicle.title,
    brand: vehicle.brand,
    model_name: vehicle.model_name,
    year: vehicle.year ? String(vehicle.year) : "",
    description: vehicle.description,
    transmission: vehicle.transmission || "automatic",
    fuel_type: vehicle.fuel_type || "gasoline",
    seats: vehicle.seats ? String(vehicle.seats) : "5",
    insurance_expiry: vehicle.insurance_expiry ?? "",
    price_per_hour: String(vehicle.price_per_hour),
    price_per_day: String(vehicle.price_per_day),
    deposit: String(vehicle.deposit),
    daily_km_limit: vehicle.daily_km_limit ? String(vehicle.daily_km_limit) : "",
    min_fuel_percent:
      vehicle.min_fuel_percent !== null ? String(vehicle.min_fuel_percent) : "",
    address: vehicle.address,
  };
}

function toNumberOrNull(value: string) {
  return value ? Number(value) : null;
}

function todayIso() {
  return buildDayWindow(1)[0].iso;
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
  if (
    form.year &&
    (Number(form.year) < YEAR_MIN || Number(form.year) > YEAR_MAX)
  ) {
    errors.year = "سال ساخت را به شمسی وارد کنید (مثلاً ۱۳۹۹).";
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
      errors.insurance_expiry = "تاریخ انقضای بیمه شخص ثالث را انتخاب کنید.";
    } else if (form.insurance_expiry < todayIso()) {
      errors.insurance_expiry =
        "بیمه‌نامه منقضی شده است. تاریخ جدید را انتخاب کنید.";
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
        result[key] =
          key === "latitude"
            ? "مکان وسیله تا زمانی که رزرو آینده یا فعال دارد قابل تغییر نیست."
            : "مقدار واردشده معتبر نیست.";
      }
    }
  }
  return result;
}

function moved(a: LatLng, b: LatLng) {
  return Math.abs(a.lat - b.lat) > 1e-6 || Math.abs(a.lng - b.lng) > 1e-6;
}

type Props = {
  /** When set, the form edits this vehicle instead of creating a new one. */
  vehicle?: Vehicle;
  onSaved: (vehicle: Vehicle) => void;
};

export function VehicleForm({ vehicle, onSaved }: Props) {
  const { authFetch } = useAuth();
  const isEdit = !!vehicle;

  const [form, setForm] = useState<FormState>(() => initialState(vehicle));
  const [initialPoint] = useState<LatLng | null>(() =>
    vehicle ? { lat: vehicle.latitude, lng: vehicle.longitude } : null,
  );
  const [point, setPoint] = useState<LatLng | null>(initialPoint);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const insuranceDays = useMemo(() => buildDayWindow(731), []);
  const locationLocked = vehicle?.location_locked ?? false;
  const isCar = form.kind === "car";

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

    const carOnly = isCar
      ? {
          transmission: form.transmission,
          fuel_type: form.fuel_type,
          seats: Number(form.seats),
          insurance_expiry: form.insurance_expiry,
          daily_km_limit: toNumberOrNull(form.daily_km_limit),
          min_fuel_percent: toNumberOrNull(form.min_fuel_percent),
        }
      : {};

    // When editing, the location is sent only if the owner actually moved it.
    const sendLocation = !isEdit || (initialPoint && moved(point, initialPoint));
    const location = sendLocation
      ? { latitude: point.lat, longitude: point.lng }
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
      address: form.address.trim(),
      ...location,
      ...carOnly,
    };

    setSubmitting(true);
    try {
      const saved = await authFetch<Vehicle>(
        vehicle ? `/my/vehicles/${vehicle.id}/` : "/my/vehicles/",
        {
          method: vehicle ? "PATCH" : "POST",
          body: JSON.stringify(payload),
        },
      );
      onSaved(saved);
    } catch (err) {
      setErrors(serverFieldErrors(err));
      setFormError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6">
      {vehicle?.approval_status === "approved" ? (
        <p className="animate-scale-in rounded-2xl bg-primary/10 p-4 text-sm leading-relaxed">
          اگر عنوان، برند، مدل، سال ساخت، توضیحات، آدرس یا مکان وسیله را تغییر
          دهید، وسیله دوباره بررسی می‌شود و تا تأیید، در جستجو نمایش داده
          نمی‌شود. تغییر قیمت و قوانین نیازی به بررسی ندارد.
        </p>
      ) : null}

      {vehicle?.approval_status === "rejected" ? (
        <div className="animate-scale-in flex flex-col gap-2 rounded-2xl bg-red-500/10 p-4 text-sm leading-relaxed text-red-300">
          <p>
            این وسیله تأیید نشد
            {vehicle.rejection_reason
              ? `: ${vehicle.rejection_reason}`
              : "."}
          </p>
          <p>بعد از ذخیره تغییرات، وسیله دوباره برای بررسی ارسال می‌شود.</p>
        </div>
      ) : null}

      <Field label="نوع وسیله">
        {isEdit ? (
          <p className="rounded-full bg-card px-5 py-4 text-base">
            {KIND_LABEL[form.kind]}
            <span className="ms-2 text-xs text-muted-foreground">
              (بعد از ثبت قابل تغییر نیست)
            </span>
          </p>
        ) : (
          <SegmentedControl
            label="نوع وسیله"
            value={form.kind}
            onChange={(value) => set("kind", value)}
            options={[
              { value: "car", label: KIND_LABEL.car },
              { value: "bike", label: KIND_LABEL.bike },
            ]}
          />
        )}
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

      <Field label="سال ساخت (شمسی، اختیاری)" htmlFor="year" error={errors.year}>
        <DigitsInput
          id="year"
          maxLength={4}
          placeholder="مثلاً ۱۳۹۹"
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
        <div className="animate-fade-up flex flex-col gap-6">
          <Field label="گیربکس">
            <SegmentedControl
              label="گیربکس"
              value={form.transmission}
              onChange={(value) => set("transmission", value)}
              options={(Object.keys(TRANSMISSION_LABEL) as Transmission[]).map(
                (value) => ({ value, label: TRANSMISSION_LABEL[value] }),
              )}
            />
          </Field>

          <Field label="نوع سوخت">
            <SegmentedControl
              label="نوع سوخت"
              value={form.fuel_type}
              onChange={(value) => set("fuel_type", value)}
              options={(Object.keys(FUEL_LABEL) as FuelType[]).map((value) => ({
                value,
                label: FUEL_LABEL[value],
              }))}
            />
          </Field>

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
            error={errors.insurance_expiry}
            hint={
              form.insurance_expiry
                ? formatJalaliDate(form.insurance_expiry)
                : "آخرین روز اعتبار بیمه‌نامه را انتخاب کنید."
            }
          >
            <JalaliDatePicker
              days={insuranceDays}
              selected={form.insurance_expiry || null}
              onSelect={(iso) => set("insurance_expiry", iso)}
            />
          </Field>
        </div>
      ) : null}

      <Field
        label="قیمت هر ساعت (تومان)"
        htmlFor="price_per_hour"
        error={errors.price_per_hour}
        hint={
          form.price_per_hour ? formatToman(Number(form.price_per_hour)) : undefined
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
        hint={form.deposit ? formatToman(Number(form.deposit)) : undefined}
      >
        <DigitsInput
          id="deposit"
          value={form.deposit}
          onChange={(value) => set("deposit", value)}
        />
      </Field>

      {isCar ? (
        <div className="animate-fade-up grid grid-cols-2 gap-3">
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
        error={errors.location ?? errors.latitude}
        hint={
          locationLocked
            ? "تا زمانی که این وسیله رزرو آینده یا فعال دارد، مکان آن قابل تغییر نیست. آدرس را می‌توانید اصلاح کنید."
            : "روی نقشه ضربه بزنید یا نشانگر را بکشید. وسیله باید در پایان سفر به همین محل برگردد."
        }
      >
        <LocationPicker
          value={point}
          onChange={setPoint}
          readOnly={locationLocked}
        />
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
        <p
          role="alert"
          className="animate-fade-up px-2 text-sm text-destructive"
        >
          {formError}
        </p>
      ) : null}

      <Button
        type="submit"
        disabled={submitting}
        className="h-14 w-full rounded-full text-base font-bold"
      >
        {submitting ? <LoaderCircle className="animate-spin" /> : null}
        {submitting
          ? "در حال ذخیره…"
          : isEdit
            ? "ذخیره تغییرات"
            : "ثبت وسیله"}
      </Button>
      {!isEdit ? (
        <p className="text-center text-xs text-muted-foreground">
          بعد از ثبت، عکس‌ها را اضافه می‌کنید و وسیله برای تأیید بررسی می‌شود.
        </p>
      ) : null}
    </form>
  );
}
"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  JalaliDatePicker,
  Stepper,
  TimeSelect,
} from "@/components/booking-pickers";
import { Field } from "@/components/form-bits";
import { PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import type { Booking, BusyRange, Quote, Terms } from "@/lib/bookings";
import { getErrorMessage } from "@/lib/errors";
import { formatToman, toFa } from "@/lib/format";
import { createAttemptKeys } from "@/lib/idempotency";
import {
  buildDayWindow,
  formatJalaliDateTime,
  nextFullHour,
  tehranParts,
  toTehranIso,
} from "@/lib/jalali";
import type { Vehicle } from "@/lib/vehicles";

const MAX_ADVANCE_DAYS = 90;
const MAX_DAYS = 14;

const PRESETS = [
  { label: "۱ ساعت", days: 0, hours: 1 },
  { label: "۳ ساعت", days: 0, hours: 3 },
  { label: "۶ ساعت", days: 0, hours: 6 },
  { label: "۱۲ ساعت", days: 0, hours: 12 },
  { label: "۱ روز", days: 1, hours: 0 },
  { label: "۲ روز", days: 2, hours: 0 },
  { label: "۷ روز", days: 7, hours: 0 },
];

type QuoteResult = {
  key: string;
  quote: Quote | null;
  error: string | null;
};

function SummaryRow({
  label,
  value,
  strong = false,
}: {
  label: string;
  value: string;
  strong?: boolean;
}) {
  return (
    <div
      className={`flex items-center justify-between gap-4 py-2 text-sm ${
        strong ? "font-bold" : ""
      }`}
    >
      <dt className={strong ? "" : "text-muted-foreground"}>{label}</dt>
      <dd className="text-end">{value}</dd>
    </div>
  );
}

export default function BookingFlow() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const { user, ready, authFetch } = useRequireAuth();

  const days = useMemo(() => buildDayWindow(MAX_ADVANCE_DAYS + 1), []);
  const [initial] = useState(() => tehranParts(nextFullHour()));

  const [dateIso, setDateIso] = useState(initial.dateIso);
  const [hour, setHour] = useState(initial.hour);
  const [minute, setMinute] = useState(0);
  const [dayCount, setDayCount] = useState(0);
  const [hourCount, setHourCount] = useState(2);

  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [terms, setTerms] = useState<Terms | null>(null);
  const [busy, setBusy] = useState<BusyRange[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [quoteResult, setQuoteResult] = useState<QuoteResult | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [attempts] = useState(createAttemptKeys);

  const minutes = dayCount * 1440 + hourCount * 60;
  const startIso = toTehranIso(dateIso, hour, minute);
  const endDate = new Date(new Date(startIso).getTime() + minutes * 60_000);
  const quoteKey = `${startIso}|${minutes}`;

  useEffect(() => {
    let active = true;
    Promise.all([
      apiFetch<Vehicle>(`/vehicles/${id}/`),
      apiFetch<Terms>("/terms/"),
      apiFetch<BusyRange[]>(`/vehicles/${id}/busy/`),
    ])
      .then(([vehicleData, termsData, busyData]) => {
        if (!active) return;
        setVehicle(vehicleData);
        setTerms(termsData);
        setBusy(busyData);
      })
      .catch((err) => {
        if (active) setLoadError(getErrorMessage(err));
      });
    return () => {
      active = false;
    };
  }, [id]);

  useEffect(() => {
    if (!ready || !user) return;
    let active = true;
    const timer = setTimeout(() => {
      const startAt = new Date(startIso);
      const endAt = new Date(startAt.getTime() + minutes * 60_000);
      authFetch<Quote>("/bookings/quote/", {
        method: "POST",
        body: JSON.stringify({
          vehicle: Number(id),
          start_at: startAt.toISOString(),
          end_at: endAt.toISOString(),
        }),
      })
        .then((quote) => {
          if (active) setQuoteResult({ key: quoteKey, quote, error: null });
        })
        .catch((err) => {
          if (active) {
            setQuoteResult({
              key: quoteKey,
              quote: null,
              error: getErrorMessage(err),
            });
          }
        });
    }, 400);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [ready, user, id, startIso, minutes, quoteKey, authFetch]);

  const quoteLoading = quoteResult?.key !== quoteKey;
  const quote = quoteLoading ? null : (quoteResult?.quote ?? null);
  const quoteError = quoteLoading ? null : (quoteResult?.error ?? null);

  function changeDays(value: number) {
    setDayCount(value);
    if (value === MAX_DAYS) {
      setHourCount(0);
    } else if (value === 0 && hourCount === 0) {
      setHourCount(1);
    }
  }

  async function handleSubmit() {
    if (!quote) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const startAt = new Date(startIso).toISOString();
      const endAt = endDate.toISOString();
      const booking = await authFetch<Booking>("/bookings/", {
        method: "POST",
        headers: {
          "Idempotency-Key": attempts.get(`${id}|${startAt}|${endAt}`),
        },
        body: JSON.stringify({
          vehicle: Number(id),
          start_at: startAt,
          end_at: endAt,
          accept_terms: true,
          terms_version: quote.terms_version,
        }),
      });
      router.replace(`/bookings/${booking.id}`);
    } catch (err) {
      setSubmitError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  const canSubmit =
    !!quote && quote.enough_funds && accepted && !submitting && !quoteLoading;

  return (
    <PageShell>
      <header className="flex items-center gap-3 px-6 pb-4 pt-12">
        <button
          type="button"
          onClick={() => router.push(`/vehicles/${id}`)}
          aria-label="بازگشت"
          className="flex size-10 items-center justify-center rounded-full bg-card"
        >
          <ArrowRight className="size-5" />
        </button>
        <h1 className="text-xl font-bold">رزرو</h1>
      </header>

      <main className="flex flex-1 flex-col gap-6 px-6 pb-44">
        {loadError ? (
          <p role="alert" className="px-2 text-sm text-destructive">
            {loadError}
          </p>
        ) : null}

        {vehicle ? (
          <div className="rounded-3xl bg-card p-4">
            <h2 className="font-semibold">{vehicle.title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {formatToman(vehicle.price_per_hour)} / ساعت ·{" "}
              {formatToman(vehicle.price_per_day)} / روز
            </p>
          </div>
        ) : null}

        <Field label="تاریخ شروع">
          <JalaliDatePicker
            days={days}
            selected={dateIso}
            onSelect={setDateIso}
          />
        </Field>

        <Field label="ساعت شروع">
          <TimeSelect
            hour={hour}
            minute={minute}
            onChange={(nextHour, nextMinute) => {
              setHour(nextHour);
              setMinute(nextMinute);
            }}
          />
        </Field>

        <Field label="مدت اجاره">
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((preset) => {
              const active =
                preset.days === dayCount && preset.hours === hourCount;
              return (
                <button
                  key={preset.label}
                  type="button"
                  aria-pressed={active}
                  onClick={() => {
                    setDayCount(preset.days);
                    setHourCount(preset.hours);
                  }}
                  className={`h-9 rounded-full px-4 text-sm font-medium ${
                    active
                      ? "bg-primary text-primary-foreground"
                      : "bg-card"
                  }`}
                >
                  {preset.label}
                </button>
              );
            })}
          </div>
          <div className="flex gap-3">
            <Stepper
              label="روز"
              value={dayCount}
              min={0}
              max={MAX_DAYS}
              onChange={changeDays}
            />
            <Stepper
              label="ساعت"
              value={hourCount}
              min={dayCount === 0 ? 1 : 0}
              max={dayCount === MAX_DAYS ? 0 : 23}
              onChange={setHourCount}
            />
          </div>
        </Field>

        <section className="rounded-3xl bg-card p-5 text-sm">
          <dl className="divide-y divide-border">
            <SummaryRow label="شروع" value={formatJalaliDateTime(startIso)} />
            <SummaryRow label="پایان" value={formatJalaliDateTime(endDate)} />
          </dl>
          <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
            بعد از پایان اجاره، ۳۰ دقیقه برای آماده‌سازی وسیله در نظر گرفته
            می‌شود و در این مدت رزرو دیگری ثبت نمی‌شود.
          </p>
        </section>

        {busy.length > 0 ? (
          <section className="rounded-3xl bg-card p-5">
            <h3 className="font-semibold">زمان‌های غیرقابل رزرو</h3>
            <ul className="mt-2 flex flex-col gap-1.5 text-xs text-muted-foreground">
              {busy.slice(0, 5).map((range) => (
                <li key={range.start}>
                  {formatJalaliDateTime(range.start)} تا{" "}
                  {formatJalaliDateTime(range.end)}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="rounded-3xl bg-card p-5">
          <h3 className="mb-1 font-semibold">هزینه</h3>
          {quoteLoading ? (
            <p className="py-3 text-sm text-muted-foreground">
              در حال محاسبه…
            </p>
          ) : null}
          {quoteError ? (
            <p role="alert" className="py-3 text-sm text-destructive">
              {quoteError}
            </p>
          ) : null}
          {quote ? (
            <>
              <dl className="divide-y divide-border">
                <SummaryRow
                  label={`اجاره (${toFa(quote.hours)} ساعت)`}
                  value={formatToman(quote.rental_amount)}
                />
                <SummaryRow
                  label="سپرده (بازگشت‌پذیر)"
                  value={
                    quote.deposit_amount > 0
                      ? formatToman(quote.deposit_amount)
                      : "بدون سپرده"
                  }
                />
                <SummaryRow
                  label="جمع قابل پرداخت"
                  value={formatToman(quote.total)}
                  strong
                />
                <SummaryRow
                  label="موجودی کیف پول"
                  value={formatToman(quote.wallet_balance)}
                />
              </dl>
              {!quote.enough_funds ? (
                <div className="mt-3 flex flex-col gap-2 rounded-2xl bg-red-500/10 p-3 text-sm text-red-400">
                  <p>موجودی کیف پول کافی نیست.</p>
                  <Link href="/wallet" className="font-medium underline">
                    افزایش موجودی
                  </Link>
                </div>
              ) : null}
              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                لغو رایگان تا {formatJalaliDateTime(quote.free_cancellation_until)}
              </p>
            </>
          ) : null}
        </section>

        {terms ? (
          <section className="rounded-3xl bg-card p-5">
            <h3 className="font-semibold">قوانین و شرایط اجاره</h3>
            <div className="mt-2 flex flex-col divide-y divide-border">
              {terms.sections.map((section) => (
                <details key={section.title} className="py-2">
                  <summary className="cursor-pointer text-sm font-medium">
                    {section.title}
                  </summary>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {section.text}
                  </p>
                </details>
              ))}
            </div>
            <label className="mt-4 flex cursor-pointer items-start gap-3 text-sm">
              <input
                type="checkbox"
                checked={accepted}
                onChange={(event) => setAccepted(event.target.checked)}
                className="mt-0.5 size-5 shrink-0 accent-[#ffc700]"
              />
              <span>قوانین و شرایط اجاره را خوانده‌ام و می‌پذیرم.</span>
            </label>
          </section>
        ) : null}

        {submitError ? (
          <p role="alert" className="px-2 text-sm text-destructive">
            {submitError}
          </p>
        ) : null}
      </main>

      <div className="fixed inset-x-0 bottom-0 z-20 mx-auto flex max-w-md items-center justify-between gap-4 border-t border-border bg-background/95 px-6 py-4 backdrop-blur">
        <div>
          <p className="text-xs text-muted-foreground">جمع قابل پرداخت</p>
          <p className="font-bold text-primary">
            {quote ? formatToman(quote.total) : "—"}
          </p>
        </div>
        <Button
          disabled={!canSubmit}
          onClick={handleSubmit}
          className="h-12 rounded-full px-8 font-bold"
        >
          {submitting ? "در حال ثبت…" : "پرداخت و رزرو"}
        </Button>
      </div>
    </PageShell>
  );
}
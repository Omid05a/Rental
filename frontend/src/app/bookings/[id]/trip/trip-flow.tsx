"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Stepper } from "@/components/booking-pickers";
import { DigitsInput, Field } from "@/components/form-bits";
import { PageShell } from "@/components/page-shell";
import { PhotoCapture } from "@/components/photo-capture";
import { QrInput } from "@/components/qr-input";
import { Button } from "@/components/ui/button";
import { useRequireAuth } from "@/lib/auth";
import { DEPOSIT_STATUS, type Booking } from "@/lib/bookings";
import { DEMO_MODE } from "@/lib/demo";
import { getErrorMessage } from "@/lib/errors";
import { formatToman, toFa } from "@/lib/format";
import { getPosition, isPositionError, positionErrorMessage } from "@/lib/geo";
import { createAttemptKeys } from "@/lib/idempotency";
import { formatJalaliDateTime } from "@/lib/jalali";

function formatDuration(totalSeconds: number) {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = seconds % 60;
  const pad = (value: number) => String(value).padStart(2, "0");
  return toFa(`${pad(hours)}:${pad(minutes)}:${pad(rest)}`);
}

function Card({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-4 rounded-3xl bg-card p-5">
      <h2 className="font-semibold">{title}</h2>
      {children}
    </section>
  );
}

export default function TripFlow() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const { user, ready, authFetch } = useRequireAuth();

  const [booking, setBooking] = useState<Booking | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [qr, setQr] = useState("");
  const [fuel, setFuel] = useState("");
  const [demoLocation, setDemoLocation] = useState(DEMO_MODE);
  const [extendHours, setExtendHours] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempts] = useState(createAttemptKeys);

  const reload = useCallback(async () => {
    setBooking(await authFetch<Booking>(`/bookings/${id}/`));
  }, [authFetch, id]);

  useEffect(() => {
    if (!ready || !user) return;
    let active = true;
    authFetch<Booking>(`/bookings/${id}/`)
      .then((data) => {
        if (active) setBooking(data);
      })
      .catch(() => {
        if (active) setLoadError("این رزرو پیدا نشد.");
      });
    return () => {
      active = false;
    };
  }, [ready, user, id, authFetch]);

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  // While a trip is active, refresh the fees shown on screen every minute.
  const status = booking?.status;
  useEffect(() => {
    if (status !== "active") return;
    const timer = setInterval(() => {
      void reload().catch(() => undefined);
    }, 60_000);
    return () => clearInterval(timer);
  }, [status, reload]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(isPositionError(err) ? positionErrorMessage(err) : getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function currentPosition() {
    if (demoLocation && booking) {
      return {
        latitude: booking.vehicle.latitude,
        longitude: booking.vehicle.longitude,
      };
    }
    return getPosition();
  }

  const handleStart = () =>
    run(async () => {
      if (!booking) return;
      const position = await currentPosition();
      await authFetch(`/bookings/${id}/start/`, {
        method: "POST",
        body: JSON.stringify({
          qr_code: qr.trim(),
          fuel_percent: booking.trip.needs_fuel ? Number(fuel) : null,
          ...position,
        }),
      });
      setQr("");
      setFuel("");
      await reload();
    });

  const handleExtend = () =>
    run(async () => {
      if (!booking) return;
      await authFetch(`/bookings/${id}/extend/`, {
        method: "POST",
        headers: {
          "Idempotency-Key": attempts.get(
            `extend|${extendHours}|${booking.end_at}`,
          ),
        },
        body: JSON.stringify({ hours: extendHours }),
      });
      await reload();
    });

  const handleEnd = () =>
    run(async () => {
      if (!booking) return;
      const position = await currentPosition();
      await authFetch(`/bookings/${id}/end/`, {
        method: "POST",
        body: JSON.stringify({
          fuel_percent: booking.trip.needs_fuel ? Number(fuel) : null,
          ...position,
        }),
      });
      setFuel("");
      await reload();
    });

  const fillDemoQr = () =>
    run(async () => {
      const data = await authFetch<{ qr_code: string }>(
        `/bookings/${id}/dev-qr/`,
      );
      setQr(data.qr_code);
    });

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  const trip = booking?.trip;
  const needsFuel = trip?.needs_fuel ?? false;
  const fuelOk = !needsFuel || (fuel !== "" && Number(fuel) <= 100);
  const remaining = booking
    ? (new Date(booking.end_at).getTime() - now) / 1000
    : 0;
  const radius = booking
    ? booking.vehicle.pickup_radius_m + 50
    : 0;

  const demoPanel = DEMO_MODE ? (
    <label className="flex cursor-pointer items-start gap-3 rounded-2xl bg-secondary p-4 text-sm">
      <input
        type="checkbox"
        checked={demoLocation}
        onChange={(event) => setDemoLocation(event.target.checked)}
        className="mt-0.5 size-5 shrink-0 accent-[#ffc700]"
      />
      <span>
        حالت نمایشی: موقعیت من را همان محل وسیله در نظر بگیر
        <span className="mt-1 block text-xs text-muted-foreground">
          فقط برای تست و ارائه. در حالت عادی از GPS گوشی استفاده می‌شود.
        </span>
      </span>
    </label>
  ) : null;

  return (
    <PageShell>
      <header className="flex items-center gap-3 px-6 pb-4 pt-12">
        <button
          type="button"
          onClick={() => router.push(`/bookings/${id}`)}
          aria-label="بازگشت"
          className="flex size-10 items-center justify-center rounded-full bg-card"
        >
          <ArrowRight className="size-5" />
        </button>
        <h1 className="text-xl font-bold">سفر</h1>
      </header>

      <main className="flex flex-1 flex-col gap-4 px-6 pb-10">
        {loadError ? (
          <p role="alert" className="px-2 text-sm text-destructive">
            {loadError}
          </p>
        ) : null}

        {!booking && !loadError ? (
          <p className="text-center text-sm text-muted-foreground">
            در حال بارگذاری…
          </p>
        ) : null}

        {booking && booking.role !== "renter" ? (
          <p className="rounded-3xl bg-card p-5 text-sm text-muted-foreground">
            این صفحه مخصوص اجاره‌کننده است.{" "}
            <Link href={`/bookings/${id}`} className="text-primary underline">
              بازگشت به رزرو
            </Link>
          </p>
        ) : null}

        {booking && trip && booking.role === "renter" ? (
          <>
            <div className="rounded-3xl bg-card p-4">
              <h2 className="font-semibold">{booking.vehicle.title}</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {booking.vehicle.address}
              </p>
            </div>

            {booking.status === "confirmed" && !trip.can_start ? (
              <Card title="هنوز زود است">
                <p className="text-sm leading-relaxed text-muted-foreground">
                  شروع سفر از {formatJalaliDateTime(trip.start_window_opens_at)}{" "}
                  امکان‌پذیر است. در همان لحظه می‌توانید از وسیله عکس بگیرید و
                  قفل آن را باز کنید.
                </p>
                <Button
                  variant="outline"
                  onClick={() => router.push(`/bookings/${id}`)}
                  className="h-12 rounded-full border-border bg-secondary"
                >
                  بازگشت به رزرو
                </Button>
              </Card>
            ) : null}

            {booking.status === "confirmed" && trip.can_start ? (
              <>
                {demoPanel}

                <Card title="۱. عکس‌های وضعیت وسیله قبل از سفر">
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    از همه زاویه‌ها واضح عکس بگیرید. این عکس‌ها برای بررسی
                    خسارت‌های احتمالی نگه داشته می‌شوند.
                  </p>
                  <PhotoCapture
                    bookingId={booking.id}
                    phase="start"
                    angles={trip.required_angles}
                    photos={trip.start_photos}
                    disabled={busy}
                    onChanged={reload}
                  />
                </Card>

                <Card title="۲. باز کردن قفل">
                  <Field
                    label="کد QR روی وسیله"
                    hint="با دوربین اسکن کنید یا کد را وارد کنید."
                  >
                    <QrInput value={qr} onChange={setQr} disabled={busy} />
                  </Field>
                  {DEMO_MODE ? (
                    <Button
                      variant="outline"
                      disabled={busy}
                      onClick={fillDemoQr}
                      className="h-11 rounded-full border-border bg-secondary text-sm"
                    >
                      پر کردن خودکار کد (نمایشی)
                    </Button>
                  ) : null}

                  {needsFuel ? (
                    <Field
                      label="سطح بنزین یا شارژ فعلی (درصد)"
                      htmlFor="start-fuel"
                    >
                      <DigitsInput
                        id="start-fuel"
                        maxLength={3}
                        placeholder="مثلاً ۸۰"
                        value={fuel}
                        onChange={setFuel}
                      />
                    </Field>
                  ) : null}

                  <p className="text-xs leading-relaxed text-muted-foreground">
                    هنگام شروع، موقعیت شما بررسی می‌شود و باید کمتر از{" "}
                    {toFa(radius)} متر با وسیله فاصله داشته باشید.
                  </p>
                </Card>

                {error ? (
                  <p role="alert" className="px-2 text-sm text-destructive">
                    {error}
                  </p>
                ) : null}

                <Button
                  disabled={
                    busy || !trip.start_photos_done || !qr.trim() || !fuelOk
                  }
                  onClick={handleStart}
                  className="h-14 rounded-full text-base font-bold"
                >
                  {busy ? "در حال بررسی…" : "باز کردن قفل و شروع سفر"}
                </Button>
                {!trip.start_photos_done ? (
                  <p className="text-center text-xs text-muted-foreground">
                    برای شروع، همه عکس‌ها را ثبت کنید.
                  </p>
                ) : null}
              </>
            ) : null}

            {booking.status === "active" ? (
              <>
                <section
                  className={`rounded-3xl p-6 text-center ${
                    remaining > 0
                      ? "bg-primary text-primary-foreground"
                      : "bg-red-500/15 text-red-300"
                  }`}
                >
                  <p className="text-sm opacity-80">
                    {remaining > 0 ? "زمان باقی‌مانده" : "تأخیر در بازگشت"}
                  </p>
                  <p className="mt-1 text-4xl font-extrabold tabular-nums">
                    <bdi dir="ltr">{formatDuration(Math.abs(remaining))}</bdi>
                  </p>
                  <p className="mt-2 text-xs opacity-80">
                    پایان اجاره: {formatJalaliDateTime(booking.end_at)}
                  </p>
                  {remaining <= 0 ? (
                    <p className="mt-3 text-sm">
                      جریمه تأخیر تا اینون: {formatToman(trip.late_fee_now)} (از
                      سپرده کم می‌شود)
                    </p>
                  ) : null}
                </section>

                <Card title="تمدید اجاره">
                  <Stepper
                    label="ساعت اضافه"
                    value={extendHours}
                    min={1}
                    max={12}
                    onChange={setExtendHours}
                  />
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    هزینه تمدید از کیف پول کم می‌شود. اگر وسیله بعد از شما رزرو
                    شده باشد، تمدید ممکن نیست.
                  </p>
                  <Button
                    disabled={busy}
                    onClick={handleExtend}
                    className="h-12 rounded-full font-bold"
                  >
                    {busy ? "در حال انجام…" : `تمدید ${toFa(extendHours)} ساعت`}
                  </Button>
                </Card>

                {demoPanel}

                <Card title="پایان سفر">
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    وسیله را به محل تحویل برگردانید و از همه زاویه‌ها عکس
                    بگیرید.
                  </p>
                  <PhotoCapture
                    bookingId={booking.id}
                    phase="end"
                    angles={trip.required_angles}
                    photos={trip.end_photos}
                    disabled={busy}
                    onChanged={reload}
                  />
                  {needsFuel ? (
                    <Field
                      label="سطح بنزین یا شارژ هنگام تحویل (درصد)"
                      htmlFor="end-fuel"
                      hint={
                        booking.start_fuel_percent !== null
                          ? `هنگام شروع: ${toFa(booking.start_fuel_percent)} درصد`
                          : undefined
                      }
                    >
                      <DigitsInput
                        id="end-fuel"
                        maxLength={3}
                        value={fuel}
                        onChange={setFuel}
                      />
                    </Field>
                  ) : null}
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    پایان سفر فقط داخل محدوده تحویل (حدود {toFa(radius)} متر از
                    محل وسیله) ممکن است.
                  </p>
                </Card>

                {error ? (
                  <p role="alert" className="px-2 text-sm text-destructive">
                    {error}
                  </p>
                ) : null}

                <Button
                  disabled={busy || !trip.end_photos_done || !fuelOk}
                  onClick={handleEnd}
                  className="h-14 rounded-full text-base font-bold"
                >
                  {busy ? "در حال بررسی…" : "پایان سفر و قفل کردن"}
                </Button>
                {!trip.end_photos_done ? (
                  <p className="text-center text-xs text-muted-foreground">
                    برای پایان، همه عکس‌ها را ثبت کنید.
                  </p>
                ) : null}
              </>
            ) : null}

            {booking.status === "completed" ? (
              <Card title="سفر به پایان رسید">
                <dl className="divide-y divide-border text-sm">
                  <div className="flex justify-between gap-4 py-2.5">
                    <dt className="text-muted-foreground">زمان پایان</dt>
                    <dd>{booking.ended_at ? formatJalaliDateTime(booking.ended_at) : "—"}</dd>
                  </div>
                  <div className="flex justify-between gap-4 py-2.5">
                    <dt className="text-muted-foreground">جریمه تأخیر</dt>
                    <dd>{formatToman(booking.late_fee)}</dd>
                  </div>
                  {booking.vehicle.kind === "car" ? (
                    <div className="flex justify-between gap-4 py-2.5">
                      <dt className="text-muted-foreground">جریمه کمبود بنزین</dt>
                      <dd>{formatToman(booking.fuel_fee)}</dd>
                    </div>
                  ) : null}
                  <div className="flex justify-between gap-4 py-2.5">
                    <dt className="text-muted-foreground">وضعیت سپرده</dt>
                    <dd>{DEPOSIT_STATUS[booking.deposit_status]}</dd>
                  </div>
                </dl>
                {booking.deposit_status === "held" && booking.deposit_release_at ? (
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    سپرده تا {formatJalaliDateTime(booking.deposit_release_at)}{" "}
                    نگه داشته می‌شود تا مالک بتواند خسارت احتمالی را گزارش کند.
                    بعد از آن، باقی‌مانده به کیف پول شما برمی‌گردد.
                  </p>
                ) : null}
                <Button
                  onClick={() => router.push(`/bookings/${id}`)}
                  className="h-12 rounded-full font-bold"
                >
                  مشاهده جزئیات رزرو
                </Button>
              </Card>
            ) : null}

            {booking.status === "cancelled" ? (
              <p className="rounded-3xl bg-card p-5 text-sm text-muted-foreground">
                این رزرو لغو شده است.
              </p>
            ) : null}
          </>
        ) : null}
      </main>
    </PageShell>
  );
}
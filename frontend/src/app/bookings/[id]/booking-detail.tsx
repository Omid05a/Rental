"use client";

import { ArrowRight, MapPin } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useRequireAuth } from "@/lib/auth";
import { BOOKING_STATUS, DEPOSIT_STATUS, type Booking } from "@/lib/bookings";
import { getErrorMessage } from "@/lib/errors";
import { formatToman, toFa } from "@/lib/format";
import { formatJalaliDateTime } from "@/lib/jalali";

function Row({
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
      className={`flex items-center justify-between gap-4 py-2.5 text-sm ${
        strong ? "font-bold" : ""
      }`}
    >
      <dt className={strong ? "" : "text-muted-foreground"}>{label}</dt>
      <dd className="text-end">{value}</dd>
    </div>
  );
}

export default function BookingDetail() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const { user, ready, authFetch } = useRequireAuth();

  const [booking, setBooking] = useState<Booking | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [reason, setReason] = useState("");
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    if (!ready || !user) return;
    let active = true;
    authFetch<Booking>(`/bookings/${id}/`)
      .then((data) => {
        if (active) setBooking(data);
      })
      .catch(() => {
        if (active) setError("این رزرو پیدا نشد.");
      });
    return () => {
      active = false;
    };
  }, [ready, user, id, authFetch]);

  async function handleCancel() {
    setCancelling(true);
    setError(null);
    try {
      const updated = await authFetch<Booking>(`/bookings/${id}/cancel/`, {
        method: "POST",
        body: JSON.stringify({ reason: reason.trim() }),
      });
      setBooking(updated);
      setConfirming(false);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setCancelling(false);
    }
  }

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  const status = booking ? BOOKING_STATUS[booking.status] : null;
  const isRenter = booking?.role === "renter";
  const showTripCard =
    isRenter &&
    booking &&
    (booking.status === "confirmed" || booking.status === "active");

  return (
    <PageShell>
      <header className="flex items-center gap-3 px-6 pb-4 pt-12">
        <button
          type="button"
          onClick={() => router.push("/bookings")}
          aria-label="بازگشت"
          className="flex size-10 items-center justify-center rounded-full bg-card"
        >
          <ArrowRight className="size-5" />
        </button>
        <h1 className="text-xl font-bold">جزئیات رزرو</h1>
      </header>

      <main className="flex flex-1 flex-col gap-4 px-6 pb-10">
        {error ? (
          <p role="alert" className="px-2 text-sm text-destructive">
            {error}
          </p>
        ) : null}

        {!booking && !error ? (
          <p className="text-center text-sm text-muted-foreground">
            در حال بارگذاری…
          </p>
        ) : null}

        {booking && status ? (
          <>
            <section className="flex flex-col gap-3 rounded-3xl bg-card p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-semibold">{booking.vehicle.title}</h2>
                <span
                  className={`rounded-full px-3 py-0.5 text-xs font-medium ${status.className}`}
                >
                  {status.label}
                </span>
              </div>
              <p className="flex items-center gap-1 text-sm text-muted-foreground">
                <MapPin className="size-4 shrink-0" />
                {booking.vehicle.address}
              </p>
              <Link
                href={`/vehicles/${booking.vehicle.id}`}
                className="text-sm font-medium text-primary underline underline-offset-4"
              >
                مشاهده وسیله
              </Link>
            </section>

            {showTripCard ? (
              <section className="flex flex-col gap-3 rounded-3xl bg-primary/10 p-5">
                <h3 className="font-semibold">سفر</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {booking.status === "active"
                    ? "سفر در حال انجام است. از اینجا می‌توانید تمدید کنید یا سفر را پایان دهید."
                    : booking.trip.can_start
                      ? "می‌توانید از وسیله عکس بگیرید، قفل را باز کنید و سفر را شروع کنید."
                      : `شروع سفر از ${formatJalaliDateTime(booking.trip.start_window_opens_at)} امکان‌پذیر است.`}
                </p>
                <Button
                  onClick={() => router.push(`/bookings/${id}/trip`)}
                  className="h-12 rounded-full font-bold"
                >
                  {booking.status === "active" ? "ادامه سفر" : "شروع سفر"}
                </Button>
              </section>
            ) : null}

            <section className="rounded-3xl bg-card px-5 py-2">
              <dl className="divide-y divide-border">
                <Row label="شروع" value={formatJalaliDateTime(booking.start_at)} />
                <Row label="پایان" value={formatJalaliDateTime(booking.end_at)} />
                <Row label="مدت" value={`${toFa(booking.hours)} ساعت`} />
                <Row
                  label={isRenter ? "مالک" : "اجاره‌کننده"}
                  value={booking.counterpart.first_name || "کاربر رنتال"}
                />
                {!isRenter ? (
                  <Row
                    label="شماره تماس"
                    value={toFa(booking.counterpart.phone)}
                  />
                ) : null}
              </dl>
            </section>

            <section className="rounded-3xl bg-card px-5 py-2">
              <dl className="divide-y divide-border">
                <Row
                  label="هزینه اجاره"
                  value={formatToman(booking.rental_amount)}
                />
                <Row
                  label="سپرده"
                  value={
                    booking.deposit_amount > 0
                      ? formatToman(booking.deposit_amount)
                      : "بدون سپرده"
                  }
                />
                <Row
                  label="جمع پرداختی"
                  value={formatToman(booking.total_paid)}
                  strong
                />
                {booking.status === "cancelled" ? (
                  <>
                    <Row
                      label="لغو توسط"
                      value={
                        booking.cancelled_by === "owner" ? "مالک" : "اجاره‌کننده"
                      }
                    />
                    <Row
                      label="کارمزد لغو"
                      value={formatToman(booking.cancellation_fee)}
                    />
                    <Row
                      label="مبلغ بازگشتی"
                      value={formatToman(booking.refund_amount)}
                    />
                  </>
                ) : null}
              </dl>
            </section>

            {booking.status === "completed" ? (
              <section className="rounded-3xl bg-card px-5 py-2">
                <dl className="divide-y divide-border">
                  <Row
                    label="زمان پایان سفر"
                    value={
                      booking.ended_at
                        ? formatJalaliDateTime(booking.ended_at)
                        : "—"
                    }
                  />
                  <Row
                    label="جریمه تأخیر"
                    value={formatToman(booking.late_fee)}
                  />
                  {booking.vehicle.kind === "car" ? (
                    <Row
                      label="جریمه کمبود بنزین"
                      value={formatToman(booking.fuel_fee)}
                    />
                  ) : null}
                  {booking.damage_deduction > 0 ? (
                    <Row
                      label="کسر بابت خسارت"
                      value={formatToman(booking.damage_deduction)}
                    />
                  ) : null}
                  <Row
                    label="وضعیت سپرده"
                    value={DEPOSIT_STATUS[booking.deposit_status]}
                  />
                </dl>
                {booking.deposit_status === "held" &&
                booking.deposit_release_at ? (
                  <p className="pb-3 text-xs leading-relaxed text-muted-foreground">
                    سپرده تا {formatJalaliDateTime(booking.deposit_release_at)}{" "}
                    نگه داشته می‌شود.
                  </p>
                ) : null}
              </section>
            ) : null}

            {booking.status === "cancelled" && booking.cancel_reason ? (
              <p className="rounded-2xl bg-card p-4 text-sm text-muted-foreground">
                دلیل لغو: {booking.cancel_reason}
              </p>
            ) : null}

            {booking.can_cancel ? (
              <section className="flex flex-col gap-3 rounded-3xl bg-card p-5">
                <h3 className="font-semibold">لغو رزرو</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {!isRenter
                    ? "اگر شما لغو کنید، مبلغ کامل به اجاره‌کننده بازگردانده می‌شود."
                    : booking.cancel_fee_now > 0
                      ? `در صورت لغو، ${formatToman(booking.cancel_fee_now)} به‌عنوان کارمزد کسر می‌شود و بقیه مبلغ به کیف پول برمی‌گردد.`
                      : "لغو در حال حاضر رایگان است و کل مبلغ به کیف پول برمی‌گردد."}
                </p>

                {confirming ? (
                  <div className="flex flex-col gap-3">
                    <Textarea
                      placeholder="دلیل لغو (اختیاری)"
                      maxLength={300}
                      value={reason}
                      onChange={(event) => setReason(event.target.value)}
                      className="min-h-24 rounded-3xl border-0 bg-secondary p-4 text-base"
                    />
                    <div className="flex gap-3">
                      <Button
                        disabled={cancelling}
                        onClick={handleCancel}
                        className="h-12 flex-1 rounded-full bg-destructive font-bold text-white hover:bg-destructive/90"
                      >
                        {cancelling ? "در حال لغو…" : "تأیید لغو"}
                      </Button>
                      <Button
                        variant="outline"
                        disabled={cancelling}
                        onClick={() => setConfirming(false)}
                        className="h-12 flex-1 rounded-full border-border bg-secondary"
                      >
                        انصراف
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    onClick={() => setConfirming(true)}
                    className="h-12 rounded-full border-border bg-secondary font-medium text-destructive"
                  >
                    لغو رزرو
                  </Button>
                )}
              </section>
            ) : null}
          </>
        ) : null}
      </main>
    </PageShell>
  );
}
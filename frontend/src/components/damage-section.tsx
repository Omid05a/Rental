"use client";

import { ImagePlus } from "lucide-react";
import { useState, type ChangeEvent, type FormEvent } from "react";

import { DigitsInput, Field } from "@/components/form-bits";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/lib/auth";
import type { Booking } from "@/lib/bookings";
import { getErrorMessage } from "@/lib/errors";
import { formatToman, toFa } from "@/lib/format";
import { compressImage } from "@/lib/image";
import { formatJalaliDateTime } from "@/lib/jalali";

const MAX_PHOTOS = 6;

type Props = {
  booking: Booking;
  onChanged: () => Promise<void>;
};

function depositLeft(booking: Booking) {
  return Math.max(
    0,
    booking.deposit_amount -
      booking.late_fee -
      booking.fuel_fee -
      booking.damage_deduction,
  );
}

function ReportForm({ booking, onChanged }: Props) {
  const { authFetch } = useAuth();
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const left = depositLeft(booking);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const value = Number(amount);
    if (description.trim().length < 5) {
      setError("توضیح خسارت را بنویسید.");
      return;
    }
    if (!value || value > left) {
      setError(`مبلغ باید بین ۱ تا ${formatToman(left)} باشد.`);
      return;
    }

    setBusy(true);
    setError(null);
    try {
      await authFetch(`/bookings/${booking.id}/damage/`, {
        method: "POST",
        body: JSON.stringify({
          description: description.trim(),
          claimed_amount: value,
        }),
      });
      await onChanged();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-3xl bg-card p-5">
      <h3 className="font-semibold">گزارش خسارت</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
        اگر هنگام تحویل خسارتی دیدید، تا{" "}
        {booking.deposit_release_at
          ? formatJalaliDateTime(booking.deposit_release_at)
          : "پایان مهلت"}{" "}
        می‌توانید آن را گزارش کنید. بعد از ثبت گزارش، می‌توانید عکس مدرک اضافه
        کنید و تیم رنتال مبلغ را از سپرده تعیین می‌کند. سپرده باقی‌مانده:{" "}
        {formatToman(left)}.
      </p>

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
        <Field label="توضیح خسارت" htmlFor="damage-description">
          <Textarea
            id="damage-description"
            maxLength={1000}
            placeholder="مثلاً: خط و خش روی درب سمت چپ"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="min-h-28 rounded-3xl border-0 bg-secondary p-4 text-base"
          />
        </Field>

        <Field
          label="مبلغ مطالبه (تومان)"
          htmlFor="damage-amount"
          hint={amount ? formatToman(Number(amount)) : undefined}
        >
          <DigitsInput
            id="damage-amount"
            value={amount}
            onChange={setAmount}
            className="bg-secondary"
          />
        </Field>

        {error ? (
          <p role="alert" className="px-2 text-sm text-destructive">
            {error}
          </p>
        ) : null}

        <Button
          type="submit"
          disabled={busy}
          className="h-12 rounded-full font-bold"
        >
          {busy ? "در حال ثبت…" : "ثبت گزارش"}
        </Button>
      </form>
    </section>
  );
}

function ClaimView({ booking, onChanged }: Props) {
  const { authFetch } = useAuth();
  const damage = booking.damage;

  const [note, setNote] = useState(damage?.renter_response ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!damage) return null;

  const isOwner = booking.role === "owner";
  const open = damage.status === "open";

  async function handlePhotos(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (!damage || files.length === 0) return;

    const slots = MAX_PHOTOS - damage.photos.length;
    setBusy(true);
    setError(null);
    try {
      for (const file of files.slice(0, slots)) {
        const body = new FormData();
        body.append("image", await compressImage(file));
        body.append("phase", "damage");
        body.append("angle", "damage");
        await authFetch(`/bookings/${booking.id}/photos/`, {
          method: "POST",
          body,
        });
      }
      await onChanged();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleRespond(event: FormEvent) {
    event.preventDefault();
    if (!note.trim()) {
      setError("پاسخ خود را بنویسید.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await authFetch(`/bookings/${booking.id}/damage/respond/`, {
        method: "POST",
        body: JSON.stringify({ note: note.trim() }),
      });
      await onChanged();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-4 rounded-3xl bg-card p-5">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold">گزارش خسارت</h3>
        <span
          className={`rounded-full px-3 py-0.5 text-xs font-medium ${
            open
              ? "bg-primary/15 text-primary"
              : "bg-green-500/15 text-green-400"
          }`}
        >
          {open ? "در حال بررسی" : "تسویه‌شده"}
        </span>
      </div>

      <dl className="divide-y divide-border text-sm">
        <div className="flex justify-between gap-4 py-2.5">
          <dt className="text-muted-foreground">مبلغ مطالبه</dt>
          <dd className="font-medium">{formatToman(damage.claimed_amount)}</dd>
        </div>
        <div className="flex flex-col gap-1 py-2.5">
          <dt className="text-muted-foreground">توضیح مالک</dt>
          <dd className="leading-relaxed">{damage.description}</dd>
        </div>
        {damage.renter_response ? (
          <div className="flex flex-col gap-1 py-2.5">
            <dt className="text-muted-foreground">پاسخ اجاره‌کننده</dt>
            <dd className="leading-relaxed">{damage.renter_response}</dd>
          </div>
        ) : null}
        {!open ? (
          <>
            <div className="flex justify-between gap-4 py-2.5">
              <dt className="text-muted-foreground">مبلغ تأییدشده</dt>
              <dd className="font-bold">{formatToman(damage.approved_amount)}</dd>
            </div>
            {damage.resolution_note ? (
              <div className="flex flex-col gap-1 py-2.5">
                <dt className="text-muted-foreground">توضیح تیم رنتال</dt>
                <dd className="leading-relaxed">{damage.resolution_note}</dd>
              </div>
            ) : null}
          </>
        ) : null}
      </dl>

      {damage.photos.length > 0 ? (
        <ul className="grid grid-cols-3 gap-2">
          {damage.photos.map((photo) => (
            <li key={photo.image}>
              <a
                href={photo.image}
                target="_blank"
                rel="noopener noreferrer"
                className="block aspect-square overflow-hidden rounded-2xl bg-secondary"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={photo.image}
                  alt=""
                  className="size-full object-cover"
                />
              </a>
            </li>
          ))}
        </ul>
      ) : null}

      {open && isOwner && damage.photos.length < MAX_PHOTOS ? (
        <label
          className={`flex h-12 cursor-pointer items-center justify-center gap-2 rounded-full bg-secondary font-medium ${
            busy ? "pointer-events-none opacity-60" : ""
          }`}
        >
          <ImagePlus className="size-5" />
          {busy
            ? "در حال ارسال…"
            : `افزودن عکس مدرک (${toFa(damage.photos.length)} از ${toFa(MAX_PHOTOS)})`}
          <input
            type="file"
            multiple
            accept="image/*"
            className="sr-only"
            disabled={busy}
            onChange={handlePhotos}
          />
        </label>
      ) : null}

      {open && !isOwner ? (
        <form onSubmit={handleRespond} className="flex flex-col gap-3">
          <Field label="پاسخ شما" htmlFor="damage-response">
            <Textarea
              id="damage-response"
              maxLength={1000}
              placeholder="اگر موافق نیستید، توضیح دهید."
              value={note}
              onChange={(event) => setNote(event.target.value)}
              className="min-h-24 rounded-3xl border-0 bg-secondary p-4 text-base"
            />
          </Field>
          <Button
            type="submit"
            disabled={busy}
            className="h-12 rounded-full font-bold"
          >
            {busy ? "در حال ارسال…" : "ثبت پاسخ"}
          </Button>
        </form>
      ) : null}

      {open ? (
        <p className="text-xs leading-relaxed text-muted-foreground">
          تا پایان بررسی، سپرده نگه داشته می‌شود. تیم رنتال با توجه به عکس‌های
          قبل و بعد از سفر، مبلغ نهایی را تعیین می‌کند و بقیه سپرده بازگردانده
          می‌شود.
        </p>
      ) : null}

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </section>
  );
}

export function DamageSection({ booking, onChanged }: Props) {
  if (booking.damage) {
    return <ClaimView booking={booking} onChanged={onChanged} />;
  }
  if (booking.trip.can_report_damage) {
    return <ReportForm booking={booking} onChanged={onChanged} />;
  }
  return null;
}
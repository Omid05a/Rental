"use client";

import { LoaderCircle } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { RatingBadge, StarInput, Stars } from "@/components/stars";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";
import { formatJalaliDateTime } from "@/lib/jalali";
import type { ReviewItem, ReviewState } from "@/lib/social";

function ReviewCard({
  title,
  review,
}: {
  title: string;
  review: ReviewItem;
}) {
  return (
    <div className="animate-scale-in flex flex-col gap-2 rounded-2xl bg-secondary p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium">{title}</span>
        <Stars value={review.rating} />
      </div>
      {review.comment ? (
        <p className="text-sm leading-relaxed text-muted-foreground">
          {review.comment}
        </p>
      ) : null}
    </div>
  );
}

export function ReviewSection({ bookingId }: { bookingId: number }) {
  const { authFetch } = useAuth();

  const [state, setState] = useState<ReviewState | null>(null);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    authFetch<ReviewState>(`/bookings/${bookingId}/review/`)
      .then((data) => {
        if (active) setState(data);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [authFetch, bookingId]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (rating < 1) {
      setError("ابتدا امتیاز خود را انتخاب کنید.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const data = await authFetch<ReviewState>(
        `/bookings/${bookingId}/review/`,
        {
          method: "POST",
          body: JSON.stringify({ rating, comment: comment.trim() }),
        },
      );
      setState(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (!state) return null;

  const target = state.role === "renter" ? "مالک" : "اجاره‌کننده";
  const name = state.counterpart_name || target;

  return (
    <section className="animate-fade-up flex flex-col gap-4 rounded-3xl bg-card p-5">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold">امتیاز و نظر</h3>
        <RatingBadge
          avg={state.counterpart_rating.avg}
          count={state.counterpart_rating.count}
        />
      </div>

      {state.can_review ? (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <p className="text-sm leading-relaxed text-muted-foreground">
            تجربه خود از همکاری با {target} ({name}) را ثبت کنید.
            {state.deadline
              ? ` مهلت ثبت نظر تا ${formatJalaliDateTime(state.deadline)} است.`
              : ""}
          </p>
          <StarInput value={rating} onChange={setRating} disabled={busy} />
          <Textarea
            maxLength={500}
            placeholder="نظر شما (اختیاری)"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            className="min-h-24 rounded-3xl border-0 bg-secondary p-4 text-base"
          />
          {error ? (
            <p
              role="alert"
              className="animate-fade-up px-2 text-sm text-destructive"
            >
              {error}
            </p>
          ) : null}
          <Button
            type="submit"
            disabled={busy}
            className="h-12 rounded-full font-bold"
          >
            {busy ? <LoaderCircle className="animate-spin" /> : null}
            {busy ? "در حال ثبت…" : "ثبت نظر"}
          </Button>
          <p className="text-center text-xs leading-relaxed text-muted-foreground">
            نظر {target} بعد از ثبت نظر شما نمایش داده می‌شود، تا هیچ‌کس تحت
            تأثیر نظر دیگری قرار نگیرد.
          </p>
        </form>
      ) : null}

      {state.mine ? (
        <ReviewCard title="نظر شما" review={state.mine} />
      ) : null}

      {state.theirs ? (
        <ReviewCard title={`نظر ${target} درباره شما`} review={state.theirs} />
      ) : null}

      {state.mine && !state.theirs ? (
        <p className="text-xs leading-relaxed text-muted-foreground">
          نظر {target} هنوز ثبت نشده است. بعد از ثبت، اینجا نمایش داده می‌شود.
        </p>
      ) : null}

      {state.closed && !state.mine ? (
        <p className="text-sm text-muted-foreground">
          مهلت ثبت نظر برای این سفر تمام شده است.
        </p>
      ) : null}
    </section>
  );
}
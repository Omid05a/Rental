"use client";

import { ArrowRight, Bike, Car, MapPin } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageShell } from "@/components/page-shell";
import { RatingBadge, Stars } from "@/components/stars";
import { Button } from "@/components/ui/button";
import { ApiError, apiFetch } from "@/lib/api";
import { formatToman, toFa } from "@/lib/format";
import { formatJalaliDateTime } from "@/lib/jalali";
import type { VehicleReviews } from "@/lib/social";
import {
  FUEL_LABEL,
  KIND_LABEL,
  TRANSMISSION_LABEL,
  type Vehicle,
} from "@/lib/vehicles";

type LoadState = {
  id: string;
  vehicle: Vehicle | null;
  error: string | null;
};

type ReviewsState = { id: string; data: VehicleReviews | null };

function Chip({ children }: { children: string }) {
  return (
    <span className="rounded-full bg-card px-3 py-1 text-xs text-muted-foreground">
      {children}
    </span>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-end font-medium">{value}</dd>
    </div>
  );
}

export default function VehicleDetail() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const [state, setState] = useState<LoadState | null>(null);
  const [reviewsState, setReviewsState] = useState<ReviewsState | null>(null);

  useEffect(() => {
    let active = true;
    apiFetch<Vehicle>(`/vehicles/${id}/`)
      .then((vehicle) => {
        if (active) setState({ id, vehicle, error: null });
      })
      .catch((err) => {
        if (!active) return;
        const notFound = err instanceof ApiError && err.status === 404;
        setState({
          id,
          vehicle: null,
          error: notFound
            ? "این وسیله پیدا نشد یا دیگر در دسترس نیست."
            : "مشکلی پیش آمد. دوباره تلاش کنید.",
        });
      });
    return () => {
      active = false;
    };
  }, [id]);

  useEffect(() => {
    let active = true;
    apiFetch<VehicleReviews>(`/vehicles/${id}/reviews/`)
      .then((data) => {
        if (active) setReviewsState({ id, data });
      })
      .catch(() => {
        if (active) setReviewsState({ id, data: null });
      });
    return () => {
      active = false;
    };
  }, [id]);

  const current = state?.id === id ? state : null;
  const vehicle = current?.vehicle ?? null;
  const reviews = reviewsState?.id === id ? reviewsState.data : null;
  const isCar = vehicle?.kind === "car";
  const Icon = vehicle?.kind === "bike" ? Bike : Car;

  return (
    <PageShell>
      <header className="flex items-center gap-3 px-6 pb-4 pt-12">
        <button
          type="button"
          onClick={() => router.push("/explore")}
          aria-label="بازگشت"
          className="flex size-10 items-center justify-center rounded-full bg-card"
        >
          <ArrowRight className="size-5" />
        </button>
        <h1 className="truncate text-xl font-bold">
          {vehicle?.title ?? "جزئیات وسیله"}
        </h1>
      </header>

      <main className="flex flex-1 flex-col gap-5 pb-32">
        {!current ? (
          <p className="text-center text-sm text-muted-foreground">
            در حال بارگذاری…
          </p>
        ) : null}

        {current?.error ? (
          <p role="alert" className="px-6 text-center text-sm text-destructive">
            {current.error}
          </p>
        ) : null}

        {vehicle ? (
          <>
            {vehicle.photos.length > 0 ? (
              <ul className="flex snap-x snap-mandatory overflow-x-auto [scrollbar-width:none]">
                {vehicle.photos.map((photo) => (
                  <li
                    key={photo.id}
                    className="aspect-[4/3] w-full shrink-0 snap-center"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={photo.image}
                      alt=""
                      className="size-full object-cover"
                    />
                  </li>
                ))}
              </ul>
            ) : (
              <div className="mx-6 flex aspect-[4/3] items-center justify-center rounded-3xl bg-card text-muted-foreground">
                <Icon className="size-14" />
              </div>
            )}

            <div className="flex flex-col gap-3 px-6">
              <div>
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-lg font-bold">{vehicle.title}</h2>
                  <RatingBadge
                    avg={reviews?.avg ?? null}
                    count={reviews?.count ?? 0}
                  />
                </div>
                <p className="mt-1 flex items-center gap-1 text-sm text-muted-foreground">
                  <MapPin className="size-4 shrink-0" />
                  {vehicle.address}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <Chip>{KIND_LABEL[vehicle.kind]}</Chip>
                <Chip>{`${vehicle.brand} ${vehicle.model_name}`}</Chip>
                {vehicle.year ? <Chip>{toFa(vehicle.year)}</Chip> : null}
                {isCar && vehicle.transmission ? (
                  <Chip>{TRANSMISSION_LABEL[vehicle.transmission]}</Chip>
                ) : null}
                {isCar && vehicle.fuel_type ? (
                  <Chip>{FUEL_LABEL[vehicle.fuel_type]}</Chip>
                ) : null}
                {isCar && vehicle.seats ? (
                  <Chip>{`${toFa(vehicle.seats)} صندلی`}</Chip>
                ) : null}
              </div>

              {vehicle.description ? (
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {vehicle.description}
                </p>
              ) : null}
            </div>

            <section className="mx-6 rounded-3xl bg-card px-5 py-2">
              <dl className="divide-y divide-border">
                <Row
                  label="قیمت هر ساعت"
                  value={formatToman(vehicle.price_per_hour)}
                />
                <Row
                  label="قیمت هر روز"
                  value={formatToman(vehicle.price_per_day)}
                />
                <Row
                  label="سپرده"
                  value={
                    vehicle.deposit > 0
                      ? formatToman(vehicle.deposit)
                      : "بدون سپرده"
                  }
                />
                {isCar && vehicle.daily_km_limit ? (
                  <Row
                    label="سقف کیلومتر روزانه"
                    value={`${toFa(vehicle.daily_km_limit)} کیلومتر`}
                  />
                ) : null}
                {isCar && vehicle.min_fuel_percent ? (
                  <Row
                    label="حداقل بنزین هنگام تحویل"
                    value={`${toFa(vehicle.min_fuel_percent)} درصد`}
                  />
                ) : null}
              </dl>
            </section>

            <section className="mx-6 rounded-3xl bg-card p-5">
              <h3 className="font-semibold">قوانین تحویل</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                وسیله را در پایان سفر به همین محل برگردانید و سطح بنزین یا
                شارژ آن را مطابق شروع سفر تحویل دهید. از وضعیت وسیله قبل و بعد
                از سفر عکس ثبت می‌شود.
              </p>
              <p className="mt-3 text-xs text-muted-foreground">
                مالک: {vehicle.owner_first_name || "کاربر رنتال"}
              </p>
            </section>

            {reviews && reviews.count > 0 ? (
              <section className="mx-6 flex flex-col gap-3 rounded-3xl bg-card p-5">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-semibold">نظر اجاره‌کنندگان</h3>
                  <RatingBadge avg={reviews.avg} count={reviews.count} />
                </div>
                <ul className="flex flex-col divide-y divide-border">
                  {reviews.results.map((review) => (
                    <li key={review.id} className="flex flex-col gap-1.5 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm font-medium">
                          {review.author_first_name || "کاربر رنتال"}
                        </span>
                        <Stars value={review.rating} />
                      </div>
                      {review.comment ? (
                        <p className="text-sm leading-relaxed text-muted-foreground">
                          {review.comment}
                        </p>
                      ) : null}
                      <span className="text-[11px] text-muted-foreground">
                        {formatJalaliDateTime(review.created_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            <div className="fixed inset-x-0 bottom-0 z-20 mx-auto flex max-w-md items-center justify-between gap-4 border-t border-border bg-background/95 px-6 py-4 backdrop-blur">
              <div>
                <p className="text-xs text-muted-foreground">شروع از</p>
                <p className="font-bold text-primary">
                  {formatToman(vehicle.price_per_hour)}
                  <span className="text-xs font-normal text-muted-foreground">
                    {" "}
                    / ساعت
                  </span>
                </p>
              </div>
              <Button
                onClick={() => router.push(`/vehicles/${id}/book`)}
                className="h-12 rounded-full px-8 font-bold"
              >
                رزرو
              </Button>
            </div>
          </>
        ) : null}
      </main>
    </PageShell>
  );
}
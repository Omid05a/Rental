"use client";

import { LoaderCircle, Navigation } from "lucide-react";
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { DEMO_MODE } from "@/lib/demo";
import { formatDistance, toFa } from "@/lib/format";
import { getPosition, isPositionError, positionErrorMessage } from "@/lib/geo";
import {
  fetchRoute,
  straightDistanceM,
  type LatLngTuple,
  type RoutePoint,
  type RouteResult,
} from "@/lib/routing";

// Leaflet needs the browser, so the map is loaded on the client only.
const RouteMap = dynamic(() => import("@/components/map/route-map"), {
  ssr: false,
  loading: () => <div className="skeleton size-full rounded-none" />,
});

type Status = "idle" | "locating" | "routing" | "done";

function formatDuration(seconds: number) {
  const minutes = Math.max(1, Math.round(seconds / 60));
  if (minutes < 60) return `${toFa(minutes)} دقیقه`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0
    ? `${toFa(hours)} ساعت`
    : `${toFa(hours)} ساعت و ${toFa(rest)} دقیقه`;
}

export function VehicleRoute({
  latitude,
  longitude,
}: {
  latitude: number;
  longitude: number;
}) {
  const destination = useMemo<RoutePoint>(
    () => ({ lat: latitude, lng: longitude }),
    [latitude, longitude],
  );

  const [status, setStatus] = useState<Status>("idle");
  const [origin, setOrigin] = useState<RoutePoint | null>(null);
  const [route, setRoute] = useState<RouteResult | null>(null);
  const [fallbackM, setFallbackM] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [offerDemo, setOfferDemo] = useState(false);

  const path = useMemo<LatLngTuple[] | null>(() => {
    if (route) return route.path;
    if (origin) {
      return [
        [origin.lat, origin.lng],
        [destination.lat, destination.lng],
      ];
    }
    return null;
  }, [route, origin, destination]);

  async function computeRoute(from: RoutePoint) {
    setOrigin(from);
    setRoute(null);
    setFallbackM(null);
    setStatus("routing");
    try {
      setRoute(await fetchRoute(from, destination));
      setMessage(null);
    } catch {
      setFallbackM(straightDistanceM(from, destination));
      setMessage(
        "مسیر دقیق در دسترس نیست. فاصله مستقیم نشان داده شد؛ برای مسیر کامل از برنامه مسیریاب استفاده کنید.",
      );
    } finally {
      setStatus("done");
    }
  }

  async function showRoute() {
    setStatus("locating");
    setMessage(null);
    setOfferDemo(false);
    try {
      const position = await getPosition();
      await computeRoute({ lat: position.latitude, lng: position.longitude });
    } catch (err) {
      setStatus("idle");
      setMessage(
        isPositionError(err)
          ? positionErrorMessage(err)
          : "موقعیت شما پیدا نشد.",
      );
      setOfferDemo(DEMO_MODE);
    }
  }

  // Demo only: a made-up starting point about a kilometer away.
  function useDemoLocation() {
    setOfferDemo(false);
    setMessage(null);
    void computeRoute({
      lat: destination.lat + 0.01,
      lng: destination.lng + 0.007,
    });
  }

  const busy = status === "locating" || status === "routing";
  const distanceM = route ? route.distanceM : fallbackM;

  return (
    <section className="flex flex-col gap-4 rounded-3xl bg-card p-5">
      <h3 className="font-semibold">مسیر تا وسیله</h3>

      <div className="relative isolate h-60 overflow-hidden rounded-2xl">
        <RouteMap
          destination={destination}
          origin={origin}
          path={path}
          dashed={!route}
        />
      </div>

      {distanceM !== null ? (
        <dl className="animate-fade-up flex items-center justify-between gap-4 rounded-2xl bg-secondary px-4 py-3 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">
              {route ? "طول مسیر" : "فاصله مستقیم"}
            </dt>
            <dd className="mt-0.5 font-bold">{formatDistance(distanceM)}</dd>
          </div>
          {route ? (
            <div className="text-end">
              <dt className="text-xs text-muted-foreground">
                {route.mode === "walking" ? "زمان پیاده" : "زمان با خودرو"}
              </dt>
              <dd className="mt-0.5 font-bold">
                {formatDuration(route.durationS)}
              </dd>
            </div>
          ) : null}
        </dl>
      ) : null}

      {message ? (
        <p
          role="status"
          className="animate-fade-up text-sm leading-relaxed text-muted-foreground"
        >
          {message}
        </p>
      ) : null}

      <Button
        onClick={showRoute}
        disabled={busy}
        className="h-12 rounded-full font-bold"
      >
        {busy ? (
          <LoaderCircle className="animate-spin" />
        ) : (
          <Navigation className="size-4" />
        )}
        {status === "locating"
          ? "در حال یافتن موقعیت…"
          : status === "routing"
            ? "در حال محاسبه مسیر…"
            : origin
              ? "به‌روزرسانی مسیر"
              : "نمایش مسیر از موقعیت من"}
      </Button>

      {offerDemo ? (
        <Button
          variant="outline"
          onClick={useDemoLocation}
          className="animate-fade-up h-11 rounded-full border-border bg-secondary text-sm"
        >
          استفاده از موقعیت نمایشی
        </Button>
      ) : null}

      <div className="flex flex-wrap gap-2 text-xs">
        <a
          href={`https://www.google.com/maps/dir/?api=1&destination=${latitude},${longitude}&travelmode=walking`}
          target="_blank"
          rel="noopener noreferrer"
          className="press rounded-full bg-secondary px-3 py-1.5 hover:bg-accent"
        >
          Google Maps
        </a>
        <a
          href={`https://maps.apple.com/?daddr=${latitude},${longitude}&dirflg=w`}
          target="_blank"
          rel="noopener noreferrer"
          className="press rounded-full bg-secondary px-3 py-1.5 hover:bg-accent"
        >
          Apple Maps
        </a>
        <a
          href={`https://waze.com/ul?ll=${latitude},${longitude}&navigate=yes`}
          target="_blank"
          rel="noopener noreferrer"
          className="press rounded-full bg-secondary px-3 py-1.5 hover:bg-accent"
        >
          Waze
        </a>
      </div>

      <p className="text-[11px] leading-relaxed text-muted-foreground">
        مسیریابی: OSRM (FOSSGIS) · داده نقشه © OpenStreetMap
      </p>
    </section>
  );
}
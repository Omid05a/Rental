"use client";

import { ChevronUp, LocateFixed } from "lucide-react";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

import type { LatLng } from "@/components/map/location-picker";
import { VehicleCard } from "@/components/vehicle-card";
import { apiFetch } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";
import { toFa } from "@/lib/format";
import type { Paginated, PublicVehicle, VehicleKind } from "@/lib/vehicles";

// Leaflet needs the browser, so the map is loaded on the client only.
const ExploreMap = dynamic(() => import("@/components/map/explore-map"), {
  ssr: false,
  loading: () => <div className="size-full animate-pulse bg-card" />,
});

type Kind = "all" | VehicleKind;

type SearchResult = {
  query: string;
  items: PublicVehicle[];
  error: string | null;
};

const KIND_OPTIONS: { value: Kind; label: string }[] = [
  { value: "all", label: "همه" },
  { value: "car", label: "خودرو" },
  { value: "bike", label: "دوچرخه" },
];

const NO_ITEMS: PublicVehicle[] = [];

function buildQuery(kind: Kind, point: LatLng | null) {
  const params = new URLSearchParams({ page_size: "50" });
  if (kind !== "all") params.set("kind", kind);
  if (point) {
    params.set("lat", String(point.lat));
    params.set("lng", String(point.lng));
    params.set("radius_km", "25");
  }
  return params.toString();
}

export default function ExplorePage() {
  const { user, ready } = useRequireAuth();

  const [kind, setKind] = useState<Kind>("all");
  const [userPoint, setUserPoint] = useState<LatLng | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [result, setResult] = useState<SearchResult | null>(null);

  const query = useMemo(() => buildQuery(kind, userPoint), [kind, userPoint]);

  useEffect(() => {
    let active = true;
    apiFetch<Paginated<PublicVehicle>>(`/vehicles/?${query}`)
      .then((data) => {
        if (active) setResult({ query, items: data.results, error: null });
      })
      .catch((err) => {
        if (active) {
          setResult({ query, items: NO_ITEMS, error: getErrorMessage(err) });
        }
      });
    return () => {
      active = false;
    };
  }, [query]);

  const loading = result?.query !== query;
  const items = result?.items ?? NO_ITEMS;
  const selected = items.find((vehicle) => vehicle.id === selectedId) ?? null;

  function selectVehicle(id: number | null) {
    setSelectedId(id);
    if (id !== null) setExpanded(false);
  }

  function locateMe() {
    if (!navigator.geolocation) {
      setLocationError("مرورگر شما از موقعیت‌یابی پشتیبانی نمی‌کند.");
      return;
    }
    setLocating(true);
    setLocationError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserPoint({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
        setSelectedId(null);
        setLocating(false);
      },
      () => {
        setLocationError(
          "دسترسی به موقعیت شما ممکن نشد. اجازه موقعیت‌یابی مرورگر را بررسی کنید.",
        );
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  if (!ready || !user) {
    return <div className="h-[calc(100dvh-5rem)] bg-background" />;
  }

  const sheetHeight = expanded ? "h-[68%]" : selected ? "h-56" : "h-36";

  return (
    <div className="relative h-[calc(100dvh-5rem)] w-full overflow-hidden bg-background">
      <div className="absolute inset-0 isolate">
        <ExploreMap
          vehicles={items}
          selectedId={selectedId}
          userPoint={userPoint}
          onSelect={selectVehicle}
        />
      </div>

      <div className="absolute inset-x-0 top-0 z-10 flex items-center gap-2 p-4 pt-6">
        <div
          role="group"
          aria-label="نوع وسیله"
          className="flex flex-1 gap-2 overflow-x-auto"
        >
          {KIND_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              aria-pressed={kind === option.value}
              onClick={() => {
                setKind(option.value);
                setSelectedId(null);
              }}
              className={`h-10 shrink-0 rounded-full px-5 text-sm font-medium shadow-lg ${
                kind === option.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-background/90 text-foreground"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={locateMe}
          disabled={locating}
          aria-label="موقعیت من"
          className="flex size-10 shrink-0 items-center justify-center rounded-full bg-background/90 shadow-lg disabled:opacity-60"
        >
          <LocateFixed className="size-5" />
        </button>
      </div>

      {locationError ? (
        <p
          role="alert"
          className="absolute inset-x-4 top-20 z-10 rounded-2xl bg-background/95 p-3 text-sm text-destructive shadow-lg"
        >
          {locationError}
        </p>
      ) : null}

      <section
        className={`absolute inset-x-0 bottom-0 z-10 flex flex-col rounded-t-3xl bg-background shadow-[0_-8px_24px_rgba(0,0,0,0.5)] transition-[height] duration-300 ${sheetHeight}`}
      >
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          className="flex flex-col items-center gap-2 px-6 pb-3 pt-3"
        >
          <span className="h-1.5 w-10 rounded-full bg-white/25" />
          <span className="flex w-full items-center justify-between text-sm">
            <strong>
              {loading
                ? "در حال جستجو…"
                : `${toFa(items.length)} وسیله${userPoint ? " نزدیک شما" : ""}`}
            </strong>
            <ChevronUp
              className={`size-5 transition-transform ${
                expanded ? "rotate-180" : ""
              }`}
            />
          </span>
        </button>

        <div className="flex-1 overflow-y-auto px-4 pb-4">
          {result?.error ? (
            <p role="alert" className="px-2 text-sm text-destructive">
              {result.error}
            </p>
          ) : null}

          {!result?.error && !loading && items.length === 0 ? (
            <p className="px-2 text-center text-sm text-muted-foreground">
              وسیله‌ای پیدا نشد. فیلتر را تغییر دهید.
            </p>
          ) : null}

          {expanded ? (
            <ul className="flex flex-col gap-3">
              {items.map((vehicle) => (
                <li key={vehicle.id}>
                  <VehicleCard
                    vehicle={vehicle}
                    highlighted={vehicle.id === selectedId}
                  />
                </li>
              ))}
            </ul>
          ) : selected ? (
            <VehicleCard vehicle={selected} highlighted />
          ) : items.length > 0 ? (
            <p className="px-2 text-center text-sm text-muted-foreground">
              روی یک قیمت در نقشه بزنید یا فهرست را باز کنید.
            </p>
          ) : null}
        </div>
      </section>
    </div>
  );
}
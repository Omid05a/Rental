"use client";

import "leaflet/dist/leaflet.css";

import L from "leaflet";
import { LocateFixed } from "lucide-react";
import { useEffect, useState } from "react";
import {
  MapContainer,
  Marker,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";

export type LatLng = { lat: number; lng: number };

const TEHRAN: LatLng = { lat: 35.6892, lng: 51.389 };

// A custom pin avoids Leaflet's default marker images, which break with bundlers.
const pinIcon = L.divIcon({
  className: "",
  html: `<svg width="36" height="46" viewBox="0 0 36 46" xmlns="http://www.w3.org/2000/svg"><path d="M18 1C9.2 1 2 8.1 2 16.8c0 11.6 16 28.2 16 28.2s16-16.6 16-28.2C34 8.1 26.8 1 18 1z" fill="#FFC700" stroke="#111111" stroke-width="2"/><circle cx="18" cy="17" r="6" fill="#111111"/></svg>`,
  iconSize: [36, 46],
  iconAnchor: [18, 46],
});

function ClickHandler({ onPick }: { onPick: (point: LatLng) => void }) {
  useMapEvents({
    click(event) {
      onPick({ lat: event.latlng.lat, lng: event.latlng.lng });
    },
  });
  return null;
}

function FlyTo({ target }: { target: LatLng | null }) {
  const map = useMap();
  useEffect(() => {
    if (target) {
      map.setView([target.lat, target.lng], Math.max(map.getZoom(), 15));
    }
  }, [target, map]);
  return null;
}

type Props = {
  value: LatLng | null;
  onChange: (point: LatLng) => void;
  /** Shows the pin without letting the user move it. */
  readOnly?: boolean;
};

export default function LocationPicker({
  value,
  onChange,
  readOnly = false,
}: Props) {
  const [flyTarget, setFlyTarget] = useState<LatLng | null>(null);
  const [locating, setLocating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  function locateMe() {
    if (!navigator.geolocation) {
      setMessage("مرورگر شما از موقعیت‌یابی پشتیبانی نمی‌کند.");
      return;
    }
    setLocating(true);
    setMessage(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const point = {
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        };
        onChange(point);
        setFlyTarget(point);
        setLocating(false);
      },
      () => {
        setMessage(
          "دسترسی به موقعیت شما ممکن نشد. اجازه موقعیت‌یابی مرورگر را بررسی کنید.",
        );
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  const center = value ?? TEHRAN;

  return (
    <div className="flex flex-col gap-2">
      <div className="relative isolate overflow-hidden rounded-3xl">
        <MapContainer
          center={[center.lat, center.lng]}
          zoom={value ? 15 : 12}
          scrollWheelZoom={false}
          className="h-72 w-full"
          style={{ background: "#1c1c1c" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
            className="dark-tiles"
          />
          {readOnly ? null : <ClickHandler onPick={onChange} />}
          <FlyTo target={flyTarget} />
          {value ? (
            <Marker
              position={[value.lat, value.lng]}
              icon={pinIcon}
              draggable={!readOnly}
              eventHandlers={{
                dragend(event) {
                  const next = (event.target as L.Marker).getLatLng();
                  onChange({ lat: next.lat, lng: next.lng });
                },
              }}
            />
          ) : null}
        </MapContainer>

        {readOnly ? null : (
          <button
            type="button"
            onClick={locateMe}
            disabled={locating}
            className="absolute bottom-3 end-3 z-[1000] flex h-11 items-center gap-2 rounded-full bg-background/90 px-4 text-sm font-medium text-foreground shadow-lg disabled:opacity-60"
          >
            <LocateFixed className="size-4" />
            {locating ? "در حال یافتن…" : "موقعیت من"}
          </button>
        )}
      </div>

      {message ? (
        <p className="px-2 text-sm text-destructive">{message}</p>
      ) : null}
    </div>
  );
}
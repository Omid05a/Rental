"use client";

import "leaflet/dist/leaflet.css";

import L from "leaflet";
import { useEffect, useMemo } from "react";
import {
  MapContainer,
  Marker,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";

import type { LatLng } from "@/components/map/location-picker";
import { formatPriceShort } from "@/lib/format";
import type { PublicVehicle } from "@/lib/vehicles";

const TEHRAN: LatLng = { lat: 35.6892, lng: 51.389 };

function pinHtml(text: string, selected: boolean) {
  const background = selected ? "#111111" : "#FFC700";
  const color = selected ? "#FFC700" : "#111111";
  const border = selected ? "#FFC700" : "#111111";
  return `<div style="position:absolute;left:0;top:0;transform:translate(-50%,-100%);display:flex;flex-direction:column;align-items:center">
    <div style="background:${background};color:${color};border:2px solid ${border};border-radius:9999px;padding:4px 10px;font:700 12px 'Vazirmatn Variable',system-ui,sans-serif;white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,0.4)">${text}</div>
    <div style="width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-top:8px solid ${border};margin-top:-1px"></div>
  </div>`;
}

const userIcon = L.divIcon({
  className: "",
  iconSize: [22, 22],
  iconAnchor: [11, 11],
  html: '<div style="width:22px;height:22px;border-radius:9999px;background:#3b82f6;border:3px solid #ffffff;box-shadow:0 0 0 8px rgba(59,130,246,0.25)"></div>',
});

function PricePin({
  vehicle,
  selected,
  onSelect,
}: {
  vehicle: PublicVehicle;
  selected: boolean;
  onSelect: (id: number) => void;
}) {
  const icon = useMemo(
    () =>
      L.divIcon({
        className: "",
        iconSize: [0, 0],
        html: pinHtml(formatPriceShort(vehicle.price_per_hour), selected),
      }),
    [vehicle.price_per_hour, selected],
  );

  return (
    <Marker
      position={[vehicle.latitude, vehicle.longitude]}
      icon={icon}
      zIndexOffset={selected ? 1000 : 0}
      eventHandlers={{ click: () => onSelect(vehicle.id) }}
    />
  );
}

function MapClick({ onClear }: { onClear: () => void }) {
  useMapEvents({
    click() {
      onClear();
    },
  });
  return null;
}

function FitView({
  points,
  user,
}: {
  points: LatLng[];
  user: LatLng | null;
}) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 0) {
      const bounds = L.latLngBounds(points.map((p) => L.latLng(p.lat, p.lng)));
      map.fitBounds(bounds, {
        paddingTopLeft: [40, 90],
        paddingBottomRight: [40, 180],
        maxZoom: 15,
      });
    } else if (user) {
      map.setView([user.lat, user.lng], 14);
    }
  }, [points, user, map]);
  return null;
}

function PanToSelected({ vehicle }: { vehicle: PublicVehicle | null }) {
  const map = useMap();
  useEffect(() => {
    if (vehicle) {
      map.panTo([vehicle.latitude, vehicle.longitude]);
    }
  }, [vehicle, map]);
  return null;
}

type Props = {
  vehicles: PublicVehicle[];
  selectedId: number | null;
  userPoint: LatLng | null;
  onSelect: (id: number | null) => void;
};

export default function ExploreMap({
  vehicles,
  selectedId,
  userPoint,
  onSelect,
}: Props) {
  const points = useMemo(
    () => vehicles.map((v) => ({ lat: v.latitude, lng: v.longitude })),
    [vehicles],
  );
  const selected = useMemo(
    () => vehicles.find((v) => v.id === selectedId) ?? null,
    [vehicles, selectedId],
  );

  return (
    <MapContainer
      center={[TEHRAN.lat, TEHRAN.lng]}
      zoom={11}
      zoomControl={false}
      className="size-full"
      style={{ background: "#1c1c1c" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        maxZoom={19}
        className="dark-tiles"
      />
      <MapClick onClear={() => onSelect(null)} />
      <FitView points={points} user={userPoint} />
      <PanToSelected vehicle={selected} />

      {vehicles.map((vehicle) => (
        <PricePin
          key={vehicle.id}
          vehicle={vehicle}
          selected={vehicle.id === selectedId}
          onSelect={onSelect}
        />
      ))}

      {userPoint ? (
        <Marker
          position={[userPoint.lat, userPoint.lng]}
          icon={userIcon}
          interactive={false}
        />
      ) : null}
    </MapContainer>
  );
}
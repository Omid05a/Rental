"use client";

import { Camera, Check, LoaderCircle } from "lucide-react";
import { useEffect, useState, type ChangeEvent } from "react";

import { useAuth } from "@/lib/auth";
import { ANGLE_LABEL, type Angle, type TripPhoto } from "@/lib/bookings";
import { getErrorMessage } from "@/lib/errors";
import { toFa } from "@/lib/format";
import { compressImage } from "@/lib/image";
import { cn } from "@/lib/utils";

type Props = {
  bookingId: number;
  phase: "start" | "end";
  angles: Angle[];
  photos: TripPhoto[];
  disabled?: boolean;
  onChanged: () => Promise<void>;
};

export function PhotoCapture({
  bookingId,
  phase,
  angles,
  photos,
  disabled = false,
  onChanged,
}: Props) {
  const { authFetch } = useAuth();
  const [busyAngle, setBusyAngle] = useState<Angle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [coords, setCoords] = useState<{
    latitude: number;
    longitude: number;
  } | null>(null);

  // Best effort: photos carry the location when the browser allows it.
  useEffect(() => {
    if (typeof navigator === "undefined" || !navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (result) =>
        setCoords({
          latitude: result.coords.latitude,
          longitude: result.coords.longitude,
        }),
      () => undefined,
      { timeout: 8000, maximumAge: 60000 },
    );
  }, []);

  async function handleFile(angle: Angle, event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setBusyAngle(angle);
    setError(null);
    try {
      const image = await compressImage(file);
      const body = new FormData();
      body.append("image", image);
      body.append("phase", phase);
      body.append("angle", angle);
      if (coords) {
        body.append("latitude", String(coords.latitude));
        body.append("longitude", String(coords.longitude));
      }
      await authFetch(`/bookings/${bookingId}/photos/`, {
        method: "POST",
        body,
      });
      await onChanged();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyAngle(null);
    }
  }

  const done = angles.filter((angle) =>
    photos.some((photo) => photo.angle === angle),
  ).length;

  return (
    <div className="flex flex-col gap-3">
      <p className="px-1 text-sm text-muted-foreground">
        {toFa(done)} از {toFa(angles.length)} عکس ثبت شده
      </p>

      <ul className="grid grid-cols-3 gap-2">
        {angles.map((angle) => {
          const photo = photos.find((item) => item.angle === angle);
          const busy = busyAngle === angle;
          return (
            <li key={angle}>
              <label
                className={cn(
                  "press relative flex aspect-square cursor-pointer flex-col items-center justify-center gap-1 overflow-hidden rounded-2xl bg-card text-xs text-muted-foreground hover:bg-accent",
                  (disabled || busyAngle !== null) &&
                    "pointer-events-none opacity-60",
                )}
              >
                {photo ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={photo.image}
                    src={photo.image}
                    alt=""
                    className="animate-fade-in absolute inset-0 size-full object-cover"
                  />
                ) : busy ? (
                  <LoaderCircle className="size-6 animate-spin text-primary" />
                ) : (
                  <Camera className="size-6" />
                )}

                {photo ? (
                  <span
                    key={photo.image}
                    className="animate-scale-in absolute end-1.5 top-1.5 flex size-6 items-center justify-center rounded-full bg-green-500 text-white"
                  >
                    <Check className="size-4" />
                  </span>
                ) : null}

                <span
                  className={cn(
                    "relative z-10",
                    photo &&
                      "absolute inset-x-0 bottom-0 bg-black/60 py-1 text-center text-white",
                  )}
                >
                  {busy ? "در حال ارسال…" : ANGLE_LABEL[angle]}
                </span>

                <input
                  type="file"
                  accept="image/*"
                  capture="environment"
                  className="sr-only"
                  disabled={disabled || busyAngle !== null}
                  onChange={(event) => handleFile(angle, event)}
                />
              </label>
            </li>
          );
        })}
      </ul>

      {error ? (
        <p
          role="alert"
          className="animate-fade-up px-1 text-sm text-destructive"
        >
          {error}
        </p>
      ) : null}
    </div>
  );
}
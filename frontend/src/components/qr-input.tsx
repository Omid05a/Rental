"use client";

import { ScanLine, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { INPUT_CLASS } from "@/components/form-bits";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type Detector = {
  detect: (source: CanvasImageSource) => Promise<{ rawValue: string }[]>;
};
type DetectorConstructor = new (options: { formats: string[] }) => Detector;

function createDetector(): Detector | null {
  const Constructor = (
    globalThis as { BarcodeDetector?: DetectorConstructor }
  ).BarcodeDetector;
  return Constructor ? new Constructor({ formats: ["qr_code"] }) : null;
}

type Props = {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
};

export function QrInput({ value, onChange, disabled = false }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [scanning, setScanning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!scanning) return;

    const detector = createDetector();
    let stream: MediaStream | null = null;
    let timer: number | undefined;
    let cancelled = false;

    async function run() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
        });
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        const video = videoRef.current;
        if (!video || !detector) return;

        video.srcObject = stream;
        await video.play();
        timer = window.setInterval(async () => {
          try {
            const codes = await detector.detect(video);
            if (codes.length > 0 && codes[0].rawValue) {
              onChange(codes[0].rawValue);
              setScanning(false);
            }
          } catch {
            // A frame without a readable code is normal; keep scanning.
          }
        }, 400);
      } catch {
        setMessage("دسترسی به دوربین ممکن نشد. کد را دستی وارد کنید.");
        setScanning(false);
      }
    }
    void run();

    return () => {
      cancelled = true;
      if (timer) window.clearInterval(timer);
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, [scanning, onChange]);

  function startScan() {
    if (!createDetector()) {
      setMessage(
        "مرورگر شما اسکن QR را پشتیبانی نمی‌کند. کد چاپ‌شده روی وسیله را دستی وارد کنید.",
      );
      return;
    }
    setMessage(null);
    setScanning(true);
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2">
        <Input
          dir="ltr"
          placeholder="RENTAL-12-ab12cd34ef"
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          className={cn(INPUT_CLASS, "flex-1")}
        />
        <button
          type="button"
          onClick={startScan}
          disabled={disabled}
          aria-label="اسکن QR با دوربین"
          className="flex size-14 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground disabled:opacity-50"
        >
          <ScanLine className="size-6" />
        </button>
      </div>

      {scanning ? (
        <div className="relative overflow-hidden rounded-3xl bg-black">
          <video
            ref={videoRef}
            playsInline
            muted
            className="aspect-square w-full object-cover"
          />
          <button
            type="button"
            onClick={() => setScanning(false)}
            aria-label="بستن دوربین"
            className="absolute end-3 top-3 flex size-10 items-center justify-center rounded-full bg-black/60 text-white"
          >
            <X className="size-5" />
          </button>
        </div>
      ) : null}

      {message ? (
        <p role="alert" className="px-2 text-sm text-destructive">
          {message}
        </p>
      ) : null}
    </div>
  );
}
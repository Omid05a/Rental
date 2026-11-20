"use client";

import { ChevronLeft, ChevronRight, Minus, Plus } from "lucide-react";
import { useMemo, useState } from "react";

import { toFa } from "@/lib/format";
import { JALALI_MONTHS, WEEKDAYS_SHORT, type DayInfo } from "@/lib/jalali";
import { cn } from "@/lib/utils";

export function JalaliDatePicker({
  days,
  selected,
  onSelect,
}: {
  days: DayInfo[];
  selected: string | null;
  onSelect: (iso: string) => void;
}) {
  const months = useMemo(() => {
    const groups = new Map<string, DayInfo[]>();
    for (const day of days) {
      const key = `${day.jy}-${day.jm}`;
      const list = groups.get(key);
      if (list) {
        list.push(day);
      } else {
        groups.set(key, [day]);
      }
    }
    return Array.from(groups.values());
  }, [days]);

  const [monthIndex, setMonthIndex] = useState(() => {
    const index = months.findIndex((month) =>
      month.some((day) => day.iso === selected),
    );
    return Math.max(0, index);
  });

  const month = months[monthIndex];
  if (!month) return null;

  const first = month[0];
  const todayIso = days[0]?.iso;

  return (
    <div className="rounded-3xl bg-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <button
          type="button"
          aria-label="ماه قبل"
          disabled={monthIndex === 0}
          onClick={() => setMonthIndex(monthIndex - 1)}
          className="flex size-9 items-center justify-center rounded-full bg-secondary disabled:opacity-30"
        >
          <ChevronRight className="size-5" />
        </button>
        <h3 className="font-semibold">
          {JALALI_MONTHS[first.jm - 1]} {toFa(first.jy)}
        </h3>
        <button
          type="button"
          aria-label="ماه بعد"
          disabled={monthIndex === months.length - 1}
          onClick={() => setMonthIndex(monthIndex + 1)}
          className="flex size-9 items-center justify-center rounded-full bg-secondary disabled:opacity-30"
        >
          <ChevronLeft className="size-5" />
        </button>
      </div>

      <div className="grid grid-cols-7 gap-1 text-center text-xs text-muted-foreground">
        {WEEKDAYS_SHORT.map((name) => (
          <span key={name} className="py-1">
            {name}
          </span>
        ))}
      </div>

      <div className="mt-1 grid grid-cols-7 gap-1">
        {Array.from({ length: first.weekday }).map((_, i) => (
          <span key={`blank-${i}`} />
        ))}
        {month.map((day) => {
          const isSelected = day.iso === selected;
          return (
            <button
              key={day.iso}
              type="button"
              aria-pressed={isSelected}
              onClick={() => onSelect(day.iso)}
              className={cn(
                "flex aspect-square items-center justify-center rounded-full text-sm",
                isSelected
                  ? "bg-primary font-bold text-primary-foreground"
                  : "bg-secondary/40 text-foreground",
                !isSelected && day.iso === todayIso && "ring-1 ring-primary",
              )}
            >
              {toFa(day.jd)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const MINUTES = [0, 15, 30, 45];
const SELECT_CLASS =
  "h-14 flex-1 appearance-none rounded-full border-0 bg-card px-5 text-center text-base";

export function TimeSelect({
  hour,
  minute,
  onChange,
}: {
  hour: number;
  minute: number;
  onChange: (hour: number, minute: number) => void;
}) {
  const pad = (value: number) => toFa(String(value).padStart(2, "0"));

  return (
    <div dir="ltr" className="flex items-center gap-3">
      <select
        aria-label="ساعت"
        className={SELECT_CLASS}
        style={{ colorScheme: "dark" }}
        value={hour}
        onChange={(event) => onChange(Number(event.target.value), minute)}
      >
        {HOURS.map((value) => (
          <option key={value} value={value}>
            {pad(value)}
          </option>
        ))}
      </select>
      <span className="text-xl font-bold">:</span>
      <select
        aria-label="دقیقه"
        className={SELECT_CLASS}
        style={{ colorScheme: "dark" }}
        value={minute}
        onChange={(event) => onChange(hour, Number(event.target.value))}
      >
        {MINUTES.map((value) => (
          <option key={value} value={value}>
            {pad(value)}
          </option>
        ))}
      </select>
    </div>
  );
}

export function Stepper({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="flex flex-1 flex-col items-center gap-2 rounded-3xl bg-card p-3">
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="flex items-center gap-3">
        <button
          type="button"
          aria-label={`کاهش ${label}`}
          disabled={value <= min}
          onClick={() => onChange(value - 1)}
          className="flex size-10 items-center justify-center rounded-full bg-secondary disabled:opacity-30"
        >
          <Minus className="size-4" />
        </button>
        <span className="min-w-8 text-center text-xl font-bold">
          {toFa(value)}
        </span>
        <button
          type="button"
          aria-label={`افزایش ${label}`}
          disabled={value >= max}
          onClick={() => onChange(value + 1)}
          className="flex size-10 items-center justify-center rounded-full bg-secondary disabled:opacity-30"
        >
          <Plus className="size-4" />
        </button>
      </div>
    </div>
  );
}
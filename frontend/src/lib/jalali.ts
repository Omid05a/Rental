// Helpers for the Persian (Solar Hijri) calendar built on the Intl API.
// Iran has no daylight saving time, so Tehran is always UTC+03:30.

export const TEHRAN_TZ = "Asia/Tehran";
const TEHRAN_OFFSET = "+03:30";
const OFFSET_MS = 210 * 60_000;
const HOUR_MS = 3_600_000;
const DAY_MS = 86_400_000;

export const JALALI_MONTHS = [
  "فروردین",
  "اردیبهشت",
  "خرداد",
  "تیر",
  "مرداد",
  "شهریور",
  "مهر",
  "آبان",
  "آذر",
  "دی",
  "بهمن",
  "اسفند",
];

// Saturday first, as in the Persian week.
export const WEEKDAYS_SHORT = ["ش", "ی", "د", "س", "چ", "پ", "ج"];

export type DayInfo = {
  /** Gregorian date, YYYY-MM-DD, in Tehran. */
  iso: string;
  jy: number;
  jm: number;
  jd: number;
  /** 0 = Saturday ... 6 = Friday */
  weekday: number;
};

const gregorianFormat = new Intl.DateTimeFormat("en-CA", {
  timeZone: TEHRAN_TZ,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

const persianFormat = new Intl.DateTimeFormat("en-US-u-ca-persian-nu-latn", {
  timeZone: TEHRAN_TZ,
  year: "numeric",
  month: "numeric",
  day: "numeric",
});

const timeFormat = new Intl.DateTimeFormat("en-GB", {
  timeZone: TEHRAN_TZ,
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const displayFormat = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
  timeZone: TEHRAN_TZ,
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function persianParts(date: Date) {
  const parts = persianFormat.formatToParts(date);
  const read = (...types: string[]) =>
    Number(parts.find((part) => types.includes(part.type))?.value);
  return {
    jy: read("year", "relatedYear"),
    jm: read("month"),
    jd: read("day"),
  };
}

/** Consecutive days starting today (Tehran time). */
export function buildDayWindow(count: number, from: Date = new Date()) {
  const days: DayInfo[] = [];
  for (let i = 0; i < count; i++) {
    const date = new Date(from.getTime() + i * DAY_MS);
    const iso = gregorianFormat.format(date);
    const weekday = (new Date(`${iso}T12:00:00Z`).getUTCDay() + 1) % 7;
    days.push({ iso, weekday, ...persianParts(date) });
  }
  return days;
}

/** The next whole hour in Tehran, at least one minute from now. */
export function nextFullHour(from: Date = new Date()) {
  const local = from.getTime() + OFFSET_MS;
  const rounded = Math.ceil((local + 60_000) / HOUR_MS) * HOUR_MS;
  return new Date(rounded - OFFSET_MS);
}

export function tehranParts(date: Date) {
  const [hour, minute] = timeFormat.format(date).split(":").map(Number);
  return { dateIso: gregorianFormat.format(date), hour, minute };
}

/** Builds an ISO timestamp with the Tehran offset from picker values. */
export function toTehranIso(dateIso: string, hour: number, minute: number) {
  const hh = String(hour).padStart(2, "0");
  const mm = String(minute).padStart(2, "0");
  return `${dateIso}T${hh}:${mm}:00${TEHRAN_OFFSET}`;
}

export function formatJalaliDateTime(value: string | Date) {
  return displayFormat.format(typeof value === "string" ? new Date(value) : value);
}
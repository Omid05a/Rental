const FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
const AR_DIGITS = "٠١٢٣٤٥٦٧٨٩";

export function toFa(value: string | number): string {
  return String(value).replace(/\d/g, (digit) => FA_DIGITS[Number(digit)]);
}

/** Converts Persian and Arabic-Indic digits to ASCII digits. */
export function toEnDigits(value: string): string {
  return value.replace(/[۰-۹٠-٩]/g, (char) => {
    const fa = FA_DIGITS.indexOf(char);
    return String(fa >= 0 ? fa : AR_DIGITS.indexOf(char));
  });
}

export function formatCountdown(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  return toFa(`${minutes}:${seconds}`);
}

export function formatToman(amount: number): string {
  return `${new Intl.NumberFormat("fa-IR").format(amount)} تومان`;
}

export function formatPriceShort(amount: number): string {
  const fa = (value: number, digits: number) =>
    new Intl.NumberFormat("fa-IR", { maximumFractionDigits: digits }).format(
      value,
    );
  if (amount >= 1_000_000) return `${fa(amount / 1_000_000, 1)} میلیون`;
  if (amount >= 1_000) return `${fa(amount / 1_000, 0)} هزار`;
  return fa(amount, 0);
}

export function formatDistance(meters: number): string {
  if (meters < 1000) {
    return `${toFa(Math.max(10, Math.round(meters / 10) * 10))} متر`;
  }
  const km = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 1 }).format(
    meters / 1000,
  );
  return `${km} کیلومتر`;
}
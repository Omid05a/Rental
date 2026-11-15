import { Star } from "lucide-react";

import { toFa } from "@/lib/format";
import { cn } from "@/lib/utils";

export function Stars({
  value,
  className,
}: {
  value: number;
  className?: string;
}) {
  const rounded = Math.round(value);
  return (
    <span
      role="img"
      aria-label={`${toFa(value)} از ${toFa(5)}`}
      className={cn("inline-flex items-center gap-0.5", className)}
    >
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          className={cn(
            "size-4",
            n <= rounded
              ? "fill-primary text-primary"
              : "text-muted-foreground/40",
          )}
        />
      ))}
    </span>
  );
}

export function RatingBadge({
  avg,
  count,
}: {
  avg: number | null;
  count: number;
}) {
  if (!avg || count === 0) {
    return <span className="text-xs text-muted-foreground">بدون نظر</span>;
  }
  const text = new Intl.NumberFormat("fa-IR", {
    maximumFractionDigits: 1,
  }).format(avg);
  return (
    <span className="inline-flex items-center gap-1 text-xs">
      <Star className="size-3.5 fill-primary text-primary" />
      <strong>{text}</strong>
      <span className="text-muted-foreground">({toFa(count)})</span>
    </span>
  );
}

const LABELS = ["", "خیلی بد", "بد", "متوسط", "خوب", "عالی"];

export function StarInput({
  value,
  onChange,
  disabled = false,
}: {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        role="radiogroup"
        aria-label="امتیاز"
        dir="ltr"
        className="flex items-center justify-center gap-1"
      >
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={value === n}
            aria-label={`${toFa(n)} ستاره`}
            disabled={disabled}
            onClick={() => onChange(n)}
            className="p-1 disabled:opacity-50"
          >
            <Star
              className={cn(
                "size-9 transition-colors",
                n <= value
                  ? "fill-primary text-primary"
                  : "text-muted-foreground/40",
              )}
            />
          </button>
        ))}
      </div>
      <span className="h-4 text-xs text-muted-foreground">{LABELS[value]}</span>
    </div>
  );
}
"use client";

import type { InputHTMLAttributes, ReactNode } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toEnDigits, toFa } from "@/lib/format";
import { cn } from "@/lib/utils";

export const INPUT_CLASS = "h-14 rounded-full border-0 bg-card px-5 text-base";

export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
}: {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={htmlFor} className="px-2">
        {label}
      </Label>
      {children}
      {hint && !error ? (
        <p className="px-2 text-xs text-muted-foreground">{hint}</p>
      ) : null}
      {error ? (
        <p role="alert" className="px-2 text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function SegmentedControl<T extends string>({
  value,
  onChange,
  options,
  label,
}: {
  value: T;
  onChange: (value: T) => void;
  options: { value: T; label: string }[];
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-2">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          onClick={() => onChange(option.value)}
          className={cn(
            "h-12 min-w-24 flex-1 rounded-full px-4 text-sm font-medium transition-colors",
            value === option.value
              ? "bg-primary text-primary-foreground"
              : "bg-card text-foreground",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

/** Numeric text input: shows Persian digits and keeps ASCII digits in state. */
export function DigitsInput({
  value,
  onChange,
  className,
  ...props
}: Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange"> & {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <Input
      inputMode="numeric"
      className={cn(INPUT_CLASS, className)}
      value={toFa(value)}
      onChange={(event) =>
        onChange(toEnDigits(event.target.value).replace(/\D/g, ""))
      }
      {...props}
    />
  );
}
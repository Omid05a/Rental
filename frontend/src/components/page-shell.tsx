import "@fontsource/poppins/600.css";
import type { ReactNode } from "react";

export function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative mx-auto flex min-h-dvh w-full max-w-md flex-col overflow-hidden bg-background text-foreground">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(ellipse_at_top,rgba(255,199,0,0.14),transparent_70%)]"
      />
      <div className="relative flex flex-1 flex-col">{children}</div>
    </div>
  );
}

export function BrandMark() {
  return (
    <div className="flex flex-col items-center gap-3">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/images/logo-mark.svg" alt="" className="h-20 w-auto" />
      <span
        className="text-2xl font-semibold tracking-[0.18em] text-primary"
        style={{ fontFamily: "Poppins, system-ui, sans-serif" }}
      >
        RENTAL
      </span>
    </div>
  );
}

export function AuthHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <header className="flex flex-col items-center px-6 pb-8 pt-16 text-center">
      <BrandMark />
      <h1 className="mt-8 text-2xl font-bold">{title}</h1>
      {subtitle ? (
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          {subtitle}
        </p>
      ) : null}
    </header>
  );
}
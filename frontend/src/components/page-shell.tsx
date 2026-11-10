import type { ReactNode } from "react";

export function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col bg-background">
      {children}
    </div>
  );
}

export function BrandHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <header className="rounded-b-[40px] bg-foreground px-6 pb-10 pt-14 text-background">
      <span className="text-2xl font-extrabold text-primary">رنتال</span>
      <h1 className="mt-6 text-2xl font-bold leading-snug">{title}</h1>
      {subtitle ? (
        <p className="mt-2 text-sm leading-relaxed text-background/70">
          {subtitle}
        </p>
      ) : null}
    </header>
  );
}
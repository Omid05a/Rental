"use client";

import { Compass, User } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/explore", label: "جستجو", icon: Compass },
  { href: "/profile", label: "پروفایل", icon: User },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="ناوبری اصلی"
      className="fixed inset-x-0 bottom-0 z-50 mx-auto flex h-20 w-full max-w-md items-center justify-around border-t border-border bg-background/95 px-6 backdrop-blur"
    >
      {TABS.map((tab) => {
        const active = pathname.startsWith(tab.href);
        const Icon = tab.icon;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={`flex w-24 flex-col items-center gap-1 text-xs ${
              active ? "font-bold text-primary" : "text-muted-foreground"
            }`}
          >
            <Icon className="size-6" />
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
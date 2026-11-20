"use client";

import { Bell, CalendarClock, Compass, User } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useUnread } from "@/components/unread-provider";
import { toFa } from "@/lib/format";

const TABS = [
  { href: "/explore", label: "جستجو", icon: Compass, badge: false },
  { href: "/bookings", label: "رزروها", icon: CalendarClock, badge: false },
  { href: "/notifications", label: "اعلان‌ها", icon: Bell, badge: true },
  { href: "/profile", label: "پروفایل", icon: User, badge: false },
];

export function BottomNav() {
  const pathname = usePathname();
  const { count } = useUnread();

  return (
    <nav
      aria-label="ناوبری اصلی"
      className="fixed inset-x-0 bottom-0 z-50 mx-auto flex h-20 w-full max-w-md items-center justify-around border-t border-border bg-background/95 px-2 backdrop-blur"
    >
      {TABS.map((tab) => {
        const active = pathname.startsWith(tab.href);
        const Icon = tab.icon;
        const showBadge = tab.badge && count > 0;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={`press relative flex h-full w-20 flex-col items-center justify-center gap-1 text-xs ${
              active
                ? "font-bold text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {active ? (
              <span
                aria-hidden="true"
                className="animate-scale-in absolute inset-x-0 top-0 mx-auto h-0.5 w-8 rounded-full bg-primary"
              />
            ) : null}
            <span
              className={`relative transition-transform duration-300 ease-out ${
                active ? "-translate-y-0.5 scale-110" : ""
              }`}
            >
              <Icon className="size-6" />
              {showBadge ? (
                <span
                  key={count}
                  aria-label={`${toFa(count)} اعلان خوانده‌نشده`}
                  className="animate-scale-in absolute -end-2 -top-1.5 flex min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold leading-4 text-white"
                >
                  {count > 9 ? `${toFa(9)}+` : toFa(count)}
                </span>
              ) : null}
            </span>
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
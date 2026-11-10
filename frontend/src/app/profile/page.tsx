"use client";

import { useRouter } from "next/navigation";

import { PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
import { useRequireAuth, type VerificationStatus } from "@/lib/auth";
import { toFa } from "@/lib/format";

const STATUS: Record<
  VerificationStatus,
  { label: string; hint: string; className: string }
> = {
  not_submitted: {
    label: "احراز هویت انجام نشده",
    hint: "برای اجاره یا ثبت وسیله، ابتدا مدارک خود را ارسال کنید.",
    className: "bg-muted text-muted-foreground",
  },
  pending: {
    label: "در انتظار بررسی",
    hint: "مدارک شما در حال بررسی است. نتیجه به‌زودی اعلام می‌شود.",
    className: "bg-amber-100 text-amber-800",
  },
  approved: {
    label: "تأییدشده",
    hint: "هویت شما تأیید شده است.",
    className: "bg-green-100 text-green-800",
  },
  rejected: {
    label: "ردشده",
    hint: "مدارک شما تأیید نشد. دوباره ارسال کنید.",
    className: "bg-red-100 text-red-800",
  },
};

export default function ProfilePage() {
  const router = useRouter();
  const { user, ready, signOut } = useRequireAuth();

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  const status = STATUS[user.verification_status];
  const fullName = `${user.first_name} ${user.last_name}`.trim();
  const initial = (user.first_name || "ر").charAt(0);

  return (
    <PageShell>
      <header className="flex items-center gap-4 rounded-b-[40px] bg-foreground px-6 pb-10 pt-14 text-background">
        <div className="flex size-16 shrink-0 items-center justify-center rounded-full bg-primary text-2xl font-bold text-primary-foreground">
          {initial}
        </div>
        <div className="min-w-0">
          <h1 className="truncate text-xl font-bold">
            {fullName || "کاربر رنتال"}
          </h1>
          <p className="mt-1 text-sm text-background/70">
            <bdi dir="ltr">{toFa(user.phone)}</bdi>
          </p>
        </div>
      </header>

      <main className="flex flex-1 flex-col gap-4 px-6 py-8">
        <section className="flex flex-col gap-3 rounded-2xl border border-border p-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-semibold">وضعیت احراز هویت</h2>
            <span
              className={`rounded-full px-3 py-1 text-xs font-medium ${status.className}`}
            >
              {status.label}
            </span>
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {status.hint}
          </p>
          <Button disabled className="h-11 rounded-xl">
            ارسال مدارک (به‌زودی)
          </Button>
        </section>

        <Button
          variant="outline"
          className="h-12 rounded-xl"
          onClick={() => router.push("/onboarding")}
        >
          ویرایش نام
        </Button>

        <Button
          variant="ghost"
          className="h-12 rounded-xl text-destructive"
          onClick={() => {
            signOut();
            router.replace("/login");
          }}
        >
          خروج از حساب
        </Button>
      </main>
    </PageShell>
  );
}
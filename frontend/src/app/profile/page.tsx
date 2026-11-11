"use client";

import { ShieldCheck } from "lucide-react";
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
    className: "bg-white/10 text-white/70",
  },
  pending: {
    label: "در انتظار بررسی",
    hint: "مدارک شما در حال بررسی است. نتیجه به‌زودی اعلام می‌شود.",
    className: "bg-primary/15 text-primary",
  },
  approved: {
    label: "تأییدشده",
    hint: "هویت شما تأیید شده است.",
    className: "bg-green-500/15 text-green-400",
  },
  rejected: {
    label: "ردشده",
    hint: "مدارک شما تأیید نشد. دوباره ارسال کنید.",
    className: "bg-red-500/15 text-red-400",
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
      <header className="flex flex-col items-center px-6 pb-8 pt-16 text-center">
        <div className="flex size-20 items-center justify-center rounded-full bg-primary text-3xl font-bold text-primary-foreground">
          {initial}
        </div>
        <h1 className="mt-4 text-xl font-bold">{fullName || "کاربر رنتال"}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          <bdi dir="ltr">{toFa(user.phone)}</bdi>
        </p>
      </header>

      <main className="flex flex-1 flex-col gap-4 px-6 pb-10">
        <section className="flex flex-col gap-4 rounded-3xl bg-card p-5">
          <div className="flex items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
              <ShieldCheck className="size-5" />
            </div>
            <div className="flex flex-1 flex-col items-start gap-1">
              <h2 className="font-semibold">وضعیت احراز هویت</h2>
              <span
                className={`rounded-full px-3 py-0.5 text-xs font-medium ${status.className}`}
              >
                {status.label}
              </span>
            </div>
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {status.hint}
          </p>
          <Button disabled className="h-12 rounded-full font-bold">
            ارسال مدارک (به‌زودی)
          </Button>
        </section>

        <Button
          variant="outline"
          className="h-14 rounded-full border-border bg-card text-base"
          onClick={() => router.push("/onboarding")}
        >
          ویرایش نام
        </Button>

        <Button
          variant="ghost"
          className="h-14 rounded-full text-base text-destructive"
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
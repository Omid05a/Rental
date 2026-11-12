"use client";

import { Smartphone } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { IconInput } from "@/components/icon-input";
import { AuthHeader, PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@/components/ui/input-otp";
import { Label } from "@/components/ui/label";
import { apiFetch } from "@/lib/api";
import { useAuth, type User } from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";
import { formatCountdown, toFa } from "@/lib/format";

const RESEND_SECONDS = 60;

type RequestOtpResponse = { detail: string; dev_code?: string };
type VerifyOtpResponse = {
  access: string;
  refresh: string;
  user: User;
  is_new_user: boolean;
};

export default function LoginPage() {
  const router = useRouter();
  const { user, ready, signIn } = useAuth();

  const [step, setStep] = useState<"phone" | "code">("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Single place that decides where a signed-in user goes.
  useEffect(() => {
    if (ready && user) {
      router.replace(user.first_name ? "/explore" : "/onboarding");
    }
  }, [ready, user, router]);

  useEffect(() => {
    if (secondsLeft <= 0) return;
    const timer = setTimeout(() => setSecondsLeft((value) => value - 1), 1000);
    return () => clearTimeout(timer);
  }, [secondsLeft]);

  const requestCode = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<RequestOtpResponse>("/auth/request-otp/", {
        method: "POST",
        body: JSON.stringify({ phone }),
      });
      setDevCode(data.dev_code ?? null);
      setCode("");
      setSecondsLeft(RESEND_SECONDS);
      setStep("code");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [phone]);

  async function handlePhoneSubmit(event: FormEvent) {
    event.preventDefault();
    await requestCode();
  }

  async function verify(value: string) {
    if (value.length !== 6 || loading) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<VerifyOtpResponse>("/auth/verify-otp/", {
        method: "POST",
        body: JSON.stringify({ phone, code: value }),
      });
      signIn({ access: data.access, refresh: data.refresh }, data.user);
    } catch (err) {
      setError(getErrorMessage(err));
      setCode("");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageShell>
      <AuthHeader
        title={
          step === "phone" ? "سفر خود را شروع کنید" : "کد تأیید را وارد کنید"
        }
        subtitle={
          step === "phone"
            ? "شماره موبایل خود را برای ورود یا ثبت‌نام وارد کنید."
            : undefined
        }
      />

      <main className="flex flex-1 flex-col px-6">
        {step === "phone" ? (
          <form
            onSubmit={handlePhoneSubmit}
            className="flex flex-1 flex-col gap-5"
          >
            <div className="flex flex-col gap-2">
              <Label htmlFor="phone" className="px-2">
                شماره موبایل
              </Label>
              <IconInput
                id="phone"
                icon={<Smartphone className="size-5" />}
                type="tel"
                inputMode="numeric"
                autoComplete="tel"
                placeholder="۰۹۱۲۳۴۵۶۷۸۹"
                maxLength={11}
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
              />
            </div>

            {error ? (
              <p role="alert" className="px-2 text-sm text-destructive">
                {error}
              </p>
            ) : null}

            <Button
              type="submit"
              disabled={loading || phone.length < 11}
              className="h-14 w-full rounded-full text-base font-bold"
            >
              {loading ? "در حال ارسال…" : "دریافت کد تأیید"}
            </Button>

            <p className="mt-auto pb-8 pt-6 text-center text-xs text-muted-foreground">
              با ورود، قوانین و شرایط رنتال را می‌پذیرید.
            </p>
          </form>
        ) : (
          <div className="flex flex-1 flex-col gap-5">
            <div className="flex flex-col items-center gap-1 text-center">
              <p className="text-sm text-muted-foreground">
                کد ۶ رقمی به شماره <bdi dir="ltr">{toFa(phone)}</bdi> ارسال شد.
              </p>
              <button
                type="button"
                onClick={() => {
                  setStep("phone");
                  setError(null);
                }}
                className="text-sm font-medium text-primary underline underline-offset-4"
              >
                ویرایش شماره
              </button>
            </div>

            <div dir="ltr" className="flex justify-center">
              <InputOTP
                maxLength={6}
                value={code}
                onChange={setCode}
                onComplete={verify}
                disabled={loading}
                inputMode="numeric"
                autoFocus
              >
                <InputOTPGroup className="gap-2">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <InputOTPSlot
                      key={i}
                      index={i}
                      className="size-12 rounded-xl! border! bg-card text-lg"
                    />
                  ))}
                </InputOTPGroup>
              </InputOTP>
            </div>

            {error ? (
              <p role="alert" className="text-center text-sm text-destructive">
                {error}
              </p>
            ) : null}

            <Button
              type="button"
              disabled={loading || code.length !== 6}
              onClick={() => verify(code)}
              className="h-14 w-full rounded-full text-base font-bold"
            >
              {loading ? "در حال بررسی…" : "تأیید و ورود"}
            </Button>

            {secondsLeft > 0 ? (
              <p className="text-center text-sm text-muted-foreground">
                ارسال مجدد کد تا {formatCountdown(secondsLeft)} دیگر
              </p>
            ) : (
              <Button
                type="button"
                variant="ghost"
                disabled={loading}
                onClick={requestCode}
                className="h-12 rounded-full text-primary"
              >
                ارسال مجدد کد
              </Button>
            )}

            {devCode ? (
              <div className="mt-auto mb-8 rounded-2xl bg-card p-4 text-center text-sm text-muted-foreground">
                <p>
                  کد آزمایشی (فقط در حالت توسعه):{" "}
                  <bdi dir="ltr" className="font-bold text-foreground">
                    {devCode}
                  </bdi>
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setCode(devCode);
                    void verify(devCode);
                  }}
                  className="mt-1 font-medium text-primary underline underline-offset-4"
                >
                  پر کردن خودکار
                </button>
              </div>
            ) : null}
          </div>
        )}
      </main>
    </PageShell>
  );
}
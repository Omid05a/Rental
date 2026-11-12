"use client";

import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DigitsInput, Field } from "@/components/form-bits";
import { PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
import { useRequireAuth } from "@/lib/auth";
import {
  TRANSACTION_LABEL,
  type WalletData,
  type WalletTransaction,
} from "@/lib/bookings";
import { getErrorMessage } from "@/lib/errors";
import { formatToman, toFa } from "@/lib/format";
import { createAttemptKeys } from "@/lib/idempotency";
import { formatJalaliDateTime } from "@/lib/jalali";

const PRESETS = [500_000, 1_000_000, 2_000_000, 5_000_000];
const MIN_AMOUNT = 10_000;
const MAX_AMOUNT = 100_000_000;

export default function WalletPage() {
  const router = useRouter();
  const { user, ready, authFetch } = useRequireAuth();

  const [wallet, setWallet] = useState<WalletData | null>(null);
  const [amount, setAmount] = useState("1000000");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [attempts] = useState(createAttemptKeys);

  const reload = useCallback(async () => {
    setWallet(await authFetch<WalletData>("/wallet/"));
  }, [authFetch]);

  useEffect(() => {
    if (!ready || !user) return;
    let active = true;
    authFetch<WalletData>("/wallet/")
      .then((data) => {
        if (active) setWallet(data);
      })
      .catch((err) => {
        if (active) setError(getErrorMessage(err));
      });
    return () => {
      active = false;
    };
  }, [ready, user, authFetch]);

  async function handleTopUp() {
    const value = Number(amount);
    if (!value || value < MIN_AMOUNT || value > MAX_AMOUNT) {
      setError("مبلغ باید بین ۱۰ هزار تا ۱۰۰ میلیون تومان باشد.");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await authFetch("/wallet/topup/", {
        method: "POST",
        headers: { "Idempotency-Key": attempts.get(`topup|${value}`) },
        body: JSON.stringify({ amount: value }),
      });
      attempts.reset();
      await reload();
      setSuccess(`${formatToman(value)} به کیف پول اضافه شد.`);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  return (
    <PageShell>
      <header className="flex items-center gap-3 px-6 pb-4 pt-12">
        <button
          type="button"
          onClick={() => router.push("/profile")}
          aria-label="بازگشت"
          className="flex size-10 items-center justify-center rounded-full bg-card"
        >
          <ArrowRight className="size-5" />
        </button>
        <h1 className="text-xl font-bold">کیف پول</h1>
      </header>

      <main className="flex flex-1 flex-col gap-5 px-6 pb-10">
        <section className="rounded-3xl bg-primary p-6 text-primary-foreground">
          <p className="text-sm opacity-70">موجودی</p>
          <p className="mt-1 text-3xl font-extrabold">
            {wallet ? formatToman(wallet.balance) : "…"}
          </p>
        </section>

        <section className="flex flex-col gap-4 rounded-3xl bg-card p-5">
          <h2 className="font-semibold">افزایش موجودی</h2>
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={Number(amount) === value}
                onClick={() => setAmount(String(value))}
                className={`h-10 rounded-full px-4 text-sm font-medium ${
                  Number(amount) === value
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary"
                }`}
              >
                {toFa(new Intl.NumberFormat("en-US").format(value))}
              </button>
            ))}
          </div>

          <Field
            label="مبلغ دلخواه (تومان)"
            htmlFor="amount"
            hint={amount ? formatToman(Number(amount)) : undefined}
          >
            <DigitsInput id="amount" value={amount} onChange={setAmount} />
          </Field>

          {error ? (
            <p role="alert" className="px-2 text-sm text-destructive">
              {error}
            </p>
          ) : null}
          {success ? (
            <p role="status" className="px-2 text-sm text-green-400">
              {success}
            </p>
          ) : null}

          <Button
            disabled={loading}
            onClick={handleTopUp}
            className="h-14 rounded-full text-base font-bold"
          >
            {loading ? "در حال پرداخت…" : "پرداخت و شارژ"}
          </Button>
          <p className="text-center text-xs text-muted-foreground">
            این پرداخت از طریق درگاه آزمایشی انجام می‌شود و پول واقعی کم نمی‌شود.
          </p>
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="px-2 font-semibold">تراکنش‌های اخیر</h2>
          {wallet && wallet.transactions.length === 0 ? (
            <p className="px-2 text-sm text-muted-foreground">
              هنوز تراکنشی ثبت نشده است.
            </p>
          ) : null}
          <ul className="flex flex-col gap-2">
            {wallet?.transactions.map((item: WalletTransaction) => (
              <li
                key={item.id}
                className="flex items-center justify-between gap-3 rounded-2xl bg-card px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium">
                    {TRANSACTION_LABEL[item.kind]}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {formatJalaliDateTime(item.created_at)}
                  </p>
                </div>
                <span
                  className={`shrink-0 text-sm font-bold ${
                    item.amount >= 0 ? "text-green-400" : "text-red-400"
                  }`}
                >
                  <bdi dir="ltr">
                    {item.amount >= 0 ? "+" : "−"}
                    {toFa(
                      new Intl.NumberFormat("en-US").format(Math.abs(item.amount)),
                    )}
                  </bdi>
                </span>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </PageShell>
  );
}
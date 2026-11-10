"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { BrandHeader, PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRequireAuth, type User } from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";

export default function OnboardingPage() {
  const router = useRouter();
  const { user, ready, authFetch, updateUser } = useRequireAuth();

  // null means "not edited yet": fall back to the saved value.
  const [firstName, setFirstName] = useState<string | null>(null);
  const [lastName, setLastName] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  const first = (firstName ?? user.first_name).trim();
  const last = (lastName ?? user.last_name).trim();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const updated = await authFetch<User>("/me/", {
        method: "PATCH",
        body: JSON.stringify({ first_name: first, last_name: last }),
      });
      updateUser(updated);
      router.replace("/profile");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageShell>
      <BrandHeader
        title="اطلاعات شما"
        subtitle="نام و نام خانوادگی خود را همان‌طور که در مدارک آمده وارد کنید."
      />

      <main className="flex flex-1 flex-col px-6 py-8">
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <Label htmlFor="first_name">نام</Label>
            <Input
              id="first_name"
              autoComplete="given-name"
              value={firstName ?? user.first_name}
              onChange={(event) => setFirstName(event.target.value)}
              className="h-12 rounded-xl"
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="last_name">نام خانوادگی</Label>
            <Input
              id="last_name"
              autoComplete="family-name"
              value={lastName ?? user.last_name}
              onChange={(event) => setLastName(event.target.value)}
              className="h-12 rounded-xl"
            />
          </div>

          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}

          <Button
            type="submit"
            disabled={loading || !first || !last}
            className="h-12 w-full rounded-xl text-base font-semibold"
          >
            {loading ? "در حال ذخیره…" : "ذخیره و ادامه"}
          </Button>
        </form>
      </main>
    </PageShell>
  );
}
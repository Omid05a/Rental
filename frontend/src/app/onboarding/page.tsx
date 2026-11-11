"use client";

import { User as UserIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { IconInput } from "@/components/icon-input";
import { AuthHeader, PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
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
      <AuthHeader
        title="اطلاعات شما"
        subtitle="نام و نام خانوادگی خود را همان‌طور که در مدارک آمده وارد کنید."
      />

      <main className="flex flex-1 flex-col px-6">
        <form onSubmit={handleSubmit} className="flex flex-1 flex-col gap-5">
          <div className="flex flex-col gap-2">
            <Label htmlFor="first_name" className="px-2">
              نام
            </Label>
            <IconInput
              id="first_name"
              icon={<UserIcon className="size-5" />}
              autoComplete="given-name"
              value={firstName ?? user.first_name}
              onChange={(event) => setFirstName(event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="last_name" className="px-2">
              نام خانوادگی
            </Label>
            <IconInput
              id="last_name"
              icon={<UserIcon className="size-5" />}
              autoComplete="family-name"
              value={lastName ?? user.last_name}
              onChange={(event) => setLastName(event.target.value)}
            />
          </div>

          {error ? (
            <p role="alert" className="px-2 text-sm text-destructive">
              {error}
            </p>
          ) : null}

          <Button
            type="submit"
            disabled={loading || !first || !last}
            className="mt-2 h-14 w-full rounded-full text-base font-bold"
          >
            {loading ? "در حال ذخیره…" : "ذخیره و ادامه"}
          </Button>
        </form>
      </main>
    </PageShell>
  );
}
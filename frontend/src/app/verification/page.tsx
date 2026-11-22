"use client";

import { ArrowRight, Check, ImagePlus, LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useState,
  type ChangeEvent,
  type CSSProperties,
} from "react";

import { PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
import {
  useRequireAuth,
  type User,
  type VerificationStatus,
} from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";

type DocType =
  | "national_card_front"
  | "national_card_back"
  | "driver_license"
  | "selfie";

type DocItem = {
  doc_type: DocType;
  uploaded: boolean;
  uploaded_at: string | null;
};

type DocumentsResponse = {
  status: VerificationStatus;
  rejection_reason: string;
  documents: DocItem[];
};

const DOC_INFO: Record<DocType, { title: string; hint: string }> = {
  national_card_front: {
    title: "کارت ملی (روی کارت)",
    hint: "عکس واضح از روی کارت، بدون انعکاس نور.",
  },
  national_card_back: {
    title: "کارت ملی (پشت کارت)",
    hint: "عکس واضح از پشت کارت.",
  },
  driver_license: {
    title: "گواهینامه",
    hint: "عکس واضح از روی گواهینامه معتبر.",
  },
  selfie: {
    title: "سلفی همراه کارت ملی",
    hint: "صورت و کارت ملی هر دو در تصویر دیده شوند.",
  },
};

const MAX_BYTES = 5 * 1024 * 1024;

// Staggered entrance delay index (see .stagger in globals.css)
function stagger(index: number): CSSProperties {
  return { "--i": index } as CSSProperties;
}

export default function VerificationPage() {
  const router = useRouter();
  const { user, ready, authFetch, updateUser } = useRequireAuth();

  const [data, setData] = useState<DocumentsResponse | null>(null);
  const [busyType, setBusyType] = useState<DocType | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await authFetch<DocumentsResponse>("/verification/documents/"));
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [authFetch]);

  useEffect(() => {
    if (!ready || !user) return;
    let active = true;
    authFetch<DocumentsResponse>("/verification/documents/")
      .then((result) => {
        if (active) setData(result);
      })
      .catch((err) => {
        if (active) setError(getErrorMessage(err));
      });
    return () => {
      active = false;
    };
  }, [ready, user, authFetch]);

  async function handleFile(
    docType: DocType,
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (file.size > MAX_BYTES) {
      setError("حجم فایل باید کمتر از ۵ مگابایت باشد.");
      return;
    }

    setBusyType(docType);
    setError(null);
    try {
      const body = new FormData();
      body.append("file", file);
      await authFetch(`/verification/documents/${docType}/`, {
        method: "PUT",
        body,
      });
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyType(null);
    }
  }

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const updated = await authFetch<User>("/verification/submit/", {
        method: "POST",
      });
      updateUser(updated);
      router.replace("/profile");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (!ready || !user) {
    return <div className="min-h-dvh bg-background" />;
  }

  const editable =
    data?.status === "not_submitted" || data?.status === "rejected";
  const allUploaded = data?.documents.every((doc) => doc.uploaded) ?? false;

  return (
    <PageShell>
      <header className="flex items-center gap-3 px-6 pb-4 pt-12">
        <button
          type="button"
          onClick={() => router.push("/profile")}
          aria-label="بازگشت"
          className="press flex size-10 items-center justify-center rounded-full bg-card hover:bg-accent"
        >
          <ArrowRight className="size-5" />
        </button>
        <h1 className="text-xl font-bold">ارسال مدارک</h1>
      </header>

      <main className="flex flex-1 flex-col gap-4 px-6 pb-10">
        <p className="animate-fade-up text-sm leading-relaxed text-muted-foreground">
          برای اجاره یا ثبت وسیله، هویت شما باید تأیید شود. تصاویر باید واضح و
          خوانا باشند (JPG، PNG یا WebP، حداکثر ۵ مگابایت).
        </p>

        {data?.status === "rejected" && data.rejection_reason ? (
          <p className="animate-scale-in rounded-2xl bg-red-500/10 p-3 text-sm text-red-400">
            دلیل رد مدارک: {data.rejection_reason}
          </p>
        ) : null}

        {data && !editable ? (
          <p className="animate-fade-in rounded-2xl bg-card p-3 text-sm text-muted-foreground">
            مدارک شما در حال بررسی است یا تأیید شده و قابل تغییر نیست.
          </p>
        ) : null}

        {!data && !error ? (
          <ul className="flex flex-col gap-3" aria-hidden="true">
            {[0, 1, 2, 3].map((n) => (
              <li key={n} className="skeleton h-24 rounded-3xl" />
            ))}
          </ul>
        ) : null}

        <ul className="flex flex-col gap-3">
          {data?.documents.map((doc, index) => {
            const info = DOC_INFO[doc.doc_type];
            const busy = busyType === doc.doc_type;
            return (
              <li
                key={doc.doc_type}
                className="stagger flex items-center gap-4 rounded-3xl bg-card p-4"
                style={stagger(index)}
              >
                <div
                  className={`flex size-11 shrink-0 items-center justify-center rounded-full transition-colors duration-300 ${
                    doc.uploaded
                      ? "bg-green-500/15 text-green-400"
                      : "bg-white/10 text-white/60"
                  }`}
                >
                  {doc.uploaded ? (
                    <Check key="done" className="animate-scale-in size-5" />
                  ) : (
                    <ImagePlus key="todo" className="size-5" />
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <h2 className="font-semibold">{info.title}</h2>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                    {info.hint}
                  </p>
                </div>

                {editable ? (
                  <label
                    className={`press inline-flex h-10 shrink-0 cursor-pointer items-center gap-1.5 rounded-full bg-secondary px-4 text-sm font-medium hover:bg-accent ${
                      busy || submitting ? "pointer-events-none opacity-50" : ""
                    }`}
                  >
                    {busy ? (
                      <LoaderCircle className="size-4 animate-spin" />
                    ) : null}
                    {busy ? "در حال ارسال…" : doc.uploaded ? "تغییر" : "انتخاب"}
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      className="sr-only"
                      disabled={busy || submitting}
                      onChange={(event) => handleFile(doc.doc_type, event)}
                    />
                  </label>
                ) : null}
              </li>
            );
          })}
        </ul>

        {error ? (
          <p
            role="alert"
            className="animate-fade-up px-2 text-sm text-destructive"
          >
            {error}
          </p>
        ) : null}

        {editable ? (
          <div className="animate-fade-up mt-auto flex flex-col gap-3 pt-4">
            <Button
              disabled={!allUploaded || submitting || busyType !== null}
              onClick={handleSubmit}
              className="h-14 w-full rounded-full text-base font-bold"
            >
              {submitting ? <LoaderCircle className="animate-spin" /> : null}
              {submitting ? "در حال ارسال…" : "ارسال برای بررسی"}
            </Button>
            <p className="text-center text-xs text-muted-foreground">
              پس از ارسال، مدارک شما توسط تیم رنتال بررسی می‌شود.
            </p>
          </div>
        ) : null}
      </main>
    </PageShell>
  );
}
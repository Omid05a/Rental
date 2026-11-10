import { ApiError } from "@/lib/api";

const MESSAGES: Record<string, string> = {
  too_many_requests: "لطفاً کمی صبر کنید و دوباره تلاش کنید.",
  invalid_code: "کد واردشده نادرست است یا منقضی شده.",
  too_many_attempts: "تعداد تلاش‌ها زیاد است. کد جدید دریافت کنید.",
};

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const data = error.data;
    if (data && typeof data === "object") {
      const { code } = data as { code?: string };
      if (code && MESSAGES[code]) {
        return MESSAGES[code];
      }
      if ("phone" in data) {
        return "شماره موبایل معتبر نیست. نمونه: ۰۹۱۲۳۴۵۶۷۸۹";
      }
    }
    return "مشکلی پیش آمد. دوباره تلاش کنید.";
  }
  return "ارتباط با سرور برقرار نشد. اتصال را بررسی کنید.";
}
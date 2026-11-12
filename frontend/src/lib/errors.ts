import { ApiError } from "@/lib/api";

const MESSAGES: Record<string, string> = {
  too_many_requests: "لطفاً کمی صبر کنید و دوباره تلاش کنید.",
  invalid_code: "کد واردشده نادرست است یا منقضی شده.",
  too_many_attempts: "تعداد تلاش‌ها زیاد است. کد جدید دریافت کنید.",
  locked: "مدارک شما در حال بررسی یا تأییدشده است و قابل تغییر نیست.",
  missing_documents: "ابتدا همه مدارک را ارسال کنید.",
  profile_incomplete: "ابتدا نام و نام خانوادگی خود را در پروفایل وارد کنید.",
  not_verified: "برای این کار ابتدا باید هویت شما تأیید شود.",
  too_many_photos: "حداکثر ۶ عکس برای هر وسیله مجاز است.",
  slot_taken: "این بازه زمانی قبلاً رزرو شده است. زمان دیگری انتخاب کنید.",
  start_in_past: "زمان شروع گذشته است.",
  too_far_ahead: "حداکثر تا ۹۰ روز آینده قابل رزرو است.",
  invalid_period: "مدت اجاره معتبر نیست.",
  duration_too_short: "حداقل مدت اجاره یک ساعت است.",
  duration_too_long: "حداکثر مدت اجاره ۱۴ روز است.",
  own_vehicle: "نمی‌توانید وسیله خودتان را اجاره کنید.",
  insurance_expired: "بیمه این وسیله قبل از پایان اجاره منقضی می‌شود.",
  insufficient_funds: "موجودی کیف پول کافی نیست.",
  terms_outdated: "قوانین تغییر کرده است. صفحه را دوباره باز کنید.",
  vehicle_not_found: "این وسیله دیگر در دسترس نیست.",
  not_cancellable: "این رزرو قابل لغو نیست.",
  already_started: "زمان اجاره شروع شده و قابل لغو نیست.",
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
      if ("file" in data || "image" in data) {
        return "فایل باید تصویر JPG، PNG یا WebP و کمتر از ۵ مگابایت باشد.";
      }
      if ("amount" in data) {
        return "مبلغ باید بین ۱۰ هزار تا ۱۰۰ میلیون تومان باشد.";
      }
    }
    return "مشکلی پیش آمد. دوباره تلاش کنید.";
  }
  return "ارتباط با سرور برقرار نشد. اتصال را بررسی کنید.";
}
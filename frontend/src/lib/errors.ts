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
  too_early: "هنوز زمان شروع این سفر نرسیده است.",
  too_late: "زمان این رزرو به پایان رسیده است.",
  not_startable: "این رزرو قابل شروع نیست.",
  not_active: "سفر در حال انجام نیست.",
  inspection_incomplete: "ابتدا از همه زاویه‌ها عکس بگیرید.",
  invalid_qr: "کد QR با این وسیله مطابقت ندارد.",
  too_far: "شما از وسیله دور هستید. نزدیک وسیله بروید و دوباره تلاش کنید.",
  outside_return_area: "برای پایان سفر، وسیله را به محل تحویل برگردانید.",
  fuel_required: "سطح بنزین یا شارژ را وارد کنید.",
  vehicle_in_use: "وسیله هنوز توسط اجاره‌کننده قبلی برگردانده نشده است.",
  extension_blocked: "بعد از رزرو شما، رزرو دیگری ثبت شده و تمدید ممکن نیست.",
  extension_too_short: "این مقدار تمدید برای جبران زمان گذشته کافی نیست.",
  forbidden: "شما اجازه این کار را ندارید.",
  invalid_angle: "این زاویه برای این وسیله مجاز نیست.",
  report_closed: "مهلت گزارش خسارت تمام شده است.",
  already_reported: "برای این رزرو قبلاً گزارش ثبت شده است.",
  no_open_report: "گزارش بازی وجود ندارد.",
  no_deposit_left: "سپرده‌ای برای مطالبه باقی نمانده است.",
  claim_too_high: "مبلغ مطالبه بیشتر از سپرده باقی‌مانده است.",
};

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const data = error.data;
    if (data && typeof data === "object") {
      const { code, distance_m: distance } = data as {
        code?: string;
        distance_m?: number;
      };
      if (code && MESSAGES[code]) {
        const showDistance =
          (code === "too_far" || code === "outside_return_area") &&
          typeof distance === "number";
        const extra = showDistance
          ? ` (حدود ${new Intl.NumberFormat("fa-IR").format(Math.round(distance))} متر فاصله)`
          : "";
        return MESSAGES[code] + extra;
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
      if ("fuel_percent" in data) {
        return "سطح بنزین یا شارژ باید عددی بین ۰ تا ۱۰۰ باشد.";
      }
    }
    return "مشکلی پیش آمد. دوباره تلاش کنید.";
  }
  return "ارتباط با سرور برقرار نشد. اتصال را بررسی کنید.";
}
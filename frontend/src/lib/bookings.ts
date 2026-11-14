import type { VehicleKind } from "@/lib/vehicles";

export type BookingStatus = "confirmed" | "active" | "completed" | "cancelled";

export type Angle = "front" | "rear" | "left" | "right" | "dashboard";

export type TripPhoto = {
  angle: Angle | "damage";
  image: string;
  taken_at: string;
};

export type TripInfo = {
  required_angles: Angle[];
  start_photos: TripPhoto[];
  end_photos: TripPhoto[];
  start_photos_done: boolean;
  end_photos_done: boolean;
  start_window_opens_at: string;
  can_start: boolean;
  can_extend: boolean;
  can_end: boolean;
  late_fee_now: number;
  fuel_fee_now: number;
  needs_fuel: boolean;
  can_report_damage: boolean;
};

export type DamageInfo = {
  description: string;
  claimed_amount: number;
  renter_response: string;
  status: "open" | "resolved";
  approved_amount: number;
  resolution_note: string;
  created_at: string;
  photos: TripPhoto[];
};

export type Booking = {
  id: number;
  status: BookingStatus;
  role: "renter" | "owner";
  vehicle: {
    id: number;
    kind: VehicleKind;
    title: string;
    brand: string;
    model_name: string;
    address: string;
    latitude: number;
    longitude: number;
    pickup_radius_m: number;
    cover: string | null;
  };
  counterpart: { first_name: string; phone: string };
  start_at: string;
  end_at: string;
  hours: number;
  price_per_hour: number;
  price_per_day: number;
  rental_amount: number;
  deposit_amount: number;
  total_paid: number;
  can_cancel: boolean;
  cancel_fee_now: number;
  cancelled_at: string | null;
  cancelled_by: string;
  cancel_reason: string;
  cancellation_fee: number;
  refund_amount: number;
  started_at: string | null;
  ended_at: string | null;
  start_fuel_percent: number | null;
  end_fuel_percent: number | null;
  late_minutes: number;
  late_fee: number;
  fuel_fee: number;
  damage_deduction: number;
  deposit_status: "none" | "held" | "released";
  deposit_release_at: string | null;
  trip: TripInfo;
  damage: DamageInfo | null;
  created_at: string;
};

export type Quote = {
  hours: number;
  rental_amount: number;
  deposit_amount: number;
  total: number;
  price_per_hour: number;
  price_per_day: number;
  wallet_balance: number;
  enough_funds: boolean;
  free_cancellation_until: string;
  terms_version: string;
};

export type Terms = {
  version: string;
  sections: { title: string; text: string }[];
};

export type BusyRange = { start: string; end: string };

export type WalletTransaction = {
  id: number;
  kind: "topup" | "booking_charge" | "deposit_hold" | "refund" | "payout";
  amount: number;
  balance_after: number;
  reference: string;
  created_at: string;
};

export type WalletData = {
  balance: number;
  transactions: WalletTransaction[];
};

export const BOOKING_STATUS: Record<
  BookingStatus,
  { label: string; className: string }
> = {
  confirmed: { label: "تأییدشده", className: "bg-primary/15 text-primary" },
  active: { label: "در حال انجام", className: "bg-blue-500/15 text-blue-400" },
  completed: {
    label: "پایان‌یافته",
    className: "bg-green-500/15 text-green-400",
  },
  cancelled: { label: "لغوشده", className: "bg-red-500/15 text-red-400" },
};

export const TRANSACTION_LABEL: Record<WalletTransaction["kind"], string> = {
  topup: "شارژ کیف پول",
  booking_charge: "هزینه اجاره",
  deposit_hold: "سپرده",
  refund: "بازپرداخت",
  payout: "دریافتی",
};

export const ANGLE_LABEL: Record<Angle | "damage", string> = {
  front: "جلو",
  rear: "عقب",
  left: "سمت چپ",
  right: "سمت راست",
  dashboard: "داشبورد",
  damage: "خسارت",
};

export const DEPOSIT_STATUS: Record<Booking["deposit_status"], string> = {
  none: "بدون سپرده",
  held: "نگه‌داری‌شده",
  released: "بازگردانده‌شده",
};
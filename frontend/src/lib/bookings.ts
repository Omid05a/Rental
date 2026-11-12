import type { VehicleKind } from "@/lib/vehicles";

export type BookingStatus = "confirmed" | "active" | "completed" | "cancelled";

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
  payout: "دریافتی از لغو رزرو",
};
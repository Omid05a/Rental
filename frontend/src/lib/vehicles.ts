export type VehicleKind = "car" | "bike";
export type ApprovalStatus = "pending" | "approved" | "rejected";
export type Transmission = "automatic" | "manual";
export type FuelType = "gasoline" | "diesel" | "hybrid" | "electric";

export type VehiclePhoto = {
  id: number;
  image: string;
  position: number;
};

export type Vehicle = {
  id: number;
  kind: VehicleKind;
  title: string;
  brand: string;
  model_name: string;
  year: number | null;
  description: string;
  transmission: Transmission | "";
  fuel_type: FuelType | "";
  seats: number | null;
  insurance_expiry: string | null;
  price_per_hour: number;
  price_per_day: number;
  deposit: number;
  daily_km_limit: number | null;
  min_fuel_percent: number | null;
  latitude: number;
  longitude: number;
  address: string;
  pickup_radius_m: number;
  is_active: boolean;
  approval_status: ApprovalStatus;
  rejection_reason: string;
  photos: VehiclePhoto[];
  owner_first_name: string;
  distance_m: number | null;
};

export const KIND_LABEL: Record<VehicleKind, string> = {
  car: "خودرو",
  bike: "دوچرخه",
};

export const TRANSMISSION_LABEL: Record<Transmission, string> = {
  automatic: "اتوماتیک",
  manual: "دنده‌ای",
};

export const FUEL_LABEL: Record<FuelType, string> = {
  gasoline: "بنزین",
  diesel: "گازوییل",
  hybrid: "هیبرید",
  electric: "برقی",
};

export const APPROVAL: Record<
  ApprovalStatus,
  { label: string; hint: string; className: string }
> = {
  pending: {
    label: "در انتظار تأیید",
    hint: "وسیله شما در حال بررسی است. بعد از تأیید در جستجو نمایش داده می‌شود.",
    className: "bg-primary/15 text-primary",
  },
  approved: {
    label: "تأییدشده",
    hint: "وسیله شما در جستجو نمایش داده می‌شود.",
    className: "bg-green-500/15 text-green-400",
  },
  rejected: {
    label: "ردشده",
    hint: "وسیله تأیید نشد. دلیل را ببینید و وسیله جدیدی ثبت کنید.",
    className: "bg-red-500/15 text-red-400",
  },
};
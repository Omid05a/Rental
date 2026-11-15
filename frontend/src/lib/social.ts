export type NotificationKind =
  | "verification"
  | "vehicle"
  | "booking"
  | "trip"
  | "payment"
  | "damage"
  | "review"
  | "reminder";

export type AppNotification = {
  id: number;
  kind: NotificationKind;
  title: string;
  body: string;
  link: string;
  is_read: boolean;
  created_at: string;
};

export type NotificationList = {
  unread_count: number;
  results: AppNotification[];
};

export type RatingSummary = { avg: number | null; count: number };

export type ReviewItem = {
  id: number;
  rating: number;
  comment: string;
  created_at: string;
};

export type ReviewState = {
  role: "renter" | "owner";
  can_review: boolean;
  closed: boolean;
  deadline: string | null;
  counterpart_name: string;
  counterpart_rating: RatingSummary;
  mine: ReviewItem | null;
  theirs: ReviewItem | null;
};

export type VehicleReviews = RatingSummary & {
  results: {
    id: number;
    rating: number;
    comment: string;
    author_first_name: string;
    created_at: string;
  }[];
};

export type EarningsItem = {
  booking_id: number;
  vehicle_id: number;
  vehicle_title: string;
  kind: "trip" | "cancellation";
  date: string;
  gross: number;
  fee: number;
  net: number;
};

export type Earnings = {
  total_gross: number;
  total_fees: number;
  total_net: number;
  trips: number;
  cancellations: number;
  pending_gross: number;
  by_vehicle: {
    vehicle_id: number;
    title: string;
    trips: number;
    net: number;
  }[];
  items: EarningsItem[];
};
import { Suspense } from "react";

import BookingDetail from "./booking-detail";

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-background" />}>
      <BookingDetail />
    </Suspense>
  );
}
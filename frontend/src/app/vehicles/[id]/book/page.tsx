import { Suspense } from "react";

import BookingFlow from "./booking-flow";

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-background" />}>
      <BookingFlow />
    </Suspense>
  );
}
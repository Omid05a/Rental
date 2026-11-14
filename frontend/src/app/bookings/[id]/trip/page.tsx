import { Suspense } from "react";

import TripFlow from "./trip-flow";

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-background" />}>
      <TripFlow />
    </Suspense>
  );
}
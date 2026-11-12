import { Suspense } from "react";

import VehicleDetail from "./vehicle-detail";

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-background" />}>
      <VehicleDetail />
    </Suspense>
  );
}
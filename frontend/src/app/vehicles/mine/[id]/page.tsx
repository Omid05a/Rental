import { Suspense } from "react";

import ManageVehiclePage from "./manage-vehicle";

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-background" />}>
      <ManageVehiclePage />
    </Suspense>
  );
}
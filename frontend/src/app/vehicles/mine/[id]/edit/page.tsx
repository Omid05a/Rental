import { Suspense } from "react";

import EditVehicle from "./edit-vehicle";

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-background" />}>
      <EditVehicle />
    </Suspense>
  );
}
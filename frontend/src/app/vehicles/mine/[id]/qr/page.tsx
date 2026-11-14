import { Suspense } from "react";

import QrSheet from "./qr-sheet";

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-background" />}>
      <QrSheet />
    </Suspense>
  );
}
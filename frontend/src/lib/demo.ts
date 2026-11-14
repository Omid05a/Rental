// Demo helpers (simulated location and QR code) are shown while developing
// and in a demo deployment built with NEXT_PUBLIC_DEMO_MODE=1.
export const DEMO_MODE =
  process.env.NODE_ENV !== "production" ||
  process.env.NEXT_PUBLIC_DEMO_MODE === "1";
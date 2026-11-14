export type Position = { latitude: number; longitude: number };

const POSITION_ERRORS = ["unsupported", "denied", "unavailable"];

export function getPosition(timeout = 10000): Promise<Position> {
  return new Promise((resolve, reject) => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      reject(new Error("unsupported"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (result) =>
        resolve({
          latitude: result.coords.latitude,
          longitude: result.coords.longitude,
        }),
      (failure) => reject(new Error(failure.code === 1 ? "denied" : "unavailable")),
      { enableHighAccuracy: true, timeout, maximumAge: 5000 },
    );
  });
}

export function isPositionError(error: unknown): boolean {
  return error instanceof Error && POSITION_ERRORS.includes(error.message);
}

export function positionErrorMessage(error: unknown): string {
  const reason = error instanceof Error ? error.message : "";
  if (reason === "denied") {
    return "اجازه دسترسی به موقعیت داده نشد. آن را در تنظیمات مرورگر فعال کنید.";
  }
  if (reason === "unsupported") {
    return "مرورگر شما از موقعیت‌یابی پشتیبانی نمی‌کند.";
  }
  return "موقعیت شما پیدا نشد. GPS را روشن کنید و دوباره تلاش کنید.";
}
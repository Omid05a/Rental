export function makeKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/**
 * Keeps the same idempotency key while the request content (fingerprint)
 * stays the same, so a retry after a network error never pays twice.
 */
export function createAttemptKeys() {
  let current: { fingerprint: string; key: string } | null = null;
  return {
    get(fingerprint: string) {
      if (!current || current.fingerprint !== fingerprint) {
        current = { fingerprint, key: makeKey() };
      }
      return current.key;
    },
    reset() {
      current = null;
    },
  };
}
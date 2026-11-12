def get_idempotency_key(request):
    """Reads the optional Idempotency-Key header (max 64 characters)."""
    key = request.headers.get("Idempotency-Key", "").strip()
    return key[:64] or None
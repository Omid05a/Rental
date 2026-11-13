import hashlib
import hmac
import math

from django.conf import settings

# Photos the renter must take at the start and at the end of a trip.
REQUIRED_ANGLES = {
    "car": ["front", "rear", "left", "right", "dashboard"],
    "bike": ["left", "right"],
}


def required_angles(vehicle_kind):
    return REQUIRED_ANGLES[vehicle_kind]


def qr_code_for_vehicle(vehicle_id):
    """The code printed on a vehicle. It is signed, so it cannot be guessed."""
    digest = hmac.new(
        settings.SECRET_KEY.encode(),
        f"vehicle:{vehicle_id}".encode(),
        hashlib.sha256,
    ).hexdigest()[:10]
    return f"RENTAL-{vehicle_id}-{digest}"


def qr_matches(vehicle_id, code):
    return hmac.compare_digest(
        qr_code_for_vehicle(vehicle_id), (code or "").strip()
    )


def distance_m(lat1, lng1, lat2, lng2):
    """Great-circle distance in meters (haversine formula)."""
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))
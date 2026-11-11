from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from apps.users.models import User


class IsVerifiedUser(BasePermission):
    """Allows only logged-in users whose identity documents were approved."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.verification_status != User.VerificationStatus.APPROVED:
            raise PermissionDenied(
                {
                    "detail": "Identity verification is required.",
                    "code": "not_verified",
                }
            )
        return True
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.reminders import generate_due_reminders

from .models import Notification
from .serializers import MarkReadSerializer, NotificationSerializer
from .services import mark_read, unread_count


class NotificationListView(APIView):
    """Latest notifications. Query: unread=1, limit (default 30, max 100)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: None})
    def get(self, request):
        generate_due_reminders(request.user)

        queryset = Notification.objects.filter(user=request.user)
        if request.query_params.get("unread") == "1":
            queryset = queryset.filter(read_at__isnull=True)

        try:
            limit = int(request.query_params.get("limit", 30))
        except ValueError:
            limit = 30
        limit = min(100, max(1, limit))

        return Response(
            {
                "unread_count": unread_count(request.user),
                "results": NotificationSerializer(queryset[:limit], many=True).data,
            }
        )


class UnreadCountView(APIView):
    """Cheap endpoint the app polls. It also creates due reminders."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: None})
    def get(self, request):
        generate_due_reminders(request.user)
        return Response({"count": unread_count(request.user)})


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=MarkReadSerializer, responses={200: None})
    def post(self, request):
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ids = None if data.get("all") else data.get("ids", [])
        updated = mark_read(request.user, ids)
        return Response({"updated": updated, "unread_count": unread_count(request.user)})
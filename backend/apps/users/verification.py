from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, VerificationDocument
from .serializers import DocumentUploadSerializer, ProfileSerializer

LOCKED_STATUSES = (
    User.VerificationStatus.PENDING,
    User.VerificationStatus.APPROVED,
)


def locked_response():
    return Response(
        {
            "detail": "Documents can no longer be changed.",
            "code": "locked",
        },
        status=status.HTTP_409_CONFLICT,
    )


class DocumentListView(APIView):
    """Shows which documents the current user has uploaded."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        uploaded = {doc.doc_type: doc.uploaded_at for doc in user.documents.all()}
        return Response(
            {
                "status": user.verification_status,
                "rejection_reason": user.rejection_reason,
                "documents": [
                    {
                        "doc_type": doc_type,
                        "uploaded": doc_type in uploaded,
                        "uploaded_at": uploaded.get(doc_type),
                    }
                    for doc_type in VerificationDocument.DocType.values
                ],
            }
        )


class DocumentUploadView(APIView):
    """Uploads or replaces one document of the current user."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    @extend_schema(request=DocumentUploadSerializer, responses={200: None})
    def put(self, request, doc_type):
        if doc_type not in VerificationDocument.DocType.values:
            raise NotFound("Unknown document type.")

        user = request.user
        if user.verification_status in LOCKED_STATUSES:
            return locked_response()

        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data["file"]

        with transaction.atomic():
            existing = VerificationDocument.objects.filter(
                user=user, doc_type=doc_type
            ).first()
            if existing:
                existing.file.delete(save=False)
                existing.file = file
                existing.uploaded_at = timezone.now()
                existing.save()
            else:
                VerificationDocument.objects.create(
                    user=user, doc_type=doc_type, file=file
                )

        return Response({"doc_type": doc_type, "uploaded": True})


class SubmitVerificationView(APIView):
    """Sends the uploaded documents for review."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: ProfileSerializer})
    def post(self, request):
        user = request.user
        if user.verification_status in LOCKED_STATUSES:
            return locked_response()

        if not (user.first_name and user.last_name):
            return Response(
                {"detail": "Complete your profile first.", "code": "profile_incomplete"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded = set(user.documents.values_list("doc_type", flat=True))
        missing = [
            doc_type
            for doc_type in VerificationDocument.DocType.values
            if doc_type not in uploaded
        ]
        if missing:
            return Response(
                {
                    "detail": "Some documents are missing.",
                    "code": "missing_documents",
                    "missing": missing,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.verification_status = User.VerificationStatus.PENDING
        user.rejection_reason = ""
        user.save(update_fields=["verification_status", "rejection_reason"])
        return Response(ProfileSerializer(user).data)
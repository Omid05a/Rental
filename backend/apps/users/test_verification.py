import io
import tempfile
from unittest.mock import patch

from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, VerificationDocument

DOC_TYPES = VerificationDocument.DocType.values


def make_image(name="doc.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class VerificationTests(APITestCase):
    def setUp(self):
        # Write uploaded files to a temporary folder, not to private_media.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        field = VerificationDocument._meta.get_field("file")
        original = field.storage
        field.storage = FileSystemStorage(location=tmp.name)
        self.addCleanup(setattr, field, "storage", original)

        self.user = User.objects.create_user(
            phone="09120000000", first_name="Ali", last_name="Rezaei"
        )
        token = RefreshToken.for_user(self.user).access_token
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def upload(self, doc_type, file=None):
        return self.client.put(
            f"/api/verification/documents/{doc_type}/",
            {"file": file or make_image()},
            format="multipart",
            **self.auth,
        )

    def upload_all(self):
        for doc_type in DOC_TYPES:
            self.upload(doc_type)

    def submit(self):
        return self.client.post("/api/verification/submit/", **self.auth)

    def test_documents_require_authentication(self):
        response = self.client.get("/api/verification/documents/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_creates_document_and_list_shows_it(self):
        response = self.upload("driver_license")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        listing = self.client.get("/api/verification/documents/", **self.auth)
        uploaded = {d["doc_type"]: d["uploaded"] for d in listing.data["documents"]}
        self.assertTrue(uploaded["driver_license"])
        self.assertFalse(uploaded["selfie"])

    def test_non_image_is_rejected(self):
        fake = SimpleUploadedFile("x.png", b"not an image", content_type="image/png")
        response = self.upload("selfie", fake)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    @patch("apps.users.serializers.MAX_UPLOAD_BYTES", 10)
    def test_large_file_is_rejected(self):
        response = self.upload("selfie")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_document_type_returns_404(self):
        response = self.upload("passport")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reupload_replaces_document(self):
        self.upload("selfie")
        self.upload("selfie")
        self.assertEqual(
            VerificationDocument.objects.filter(
                user=self.user, doc_type="selfie"
            ).count(),
            1,
        )

    def test_submit_requires_all_documents(self):
        self.upload("selfie")
        response = self.submit()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "missing_documents")

    def test_submit_requires_complete_profile(self):
        self.user.first_name = ""
        self.user.save()
        self.upload_all()
        response = self.submit()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "profile_incomplete")

    def test_submit_sets_pending_and_locks_uploads(self):
        self.upload_all()
        response = self.submit()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["verification_status"], "pending")

        again = self.upload("selfie")
        self.assertEqual(again.status_code, status.HTTP_409_CONFLICT)

    def test_rejected_user_can_resubmit(self):
        self.user.verification_status = User.VerificationStatus.REJECTED
        self.user.rejection_reason = "Blurry photo"
        self.user.save()

        self.upload_all()
        response = self.submit()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["verification_status"], "pending")
        self.assertEqual(response.data["rejection_reason"], "")
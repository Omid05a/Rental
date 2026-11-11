import io
import tempfile

from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .admin import UserAdminForm
from .models import User, VerificationDocument

DOC_TYPES = VerificationDocument.DocType.values


def png_file():
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buffer, format="PNG")
    return SimpleUploadedFile("doc.png", buffer.getvalue(), content_type="image/png")


class AdminReviewTests(TestCase):
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
        self.staff = User.objects.create_user(
            phone="09130000000", is_staff=True, is_superuser=True
        )

    def add_documents(self, doc_types=DOC_TYPES):
        documents = []
        for doc_type in doc_types:
            documents.append(
                VerificationDocument.objects.create(
                    user=self.user, doc_type=doc_type, file=png_file()
                )
            )
        return documents

    def file_url(self, document):
        return reverse("admin-document-file", args=[document.pk])

    def test_anonymous_cannot_view_document(self):
        document = self.add_documents(["selfie"])[0]
        response = self.client.get(self.file_url(document))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_regular_user_cannot_view_document(self):
        document = self.add_documents(["selfie"])[0]
        self.client.force_login(self.user)
        response = self.client.get(self.file_url(document))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_view_document(self):
        document = self.add_documents(["selfie"])[0]
        self.client.force_login(self.staff)
        response = self.client.get(self.file_url(document))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertTrue(b"".join(response.streaming_content))

    def test_rejection_requires_reason(self):
        form = UserAdminForm(
            data={"verification_status": "rejected", "rejection_reason": ""},
            instance=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("rejection_reason", form.errors)

    def test_approval_requires_all_documents(self):
        self.add_documents(["selfie"])
        form = UserAdminForm(
            data={"verification_status": "approved", "rejection_reason": ""},
            instance=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("verification_status", form.errors)

    def test_approval_with_all_documents_clears_reason(self):
        self.add_documents()
        form = UserAdminForm(
            data={"verification_status": "approved", "rejection_reason": "old"},
            instance=self.user,
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["rejection_reason"], "")
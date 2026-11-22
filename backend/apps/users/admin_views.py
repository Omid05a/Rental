import mimetypes

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache

from .models import VerificationDocument


@staff_member_required
@never_cache
def document_file(request, pk):
    """Serves a private verification document to staff who may view it."""
    if not request.user.has_perm("users.view_verificationdocument"):
        raise PermissionDenied

    document = get_object_or_404(VerificationDocument, pk=pk)
    try:
        handle = document.file.open("rb")
    except FileNotFoundError:
        raise Http404("File not found")

    content_type = (
        mimetypes.guess_type(document.file.name)[0] or "application/octet-stream"
    )
    response = FileResponse(handle, content_type=content_type)
    response["X-Content-Type-Options"] = "nosniff"
    return response
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.users.admin_views import document_file


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    # Must come before the admin include, otherwise the admin catch-all handles it.
    path("admin/documents/<int:pk>/file/", document_file, name="admin-document-file"),
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/", include("apps.users.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
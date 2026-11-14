from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Review


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ("id", "booking", "author", "subject", "direction", "rating", "created_at")
    list_filter = ("direction", "rating")
    search_fields = ("author__phone", "subject__phone", "comment")
    ordering = ("-created_at",)

    # Reviews are written through the API; staff can only remove abusive ones.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("phone", "first_name", "last_name", "verification_status", "is_staff")
    list_filter = ("verification_status", "is_staff")
    search_fields = ("phone", "first_name", "last_name")
    exclude = ("password",)
    readonly_fields = ("last_login", "date_joined")
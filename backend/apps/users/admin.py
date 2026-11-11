from django import forms
from django.contrib import admin, messages
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.models import Group
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from .models import User, VerificationDocument

DOC_COUNT = len(VerificationDocument.DocType.values)

# Groups are not used in this project.
try:
    admin.site.unregister(Group)
except NotRegistered:
    pass


class UserAdminForm(forms.ModelForm):
    """Validates verification decisions made by staff."""

    class Meta:
        model = User
        fields = ("verification_status", "rejection_reason")

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("verification_status")
        reason = (cleaned.get("rejection_reason") or "").strip()

        if status == User.VerificationStatus.REJECTED and not reason:
            self.add_error(
                "rejection_reason", "Enter a reason when rejecting documents."
            )

        if status == User.VerificationStatus.APPROVED:
            uploaded = self.instance.documents.count() if self.instance.pk else 0
            if uploaded < DOC_COUNT:
                self.add_error(
                    "verification_status",
                    "Cannot approve: some documents are missing.",
                )

        # A reason only makes sense for rejected users.
        cleaned["rejection_reason"] = (
            reason if status == User.VerificationStatus.REJECTED else ""
        )
        return cleaned


class VerificationDocumentInline(TabularInline):
    model = VerificationDocument
    extra = 0
    can_delete = False
    fields = ("doc_type", "preview", "uploaded_at")
    readonly_fields = ("doc_type", "preview", "uploaded_at")

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Preview")
    def preview(self, obj):
        if not obj.pk:
            return "-"
        url = reverse("admin-document-file", args=[obj.pk])
        return format_html(
            '<a href="{0}" target="_blank" rel="noopener">'
            '<img src="{0}" alt="" style="max-height:140px;border-radius:8px">'
            "</a>",
            url,
        )


@admin.register(User)
class UserAdmin(ModelAdmin):
    form = UserAdminForm
    list_display = (
        "phone",
        "full_name",
        "status_badge",
        "documents_count",
        "date_joined",
    )
    list_filter = ("verification_status", "is_staff")
    search_fields = ("phone", "first_name", "last_name")
    ordering = ("-date_joined",)
    list_per_page = 25
    inlines = [VerificationDocumentInline]
    actions = ["approve_selected"]
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        ("Identity", {"fields": ("phone", "first_name", "last_name")}),
        ("Verification", {"fields": ("verification_status", "rejection_reason")}),
        ("Access", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )

    def has_add_permission(self, request):
        # Users are created by logging in with a phone number.
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(doc_count=Count("documents"))

    @display(description="Name")
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or "-"

    @display(
        description="Status",
        ordering="verification_status",
        label={
            "Approved": "success",
            "Pending review": "warning",
            "Rejected": "danger",
            "Not submitted": "info",
        },
    )
    def status_badge(self, obj):
        return obj.get_verification_status_display()

    @display(description="Documents", ordering="doc_count")
    def documents_count(self, obj):
        return f"{obj.doc_count}/{DOC_COUNT}"

    @action(description="Approve selected users")
    def approve_selected(self, request, queryset):
        approved = 0
        for user in queryset:
            if user.documents.count() >= DOC_COUNT:
                user.verification_status = User.VerificationStatus.APPROVED
                user.rejection_reason = ""
                user.save(update_fields=["verification_status", "rejection_reason"])
                approved += 1

        skipped = queryset.count() - approved
        if approved:
            self.message_user(
                request, f"{approved} user(s) approved.", messages.SUCCESS
            )
        if skipped:
            self.message_user(
                request,
                f"{skipped} user(s) skipped because documents are missing.",
                messages.WARNING,
            )
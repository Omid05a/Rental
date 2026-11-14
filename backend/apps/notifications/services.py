from django.utils import timezone

from .models import Notification

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(value):
    """Writes a number with Persian digits."""
    return str(value).translate(_FA_DIGITS)


def toman(amount):
    grouped = format(int(amount), ",").replace(",", "٬")
    return f"{fa(grouped)} تومان"


def notify(user, kind, title, body="", link="", dedupe_key=None):
    """Creates a notification. Returns it, or None when this event was already
    notified (same dedupe key)."""
    if dedupe_key:
        notification, created = Notification.objects.get_or_create(
            user=user,
            dedupe_key=dedupe_key,
            defaults={"kind": kind, "title": title, "body": body, "link": link},
        )
        return notification if created else None
    return Notification.objects.create(
        user=user, kind=kind, title=title, body=body, link=link
    )


def unread_count(user):
    return Notification.objects.filter(user=user, read_at__isnull=True).count()


def mark_read(user, ids=None):
    """Marks the given notifications (or all of them when ids is None) as read."""
    queryset = Notification.objects.filter(user=user, read_at__isnull=True)
    if ids is not None:
        queryset = queryset.filter(pk__in=ids)
    return queryset.update(read_at=timezone.now())
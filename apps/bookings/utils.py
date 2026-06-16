# apps/bookings/utils.py
from datetime import timezone as dt_timezone

from django.utils import timezone


def escape_ics_text(value):
    """Escape text according to iCalendar text value rules."""
    if value is None:
        return ""

    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def format_ics_datetime(value):
    """Return UTC datetime in compact iCalendar format."""
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())

    return value.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_bookings_ics(bookings, calendar_name="SmartMeeting bookings"):
    """Build a valid .ics calendar from booking queryset/list."""
    now = timezone.now()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SmartMeeting//Bookings Calendar//RU",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics_text(calendar_name)}",
    ]

    for booking in bookings:
        description_parts = []
        if booking.description:
            description_parts.append(booking.description)

        description_parts.extend([
            f"Переговорная: {booking.room.name}",
            f"Этаж: {booking.room.floor}",
            f"Участников: {booking.attendees_count}",
            f"Статус: {booking.get_status_display()}",
        ])

        if booking.needs_projector:
            description_parts.append("Нужен проектор")
        if booking.needs_video_conf:
            description_parts.append("Нужна видеоконференция")

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:booking-{booking.pk}@smartmeeting",
            f"DTSTAMP:{format_ics_datetime(now)}",
            f"DTSTART:{format_ics_datetime(booking.start_time)}",
            f"DTEND:{format_ics_datetime(booking.end_time)}",
            f"SUMMARY:{escape_ics_text(booking.title)}",
            f"LOCATION:{escape_ics_text(booking.room.name)}",
            f"DESCRIPTION:{escape_ics_text(chr(10).join(description_parts))}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"

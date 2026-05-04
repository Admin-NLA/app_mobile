from datetime import date, datetime, timedelta
from flask import g
from .models import Event, Stats, Appointment, ExhibitorScan

_active_event_cache = (None, None)

_active_event_stats_preview_cache = (None, None, None, None)
_STATS_PREVIEW_TTL_MINUTES = 20

def get_active_event():
    d = date.today()

    current = Event.query.filter(
        Event.start_date <= d,
        Event.end_date + timedelta(days=30) >= d,
    ).first()
    if current:
        return current
    return Event.query.filter(Event.start_date >= d).order_by(Event.start_date.asc()).first()

def is_exhibitor_edit_window(event):
    if not event:
        return False
    current_day = date.today()
    day_number = (current_day - event.start_date).days + 1
    return day_number in (3, 4)

def set_active_event_for_request():
    global _active_event_cache
    today = date.today()
    cached_date, cached_event_id = _active_event_cache

    if cached_date == today and cached_event_id is not None:
        g.active_event = Event.query.get(cached_event_id)
        return
    if cached_date == today and cached_event_id is None:
        g.active_event = None
        return

    event = get_active_event()
    g.active_event = event
    _active_event_cache = (today, event.event_id if event else None)
    
def get_active_event_stats_preview():
    global _active_event_stats_preview_cache

    active_event = g.get("active_event")
    if not active_event:
        return None

    today =  date.today()
    day_number = (today - active_event.start_date).days + 1
    event_days = (active_event.end_date - active_event.start_date).days + 1

    if day_number < 1 or day_number > event_days:
        return None

    day_key = f"day_{day_number}"
    now = datetime.now()

    cached_event_id, cached_day_key, cached_expires_at, cached_payload = _active_event_stats_preview_cache
    if (cached_event_id == active_event.event_id and cached_day_key == day_key and cached_expires_at is not None and now < cached_expires_at):
        return cached_payload
    
    stats_row = (
        Stats.query
        .filter(Stats.event_id == active_event.event_id)
        .order_by(Stats.updated_at.desc())
        .first()
    )

    if not stats_row or not stats_row.stats:
        payload = None
    else:
        stats = stats_row.stats
        
        daily_stats = stats.get("daily_stats", {})
        daily_types = stats.get("daily_attendee_type_scans", {})
        daily_scanned_sh = stats.get("daily_scanned_sh", {})

        total = len(daily_stats.get(day_key, {}).get("actual", []))
        type_stats = daily_types.get(day_key, {})

        daily_exhibitor_stats = stats.get("daily_exhibitor_stats", {})
        today_str = today.isoformat()
        appointments_scheduled = (
            Appointment.query.join(ExhibitorScan)
            .filter(
                ExhibitorScan.event_id == active_event.event_id,
                Appointment.date == today_str,
            )
            .count()
        )
        appointments_completed = (
            Appointment.query.join(ExhibitorScan)
            .filter(
                ExhibitorScan.event_id == active_event.event_id,
                Appointment.date == today_str,
                Appointment.status.is_(True),
            )
            .count()
        )

        payload = {
            "event_id": active_event.event_id,
            "day": day_number,
            "total": total,
            "general": type_stats.get("general", 0),
            "courses": type_stats.get("courses", 0),
            "sessions": type_stats.get("sessions", 0),
            "scholarships": daily_scanned_sh.get(day_key, 0),
            "exhibitors": daily_exhibitor_stats.get(day_key,{}).get("actual", "---"),
            "appointments_scheduled": appointments_scheduled,
            "appointments_completed": appointments_completed,
            "updated_at": stats_row.updated_at.date().isoformat() if stats_row.updated_at else None,
        }

    _active_event_stats_preview_cache = (
        active_event.event_id,
        day_key,
        now + timedelta(minutes=_STATS_PREVIEW_TTL_MINUTES),
        payload
    )

    return payload
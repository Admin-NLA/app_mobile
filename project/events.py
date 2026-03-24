# events.py
"""
Evento activo de la app: lógica centralizada y caché por fecha
para no repetir consultas en cada request (útil en Render y entornos serverless).
"""

from datetime import date
from flask import g
from .models import Event

# Caché por fecha: (fecha_usada, event_id o None). Se invalida al cambiar el día.
_active_event_cache = (None, None)

def get_active_event():
    """
    Devuelve el evento activo según la fecha de consulta:
    - Evento en curso (fecha en [start_date, end_date]), o
    - Próximo evento (start_date >= fecha), ordenado por start_date.
    """
    d = date.today()
    if isinstance(d, str):
        d = date.fromisoformat(d)

    current = Event.query.filter(
        Event.start_date <= d,
        Event.end_date >= d,
    ).first()
    if current:
        return current
    return Event.query.filter(Event.start_date >= d).order_by(Event.start_date.asc()).first()


def set_active_event_for_request():
    """
    Poblado desde before_request: deja en g.active_event el evento activo de hoy.
    Usa caché por día para evitar la consulta pesada en cada request.
    """
    global _active_event_cache
    from .models import Event
    event = get_active_event()
    today = date.today()
    cached_date, cached_event_id = _active_event_cache

    if cached_date == today and cached_event_id is not None:
        g.active_event = Event.query.get(cached_event_id)
        return
    if cached_date == today and cached_event_id is None:
        g.active_event = None
        return

    g.active_event = event
    _active_event_cache = (today, event.event_id if event else None)
    


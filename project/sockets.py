from flask_socketio import join_room
from flask_login import current_user
from flask import g
from .import socketio
from .state import build_records_channel
from .events import set_active_event_for_request

@socketio.on("connect")
def handle_connect():
    set_active_event_for_request()
    active_event = g.get("active_event")

    channel =  build_records_channel(
        current_user.company,
        active_event.event_id if active_event else None
    )

    print("USER:", current_user.company)
    print("EVENT:", active_event.event_id if active_event else None)
    print("CHANNEL", channel)

    if channel:
        join_room(channel)

@socketio.on("disconnect")
def handle_disconnect():
    pass
from datetime import datetime, timedelta
from .models import Appointment
from .events import event_tz
from flask import g

def has_appointment_time_reached(appointment:Appointment):
    tz = event_tz(g.get("active_event"))
    now = datetime.now(tz=tz)
    year, month, day = map(int, appointment.date.split("-"))
    hours, minutes = map(int, appointment.hour.split(":"))
    appt_date = datetime(year,month,day,hours,minutes, tzinfo=tz)

    return now >= appt_date

def is_appointment_expired(appointment:Appointment):
    tz = event_tz(g.get("active_event"))
    now = datetime.now(tz=tz)
    year, month, day = map(int, appointment.date.split("-"))
    hours, minutes = map(int, appointment.hour.split(":"))
    appt_date = datetime(year,month,day,hours,minutes,tzinfo=tz)
    appt_deadline = appt_date + timedelta(hours=2)

    return now >= appt_deadline

def set_appointment_status(appointment:Appointment):
    status = ""
    if appointment.status:
        status = "Cita Completada"
    else:
        if has_appointment_time_reached(appointment):
            if appointment.status == False or is_appointment_expired(appointment):
                status = "Cita no Completada"
            else:
                status = "Cita en Curso"
        else:
            status = "Cita Pendiente"
    return status

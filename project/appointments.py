from datetime import datetime, timedelta
from .models import Appointment

def has_appointment_time_reached(appointment:Appointment):
    now = datetime.now()
    year, month, day = map(int, appointment.date.split("-"))
    hours, minutes = map(int, appointment.hour.split(":"))
    appt_date = datetime(year,month,day,hours,minutes)

    return now >= appt_date

def is_appointment_expired(appointment:Appointment):
    now = datetime.now()
    year, month, day = map(int, appointment.date.split("-"))
    hours, minutes = map(int, appointment.hour.split(":"))
    appt_date = datetime(year,month,day,hours,minutes)
    appt_deadline = appt_date + timedelta(hours=2)

    return now >= appt_deadline

def setAppointmentStatus(appointment:Appointment):
    status = ""
    if appointment.status:
        status = "Cita Completada"
    else:
        if has_appointment_time_reached(appointment):
            if is_appointment_expired(appointment) or appointment.status == False:
                status = "Cita no Completada"
            else:
                status = "Cita en Curso"
        else:
            status = "Cita Pendiente"
    return status

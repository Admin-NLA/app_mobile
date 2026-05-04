from flask import Blueprint, request, jsonify, g, Response
from flask_login import login_required, current_user
from uuid import uuid4
from datetime import datetime, date, timedelta
from sqlalchemy.orm import joinedload

from .state import pending_scans, scan_results, lock, build_records_channel, publish_records_event

from .auth import service_required, require_user_type
from .models import ExhibitorScan, Appointment
from .events import is_exhibitor_edit_window
from . import db, socketio

def get_location():
    event = g.get("active_event")

    locations = {"México" : "Pabellón M, Monterrey NL",
                 "Colombia" : "Centro de convenciones del Hotel Las Américas, Cartagena",
                 "Chile": "Hotel Radisson Blu Plaza El Bosque Santiago"}

    return locations.get(event.location, "")

def insert_scan_record(attendee: dict, event_id):

    record = ExhibitorScan(
        user_id=current_user.user_id,
        event_id=event_id,
        scanned_a_last_name=attendee.get("scanned_a_last_name", ""),
        scanned_a_name=attendee.get("scanned_a_name", ""),
        scanned_a_phone=attendee.get("scanned_a_phone", ""),
        scanned_a_email=attendee.get("scanned_a_email", ""),
        scanned_a_company=attendee.get("scanned_a_company", ""),
        notes=attendee.get("notes", ""),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.session.add(record)
    db.session.commit()
    channel = build_records_channel(current_user.company, event_id)
    if channel:
        publish_records_event(
            channel,
            {"type": "record_created", "e_scan_id": record.e_scan_id}
        )
    return True, record.to_dict()

scan = Blueprint("scan", __name__)

@scan.route("/scan", methods=["POST"])
@login_required
@require_user_type("ADMIN","STAFF")
def recieve_scan():
    data = request.get_json()

    scan_id = str(uuid4())
    with lock:
        pending_scans[scan_id] = {
            "vcard": data.get('qr_data', ''),
            "date": data.get("date", datetime.now().date().isoformat()),
            "status": "pending"
        }
    return jsonify({"scan_id": scan_id})

@scan.route("/pending-scans")
@service_required
def pending():
    with lock:
        scans = [
            {"scan_id": k, **v}
            for k, v in pending_scans.items()
            if v["status"] == "pending"
        ]
    return jsonify(scans)

@scan.route("/scan-result", methods=["POST"])
@service_required
def scan_result():
    data = request.json
    scan_id = data["scan_id"]
 
    with lock:
        if scan_id not in pending_scans:
            return jsonify({"error": "Escaneo no encontrado"}), 400
 
        pending_scans[scan_id]["status"] = "done"
        scan_results[scan_id] = {
            "result": data["result"],
            "status": data["status"],
            "message": data.get("message")
        }
 
    return jsonify({"ok": True})
 
@scan.route("/scan-status/<scan_id>")
@login_required
@require_user_type("ADMIN","STAFF")
def scan_status(scan_id):
    with lock:
        result = scan_results.get(scan_id)
 
    if not result:
        return jsonify({"status": "pending"})
 
    return jsonify(result)

@scan.route("/exhibitor-scan", methods=["POST"])
@login_required
@require_user_type("ADMIN","EXHIBITOR")
def process_exhibitor_scan():
    attendee = request.get_json() or {}

    # Evento activo inyectado por before_request
    event = g.get("active_event")
    if event is None:
        return jsonify({"result": False, "message": "No hay evento activo para registrar el escaneo"}), 400

    scan_date = datetime.now().date()
    day = (scan_date - event.start_date).days + 1

    if day not in (3,4):
        return jsonify({"result": False, "message": f"Sólo puedes escanear Contactos entre {(event.start_date + timedelta(days=2)).strftime('%d/%m/%Y')} y {(event.end_date).strftime('%d/%m/%Y')}"}), 400

    record = (
        ExhibitorScan.query
        .options(joinedload(ExhibitorScan.appointment))
        .filter(
        ExhibitorScan.user_id == current_user.user_id,
        ExhibitorScan.event_id == event.event_id,
        ExhibitorScan.scanned_a_last_name == attendee.get("scanned_a_last_name", ""),
        ExhibitorScan.scanned_a_name == attendee.get("scanned_a_name", ""),
        ExhibitorScan.scanned_a_email == attendee.get("scanned_a_email", ""),
        ExhibitorScan.scanned_a_company == attendee.get("scanned_a_company", "")
        )
        .first()
    )

    if record:
        return jsonify({"result": True, "status": "repeated", "record": record.to_dict(), "notes": record.notes, "message": "Contacto ya guardado", "current_user": current_user.company})

    result, record = insert_scan_record(attendee, event.event_id)

    channel = build_records_channel(current_user.company, event.event_id)

    if channel and record:
        publish_records_event(
            channel,
            {
                "type": "record_created",
                "record": record
            }
        )
    
    return jsonify({"result": result,"status": "new", "record": record, "message": "Contacto almacenado exitosamente", "current_user": current_user.company})

@scan.route('/update-exhibitor-record-notes', methods=["POST"])
@login_required
@require_user_type("ADMIN", "EXHIBITOR")
def update_exhibitor_record_notes():
    if not is_exhibitor_edit_window(g.get("active_event")):
        return jsonify({'success': False, 'message': 'Evento Finalizado. Sólo puedes consultar y exportar contactos.'}), 403
    data = request.get_json()
    e_scan_id = data.get('e_scan_id', '')
    notes = data.get('notes', '')
    record = ExhibitorScan.query.filter_by(e_scan_id=e_scan_id).first()
    if record:
        if record.notes == notes:
            return jsonify({'success': True, 'message': 'No se realizaron cambios en las notas'})    
        record.notes = notes
        db.session.commit()
        channel = build_records_channel(record.user.company, record.event_id)
        if channel:
            publish_records_event(
                channel,
                {"type": "record_updated", "record": record.to_dict()}
            )
        return jsonify({'success': True, 'message': 'Notas guardadas exitosamente'})
    else:
        return jsonify({'success': False, 'message': 'No se pudieron guardar las notas'})
    
# A PARTIR DE AQUÍ ES DE LAS CITAS
    
@scan.route("/add-or-update-appointment", methods=["POST"])
@login_required
@require_user_type("ADMIN", "EXHIBITOR")
def add_or_update_appointment():
    if not is_exhibitor_edit_window(g.get("active_event")):
        return jsonify({'message': 'Evento Finalizado. Sólo puedes consultar y exportar contactos.'}), 403
    data = request.get_json()

    appointment_id = int(data.get('appointment_id', 0))

    date = str(data.get('date', ''))
    hour = str(data.get('hour', ''))
    description = str(data.get('description', ''))

    appointment = Appointment.query.filter_by(appointment_id=appointment_id).first()
    if appointment:
        if str(appointment.date) == date and str(appointment.hour) == hour and str(appointment.description) == description:
            return jsonify({'message': 'No se realizaron cambios en la cita agendada', 'appointment': appointment.to_dict()})
        appointment.date = date
        appointment.hour = hour
        appointment.description = description
        appointment.status = None
        db.session.commit()
        channel = build_records_channel(current_user.company, appointment.exhibitor_scan.event_id)
        if channel:
            publish_records_event(
                channel,
                {"type": "record_updated", "record": appointment.exhibitor_scan.to_dict()}
            )
        return jsonify({'message': 'Cita actualizada exitosamente', 'appointment': appointment.to_dict()})

    e_scan_id = data.get('e_scan_id', '')
    new_appt = Appointment(
        e_scan_id = e_scan_id,
        date = date,
        hour=hour,
        description=description,
        location=get_location()
    )
    db.session.add(new_appt)
    db.session.commit()
    scan_record = (
        ExhibitorScan.query
        .options(joinedload(ExhibitorScan.appointment))
        .filter_by(e_scan_id=e_scan_id).first()
    )

    if scan_record:
        channel = build_records_channel(current_user.company, scan_record.event_id)
        if channel:
            publish_records_event(
                channel,
                {"type": "record_updated", "record": scan_record.to_dict()}
            )
    
    return jsonify({"message": "Cita agendada correctamente", 'appointment': new_appt.to_dict()})

@scan.route("/download_ics/<int:appointment_id>")
@login_required
@require_user_type("ADMIN", "EXHIBITOR")
def download_ics(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    contact_name = f"{appt.exhibitor_scan.scanned_a_name} {appt.exhibitor_scan.scanned_a_last_name}"

    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTAMP:{appt.date.replace("-", "")}T{appt.hour.replace(":", "")}00
DTSTART:{appt.date.replace("-", "")}T{appt.time.replace(":", "")}00
DTEND:{appt.date.replace("-", "")}T{appt.time.replace(":", "")}00
SUMMARY:Cita con {contact_name}
DESCRIPTION:{appt.description or ""}
LOCATION:{appt.location or ""}
END:VEVENT
END:VCALENDAR"""
    return Response(
        ics_content, 
        mimetype="text/calendar",
        headers={"Content-Disposition": f"attachment;filename=cita_{appointment_id}.ics"}
    )

@scan.route("/update-appointment-status", methods=["POST"])
@login_required
@require_user_type("ADMIN", "EXHIBITOR")
def update_appointment_status():
    if not is_exhibitor_edit_window(g.get("active_event")):
        return jsonify({'message': 'Evento Finalizado. Sólo puedes consultar y exportar contactos.'}), 403
    data = request.get_json()
    appointment_id = int(data.get('appointment_id', 0))
    status = data.get('status', None)
    
    appointment = Appointment.query.filter_by(appointment_id=appointment_id).first()
    if appointment:
        appointment.status = status
        db.session.commit()
        channel = build_records_channel(current_user.company, appointment.exhibitor_scan.event_id)
        if channel:
            publish_records_event(
                channel,
                {"type": "record_updated", "record": appointment.exhibitor_scan.to_dict()}
            )
        return jsonify({'message': 'Estado de la cita actualizado'})
    
    return jsonify({'message': 'Cita no encontrada'})
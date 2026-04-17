from flask import Blueprint, render_template, redirect, url_for, request, jsonify, g, send_file
from flask_login import login_required, current_user
from sqlalchemy import func, case
from sqlalchemy.orm import joinedload
from .models import User, Stats, ExhibitorScan, Event, Appointment
from .auth import require_user_type
from .events import get_active_event, get_active_event_stats_preview, is_exhibitor_edit_window
from .excel_writer import create_records_excel_file
from .appointments import setAppointmentStatus

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def home():
    return render_template('home.html')

@main.route('/stats-preview')
@login_required
@require_user_type("ADMIN", "STAFF")
def stats_preview():
    return jsonify({"stats": get_active_event_stats_preview()})

@main.route('/scanner')
@login_required
@require_user_type("ADMIN", "STAFF")
def scanner():
    return render_template('scanner.html')

@main.route('/statistics')
@login_required
@require_user_type("ADMIN")
def statistics():
    stats_records =(
        Stats.query
        .with_entities(Stats.stats_id, Event.location, Event.year)
        .join(Event, Event.event_id == Stats.event_id)
        .all()
    )
    stats_files = [{"id": str(stats_id), "name": f"{location} {year}"} for stats_id, location, year in stats_records]
    return render_template('statistics.html', stats_files=stats_files)

@main.route('/statistics', methods = ["POST"])
@login_required
@require_user_type("ADMIN")
def statistics_post():

    data = request.get_json()
    option:str = data.get('selected_option', '')
    stats = {}
    exhibitors_scans = []

    if option:
        stats_id = int(option)
        stats_record = Stats.query.filter_by(stats_id = stats_id).first()
        if stats_record:
            stats = stats_record.stats
            companies = stats['exhibitor_companies']
            scan_totals = (
                ExhibitorScan.query
                .join(ExhibitorScan.user)
                .outerjoin(Appointment, Appointment.e_scan_id == ExhibitorScan.e_scan_id)
                .filter(ExhibitorScan.event_id == stats_record.event_id)
                .with_entities(User.company,
                               func.count(Appointment.e_scan_id),
                               func.count(case((Appointment.status == True, 1))))
                .group_by(User.company)
                .all()
            )
            scan_dict = {
                company.upper(): {
                    'appt_count': appt_count,
                    'completed_appt_count': completed_appt_count
                }
                for company, appt_count, completed_appt_count in scan_totals
            }

            exhibitors_scans = []

            for company in companies:
                data = scan_dict.get(company, {'appt_count':0, 'completed_appt_count':0})
                exhibitors_scans.append({'company': company, 'appt_count': data['appt_count'], 
                                     'completed_appt_count': data['completed_appt_count']})

    return jsonify({'stats': stats, 'exhibitors_scans': exhibitors_scans})

@main.route('/exhibitor-scanner')
@login_required
@require_user_type("ADMIN", "EXHIBITOR")
def exhibitor_scanner():
    return render_template('exhibitor_scanner.html')

@main.route('/exhibitor-scanner', methods=["POST"])
@login_required
@require_user_type("ADMIN", "EXHIBITOR")
def exhibitor_scanner_post():
    data = request.get_json()
    qr_text = data.get('qr_data', '')

@main.route('/exhibitor-records')
@login_required
@require_user_type("ADMIN", "EXHIBITOR")
def exhibitor_records():
    return render_template("exhibitor_records.html")

@main.route('/exhibitor-records', methods=["POST"])
@login_required
@require_user_type("ADMIN", "EXHIBITOR")
def exhibitor_records_post():
    active_event = g.active_event
    records = []
    event_payload = None
    is_editable_window = False

    if active_event:
        is_editable_window = is_exhibitor_edit_window(active_event)
        scan_records = (
            ExhibitorScan.query
            .options(joinedload(ExhibitorScan.appointment))
            .join(ExhibitorScan.user)
            .filter(
                User.company == current_user.company,
                ExhibitorScan.event_id == active_event.event_id,
            )
            .order_by(ExhibitorScan.created_at.asc())
            .all()
        )
        records = [
            {   
                "e_scan_id": scan.e_scan_id,
                "day": scan.created_at.strftime('%d/%m/%Y'),
                "name": f"{scan.scanned_a_last_name} {scan.scanned_a_name}",
                "phone": scan.scanned_a_phone,
                "email": scan.scanned_a_email,
                "company": scan.scanned_a_company,
                "notes": scan.notes,
                "appointment": scan.appointment.to_dict() if scan.appointment else None
            }
            for scan in scan_records
        ]
        event_payload = {
            "event_id": active_event.event_id,
            "location": active_event.location,
            "year": active_event.year,
            "start_date": active_event.start_date.strftime('%d/%m/%Y'),
            "end_date": active_event.end_date.strftime('%d/%m/%Y'),
            "total_records": len(records),
            "is_editable_window": is_editable_window,
        }

    return jsonify({
        "event": event_payload,
        "records": records,
        "current_user": current_user.company,
        "is_editable_window": is_editable_window
    })

@main.route('/export-records')
@login_required
@require_user_type("ADMIN", "EXHIBITOR")
def export_exhibitor_records():
    active_event = g.active_event
    records = []

    if not active_event:
        return jsonify({"error": "No hay evento activo"}), 404

    scan_records = (
        ExhibitorScan.query
        .options(joinedload(ExhibitorScan.appointment))
        .join(ExhibitorScan.user)
        .filter(
            User.company == current_user.company,
            ExhibitorScan.event_id == active_event.event_id,
        )
        .order_by(ExhibitorScan.created_at.asc())
        .all()
    )

    records = [
        {   
            "DIA": scan.created_at.strftime('%d/%m/%Y'),
            "NOMBRE(S)": scan.scanned_a_name,
            "APELLIDO(S)": scan.scanned_a_last_name,
            "TELEFONO": scan.scanned_a_phone,
            "EMAIL": scan.scanned_a_email,
            "EMPRESA": scan.scanned_a_company,
            "NOTAS": scan.notes,
            "CITA": "✓" if scan.appointment else "",
            "FECHA CITA": scan.appointment.date,
            "ESTADO DE LA CITA": setAppointmentStatus(scan.appointment) if scan.appointment else "---",
            "REAGENDADA": "---" if not scan.appointment else "✓" if (scan.appointment.created_at != scan.appointment.updated_at) else ""
        }
        for scan in scan_records
    ]
    excel_file = create_records_excel_file(records, f"{active_event.location} {active_event.year}")

    return send_file(
        excel_file,
        as_attachment=True,
        download_name= f"Contactos CMC {active_event.location} {active_event.year}",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
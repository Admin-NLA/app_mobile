from flask import Blueprint, render_template, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user
from .models import Stats

main = Blueprint('main', __name__)
process_scanned_data = None

@main.route('/')
@login_required
def home():
    return render_template('home.html', username=current_user.name)

@main.route('/scanner')
@login_required
def scanner():
    return render_template('scanner.html', username=current_user.name)

@main.route('/scanner', methods=["POST"])
@login_required
def scanner_post():
    data = request.get_json()
    qr_text = data.get('qr_data', '')

    if not qr_text:
        return jsonify({'status': 'error', 'message': 'Sin info de QR'}),400

    state, result = process_scanned_data(qr_text) if process_scanned_data is not None else False, "Sin función para procesar"

    if state:
        return jsonify({"status": "success", "message": result, "data": qr_text})
    
    return jsonify({'status': 'error', 'message': result}), 400

@main.route('/statistics')
@login_required
def statistics():

    stats_records = Stats.query.all()
    stats_files = [f"{record.location} {record.year}" for record in stats_records]

    return render_template('statistics.html', username=current_user.name, stats_files=stats_files)

@main.route('/statistics', methods = ["POST"])
@login_required
def statistics_post():

    data = request.get_json()
    name:str = data.get('selected_option', '')
    parts = name.strip().split()
    location, year = parts

    stats_record = Stats.query.filter_by(location=location, year=int(year)).first()
    stats = {}

    if stats_record:
        stats = stats_record.stats

    return jsonify({'stats': stats})

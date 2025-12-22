from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from uuid import uuid4
from datetime import datetime

from .state import pending_scans, scan_results, lock
from .auth import service_required

scan = Blueprint("scan", __name__)

@scan.route("/scan", methods=["POST"])
@login_required
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
            return jsonify({"error": "Scan no encontrado"}), 404
 
        pending_scans[scan_id]["status"] = "done"
        scan_results[scan_id] = {
            "status": data["status"],
            "message": data.get("message")
        }
 
    return jsonify({"ok": True})
 
 
@scan.route("/scan-status/<scan_id>")
@login_required
def scan_status(scan_id):
    with lock:
        result = scan_results.get(scan_id)
 
    if not result:
        return jsonify({"status": "pending"})
 
    return jsonify(result)
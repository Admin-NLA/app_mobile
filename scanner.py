# app_render.py - BACKEND COMPLETO PARA RENDER
"""
Backend Flask completo para Render
Reemplaza la necesidad de ngrok con endpoints completos
"""

from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import json
import os
from datetime import datetime
from pathlib import Path
import uuid
import pandas as pd
from typing import Dict, List, Any
import tempfile
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=["*"])  # Permitir todos los orígenes para desarrollo

# === CONFIGURACIÓN ===
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

ATTENDEES_FILE = DATA_DIR / "attendees.json"
SCANS_FILE = DATA_DIR / "scans.json"
EXCEL_BACKUP = DATA_DIR / "excel_backup.xlsx"

# Configuración de tipos
ATTENDEE_TYPES = {
    'GENERAL': 'Asistente General',
    'SESSIONS': 'Asistente Sesiones', 
    'COURSES': 'Asistente Curso',
    'SCHOLARSHIP': 'Becado',
    'STAFF': 'Staff',
    'EXHIBITOR': 'Expositor'
}

SCAN_TYPES = {
    'ENTRY': 'Entrada',
    'SESSION': 'Sesión',
    'STAND': 'Stand'
}

EVENT_DAYS = [1, 2, 3]

# Data Store (simulando una base de datos en memoria)
class DataStore:
    def __init__(self):
        self.attendees: Dict[str, Any] = {}
        self.scans: List[Dict[str, Any]] = []
        self._load_data()

    def _load_data(self):
        # Cargar asistentes
        if ATTENDEES_FILE.exists():
            with open(ATTENDEES_FILE, 'r', encoding='utf-8') as f:
                self.attendees = json.load(f)
        
        # Cargar escaneos
        if SCANS_FILE.exists():
            with open(SCANS_FILE, 'r', encoding='utf-8') as f:
                self.scans = json.load(f)

    def save_scans(self):
        with open(SCANS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.scans, f, indent=2, ensure_ascii=False)
            
data_store = DataStore()

# === FUNCIONES DE LÓGICA ===
def get_attendee_info_with_scans(attendee_id: str):
    attendee = data_store.attendees.get(attendee_id)
    if not attendee:
        return None
    
    # Obtener historial de escaneos para este asistente
    attendee_scans = [scan for scan in data_store.scans if scan['attendee_id'] == attendee_id]
    
    # Retornar una copia para evitar modificar el objeto original
    attendee_info = attendee.copy()
    attendee_info['scans'] = attendee_scans
    
    return attendee_info

def save_scan(scan_data: Dict[str, Any]):
    # Verificar si ya existe un escaneo para este día y tipo
    existing_scan = next((s for s in data_store.scans 
                          if s['attendee_id'] == scan_data['attendee_id'] and 
                             s['scan_type'] == scan_data['scan_type'] and
                             s['day'] == scan_data['day']), None)
                             
    if existing_scan:
        return {"success": False, "message": "Ya existe un escaneo para este asistente, tipo y día."}
        
    new_scan = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        **scan_data
    }
    data_store.scans.append(new_scan)
    data_store.save_scans()
    
    attendee_info = data_store.attendees.get(scan_data['attendee_id'])
    return {
        "success": True, 
        "message": f"Escaneo registrado para {attendee_info.get('nombre', '')} {attendee_info.get('apellido', '')}",
        "scan_data": new_scan
    }

def get_dashboard_stats():
    stats = {}
    
    # Estadísticas generales
    total_attendees = len(data_store.attendees)
    total_scans = len(data_store.scans)
    
    # Estadísticas por tipo de asistente
    type_stats = {}
    for attendee in data_store.attendees.values():
        tipo = attendee.get('tipo', 'UNKNOWN')
        type_stats[ATTENDEE_TYPES.get(tipo, tipo)] = type_stats.get(ATTENDEE_TYPES.get(tipo, tipo), 0) + 1
    
    # Estadísticas de escaneos por día
    scans_by_day = {}
    for scan in data_store.scans:
        day = scan.get('day', 'UNKNOWN')
        scans_by_day[day] = scans_by_day.get(day, 0) + 1
        
    stats['general_stats'] = {
        'total_attendees': total_attendees,
        'total_scans': total_scans
    }
    stats['type_stats'] = type_stats
    stats['scans_by_day'] = scans_by_day
    
    return stats

# === ENDPOINTS DE LA API ===
@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de salud para verificar el estado del servidor"""
    stats = get_dashboard_stats()
    return jsonify({
        "status": "online",
        "mode": "render",
        "attendees_count": stats['general_stats']['total_attendees'],
        "scans_count": stats['general_stats']['total_scans'],
        "scan_types": list(SCAN_TYPES.keys()),
        "scan_types_map": SCAN_TYPES,
        "attendee_types": list(ATTENDEE_TYPES.keys()),
        "attendee_types_map": ATTENDEE_TYPES,
        "event_days": EVENT_DAYS,
        "location": "Entrada Principal"
    })

@app.route("/attendees", methods=["GET"])
def get_attendees():
    """Devolver la lista completa de asistentes"""
    return jsonify(list(data_store.attendees.values()))

@app.route("/attendee/<attendee_id>", methods=["GET"])
def get_attendee(attendee_id):
    """Devolver información de un asistente específico"""
    attendee_info = get_attendee_info_with_scans(attendee_id)
    if attendee_info:
        return jsonify(attendee_info)
    return jsonify({"message": "Asistente no encontrado"}), 404

@app.route("/scan", methods=["POST"])
def scan_qr():
    """Recibir un escaneo desde la app móvil"""
    data = request.json
    attendee_id = str(data.get('attendee_id', '')).zfill(4)
    scan_type = data.get('scan_type')
    scan_day = data.get('day')
    scanned_by = data.get('scanned_by')
    location = data.get('location')

    if not all([attendee_id, scan_type, scan_day]):
        return jsonify({"success": False, "message": "Faltan datos en la solicitud"}), 400

    if attendee_id not in data_store.attendees:
        return jsonify({"success": False, "message": f"ID de asistente '{attendee_id}' no válido"}), 404
        
    # Obtener info del asistente para validaciones
    attendee_info = data_store.attendees.get(attendee_id)
    
    # === REGLAS DE NEGOCIO ===
    # Regla 1: Solo becados y staff pueden escanear stands
    if scan_type == 'STAND' and attendee_info['tipo'] not in ['SCHOLARSHIP', 'STAFF']:
        return jsonify({"success": False, "message": "Solo Becados y Staff pueden escanear stands"}), 403

    # Regla 2: Un asistente general solo puede escanear su entrada
    if attendee_info['tipo'] == 'GENERAL' and scan_type != 'ENTRY':
         return jsonify({"success": False, "message": "Asistente General solo puede escanear 'Entrada'"}), 403

    # Regla 3: Un asistente de sesiones puede escanear entrada y sesiones
    if attendee_info['tipo'] == 'SESSIONS' and scan_type not in ['ENTRY', 'SESSION']:
        return jsonify({"success": False, "message": "Asistente de Sesiones solo puede escanear 'Entrada' y 'Sesión'"}), 403
        
    # Regla 4: Un expositor solo puede escanear
    if attendee_info['tipo'] == 'EXHIBITOR' and scan_type != 'STAND':
        return jsonify({"success": False, "message": "Expositor solo puede escanear 'Stand'"}), 403
        
    # Regla 5: Un asistente de cursos solo puede escanear entrada y cursos
    if attendee_info['tipo'] == 'COURSES' and scan_type not in ['ENTRY', 'COURSES']:
        return jsonify({"success": False, "message": "Asistente de Cursos solo puede escanear 'Entrada' y 'Cursos'"}), 403

    # Guardar el escaneo
    scan_data = {
        "attendee_id": attendee_id,
        "scan_type": scan_type,
        "day": scan_day,
        "scanned_by": scanned_by,
        "location": location
    }
    
    result = save_scan(scan_data)
    
    if result["success"]:
        return jsonify({"success": True, "message": result['message']}), 200
    else:
        return jsonify({"success": False, "message": result['message']}), 409 # Conflict

@app.route("/scans", methods=["GET"])
def get_scans():
    """Devolver la lista completa de escaneos"""
    return jsonify(data_store.scans)

@app.route("/dashboard", methods=["GET"])
def dashboard():
    """Página de dashboard simple para Render"""
    stats = get_dashboard_stats()
    
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard QR Congress</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: #f0f2f5;
                margin: 0;
                padding: 20px;
                color: #333;
            }}
            .container {{
                max-width: 900px;
                margin: 0 auto;
                background-color: #fff;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            }}
            h1, h2, h3 {{
                color: #1a237e;
                border-bottom: 2px solid #e8eaf6;
                padding-bottom: 10px;
                margin-top: 0;
                margin-bottom: 20px;
            }}
            .metrics {{
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
                justify-content: space-around;
                margin-bottom: 30px;
            }}
            .metric {{
                background-color: #e8eaf6;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                flex: 1;
                min-width: 150px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            }}
            .metric-value {{
                font-size: 2.5em;
                font-weight: 700;
                color: #3949ab;
            }}
            .metric-label {{
                font-size: 1em;
                color: #555;
                margin-top: 5px;
            }}
            .card {{
                background-color: #f9f9f9;
                padding: 25px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
                margin-bottom: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            th, td {{
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #3949ab;
                color: #fff;
                font-weight: 600;
            }}
            tr:hover {{
                background-color: #f1f1f1;
            }}
            @media (max-width: 768px) {{
                .metrics {{
                    flex-direction: column;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Dashboard de Escaneos</h1>
            
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{stats['general_stats']['total_attendees']}</div>
                    <div class="metric-label">👥 Asistentes</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{stats['general_stats']['total_scans']}</div>
                    <div class="metric-label">✅ Escaneos Totales</div>
                </div>
            </div>
            
            <div class="card">
                <h3>📈 Escaneos por Día</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Día</th>
                            <th>Escaneos</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f"<tr><td>Día {day}</td><td>{count}</td></tr>" for day, count in stats['scans_by_day'].items()])}
                    </tbody>
                </table>
            </div>
            
            <div class="card">
                <h3>📊 Estadísticas por Tipo de Asistente</h3>
                <div class="metrics">
                    {"".join([f"<div class='metric'><div class='metric-value'>{count}</div><div class='metric-label'>{tipo}</div></div>" for tipo, count in stats['type_stats'].items()])}
                </div>
            </div>
            
            <div style="text-align: center; margin: 40px 0; color: #666;">
                <p>Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Backend QR Congress System v2.0 - Render Cloud</p>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

# === CONFIGURACIÓN PARA RENDER ===
if __name__ == '__main__':
    # Render proporciona el puerto mediante la variable de entorno PORT
    port = int(os.environ.get('PORT', 5000))
    
    logger.info("🚀 Iniciando Backend QR Congress en Render")
    logger.info(f"📡 Puerto: {port}")
    logger.info(f"👥 Asistentes cargados: {len(data_store.attendees)}")
    logger.info(f"📊 Escaneos cargados: {len(data_store.scans)}")
    
    # Ejecutar en el puerto de Render
    app.run(host='0.0.0.0', port=port)

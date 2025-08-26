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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

# Almacenamiento de datos en memoria
class DataStore:
    def __init__(self):
        self.attendees = self._load_data(ATTENDEES_FILE)
        self.scans = self._load_data(SCANS_FILE)
        self.scans_by_attendee: Dict[str, List[Dict[str, Any]]] = self._group_scans_by_attendee()

    def _load_data(self, file_path):
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _save_data(self, file_path, data):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _group_scans_by_attendee(self):
        grouped = {}
        for scan in self.scans:
            attendee_id = scan.get('attendee_id')
            if attendee_id:
                if attendee_id not in grouped:
                    grouped[attendee_id] = []
                grouped[attendee_id].append(scan)
        return grouped

    def add_attendee(self, attendee):
        self.attendees.append(attendee)
        self._save_data(ATTENDEES_FILE, self.attendees)

    def add_scan(self, scan):
        self.scans.append(scan)
        self._save_data(SCANS_FILE, self.scans)
        self._group_scans_by_attendee()  # Re-agrupar después de un nuevo escaneo

    def get_attendee_by_id(self, attendee_id):
        return next((a for a in self.attendees if a.get('id') == attendee_id), None)

    def get_attendee_scans(self, attendee_id):
        return self.scans_by_attendee.get(attendee_id, [])

    def get_all_attendees(self):
        return self.attendees

    def get_all_scans(self):
        return self.scans

    def get_stats(self):
        total_attendees = len(self.attendees)
        total_scans = len(self.scans)

        # Estadísticas por tipo de asistente
        type_stats = {}
        for attendee in self.attendees:
            attendee_type = attendee.get('tipo', 'UNKNOWN')
            type_stats[attendee_type] = type_stats.get(attendee_type, 0) + 1

        # Estadísticas por tipo de escaneo
        scan_type_stats = {}
        for scan in self.scans:
            scan_type = scan.get('scan_type', 'UNKNOWN')
            scan_type_stats[scan_type] = scan_type_stats.get(scan_type, 0) + 1

        # Escaneos recientes
        recent_scans = sorted(self.scans, key=lambda x: x.get('timestamp', '1970-01-01'), reverse=True)[:10]
        for scan in recent_scans:
            attendee = self.get_attendee_by_id(scan.get('attendee_id', ''))
            scan['attendee_name'] = f"{attendee.get('nombre', '')} {attendee.get('apellido', '')}" if attendee else "Desconocido"

        return {
            'total_attendees': total_attendees,
            'total_scans': total_scans,
            'type_stats': type_stats,
            'scan_type_stats': scan_type_stats,
            'recent_scans': recent_scans
        }

    def import_attendees_from_excel(self, file):
        try:
            df = pd.read_excel(file, engine='openpyxl')
            imported_attendees = []
            for _, row in df.iterrows():
                attendee_id = str(row.iloc[0]).strip().zfill(4)
                if not attendee_id:
                    continue
                imported_attendees.append({
                    'id': attendee_id,
                    'apellido': str(row.iloc[1]).strip() if len(df.columns) > 1 else '',
                    'nombre': str(row.iloc[2]).strip() if len(df.columns) > 2 else '',
                    'empresa': str(row.iloc[3]).strip() if len(df.columns) > 3 else '',
                    'correo': str(row.iloc[4]).strip() if len(df.columns) > 4 else '',
                    'telefono': str(row.iloc[5]).strip() if len(df.columns) > 5 else '',
                    'curso': str(row.iloc[6]).strip() if len(df.columns) > 6 else '',
                    'sesion': str(row.iloc[7]).strip() if len(df.columns) > 7 else '',
                    'beca': str(row.iloc[8]).strip() if len(df.columns) > 8 else '',
                    'link_crm': str(row.iloc[9]).strip() if len(df.columns) > 9 else '',
                })

            self.attendees = imported_attendees
            self._save_data(ATTENDEES_FILE, self.attendees)
            return True, f"Se importaron {len(imported_attendees)} asistentes."
        except Exception as e:
            return False, f"Error al importar Excel: {e}"

app = Flask(__name__)
CORS(app, origins=["*"])  # Permitir todos los orígenes para desarrollo
data_store = DataStore()


# === RUTAS API ===
@app.route("/health")
def health_check():
    """Endpoint para verificar el estado del servidor."""
    logger.info("Health check recibido.")
    return jsonify({
        "status": "online",
        "message": "Backend QR Congress System v2.0",
        "timestamp": datetime.now().isoformat()
    })

@app.route("/attendees")
def get_attendees():
    """Retorna la lista completa de asistentes."""
    logger.info("Solicitud de asistentes recibida.")
    return jsonify(data_store.get_all_attendees())

@app.route("/scans")
def get_scans():
    """Retorna la lista completa de escaneos."""
    logger.info("Solicitud de escaneos recibida.")
    return jsonify(data_store.get_all_scans())

@app.route("/attendee/<attendee_id>")
def get_attendee_details(attendee_id):
    """Retorna los detalles de un asistente y sus escaneos."""
    logger.info(f"Solicitud de detalles para asistente ID: {attendee_id}")
    attendee = data_store.get_attendee_by_id(attendee_id)
    if not attendee:
        logger.warning(f"Asistente ID {attendee_id} no encontrado.")
        return jsonify({"error": "Attendee not found"}), 404

    scans = data_store.get_attendee_scans(attendee_id)
    return jsonify({
        "attendee": attendee,
        "scans": scans
    })

@app.route("/scan_qr", methods=["POST"])
def scan_qr():
    """Endpoint para registrar un nuevo escaneo."""
    data = request.json
    attendee_id = data.get('attendee_id')
    scan_type = data.get('scan_type')
    day = data.get('day')
    scanned_by = data.get('scanned_by')
    location = data.get('location')

    if not all([attendee_id, scan_type, day, scanned_by, location]):
        logger.error("Datos de escaneo incompletos.")
        return jsonify({"error": "Missing required scan data"}), 400

    attendee = data_store.get_attendee_by_id(attendee_id)
    if not attendee:
        logger.warning(f"Intento de escanear ID {attendee_id} no válido.")
        return jsonify({
            "success": False,
            "message": "ID de asistente no válido",
            "attendee": None
        }), 404

    new_scan = {
        "id": str(uuid.uuid4()),
        "attendee_id": attendee_id,
        "scan_type": scan_type,
        "day": day,
        "scanned_by": scanned_by,
        "location": location,
        "timestamp": datetime.now().isoformat()
    }
    data_store.add_scan(new_scan)
    logger.info(f"Escaneo de {attendee_id} registrado exitosamente.")

    return jsonify({
        "success": True,
        "message": "Escaneo registrado exitosamente.",
        "attendee": attendee,
        "scan": new_scan
    })

@app.route("/stats")
def get_stats():
    """Retorna las estadísticas del sistema."""
    logger.info("Solicitud de estadísticas recibida.")
    stats = data_store.get_stats()
    return jsonify(stats)

@app.route("/excel_report")
def export_excel():
    """Genera y descarga un reporte Excel de los escaneos."""
    logger.info("Solicitud de reporte Excel recibida.")
    
    scans_data = data_store.get_all_scans()
    if not scans_data:
        return jsonify({"error": "No hay escaneos para exportar"}), 404

    # Preparar datos para el DataFrame
    export_data = []
    for scan in scans_data:
        attendee = data_store.get_attendee_by_id(scan.get('attendee_id', ''))
        export_data.append({
            'ID_Escaneo': scan.get('id', ''),
            'ID_Asistente': scan.get('attendee_id', ''),
            'Nombre': f"{attendee.get('nombre', '')} {attendee.get('apellido', '')}" if attendee else "Desconocido",
            'Empresa': attendee.get('empresa', '') if attendee else "Desconocido",
            'Tipo_Asistente': attendee.get('tipo', '') if attendee else "Desconocido",
            'Tipo_Escaneo': scan.get('scan_type', ''),
            'Día': scan.get('day', ''),
            'Fecha_Hora': scan.get('timestamp', ''),
            'Escaneado_Por': scan.get('scanned_by', ''),
            'Ubicación': scan.get('location', ''),
            'Notas': scan.get('notes', '')
        })

    df = pd.DataFrame(export_data)

    # Crear un archivo temporal para el Excel
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
        temp_filename = temp_file.name
        df.to_excel(temp_filename, index=False, engine='openpyxl')

    logger.info(f"Reporte Excel generado en {temp_filename}")
    return send_file(temp_filename, as_attachment=True, download_name="reporte_escaneos.xlsx")


@app.route("/dashboard")
def dashboard():
    """Retorna una página de dashboard HTML para visualización."""
    stats = data_store.get_stats()
    
    # Generar la tabla de escaneos recientes
    recent_scans_html = ""
    for scan in stats.get('recent_scans', []):
        recent_scans_html += f"""
        <tr>
            <td>{scan.get('timestamp', '').split('T')[1].split('.')[0]}</td>
            <td>{scan.get('attendee_name', '')}</td>
            <td>{SCAN_TYPES.get(scan.get('scan_type', ''), 'Desconocido')}</td>
        </tr>
        """
    
    # Generar las métricas de tipo de asistente
    type_metrics_html = "".join([
        f'<div class="metric"><div class="metric-value">{count}</div><div class="metric-label">{ATTENDEE_TYPES.get(tipo, "Desconocido")}</div></div>'
        for tipo, count in stats.get('type_stats', {}).items()
    ])

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard QR Congress System</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
            body {{
                font-family: 'Inter', sans-serif;
                background-color: #f4f7f9;
                color: #333;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 960px;
                margin: 20px auto;
                padding: 20px;
            }}
            .header {{
                background-color: #2c3e50;
                color: white;
                padding: 30px;
                border-radius: 15px;
                text-align: center;
                margin-bottom: 20px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }}
            .header h1 {{
                margin: 0;
                font-weight: 700;
                font-size: 2.5em;
            }}
            .header p {{
                margin-top: 10px;
                font-size: 1.1em;
                opacity: 0.8;
            }}
            .stats {{
                display: flex;
                justify-content: space-around;
                align-items: center;
                gap: 20px;
                margin-bottom: 30px;
                text-align: center;
            }}
            .stat-card {{
                flex-grow: 1;
                background-color: #ffffff;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .stat-card .value {{
                font-size: 3em;
                font-weight: 700;
                color: #3498db;
            }}
            .stat-card .label {{
                font-size: 1em;
                font-weight: 600;
                color: #555;
            }}
            .card {{
                background-color: #ffffff;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            .card h3 {{
                margin-top: 0;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
                color: #2c3e50;
                font-weight: 600;
            }}
            .metrics {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 15px;
            }}
            .metric {{
                text-align: center;
                background-color: #ecf0f1;
                padding: 15px;
                border-radius: 10px;
            }}
            .metric-value {{
                font-size: 1.5em;
                font-weight: 700;
                color: #2c3e50;
            }}
            .metric-label {{
                font-size: 0.8em;
                font-weight: 500;
                color: #666;
                margin-top: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #34495e;
                color: white;
                font-weight: 600;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
            tr:last-child td {{
                border-bottom: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Sistema de Gestión de Asistentes</h1>
                <p>Dashboard de Escaneos y Estadísticas</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="value">{stats.get('total_attendees', 0)}</div>
                    <div class="label">Total Asistentes</div>
                </div>
                <div class="stat-card">
                    <div class="value">{stats.get('total_scans', 0)}</div>
                    <div class="label">Total Escaneos</div>
                </div>
            </div>
            
            <div class="card">
                <h3>📜 Escaneos Recientes</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Hora</th>
                            <th>Asistente</th>
                            <th>Tipo de Escaneo</th>
                        </tr>
                    </thead>
                    <tbody>
                        {recent_scans_html}
                    </tbody>
                </table>
            </div>
            
            <div class="card">
                <h3>📊 Estadísticas por Tipo</h3>
                <div class="metrics">
                    {type_metrics_html}
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

    # Ejecutar la aplicación Flask
    # Con host='0.0.0.0' para que sea accesible desde la red
    app.run(host='0.0.0.0', port=port, debug=False)

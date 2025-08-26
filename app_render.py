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

# Creamos la aplicación Flask
app = Flask(__name__)
# Permitir todos los orígenes para el escáner móvil de Streamlit
# Este código se mantiene porque la advertencia es benigna y no rompe la app
CORS(app, origins=["*"])  

# === CONFIGURACIÓN ===
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

ATTENDEES_FILE = DATA_DIR / "attendees.json"
SCANS_FILE = DATA_DIR / "scans.json"
EXCEL_BACKUP = DATA_DIR / "excel_backup.xlsx"

# Configuración de tipos (debería coincidir con config.py)
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

# === ALMACÉN DE DATOS EN MEMORIA (In-memory data store) ===
class DataStore:
    def __init__(self):
        self.attendees: Dict[str, Any] = self.load_attendees()
        self.scans: List[Dict[str, Any]] = self.load_scans()
        
    def load_attendees(self) -> Dict[str, Any]:
        """Cargar datos de asistentes desde el archivo JSON."""
        try:
            if ATTENDEES_FILE.exists():
                with open(ATTENDEES_FILE, 'r', encoding='utf-8') as f:
                    return {a['id']: a for a in json.load(f)}
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error al cargar asistentes: {e}")
        return {}

    def save_scans(self):
        """Guardar datos de escaneos en el archivo JSON."""
        try:
            with open(SCANS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.scans, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Error al guardar escaneos: {e}")

    def load_scans(self) -> List[Dict[str, Any]]:
        """Cargar escaneos desde el archivo JSON."""
        try:
            if SCANS_FILE.exists():
                with open(SCANS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error al cargar escaneos: {e}")
        return []

data_store = DataStore()

# === ENDPOINTS DE LA API ===
@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar el estado del servidor."""
    return jsonify({
        "status": "online",
        "message": "Backend QR Congress System v2.0",
        "attendees_count": len(data_store.attendees),
        "scans_count": len(data_store.scans),
        "last_updated": datetime.now().isoformat(),
        # Incluimos los tipos para que Streamlit los use
        "ATTENDEE_TYPES": ATTENDEE_TYPES,
        "SCAN_TYPES": SCAN_TYPES
    })

@app.route('/validate_attendee', methods=['POST'])
def validate_attendee():
    """Endpoint para validar un QR escaneado."""
    try:
        data = request.json
        attendee_id = data.get('attendee_id')
        scan_type = data.get('scan_type', 'ENTRY')
        user_id = data.get('user_id', 'unknown')
        location = data.get('location', 'unknown')
        
        if not attendee_id:
            return jsonify({"status": "error", "message": "ID de asistente no proporcionado"}), 400
        
        attendee = data_store.attendees.get(str(attendee_id).zfill(4))
        
        if attendee:
            # Registrar el escaneo
            scan_data = {
                "id": str(uuid.uuid4()),
                "attendee_id": attendee_id,
                "scan_type": scan_type,
                "timestamp": datetime.now().isoformat(),
                "scanned_by": user_id,
                "location": location,
                "notes": ""
            }
            data_store.scans.append(scan_data)
            data_store.save_scans()
            
            # Devolver los datos del asistente y mensaje de éxito
            return jsonify({
                "status": "success",
                "message": f"Acceso concedido para {attendee['nombre']} {attendee['apellido']}",
                "attendee": {
                    "id": attendee['id'],
                    "nombre": attendee['nombre'],
                    "apellido": attendee['apellido'],
                    "empresa": attendee['empresa'],
                    "tipo": attendee['tipo']
                }
            })
        else:
            return jsonify({"status": "error", "message": "ID de asistente no encontrado"}), 404
            
    except Exception as e:
        logger.error(f"Error en validate_attendee: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Error interno del servidor: {str(e)}"}), 500

@app.route('/attendees', methods=['GET'])
def get_attendees():
    """Endpoint para obtener la lista completa de asistentes."""
    return jsonify({
        "status": "success",
        "attendees": list(data_store.attendees.values())
    })

@app.route('/scans', methods=['GET'])
def get_scans():
    """Endpoint para obtener la lista completa de escaneos."""
    return jsonify({
        "status": "success",
        "scans": data_store.scans
    })

@app.route('/dashboard', methods=['GET'])
def dashboard_html():
    """Endpoint para generar un dashboard en HTML."""
    try:
        # Calcular estadísticas
        attendee_count = len(data_store.attendees)
        scans_count = len(data_store.scans)
        
        scans_df = pd.DataFrame(data_store.scans)
        
        # Últimos 10 escaneos
        latest_scans = scans_df.sort_values(by='timestamp', ascending=False).head(10).to_dict('records')
        for scan in latest_scans:
            attendee = data_store.attendees.get(str(scan['attendee_id']).zfill(4))
            scan['attendee_name'] = f"{attendee['nombre']} {attendee['apellido']}" if attendee else "Desconocido"

        # Estadísticas por tipo
        type_stats = {}
        if not scans_df.empty:
            scanned_attendees = scans_df['attendee_id'].apply(lambda x: data_store.attendees.get(str(x).zfill(4)))
            scanned_attendees = scanned_attendees.dropna()
            
            attendee_types = [a['tipo'] for a in scanned_attendees]
            type_stats_raw = pd.Series(attendee_types).value_counts().to_dict()
            
            type_stats = {
                ATTENDEE_TYPES.get(k, k): v for k, v in type_stats_raw.items()
            }
            
        # Contenido HTML
        html = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Dashboard QR Congress</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
            <style>
                body {{
                    font-family: 'Inter', sans-serif;
                    background-color: #f4f7f9;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }}
                .container {{
                    max-width: 900px;
                    margin: auto;
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                }}
                h1 {{
                    text-align: center;
                    color: #1a237e;
                }}
                .stats {{
                    display: flex;
                    justify-content: space-around;
                    gap: 20px;
                    margin: 30px 0;
                }}
                .stat-card {{
                    background: #e3f2fd;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    flex: 1;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
                }}
                .stat-value {{
                    font-size: 2.5em;
                    font-weight: 700;
                    color: #1a237e;
                }}
                .stat-label {{
                    font-size: 1em;
                    color: #555;
                    margin-top: 5px;
                }}
                .card {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    margin-top: 20px;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
                }}
                .table-container {{
                    overflow-x: auto;
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
                    background-color: #e0e0e0;
                    font-weight: 600;
                    color: #444;
                }}
                tr:hover {{
                    background-color: #f1f1f1;
                }}
                .metrics {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 15px;
                    margin-top: 15px;
                }}
                .metric {{
                    background: #eceff1;
                    padding: 10px 15px;
                    border-radius: 8px;
                    text-align: center;
                    flex: 1 1 calc(33% - 15px);
                }}
                .metric-value {{
                    font-size: 1.5em;
                    font-weight: 600;
                    color: #333;
                }}
                .metric-label {{
                    font-size: 0.8em;
                    color: #777;
                    margin-top: 5px;
                }}
                @media (max-width: 600px) {{
                    .stats, .metrics {{
                        flex-direction: column;
                    }}
                    .metric {{
                        flex-basis: 100%;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Dashboard de Gestión de Asistentes</h1>
                <p style="text-align: center; color: #777;">Resumen en tiempo real del evento.</p>

                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-value">{attendee_count}</div>
                        <div class="stat-label">Asistentes Registrados</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{scans_count}</div>
                        <div class="stat-label">Escaneos Realizados</div>
                    </div>
                </div>

                <div class="card">
                    <h3>🔔 Últimos Escaneos</h3>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Hora</th>
                                    <th>Asistente</th>
                                    <th>Tipo</th>
                                    <th>Ubicación</th>
                                    <th>Escaneado Por</th>
                                </tr>
                            </thead>
                            <tbody>
                                {"".join([
                                    f'<tr><td>{datetime.fromisoformat(s["timestamp"]).strftime("%H:%M:%S")}</td><td>{s["attendee_name"]} ({s["attendee_id"]})</td><td>{s["scan_type"]}</td><td>{s["location"]}</td><td>{s["scanned_by"]}</td></tr>'
                                    for s in latest_scans
                                ])}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="card">
                    <h3>📊 Estadísticas por Tipo</h3>
                    <div class="metrics">
                        {''.join([
                            f'<div class="metric"><div class="metric-value">{count}</div><div class="metric-label">{tipo}</div></div>'
                            for tipo, count in type_stats.items()
                        ])}
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
        
    except Exception as e:
        logger.error(f"Error generando dashboard: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Error interno del servidor al generar dashboard: {str(e)}"}), 500

@app.route('/export/excel', methods=['GET'])
def export_excel():
    """Endpoint para exportar los datos de escaneo a un archivo Excel."""
    try:
        if not data_store.scans:
            return jsonify({"status": "error", "message": "No hay escaneos para exportar."}), 404

        export_data = []
        for scan in data_store.scans:
            attendee = data_store.attendees.get(str(scan['attendee_id']).zfill(4))
            attendee_name = f"{attendee.get('nombre', '')} {attendee.get('apellido', '')}" if attendee else 'Desconocido'
            attendee_company = attendee.get('empresa', 'Desconocido') if attendee else 'Desconocido'
            attendee_type = attendee.get('tipo', 'Desconocido') if attendee else 'Desconocido'
            
            export_data.append({
                'ID_Escaneo': scan['id'],
                'ID_Asistente': scan['attendee_id'],
                'Nombre': attendee_name,
                'Empresa': attendee_company,
                'Tipo_Asistente': attendee_type,
                'Tipo_Escaneo': scan['scan_type'],
                'Fecha_Hora': scan['timestamp'],
                'Escaneado_Por': scan['scanned_by'],
                'Ubicación': scan['location']
            })
        
        df = pd.DataFrame(export_data)
        
        # Guardar en un archivo temporal para enviarlo
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            temp_path = temp_file.name
            df.to_excel(temp_path, index=False)
        
        return send_file(temp_path, as_attachment=True, download_name="reporte_escaneos.xlsx")
        
    except Exception as e:
        logger.error(f"Error al exportar a Excel: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Error interno del servidor: {str(e)}"}), 500

# === CONFIGURACIÓN PARA RENDER ===
if __name__ == '__main__':
    # Render proporciona el puerto mediante la variable de entorno PORT
    port = int(os.environ.get('PORT', 5000))
    
    logger.info("🚀 Iniciando Backend QR Congress en Render")
    logger.info(f"📡 Puerto: {port}")
    logger.info(f"👥 Asistentes cargados: {len(data_store.attendees)}")
    logger.info(f"📊 Escaneos cargados: {len(data_store.scans)}")
    
    # Ejecutar la aplicación
    app.run(host='0.0.0.0', port=port, debug=False)

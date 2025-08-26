# app_render.py - BACKEND COMPLETO PARA RENDER
"""
Backend Flask completo para Render
Reemplaza la necesidad de ngrok con endpoints completos
"""

from flask import Flask, request, jsonify, send_file
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

# === ALMACENAMIENTO EN MEMORIA ===
class DataStore:
    def __init__(self):
        self.attendees = []
        self.scans = []
        self.load_data()
    
    def load_data(self):
        """Cargar datos desde archivos JSON"""
        try:
            if ATTENDEES_FILE.exists():
                with open(ATTENDEES_FILE, 'r', encoding='utf-8') as f:
                    self.attendees = json.load(f)
                logger.info(f"Cargados {len(self.attendees)} asistentes")
            
            if SCANS_FILE.exists():
                with open(SCANS_FILE, 'r', encoding='utf-8') as f:
                    self.scans = json.load(f)
                logger.info(f"Cargados {len(self.scans)} escaneos")
                
        except Exception as e:
            logger.error(f"Error cargando datos: {e}")
    
    def save_attendees(self):
        """Guardar asistentes en JSON"""
        try:
            with open(ATTENDEES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.attendees, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando asistentes: {e}")
    
    def save_scans(self):
        """Guardar escaneos en JSON"""
        try:
            with open(SCANS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.scans, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando escaneos: {e}")
    
    def find_attendee_by_email(self, email: str):
        """Buscar asistente por email"""
        for attendee in self.attendees:
            if attendee.get('correo', '').lower() == email.lower():
                return attendee
        return None
    
    def find_attendee_by_name(self, full_name: str):
        """Buscar asistente por nombre completo"""
        full_name_lower = full_name.lower()
        for attendee in self.attendees:
            nombre = attendee.get('nombre', '')
            apellido = attendee.get('apellido', '')
            if f"{nombre} {apellido}".lower() == full_name_lower:
                return attendee
        return None
    
    def add_scan(self, scan_data: Dict):
        """Agregar nuevo escaneo"""
        scan_data['id'] = str(uuid.uuid4())[:8]
        scan_data['timestamp'] = datetime.now().isoformat()
        self.scans.append(scan_data)
        self.save_scans()
        return scan_data['id']
    
    def get_stats(self) -> Dict:
        """Generar estadísticas"""
        stats = {
            'total_attendees': len(self.attendees),
            'total_scans': len(self.scans),
            'entry_scans': len([s for s in self.scans if s.get('scan_type') == 'Entrada']),
            'session_scans': len([s for s in self.scans if s.get('scan_type') == 'Sesión']),
            'stand_scans': len([s for s in self.scans if s.get('scan_type') == 'Stand']),
            'daily_stats': {},
            'type_stats': {},
            'scholarship_stats': {'total_becados': 0}
        }
        
        # Estadísticas por tipo de asistente
        for attendee in self.attendees:
            tipo = attendee.get('tipo', 'Sin tipo')
            stats['type_stats'][tipo] = stats['type_stats'].get(tipo, 0) + 1
            
            if attendee.get('es_becado', False):
                stats['scholarship_stats']['total_becados'] += 1
        
        # Estadísticas por día
        for day in [1, 2, 3, 4]:
            day_scans = [s for s in self.scans if s.get('day') == day]
            unique_attendees = len(set(s.get('attendee_id') for s in day_scans))
            stats['daily_stats'][f'day_{day}'] = unique_attendees
        
        return stats

# Instancia global del almacén de datos
data_store = DataStore()

# === UTILIDADES ===
def parse_vcard(vcard_data: str) -> tuple[str, str]:
    """Parsear datos de VCard"""
    email = None
    name = None
    
    try:
        # Decodificar base64 si es necesario
        import base64
        try:
            decoded = base64.b64decode(vcard_data).decode('utf-8')
        except:
            decoded = vcard_data
        
        # Parsear VCard
        for line in decoded.split('\n'):
            line = line.strip()
            if line.startswith('EMAIL:'):
                email = line.replace('EMAIL:', '').strip()
            elif line.startswith('FN:'):
                name = line.replace('FN:', '').strip()
    
    except Exception as e:
        logger.error(f"Error parseando VCard: {e}")
    
    return email, name

def validate_access(attendee: Dict, scan_type: str) -> tuple[bool, str]:
    """Validar acceso del asistente según su tipo"""
    tipo = attendee.get('tipo', '')
    
    # Entrada principal - todos pueden acceder
    if scan_type == 'Entrada':
        return True, "Acceso autorizado"
    
    # Sesiones - solo algunos tipos
    elif scan_type == 'Sesión':
        if tipo in ['Asistente General', 'Asistente Sesiones']:
            return True, "Acceso autorizado a sesión"
        else:
            return False, "No autorizado para sesiones"
    
    # Stands - todos pueden acceder
    elif scan_type == 'Stand':
        return True, "Acceso autorizado a stand"
    
    return True, "Acceso autorizado"

def process_excel_data(file_path: Path) -> List[Dict]:
    """Procesar archivo Excel y convertir a lista de asistentes"""
    try:
        df = pd.read_excel(file_path)
        attendees = []
        
        for index, row in df.iterrows():
            try:
                attendee = {
                    'id': str(row.get('A', f"AUTO_{index:04d}")),
                    'apellido': str(row.get('C', '')).strip(),
                    'nombre': str(row.get('D', '')).strip(),
                    'empresa': str(row.get('E', '')).strip(),
                    'correo': str(row.get('F', '')).strip(),
                    'telefono': str(row.get('G', '')).strip(),
                    'curso': str(row.get('H', '')).strip() if pd.notna(row.get('H')) else '',
                    'sesion': str(row.get('I', '')).strip() if pd.notna(row.get('I')) else '',
                    'beca': str(row.get('J', '')).strip() if pd.notna(row.get('J')) else '',
                    'link_crm': str(row.get('K', '')).strip() if pd.notna(row.get('K')) else ''
                }
                
                # Determinar tipo de asistente
                has_curso = bool(attendee['curso'])
                has_sesion = bool(attendee['sesion'])
                has_beca = bool(attendee['beca'])
                
                if has_curso and has_sesion:
                    attendee['tipo'] = 'Asistente General'
                elif has_sesion:
                    attendee['tipo'] = 'Asistente Sesiones'
                elif has_curso:
                    attendee['tipo'] = 'Asistente Curso'
                else:
                    attendee['tipo'] = 'Asistente'
                
                attendee['es_becado'] = has_beca
                attendee['permisos'] = {
                    'entrada': True,
                    'sesiones': has_sesion or (has_curso and has_sesion),
                    'cursos': has_curso,
                    'stands': True
                }
                
                attendees.append(attendee)
                
            except Exception as e:
                logger.error(f"Error procesando fila {index}: {e}")
                continue
        
        return attendees
        
    except Exception as e:
        logger.error(f"Error procesando Excel: {e}")
        return []

# === ENDPOINTS PRINCIPALES ===

@app.route('/')
def index():
    """Página principal del backend"""
    stats = data_store.get_stats()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Backend QR Congress - Render</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .status {{ padding: 15px; border-radius: 5px; margin: 15px 0; }}
            .healthy {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #e9ecef; border-radius: 5px; text-align: center; min-width: 120px; }}
            .metric-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
            .metric-label {{ font-size: 0.9em; color: #666; }}
            .endpoints {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            .endpoint {{ font-family: monospace; background: #e9ecef; padding: 5px 8px; margin: 3px 0; border-radius: 3px; display: block; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Backend QR Congress System</h1>
            
            <div class="status healthy">
                <h3>✅ Sistema Operativo</h3>
                <p><strong>Estado:</strong> Conectado y funcionando</p>
                <p><strong>Servidor:</strong> Render Cloud</p>
                <p><strong>Última actualización:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <h3>📊 Estadísticas Actuales</h3>
            <div style="text-align: center;">
                <div class="metric">
                    <div class="metric-value">{stats['total_attendees']}</div>
                    <div class="metric-label">Asistentes</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{stats['total_scans']}</div>
                    <div class="metric-label">Escaneos</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{stats['entry_scans']}</div>
                    <div class="metric-label">Entradas</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{stats['session_scans']}</div>
                    <div class="metric-label">Sesiones</div>
                </div>
            </div>
            
            <h3>🔗 Endpoints API</h3>
            <div class="endpoints">
                <div class="endpoint">GET /health - Verificación de estado</div>
                <div class="endpoint">POST /upload_attendees - Subir lista de asistentes</div>
                <div class="endpoint">GET /get_attendees - Obtener asistentes</div>
                <div class="endpoint">POST /validate_attendee - Validar código QR</div>
                <div class="endpoint">GET /get_stats - Estadísticas</div>
                <div class="endpoint">POST /upload_excel - Subir archivo Excel</div>
                <div class="endpoint">POST /sync_scans - Sincronizar escaneos</div>
            </div>
            
            <h3>📱 URLs para Aplicaciones</h3>
            <div class="endpoints">
                <div class="endpoint">App Tkinter: https://{request.host}</div>
                <div class="endpoint">App Móvil Streamlit: https://{request.host}</div>
            </div>
            
            <div style="text-align: center; margin-top: 30px; color: #666;">
                <small>Sistema de Gestión de Asistentes con QR - Backend v2.0</small>
            </div>
        </div>
    </body>
    </html>
    """
    return html

@app.route('/health')
def health_check():
    """Endpoint de verificación de salud"""
    try:
        stats = data_store.get_stats()
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "attendees_loaded": len(data_store.attendees),
            "scans_count": len(data_store.scans),
            "server_info": {
                "platform": "Render",
                "version": "2.0",
                "direct_connection": True
            },
            "stats": stats
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/upload_attendees', methods=['POST'])
def upload_attendees():
    """Subir lista de asistentes"""
    try:
        data = request.get_json()
        attendees = data.get('attendees', [])
        
        if not attendees:
            return jsonify({
                "success": False,
                "message": "No se recibieron asistentes"
            }), 400
        
        # Reemplazar lista completa
        data_store.attendees = attendees
        data_store.save_attendees()
        
        logger.info(f"Subidos {len(attendees)} asistentes")
        
        return jsonify({
            "success": True,
            "message": f"Se subieron {len(attendees)} asistentes exitosamente",
            "count": len(attendees)
        }), 200
        
    except Exception as e:
        logger.error(f"Error subiendo asistentes: {e}")
        return jsonify({
            "success": False,
            "message": f"Error interno: {str(e)}"
        }), 500

@app.route('/get_attendees')
def get_attendees():
    """Obtener lista de asistentes"""
    try:
        return jsonify(data_store.attendees), 200
    except Exception as e:
        logger.error(f"Error obteniendo asistentes: {e}")
        return jsonify({
            "error": f"Error obteniendo asistentes: {str(e)}"
        }), 500

@app.route('/validate_attendee', methods=['POST'])
def validate_attendee():
    """Validar asistente por código QR - ENDPOINT PRINCIPAL"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "No se recibieron datos JSON"
            }), 400
        
        qr_data = data.get('qr_data')
        device_info = data.get('device_info', {})
        scan_config = data.get('scan_config', {
            'scan_type': 'Entrada',
            'day': 1,
            'location': 'Móvil'
        })
        
        if not qr_data:
            return jsonify({
                "success": False,
                "message": "Falta el campo 'qr_data'"
            }), 400
        
        logger.info(f"Validando QR: {qr_data[:50]}...")
        
        # Parsear VCard y buscar asistente
        email, name = parse_vcard(qr_data)
        attendee = None
        
        if email:
            attendee = data_store.find_attendee_by_email(email)
        if not attendee and name:
            attendee = data_store.find_attendee_by_name(name)
        
        if not attendee:
            logger.warning(f"Asistente no encontrado: email={email}, name={name}")
            return jsonify({
                "success": False,
                "message": "QR no reconocido o asistente no encontrado",
                "debug_info": {
                    "email_parsed": email,
                    "name_parsed": name,
                    "total_attendees": len(data_store.attendees)
                }
            }), 404
        
        # Validar acceso
        scan_type = scan_config.get('scan_type', 'Entrada')
        access_valid, access_message = validate_access(attendee, scan_type)
        
        if not access_valid:
            return jsonify({
                "success": False,
                "message": f"Acceso denegado: {access_message}",
                "attendee": {
                    "nombre": attendee.get('nombre'),
                    "apellido": attendee.get('apellido'),
                    "tipo": attendee.get('tipo')
                }
            }), 403
        
        # Crear registro de escaneo
        scan_data = {
            "attendee_id": attendee.get('id'),
            "scan_type": scan_type,
            "day": scan_config.get('day', 1),
            "location": scan_config.get('location', device_info.get('location', 'Móvil')),
            "scanned_by": f"móvil_{device_info.get('device_name', 'unknown')}",
            "notes": f"Escaneado desde {device_info.get('user_agent', 'app móvil')}"
        }
        
        scan_id = data_store.add_scan(scan_data)
        
        logger.info(f"Registro exitoso: {attendee.get('nombre')} {attendee.get('apellido')}")
        
        return jsonify({
            "success": True,
            "message": f"¡Acceso autorizado para {attendee.get('nombre')} {attendee.get('apellido')}!",
            "attendee": attendee,
            "scan_info": {
                "id": scan_id,
                "scan_type": scan_type,
                "day": scan_config.get('day', 1),
                "timestamp": datetime.now().isoformat(),
                "location": scan_data["location"]
            },
            "stats": data_store.get_stats()
        }), 200
        
    except Exception as e:
        logger.error(f"Error validando asistente: {e}")
        return jsonify({
            "success": False,
            "message": f"Error interno del servidor: {str(e)}"
        }), 500

@app.route('/get_stats')
def get_stats():
    """Obtener estadísticas"""
    try:
        return jsonify(data_store.get_stats()), 200
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({
            "error": f"Error obteniendo estadísticas: {str(e)}"
        }), 500

@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    """Subir y procesar archivo Excel"""
    try:
        if 'excel_file' not in request.files:
            return jsonify({
                "success": False,
                "message": "No se encontró archivo Excel"
            }), 400
        
        file = request.files['excel_file']
        
        if file.filename == '':
            return jsonify({
                "success": False,
                "message": "No se seleccionó archivo"
            }), 400
        
        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            file.save(tmp_file.name)
            temp_path = Path(tmp_file.name)
        
        # Procesar Excel
        attendees = process_excel_data(temp_path)
        
        # Limpiar archivo temporal
        temp_path.unlink()
        
        if not attendees:
            return jsonify({
                "success": False,
                "message": "No se pudieron procesar los datos del Excel"
            }), 400
        
        # Actualizar datos
        data_store.attendees = attendees
        data_store.save_attendees()
        
        # Guardar backup
        file.seek(0)
        file.save(str(EXCEL_BACKUP))
        
        logger.info(f"Excel procesado: {len(attendees)} asistentes")
        
        return jsonify({
            "success": True,
            "message": f"Excel procesado exitosamente: {len(attendees)} asistentes",
            "count": len(attendees),
            "backup_saved": True
        }), 200
        
    except Exception as e:
        logger.error(f"Error procesando Excel: {e}")
        return jsonify({
            "success": False,
            "message": f"Error procesando Excel: {str(e)}"
        }), 500

@app.route('/sync_scans', methods=['POST'])
def sync_scans():
    """Sincronizar escaneos"""
    try:
        data = request.get_json()
        scans = data.get('scans', [])
        
        # Agregar escaneos nuevos (evitar duplicados)
        existing_ids = {scan.get('id') for scan in data_store.scans}
        new_scans = [scan for scan in scans if scan.get('id') not in existing_ids]
        
        data_store.scans.extend(new_scans)
        data_store.save_scans()
        
        return jsonify({
            "success": True,
            "message": f"Sincronizados {len(new_scans)} nuevos escaneos",
            "new_scans": len(new_scans),
            "total_scans": len(data_store.scans)
        }), 200
        
    except Exception as e:
        logger.error(f"Error sincronizando escaneos: {e}")
        return jsonify({
            "success": False,
            "message": f"Error sincronizando: {str(e)}"
        }), 500

@app.route('/admin_dashboard')
def admin_dashboard():
    """Panel de administración web"""
    stats = data_store.get_stats()
    
    # Generar tabla de asistentes recientes
    recent_attendees = data_store.attendees[:10]
    attendees_table = ""
    for att in recent_attendees:
        attendees_table += f"""
        <tr>
            <td>{att.get('id', 'N/A')}</td>
            <td>{att.get('nombre', 'N/A')} {att.get('apellido', 'N/A')}</td>
            <td>{att.get('empresa', 'N/A')}</td>
            <td>{att.get('tipo', 'N/A')}</td>
            <td>{'Sí' if att.get('es_becado', False) else 'No'}</td>
        </tr>
        """
    
    # Generar tabla de escaneos recientes
    recent_scans = sorted(data_store.scans, key=lambda x: x.get('timestamp', ''), reverse=True)[:10]
    scans_table = ""
    for scan in recent_scans:
        scans_table += f"""
        <tr>
            <td>{scan.get('id', 'N/A')}</td>
            <td>{scan.get('attendee_id', 'N/A')}</td>
            <td>{scan.get('scan_type', 'N/A')}</td>
            <td>Día {scan.get('day', 'N/A')}</td>
            <td>{scan.get('timestamp', 'N/A')[:19] if scan.get('timestamp') else 'N/A'}</td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Panel de Administración - QR Congress</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; background: #f4f4f4; }}
            .header {{ background: #007bff; color: white; padding: 20px; text-align: center; }}
            .container {{ max-width: 1200px; margin: 20px auto; padding: 0 20px; }}
            .card {{ background: white; margin: 20px 0; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
            .metric {{ background: #e9ecef; padding: 20px; border-radius: 5px; text-align: center; }}
            .metric-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
            .metric-label {{ color: #666; margin-top: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f8f9fa; font-weight: bold; }}
            .refresh-btn {{ background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            .refresh-btn:hover {{ background: #218838; }}
        </style>
        <script>
            function refreshPage() {{
                location.reload();
            }}
        </script>
    </head>
    <body>
        <div class="header">
            <h1>📊 Panel de Administración QR Congress</h1>
            <button class="refresh-btn" onclick="refreshPage()">🔄 Actualizar</button>
        </div>
        
        <div class="container">
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{stats['total_attendees']}</div>
                    <div class="metric-label">Total Asistentes</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{stats['total_scans']}</div>
                    <div class="metric-label">Total Escaneos</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{stats['entry_scans']}</div>
                    <div class="metric-label">Entradas</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{stats['session_scans']}</div>
                    <div class="metric-label">Sesiones</div>
                </div>
            </div>
            
            <div class="card">
                <h3>👥 Asistentes Recientes</h3>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Nombre</th>
                            <th>Empresa</th>
                            <th>Tipo</th>
                            <th>Becado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {attendees_table}
                    </tbody>
                </table>
            </div>
            
            <div class="card">
                <h3>📱 Escaneos Recientes</h3>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Asistente</th>
                            <th>Tipo</th>
                            <th>Día</th>
                            <th>Timestamp</th>
                        </tr>
                    </thead>
                    <tbody>
                        {scans_table}
                    </tbody>
                </table>
            </div>
            
            <div class="card">
                <h3>📊 Estadísticas por Tipo</h3>
                <div class="metrics">
                    {
                        ''.join([
                            f'<div class="metric"><div class="metric-value">{count}</div><div class="metric-label">{tipo}</div></div>'
                            for tipo, count in stats.get('type_stats', {}).items()
                        ])
                    }
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
    return html

# === CONFIGURACIÓN PARA RENDER ===
if __name__ == '__main__':
    # Render proporciona el puerto mediante la variable de entorno PORT
    port = int(os.environ.get('PORT', 5000))
    
    logger.info("🚀 Iniciando Backend QR Congress en Render")
    logger.info(f"📡 Puerto: {port}")
    logger.info(f"👥 Asistentes cargados: {len(data_store.attendees)}")
    logger.info(f"📊 Escaneos cargados: {len(data_store.scans)}")
    
    # Ejecutar servidor
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,  # Siempre False en producción
        threaded=True
    )

# scanner_mobile.py
"""
App Streamlit para escanear QR desde móviles
Se conecta al servidor HTTP de la app tkinter principal
"""

import streamlit as st
import requests
import qrcode
from PIL import Image
import json
import time
import numpy as np
import socket
from io import BytesIO

# El import de cv2 fue removido ya que no es utilizado para la funcionalidad principal
# y causa errores de dependencia en Streamlit Cloud.
# Ahora la detección de QR se hará a través de una función de servidor.

# Configuración para móviles
st.set_page_config(
    page_title="📱 QR Scanner",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed"  # Sidebar cerrado en móviles
)

# CSS personalizado para móviles
st.markdown("""
<style>
    /* Optimización para móviles */
    .main {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    .stButton button {
        width: 100%;
        height: 3rem;
        font-size: 1.2rem;
        border-radius: 0.5rem;
    }
    
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-left: 5px solid #28a745;
        margin: 1rem 0;
        border-radius: 0.5rem;
        font-weight: bold;
    }
    
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-left: 5px solid #dc3545;
        margin: 1rem 0;
        border-radius: 0.5rem;
        font-weight: bold;
    }
    
    .stTextInput label {
        font-weight: bold;
        color: #333;
    }
    
    .stSelectbox label {
        font-weight: bold;
        color: #333;
    }
    
    h1 {
        text-align: center;
        color: #007bff;
    }

    h3 {
        color: #555;
    }
</style>
""", unsafe_allow_html=True)


def get_local_ip():
    """Obtener IP local del equipo"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

# === GESTIÓN DE ESTADO ===
if 'scan_result' not in st.session_state:
    st.session_state.scan_result = None
if 'last_status' not in st.session_state:
    st.session_state.last_status = {"message": "", "type": "info"}
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'server_info' not in st.session_state:
    st.session_state.server_info = {}
if 'server_url' not in st.session_state:
    st.session_state.server_url = ""
if 'server_port' not in st.session_state:
    st.session_state.server_port = ""


def display_status(message, message_type="info"):
    st.session_state.last_status = {"message": message, "type": message_type}
    st.experimental_rerun()

@st.cache_data
def get_attendee_info(url, attendee_id):
    """Obtener información de un asistente desde el servidor"""
    try:
        response = requests.get(
            f"{url}/attendee/{attendee_id}",
            headers={'X-API-Key': st.secrets["api_key"]} if "api_key" in st.secrets else {},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException as e:
        display_status(f"Error de conexión: {e}", "error")
        return None

def send_scan_to_server(url, attendee_id, scan_type, scan_day, scanned_by, location):
    """Enviar un escaneo al servidor"""
    payload = {
        'attendee_id': attendee_id,
        'scan_type': scan_type,
        'day': scan_day,
        'scanned_by': scanned_by,
        'location': location
    }
    try:
        response = requests.post(
            f"{url}/scan",
            json=payload,
            headers={'X-API-Key': st.secrets["api_key"]} if "api_key" in st.secrets else {},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Error de conexión: {e}"}

# ===========================
# INTERFAZ DE USUARIO
# ===========================

st.title("📱 Escáner Móvil QR")

# === CONEXIÓN ===
st.subheader("🔗 Configuración de Conexión")
col1, col2 = st.columns([3, 1])

with col1:
    server_url_input = st.text_input(
        "URL del Servidor",
        value=st.session_state.server_url,
        placeholder="Ej: http://192.168.1.100 o https://my-app.onrender.com"
    )
with col2:
    server_port_input = st.text_input(
        "Puerto",
        value=st.session_state.server_port,
        placeholder="Ej: 5000"
    )

st.session_state.server_url = server_url_input
st.session_state.server_port = server_port_input

if st.button("🔌 Conectar"):
    if st.session_state.server_url:
        full_url = st.session_state.server_url
        if st.session_state.server_port and not st.session_state.server_port.isspace():
            full_url = f"{full_url}:{st.session_state.server_port}"
        
        try:
            with st.spinner("Conectando..."):
                response = requests.get(f"{full_url}/health", timeout=10)
                if response.status_code == 200:
                    st.session_state.connected = True
                    st.session_state.server_info = response.json()
                    display_status("✅ Conexión exitosa. Listo para escanear.", "success")
                else:
                    st.session_state.connected = False
                    display_status("❌ Error al conectar. Servidor no responde.", "error")
        except requests.exceptions.RequestException as e:
            st.session_state.connected = False
            display_status(f"❌ Error de conexión: {e}", "error")
    else:
        display_status("❌ Por favor, ingresa una URL de servidor", "error")

if st.button("🔍 Auto-detectar IP local"):
    local_ip = get_local_ip()
    st.session_state.server_url = f"http://{local_ip}"
    st.session_state.server_port = "5000"
    st.experimental_rerun()

# === ESTADO Y OPCIONES ===
if st.session_state.connected:
    st.markdown("---")
    st.subheader("⚙️ Opciones de Escaneo")

    server_status = st.session_state.server_info.get('status', 'offline')
    server_mode = st.session_state.server_info.get('mode', 'desconocido')
    attendees_count = st.session_state.server_info.get('attendees_count', 0)
    scans_count = st.session_state.server_info.get('scans_count', 0)

    st.success(f"Estado del Servidor: **{server_status.upper()}** (Modo: {server_mode})")
    st.info(f"Asistentes cargados: {attendees_count} | Escaneos registrados: {scans_count}")

    scan_type = st.selectbox(
        "Tipo de Escaneo",
        options=st.session_state.server_info.get('scan_types', ['ENTRY', 'SESSION', 'STAND']),
        format_func=lambda x: st.session_state.server_info.get('scan_types_map', {}).get(x, x)
    )

    event_day = st.selectbox(
        "Día del Evento",
        options=st.session_state.server_info.get('event_days', [1, 2, 3])
    )

    user_type = st.selectbox(
        "Rol de Escáner",
        options=st.session_state.server_info.get('attendee_types', ['STAFF', 'EXHIBITOR']),
        format_func=lambda x: st.session_state.server_info.get('attendee_types_map', {}).get(x, x)
    )
    
    location = st.text_input("Ubicación del Escaneo", value=st.session_state.server_info.get('location', 'Entrada Principal'))

    # === ESCANER ===
    st.markdown("---")
    st.subheader("📷 Escáner QR")
    st.info("Presiona el botón de 'Escanear QR' para abrir la cámara.")

    # Usamos un text_input temporal para simular el escaneo
    attendee_id_manual = st.text_input("ID de Asistente (Escaneo Manual)", help="Puedes ingresar el ID manualmente aquí.")

    if st.button("✅ Enviar Escaneo"):
        if attendee_id_manual:
            full_url = st.session_state.server_url
            if st.session_state.server_port and not st.session_state.server_port.isspace():
                full_url = f"{full_url}:{st.session_state.server_port}"
            
            result = send_scan_to_server(full_url, attendee_id_manual, scan_type, event_day, user_type, location)
            
            if result.get("success"):
                display_status(result.get("message"), "success")
                attendee_info = get_attendee_info(full_url, attendee_id_manual)
                if attendee_info:
                    st.session_state.scan_result = attendee_info
                else:
                    st.session_state.scan_result = {"attendee_id": attendee_id_manual, "info": "Información no encontrada"}
            else:
                display_status(result.get("message"), "error")
                st.session_state.scan_result = None
        else:
            display_status("❌ Por favor, ingresa un ID para escanear.", "error")

    # Mostrar el resultado del escaneo
    if st.session_state.scan_result:
        st.markdown("---")
        st.subheader("📋 Información de Asistente")
        attendee_data = st.session_state.scan_result
        if 'attendee_id' in attendee_data:
            st.markdown(f"**ID:** {attendee_data['attendee_id']}")
        
        if 'nombre' in attendee_data and 'apellido' in attendee_data:
            st.markdown(f"**Nombre:** {attendee_data['nombre']} {attendee_data['apellido']}")
            
        if 'tipo' in attendee_data:
            st.markdown(f"**Tipo:** {attendee_data['tipo']}")
            
        if 'empresa' in attendee_data:
            st.markdown(f"**Empresa:** {attendee_data['empresa']}")
        
        st.markdown("---")
        st.markdown("### Historial de escaneos de este asistente")
        
        scans = attendee_data.get('scans', [])
        if scans:
            for scan in scans:
                st.markdown(f"- **Tipo:** {scan['scan_type']} | **Día:** {scan['day']} | **Hora:** {scan['timestamp']}")
        else:
            st.markdown("No hay escaneos previos registrados.")

# === ESTADO DE LA APLICACIÓN ===
st.markdown("---")
st.subheader("📢 Mensajes del Sistema")
if st.session_state.last_status["type"] == "success":
    st.markdown(f"<div class='success-message'>{st.session_state.last_status['message']}</div>", unsafe_allow_html=True)
elif st.session_state.last_status["type"] == "error":
    st.markdown(f"<div class='error-message'>{st.session_state.last_status['message']}</div>", unsafe_allow_html=True)
else:
    st.info(st.session_state.last_status["message"])

# ===========================
# INSTRUCCIONES DE CONEXIÓN
# ===========================
if not st.session_state.connected:
    st.markdown("---")
    st.error(f"❌ No conectado al servidor principal")
    
    st.markdown("""
    ### 🔧 Para conectarte:
    
    #### 💻 Si usas el backend local:
    1. **🖥️ Ejecuta:** `python main.py`
    2. **🌐 En tu dispositivo móvil**, ingresa la IP local de tu computadora (ej: `http://192.168.1.100`) y el puerto (ej: `5000`).
    3. **🔍 Presiona "Auto-detectar"**
    
    #### ☁️ Si usas el backend en la nube (Render):
    1. **🌐 Asegúrate de que tu backend en Render esté activo.**
    2. **📋 Copia la URL de tu servicio en Render** (ej: `https://your-app-name.onrender.com`).
    3. **🌐 Pégala en el campo "URL del Servidor"** en tu dispositivo móvil.
    4. **📱 Asegúrate de que el campo "Puerto" esté vacío.**
    
    ### 💡 URLs de ejemplo:
    - **Local:** `http://192.168.1.100:5000`
    - **Render:** `https://your-app-name.onrender.com`
    
    ### ⚠️ Si no puedes conectarte:
    - **Local:** Verifica que tu computadora y dispositivo móvil estén en la misma red y que la URL es correcta.
    - **Render:** Asegúrate de que tu aplicación de backend esté desplegada y en funcionamiento en Render.
    """)

# ===========================
# AUTO-REFRESH Y FOOTER
# ===========================
# Refrescar cada 5 segundos si está conectado
if st.session_state.connected:
    time.sleep(5)
    st.experimental_rerun()
    
st.markdown("---")
st.markdown("<p style='text-align: center; color: #888;'>Sistema de Gestión QR v2.0</p>", unsafe_allow_html=True)

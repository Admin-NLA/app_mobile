# scanner_mobile.py
"""
App Streamlit para escanear QR desde móviles
Se conecta al servidor HTTP del backend principal
"""

import streamlit as st
import requests
import qrcode
from PIL import Image
import json
import time
import cv2  # Importamos la librería OpenCV
import numpy as np
import socket

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
        border-radius: 0.5rem;
        margin-top: 1rem;
    }

    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar estado de sesión
if 'server_url' not in st.session_state:
    st.session_state.server_url = ""
if 'server_port' not in st.session_state:
    st.session_state.server_port = ""
if 'is_connected' not in st.session_state:
    st.session_state.is_connected = False
if 'connection_status' not in st.session_state:
    st.session_state.connection_status = "Desconectado"
if 'last_status_check' not in st.session_state:
    st.session_state.last_status_check = 0
if 'stats' not in st.session_state:
    st.session_state.stats = {}
if 'scan_result' not in st.session_state:
    st.session_state.scan_result = None

# Funciones de conexión
def check_connection(url, port):
    """Verificar la conexión con el backend."""
    full_url = url
    if port:
        full_url = f"{url}:{port}"

    health_url = f"{full_url}/health"
    try:
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            st.session_state.is_connected = True
            st.session_state.connection_status = "Conectado"
            st.session_state.server_info = response.json()
            return True, f"Conectado a: {full_url}"
        else:
            st.session_state.is_connected = False
            st.session_state.connection_status = f"Error HTTP: {response.status_code}"
            return False, st.session_state.connection_status
    except requests.exceptions.RequestException as e:
        st.session_state.is_connected = False
        st.session_state.connection_status = f"Error de conexión: {e}"
        return False, st.session_state.connection_status

def get_stats(url, port):
    """Obtener estadísticas del servidor."""
    full_url = url
    if port:
        full_url = f"{url}:{port}"
    stats_url = f"{full_url}/stats"
    try:
        response = requests.get(stats_url, timeout=5)
        if response.status_code == 200:
            st.session_state.stats = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al obtener estadísticas: {e}")
        st.session_state.stats = {}

def get_local_ip():
    """Obtener la IP local de la máquina."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# Función para escanear y enviar datos
def scan_and_send(qr_code, scan_type, day, user_id, location):
    """Simular el escaneo y enviar datos al backend."""
    full_url = st.session_state.server_url
    if st.session_state.server_port:
        full_url = f"{st.session_state.server_url}:{st.session_state.server_port}"

    try:
        response = requests.post(
            f"{full_url}/scan_qr",
            json={
                "attendee_id": qr_code,
                "scan_type": scan_type,
                "day": day,
                "scanned_by": user_id,
                "location": location
            },
            timeout=10
        )
        if response.status_code == 200:
            st.session_state.scan_result = response.json()
        else:
            st.session_state.scan_result = {"success": False, "message": f"Error del servidor: {response.status_code}"}
    except requests.exceptions.RequestException as e:
        st.session_state.scan_result = {"success": False, "message": f"Error de red: {e}"}

# Lógica de la interfaz de usuario
st.title("📱 Escáner de Códigos QR")
st.markdown("---")

# Secciones de la interfaz
with st.sidebar:
    st.header("⚙️ Configuración")
    st.session_state.server_url = st.text_input("URL del Servidor", value=st.session_state.server_url)
    st.session_state.server_port = st.text_input("Puerto", value=st.session_state.server_port)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Auto-detectar IP local"):
            st.session_state.server_url = get_local_ip()
            st.session_state.server_port = "5000"
            st.experimental_rerun()
    with col2:
        if st.button("Conectar"):
            check_connection(st.session_state.server_url, st.session_state.server_port)
            st.experimental_rerun()

# Mostrar estado de conexión
status_placeholder = st.empty()
if st.session_state.is_connected:
    status_placeholder.success(f"Estado: {st.session_state.connection_status} ✅")
    st.markdown(f"**Backend:** {st.session_state.server_url}:{st.session_state.server_port}")
else:
    status_placeholder.error(f"Estado: {st.session_state.connection_status} ❌")

# Panel de configuración de escaneo (visible solo si está conectado)
if st.session_state.is_connected:
    st.markdown("---")
    st.header("⚙️ Configuración de Escaneo")

    with st.form("scan_config_form"):
        col1, col2 = st.columns(2)
        with col1:
            scan_type = st.selectbox(
                "Tipo de Escaneo",
                options=["ENTRY", "SESSION", "STAND"],
                format_func=lambda x: {"ENTRY": "Entrada al Evento", "SESSION": "Acceso a Sesión", "STAND": "Visita a Stand"}[x]
            )
        with col2:
            event_day = st.number_input("Día del Evento", min_value=1, value=1, step=1)

        st.text_input("Usuario (ID o Nombre)", value="scanner_user", key="scanner_user")
        st.text_input("Ubicación (Opcional)", value="Entrada Principal", key="scan_location")

        submitted = st.form_submit_button("Guardar Configuración")
        if submitted:
            st.success("Configuración de escaneo guardada.")

    st.markdown("---")

    # Simulador de escaneo (para pruebas)
    st.header("🔍 Simular Escaneo")
    col3, col4 = st.columns([3, 1])
    with col3:
        attendee_id_to_scan = st.text_input("ID de Asistente a Escanear", help="Ej: 0001")
    with col4:
        if st.button("Escanear"):
            if attendee_id_to_scan:
                scan_and_send(
                    attendee_id_to_scan,
                    scan_type,
                    event_day,
                    st.session_state.scanner_user,
                    st.session_state.scan_location
                )
            else:
                st.error("Por favor, introduce un ID para escanear.")

    # Mostrar resultado del escaneo
    if st.session_state.scan_result:
        result = st.session_state.scan_result
        if result.get("success"):
            attendee = result.get("attendee")
            scan_info = result.get("scan")
            st.success(f"✅ ¡Escaneo Exitoso! {result.get('message')}")
            st.info(f"**Asistente:** {attendee.get('nombre', '')} {attendee.get('apellido', '')}")
            st.info(f"**Tipo:** {attendee.get('tipo', '')}")
            st.info(f"**Escaneado por:** {scan_info.get('scanned_by', '')}")
        else:
            st.error(f"❌ Escaneo Fallido: {result.get('message')}")

    # Auto-refrescar estadísticas
    # No es necesario un bucle, Streamlit se refresca con las interacciones.
    # Usamos un botón para refrescar manualmente
    st.markdown("---")
    st.header("📊 Estadísticas del Servidor")
    if st.button("Refrescar Estadísticas"):
        get_stats(st.session_state.server_url, st.session_state.server_port)

    # Mostrar estadísticas
    stats = st.session_state.stats
    if stats:
        st.subheader(f"Total Asistentes: {stats.get('total_attendees', 0)}")
        st.subheader(f"Total Escaneos: {stats.get('total_scans', 0)}")
        
        st.markdown("#### Escaneos Recientes")
        if stats.get('recent_scans'):
            for scan in stats.get('recent_scans'):
                st.write(f"- **{scan.get('attendee_name', 'Desconocido')}** ({scan.get('scan_type')}) a las {scan.get('timestamp').split('T')[1].split('.')[0]}")
        else:
            st.write("No hay escaneos recientes.")

        st.markdown("---")

# Mensaje para cuando no hay conexión
else:
    st.warning("No estás conectado al servidor principal.")
    
    st.markdown("""
    ### 🔧 Para conectarte:
    
    #### 💻 Si usas el backend local:
    1. **🖥️ Ejecuta:** `python main.py`
    2. **🌐 En tu dispositivo móvil**, ingresa la IP local de tu computadora (ej: `http://192.168.1.100`) y el puerto (ej: `5000`).
    3. **🔍 Presiona "Conectar"**
    
    #### ☁️ Si usas el backend en la nube (Render):
    1. **🌐 Asegúrate de que tu backend en Render esté activo.**
    2. **📋 Copia la URL de tu servicio en Render** (ej: `https://your-app-name.onrender.com`).
    3. **🌐 Pégala en el campo "URL del Servidor"** en tu dispositivo móvil.
    4. **📱 Asegúrate de que el campo "Puerto" esté vacío.**
    
    ### 💡 URLs de ejemplo:
    - **Local:** `http://192.168.1.100` + puerto `5000`
    - **Render:** `https://your-app-name.onrender.com` + puerto vacío
    
    ### ⚠️ Si no puedes conectarte:
    - **Local:** Verifica que tu computadora y dispositivo móvil estén en la misma red y que la URL es correcta.
    - **Render:** Asegúrate de que tu aplicación de backend esté desplegada y en funcionamiento en Render.
    """)

# ===========================
# AUTO-REFRESH Y FOOTER
# ===========================

# Recargar cada 60 segundos
time.sleep(60)
st.experimental_rerun()

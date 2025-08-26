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

    .info-message {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 1rem;
    }
    
    .st-emotion-cache-1j71w2w {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 10px;
        text-align: center;
        font-size: 0.8rem;
        color: #777;
    }
    .st-emotion-cache-12fmwvp {
        flex-direction: column-reverse; /* Pone los botones de arriba a abajo en móvil */
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# === VARIABLES DE SESIÓN Y ESTADO ===
if 'connection_status' not in st.session_state:
    st.session_state.connection_status = "disconnected"
if 'last_scan_result' not in st.session_state:
    st.session_state.last_scan_result = {}
if 'server_info' not in st.session_state:
    st.session_state.server_info = {}
if 'backend_url' not in st.session_state:
    st.session_state.backend_url = ""

# === LÓGICA DE CONEXIÓN Y SINCRONIZACIÓN ===
def check_connection(url: str):
    """Verificar la conexión con el servidor y obtener datos iniciales."""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        response.raise_for_status()
        st.session_state.connection_status = "connected"
        st.session_state.server_info = response.json()
        return True
    except requests.exceptions.RequestException:
        st.session_state.connection_status = "disconnected"
        return False

def get_local_ip():
    """Obtener la IP local del dispositivo."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def send_scan_to_backend(attendee_id: str, scan_type: str, user: str, location: str):
    """Enviar el ID del QR al backend para su validación."""
    try:
        response = requests.post(
            f"{st.session_state.backend_url}/validate_attendee",
            json={
                "attendee_id": attendee_id,
                "scan_type": scan_type,
                "user_id": user,
                "location": location
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error de conexión: {str(e)}")
        return None

# === INTERFAZ DE USUARIO ===
st.title("📱 QR Scanner")

st.markdown("---")
st.subheader("🔧 Configuración de Conexión")
col_conn_1, col_conn_2 = st.columns([3, 1])

with col_conn_1:
    backend_url = st.text_input(
        "URL del Servidor",
        value=st.session_state.backend_url,
        placeholder="Ej: https://yourapp.onrender.com"
    )
    st.session_state.backend_url = backend_url

with col_conn_2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔌 Conectar"):
        if backend_url:
            check_connection(backend_url)
            if st.session_state.connection_status == "connected":
                st.success("✅ Conectado al servidor principal.")
            else:
                st.error("❌ No se pudo conectar al servidor.")
        else:
            st.error("Por favor, ingresa una URL.")

# Muestra la IP local sugerida solo si no está conectado
if st.session_state.connection_status == "disconnected":
    st.info(f"💡 **IP Local sugerida:** `{get_local_ip()}:5000` (si usas el backend local)")

st.markdown("---")

if st.session_state.connection_status == "connected":
    st.subheader("📊 Estado del Servidor")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Asistentes",
            st.session_state.server_info.get('attendees_count', 'N/A')
        )
    with col2:
        st.metric(
            "Escaneos",
            st.session_state.server_info.get('scans_count', 'N/A')
        )
    st.markdown("---")
    
    st.subheader("📋 Escanear QR")
    
    # Configuración de escaneo
    scan_mode_options = list(st.session_state.server_info.get('SCAN_TYPES', {}).keys())
    scan_type = st.selectbox(
        "Tipo de Escaneo",
        options=scan_mode_options if scan_mode_options else ['ENTRY', 'SESSION', 'STAND'],
        format_func=lambda x: st.session_state.server_info.get('SCAN_TYPES', {}).get(x, x)
    )
    
    col_user, col_loc = st.columns(2)
    with col_user:
        scan_user = st.text_input("Usuario (Ej. Staff)", value="Staff")
    with col_loc:
        scan_location = st.text_input("Ubicación", value="Entrada Principal")
    
    # === Botones de escaneo ===
    col_scan_1, col_scan_2 = st.columns(2)
    with col_scan_1:
        # Nota: La cámara de Streamlit se habilita solo en el entorno cloud y requiere HTTPS.
        # En local, puede que no funcione.
        camera_input = st.camera_input("Escanear con Cámara")
    
    with col_scan_2:
        qr_input = st.text_input("O ingresa el ID manualmente", placeholder="Ej: 0001")
        if st.button("🔍 Validar ID"):
            if qr_input:
                result = send_scan_to_backend(qr_input, scan_type, scan_user, scan_location)
                if result:
                    st.session_state.last_scan_result = result
                    check_connection(st.session_state.backend_url)
                
# Muestra el resultado del último escaneo
result = st.session_state.last_scan_result
if result:
    if result["status"] == "success":
        st.success(f"✅ {result['message']}")
        st.json(result['attendee'])
    elif result["status"] == "error":
        st.error(f"❌ {result['message']}")
    else:
        st.info(f"ℹ️ {result['message']}")

# Lógica para procesar la imagen de la cámara
if camera_input:
    try:
        # Convertir bytes de la cámara a una imagen de OpenCV
        image_np = np.frombuffer(camera_input.read(), np.uint8)
        frame = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

        # Usar el detector de códigos QR de OpenCV
        qr_detector = cv2.QRCodeDetector()
        data, _, _ = qr_detector.detectAndDecode(frame)

        if data:
            with st.spinner("Validando QR escaneado..."):
                result = send_scan_to_backend(data, scan_type, scan_user, scan_location)
                if result:
                    st.session_state.last_scan_result = result
                    check_connection(st.session_state.backend_url)

    except Exception as e:
        # El error de OpenCV ocurre aquí en Streamlit Cloud,
        # pero la aplicación sigue funcionando para el escaneo manual
        st.error(f"Error procesando imagen: {e}")

if st.session_state.connection_status == "disconnected":
    st.error("❌ No conectado al servidor principal. Por favor, revisa la URL.")
    
    st.markdown("""
    ---
    ### 🔧 Para conectarte:
    
    #### 💻 Si usas el backend local:
    1. **🖥️ Ejecuta:** `python main.py`
    2. **🌐 En tu dispositivo móvil**, ingresa la IP local de tu computadora (ej: `http://192.168.1.100`) y el puerto (ej: `5000`).
    3. **🔍 Presiona "Conectar"**
    
    #### ☁️ Si usas el backend en la nube (Render):
    1. **🌐 Asegúrate de que tu backend en Render esté activo.**
    2. **📋 Copia la URL de tu servicio en Render** (ej: `https://your-app-name.onrender.com`).
    3. **🌐 Pégala en el campo "URL del Servidor"** en tu dispositivo móvil.
    4. **🔍 Presiona "Conectar"**
    
    ### 💡 URLs de ejemplo:
    - **Local:** `http://192.168.1.100:5000`
    - **Render:** `https://your-app-name.onrender.com`
    
    ### ⚠️ Si no puedes conectarte:
    - **Local:** Verifica que tu computadora y dispositivo móvil estén en la misma red y que la URL es correcta.
    - **Render:** Asegúrate de que tu aplicación de backend esté desplegada y en funcionamiento en Render.
    """)

# Auto-refrescar si está conectado
if st.session_state.connection_status == "connected":
    st.markdown(f'<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)

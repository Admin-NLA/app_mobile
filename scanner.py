# scanner.py
"""
App Streamlit para escanear QR desde móviles
Se conecta al servidor HTTP de la app principal en Render.com
"""

import streamlit as st
import requests
import json
import time
import os
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
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
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
    
    h1 {
        text-align: center;
        color: #333;
    }
    
    h2 {
        text-align: center;
        color: #555;
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
if 'scan_result' not in st.session_state:
    st.session_state.scan_result = {"status": "info", "message": "Esperando escaneo..."}
if 'connection_status' not in st.session_state:
    st.session_state.connection_status = "disconnected"
if 'stats' not in st.session_state:
    st.session_state.stats = {}

# === FUNCIONES DE CONEXIÓN ===
@st.cache_data(ttl=60)
def get_backend_url():
    """Obtener la URL del backend desde una variable de entorno o por defecto."""
    return os.getenv('RENDER_BACKEND_URL', 'https://qr-scanner-mobile.onrender.com')

def check_connection(url: str):
    """Verificar la conexión con el servidor."""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        response.raise_for_status()
        st.session_state.connection_status = "connected"
        st.session_state.stats = response.json()
        return True
    except requests.exceptions.RequestException as e:
        st.session_state.connection_status = "disconnected"
        return False

def get_local_ip():
    """Obtener la IP local del dispositivo."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # noinspection PyUnresolvedReferences
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# === LÓGICA DE ESCANEO ===
def send_scan_to_backend(attendee_id: str, scan_type: str, user: str, location: str):
    """Enviar el ID del QR al backend para su validación."""
    backend_url = st.session_state.get('backend_url', get_backend_url())
    try:
        response = requests.post(
            f"{backend_url}/validate_attendee",
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
        st.session_state.scan_result = {
            "status": "error",
            "message": f"Error de conexión: {str(e)}"
        }
        return None

def process_scan(attendee_id: str, scan_type: str, user: str, location: str):
    """Procesar un escaneo y mostrar el resultado."""
    with st.spinner("Validando QR..."):
        result = send_scan_to_backend(attendee_id, scan_type, user, location)
        
        if result:
            st.session_state.scan_result = result
            # Actualizar estadísticas en segundo plano
            check_connection(st.session_state.get('backend_url', get_backend_url()))
            
# === INTERFAZ DE USUARIO ===
st.title("📱 QR Scanner Móvil")
st.markdown("---")

# Formulario para configuración
with st.sidebar:
    st.header("🔧 Configuración")
    
    st.subheader("Conexión del Servidor")
    backend_url = st.text_input(
        "URL del Servidor",
        value=get_backend_url(),
        placeholder="Ej: https://backend.onrender.com"
    )
    st.session_state.backend_url = backend_url
    
    st.markdown(f"**IP Local sugerida:** `{get_local_ip()}`")
    st.markdown("---")
    
    st.subheader("Modo de Escaneo")
    scan_mode_options = list(st.session_state.stats.get('SCAN_TYPES', {}).keys())
    scan_type = st.selectbox(
        "Tipo de Escaneo",
        options=scan_mode_options if scan_mode_options else ['ENTRY', 'SESSION', 'STAND'],
        format_func=lambda x: st.session_state.stats.get('SCAN_TYPES', {}).get(x, x)
    )
    
    scan_user = st.text_input("Usuario (Ej. Staff)", value="Staff")
    scan_location = st.text_input("Ubicación", value="Entrada Principal")

# Secciones principales
st.subheader("Estadísticas del Servidor")
col1, col2 = st.columns(2)
with col1:
    st.metric(
        "Asistentes",
        st.session_state.stats.get('attendees_count', 'N/A')
    )
with col2:
    st.metric(
        "Escaneos",
        st.session_state.stats.get('scans_count', 'N/A')
    )

st.markdown("---")

st.subheader("Escanear Código QR")

# Entrada para el ID del QR
qr_input = st.text_input("Ingresar ID del Asistente", placeholder="Ej: 0001")

if st.button("🔍 Validar QR"):
    if qr_input:
        process_scan(qr_input, scan_type, scan_user, scan_location)
    else:
        st.session_state.scan_result = {"status": "error", "message": "Por favor, ingresa un ID."}

# Mostrar el resultado del escaneo
result = st.session_state.scan_result
if result["status"] == "success":
    st.success(f"✅ {result['message']}")
    st.json(result['attendee'])
elif result["status"] == "error":
    st.error(f"❌ {result['message']}")
else:
    st.info(f"ℹ️ {result['message']}")

st.markdown("---")

# Botón para refrescar
if st.button("🔄 Actualizar Conexión"):
    check_connection(st.session_state.get('backend_url', get_backend_url()))
    if st.session_state.connection_status == "connected":
        st.success("✅ Conectado al servidor principal.")
    else:
        st.error("❌ No se pudo conectar al servidor principal.")

# Footer
st.markdown("<p style='text-align: center; color: #aaa;'>Powered by Streamlit</p>", unsafe_allow_html=True)

# Auto-refresh
if st.session_state.connection_status != "connected":
    st.warning("No conectado al servidor. Por favor, verifica la URL.")
else:
    # Este bloque de código invisible actualiza la página cada 30 segundos
    # para refrescar las estadísticas.
    st.markdown(f'<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)

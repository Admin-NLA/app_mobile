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
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 2px solid #c3e6cb;
        margin: 1rem 0;
        font-size: 1.1rem;
    }
    
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 2px solid #f5c6cb;
        margin: 1rem 0;
        font-size: 1.1rem;
    }
    
    .info-message {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #bee5eb;
        margin: 1rem 0;
    }
    
    /* Hacer botones más táctiles */
    .stButton button:active {
        transform: scale(0.95);
    }
    
    /* Mejorar legibilidad en móviles */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        line-height: 1.2;
    }
    
    /* Espaciado mejor para pantallas pequeñas */
    .stColumns > div {
        padding: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ===========================
# FUNCIONES AUXILIARES
# ===========================

@st.cache_data(ttl=10)  # Cache por 10 segundos
def test_connection(host, port=5000):
    """Probar conexión con el servidor tkinter"""
    try:
        # Detectar si es una URL de ngrok o local
        if 'onrender.com' in host or 'localhost' in host:
            # Para URLs de Render o localhost, usar la URL directamente sin puerto
            if host.startswith('http'):
                url = f"{host}/health"
            else:
                url = f"https://{host}/health"
        else:
            # Para IPs locales, usar http y puerto específico
            url = f"http://{host}:{port}/health"
        
        response = requests.get(url, timeout=5)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except Exception as e:
        return False, None

def send_qr_to_server(host, port, qr_data, device_info):
    """Enviar QR al servidor para validación"""
    try:
        # Detectar si es una URL de Render o local
        if 'onrender.com' in host or 'localhost' in host:
            if host.startswith('http'):
                url = f"{host}/validate_attendee"
            else:
                url = f"https://{host}/validate_attendee"
        else:
            url = f"http://{host}:{port}/validate_attendee"
        
        response = requests.post(
            url,
            json={
                'qr_data': qr_data,
                'device_info': device_info
            },
            timeout=10
        )
        
        return True, response.json()
    
    except requests.exceptions.Timeout:
        return False, {'error': '⏰ Timeout - El servidor no responde'}
    except requests.exceptions.ConnectionError:
        return False, {'error': '🔌 Error de conexión - Verifica que el servidor esté activo'}
    except Exception as e:
        return False, {'error': f'🔥 Error: {str(e)}'}

@st.cache_data(ttl=30)  # Cache por 30 segundos
def get_server_stats(host, port=5000):
    """Obtener estadísticas del servidor"""
    try:
        # Detectar si es una URL de Render o local
        if 'onrender.com' in host or 'localhost' in host:
            if host.startswith('http'):
                url = f"{host}/get_stats"
            else:
                url = f"https://{host}/get_stats"
        else:
            url = f"http://{host}:{port}/get_stats"
            
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def decode_qr_from_image(image):
    """Detectar y decodificar QR de una imagen usando OpenCV"""
    try:
        # Convertir la imagen de PIL a un array de NumPy (formato BGR para OpenCV)
        img_array = np.array(image.convert('RGB'))
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Inicializar el detector de QR de OpenCV
        qr_detector = cv2.QRCodeDetector()
        
        # Detectar y decodificar el código QR
        qr_data, points, _ = qr_detector.detectAndDecode(img_bgr)
        results = []
        if qr_data:
            results.append({
                'data': qr_data,
                'type': 'QRCODE',  # OpenCV no da el tipo, lo ponemos fijo
                'rect': None       # OpenCV no da un objeto rect, lo dejamos como None
            })
        return results
    except Exception as e:
        st.error(f"Error detectando QR con OpenCV: {str(e)}")
        return []

def get_device_info():
    """Obtener información del dispositivo móvil"""
    return {
        'device_name': 'Móvil Streamlit',
        'location': 'Scanner Móvil',
        'user_agent': 'Streamlit Mobile Scanner',
        'timestamp': time.time()
    }
    
def auto_detect_server():
    """Auto-detectar servidor en la red local (solo WiFi local)"""
    try:
        # Obtener IP local del móvil
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Verificar si estamos en una red local
        if not (local_ip.startswith('192.168.') or local_ip.startswith('10.') or local_ip.startswith('172.')):
            return None, "No estás en una red WiFi local"
        
        # Obtener rango de red
        base_ip = ".".join(local_ip.split(".")[:-1]) + "."
        
        # Probar IPs comunes en la red local (ej. 192.168.1.1, 192.168.1.100)
        # Se pueden ajustar estos rangos según la red
        test_ips = [f"{base_ip}{i}" for i in [1, 100, 101, 102, 103, 104, 105]]
        
        for ip in test_ips:
            st.info(f"🔍 Probando conexión con {ip}...")
            try:
                response = requests.get(f"http://{ip}:5000/health", timeout=1)
                if response.status_code == 200:
                    return ip, "Servidor local encontrado"
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                continue
        
        return None, "No se encontró ningún servidor local"
        
    except Exception as e:
        return None, f"Error en auto-detección: {str(e)}"

# ===========================
# INTERFAZ DE USUARIO
# ===========================

st.title("📱 Escáner de Códigos QR")
st.subheader("Conéctate y escanea para registrar asistentes")

# Estado de la conexión
connection_status = st.empty()

# Input del servidor
server_host = st.text_input(
    "URL del Servidor", 
    placeholder="Ej: https://yourapp.onrender.com o 192.168.1.100",
    key='server_host'
)

# Input del puerto
server_port = st.text_input(
    "Puerto (dejar vacío para Render)",
    placeholder="Ej: 5000",
    value="5000",
    key='server_port'
)

# Botones de acción
col1, col2 = st.columns(2)
with col1:
    if st.button("🔌 Conectar", type="primary"):
        with st.spinner("Probando conexión..."):
            host = server_host.strip()
            port = int(server_port) if server_port else 80
            
            is_connected, server_info = test_connection(host, port)
            
            if is_connected:
                st.session_state.is_connected = True
                st.session_state.host = host
                st.session_state.port = port
                st.session_state.server_info = server_info
                st.success(f"✅ Conectado a {host}")
            else:
                st.session_state.is_connected = False
                st.session_state.host = ""
                st.session_state.port = ""
                st.error("❌ No se pudo conectar. Verifica la URL/IP y puerto.")
with col2:
    if st.button("🔍 Auto-detectar Servidor Local"):
        with st.spinner("Buscando servidor en tu red local..."):
            host, message = auto_detect_server()
            if host:
                st.session_state.is_connected = True
                st.session_state.host = host
                st.session_state.port = 5000
                st.session_state.server_info = None
                st.success(f"✅ Servidor local encontrado en: {host}")
                st.warning("Para usar en producción, se recomienda una URL pública de Render.")
            else:
                st.session_state.is_connected = False
                st.session_state.host = ""
                st.session_state.port = ""
                st.error(f"❌ Auto-detección fallida. {message}")

st.divider()

# Sección de escaneo
if st.session_state.get('is_connected'):
    st.subheader("📸 Escanear QR")
    
    # Mostrar estadísticas del servidor
    stats = get_server_stats(st.session_state.host, st.session_state.port)
    if stats:
        st.info(
            f"👥 **Asistentes cargados:** {stats.get('total_attendees', 0)} | "
            f"✅ **Registros:** {stats.get('total_scans', 0)} | "
            f"📊 **Tasa:** {stats.get('scan_rate', 0):.2f}%"
        )
    
    # Cargar foto del QR
    uploaded_file = st.camera_input("Toma una foto del código QR")
    
    if uploaded_file is not None:
        try:
            image = Image.open(uploaded_file)
            
            # Decodificar el QR desde la imagen
            decoded_qrs = decode_qr_from_image(image)
            
            if decoded_qrs:
                # Solo procesamos el primer QR encontrado
                qr_data = decoded_qrs[0]['data']
                
                with st.spinner("Enviando QR al servidor..."):
                    success, response_data = send_qr_to_server(
                        st.session_state.host,
                        st.session_state.port,
                        qr_data,
                        get_device_info()
                    )
                
                if success:
                    if response_data.get('status') == 'success':
                        attendee_data = response_data.get('attendee', {})
                        st.success(
                            f"✅ ¡Registro exitoso! "
                            f"Asistente: **{attendee_data.get('nombre', '')} {attendee_data.get('apellido', '')}**"
                        )
                    else:
                        st.error(f"❌ Error del servidor: {response_data.get('error', 'Error desconocido')}")
                else:
                    st.error(f"❌ No se pudo registrar el QR: {response_data.get('error', 'Error de conexión')}")
            else:
                st.warning("⚠️ No se detectó un código QR en la imagen. Intenta de nuevo.")
        
        except Exception as e:
            st.error(f"❌ Error procesando la imagen: {str(e)}")

else:
    # Instrucciones de conexión si no está conectado
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
if st.session_state.get('is_connected'):
    st.markdown("---")
    st.info("💡 **Conectado**. Esta página se actualizará automáticamente cada 30 segundos para mostrar las últimas estadísticas.")
    time.sleep(30)
    st.experimental_rerun()
else:
    st.markdown("---")
    st.info("⚠️ **Desconectado**. No se mostrarán estadísticas.")

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
        if 'ngrok.io' in host or 'ngrok.app' in host:
            # Para ngrok, usar https y puerto estándar
            if not host.startswith('http'):
                url = f"https://{host}/health"
            else:
                url = f"{host}/health"
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
        # Detectar si es una URL de ngrok o local
        if 'ngrok.io' in host or 'ngrok.app' in host:
            # Para ngrok, usar https y puerto estándar
            if not host.startswith('http'):
                url = f"https://{host}/validate_attendee"
            else:
                url = f"{host}/validate_attendee"
        else:
            # Para IPs locales, usar http y puerto específico
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
        # Detectar si es una URL de ngrok o local
        if 'ngrok.io' in host or 'ngrok.app' in host:
            if not host.startswith('http'):
                url = f"https://{host}/get_stats"
            else:
                url = f"{host}/get_stats"
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
                'type': 'QRCODE', # OpenCV no da el tipo, lo ponemos fijo
                'rect': None # OpenCV no da un objeto rect, lo dejamos como None
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
        if not (local_ip.startswith('192.168.') or 
                local_ip.startswith('10.') or 
                local_ip.startswith('172.')):
            return None, "No estás en una red WiFi local"
        
        # Obtener rango de red
        base_ip = ".".join(local_ip.split(".")[:-1]) + "."
        
        # IPs comunes a probar (limitado para ser más rápido)
        common_ips = [f"{base_ip}{i}" for i in [1, 100, 101, 102, 103, 104, 105]]
        
        for test_ip in common_ips:
            is_connected, health_data = test_connection(test_ip, 5000)
            if is_connected:
                return test_ip, health_data
                
        return None, "No se encontró servidor en la red local"
        
    except Exception as e:
        return None, f"Error en auto-detección: {str(e)}"

# ===========================
# ESTADO DE LA APLICACIÓN
# ===========================

# Inicializar session state
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'server_host' not in st.session_state:
    st.session_state.server_host = ""
if 'scan_history' not in st.session_state:
    st.session_state.scan_history = []
if 'last_connection_check' not in st.session_state:
    st.session_state.last_connection_check = 0

# ===========================
# INTERFAZ PRINCIPAL
# ===========================

# Título principal con emoji llamativo
st.title("📱 QR Scanner Móvil")
st.markdown("### 🔗 Conectar al Sistema Principal")

# ===========================
# CONFIGURACIÓN DE CONEXIÓN
# ===========================

with st.expander("⚙️ Configuración del Servidor", expanded=not st.session_state.connected):
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        server_host = st.text_input(
            "🌐 Servidor Principal",
            value=st.session_state.server_host or "192.168.1.100",
            placeholder="192.168.1.100 o abc123.ngrok.io",
            help="IP local (misma WiFi) o URL pública de ngrok (acceso remoto)"
        )
    
    with col2:
        server_port = st.number_input(
            "Puerto",
            value=5000,
            min_value=1000,
            max_value=9999
        )

    # Botones de conexión
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Probar Conexión", use_container_width=True):
            with st.spinner("🔄 Conectando..."):
                is_connected, health_data = test_connection(server_host, server_port)
                
                if is_connected:
                    st.session_state.connected = True
                    st.session_state.server_host = server_host
                    st.success("✅ ¡Conexión exitosa!")
                    
                    if health_data:
                        st.info(f"""
                        **Estado del Servidor:**
                        - 👥 Asistentes: {health_data.get('attendees_loaded', 0)}
                        - 📊 Escaneos: {health_data.get('scans_count', 0)}
                        - ⏰ Última actualización: {health_data.get('timestamp', 'N/A')[:19]}
                        """)
                else:
                    st.session_state.connected = False
                    st.error("❌ No se puede conectar")
    
    with col2:
        if st.button("🔄 Auto-detectar", use_container_width=True):
            with st.spinner("🔍 Buscando servidor local..."):
                found_ip, result = auto_detect_server()
                
                if found_ip:
                    st.session_state.server_host = found_ip
                    st.session_state.connected = True
                    st.success(f"✅ ¡Servidor encontrado en {found_ip}!")
                else:
                    st.warning(f"⚠️ {result}")
                    st.info("💡 **Sugerencias:**\n- Para WiFi local: verifica que la PC esté en la misma red\n- Para acceso remoto: usa la URL de ngrok manualmente")
    
    with col3:
        if st.button("❌ Desconectar", use_container_width=True):
            st.session_state.connected = False
            st.session_state.server_host = ""
            st.info("🔌 Desconectado del servidor")

# ===========================
# VERIFICACIÓN DE CONEXIÓN AUTOMÁTICA
# ===========================

# Verificar conexión cada 15 segundos si hay un host configurado
current_time = time.time()
if current_time - st.session_state.last_connection_check > 15:
    if st.session_state.server_host:
        is_connected, _ = test_connection(st.session_state.server_host, server_port)
        st.session_state.connected = is_connected
        st.session_state.last_connection_check = current_time

# ===========================
# ESTADO DE CONEXIÓN Y DASHBOARD
# ===========================

if st.session_state.connected:
    st.success(f"🔗 Conectado a {st.session_state.server_host}:{server_port}")
    
    # Mostrar estadísticas del servidor
    stats = get_server_stats(st.session_state.server_host, server_port)
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("👥 Asistentes", stats.get('total_attendees', 0))
        with col2:
            st.metric("🚪 Entradas", stats.get('entry_scans', 0))
        with col3:
            st.metric("🎯 Sesiones", stats.get('session_scans', 0))
        with col4:
            st.metric("🛍️ Stands", stats.get('stand_scans', 0))
    
    st.markdown("---")
    
    # ===========================
    # SECCIÓN DE ESCANEO PRINCIPAL
    # ===========================
    
    st.subheader("📸 Escanear Código QR")
    
    # Instrucciones claras
    st.info("👆 **Instrucciones:** Usa la cámara para capturar el código QR del asistente. El sistema validará automáticamente la información.")
    
    # Pestañas para diferentes métodos de escaneo
    tab1, tab2, tab3 = st.tabs(["📷 Cámara en Vivo", "📁 Subir Imagen", "📊 Historial"])
    
    with tab1:
        st.markdown("**🔴 Captura en tiempo real**")
        
        # Captura con cámara - optimizada para móviles
        camera_input = st.camera_input("Enfocar al código QR y tomar foto", key="camera_live")
        
        if camera_input is not None:
            # Mostrar imagen capturada con tamaño optimizado para móvil
            image = Image.open(camera_input)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(image, caption="📸 Imagen capturada", use_column_width=True)
            
            with st.spinner("🔍 Analizando código QR..."):
                # Detectar QRs en la imagen
                qr_results = decode_qr_from_image(image)
                
                if qr_results:
                    st.success(f"🎯 ¡{len(qr_results)} código(s) QR detectado(s)!")
                    
                    for i, qr_result in enumerate(qr_results):
                        qr_data = qr_result['data']
                        
                        with st.expander(f"📱 QR #{i+1} - Ver contenido", expanded=True):
                            st.code(qr_data[:200] + ("..." if len(qr_data) > 200 else ""))
                        
                        # Botón grande para validar
                        if st.button(
                            f"✅ VALIDAR ASISTENTE #{i+1}", 
                            key=f"validate_live_{i}",
                            use_container_width=True,
                            type="primary"
                        ):
                            with st.spinner("⏳ Validando con el servidor..."):
                                success, result = send_qr_to_server(
                                    st.session_state.server_host,
                                    server_port,
                                    qr_data,
                                    get_device_info()
                                )
                                
                                # Guardar en historial
                                scan_record = {
                                    'timestamp': time.time(),
                                    'qr_data': qr_data[:50] + "...",
                                    'success': success,
                                    'result': result
                                }
                                st.session_state.scan_history.insert(0, scan_record)
                                
                                # Mantener solo últimos 10 registros
                                if len(st.session_state.scan_history) > 10:
                                    st.session_state.scan_history = st.session_state.scan_history[:10]
                                
                                if success and result.get('success'):
                                    # ✅ VALIDACIÓN EXITOSA
                                    attendee = result.get('attendee', {})
                                    scan_info = result.get('scan_info', {})
                                    
                                    st.markdown(f"""
                                    <div class="success-message">
                                        <h3>✅ ACCESO AUTORIZADO</h3>
                                        <h4>👤 {attendee.get('nombre', 'N/A')} {attendee.get('apellido', 'N/A')}</h4>
                                        
                                        <p><strong>🏢 Empresa:</strong> {attendee.get('empresa', 'N/A')}</p>
                                        <p><strong>🎫 Tipo de pase:</strong> {attendee.get('tipo', 'N/A')}</p>
                                        <p><strong>🆔 ID:</strong> {attendee.get('id', 'N/A')}</p>
                                        
                                        <hr>
                                        <p><strong>📊 Registro:</strong> {scan_info.get('scan_type', 'N/A').title()}</p>
                                        <p><strong>📅 Día:</strong> {scan_info.get('day', 'N/A')}</p>
                                        <p><strong>📍 Ubicación:</strong> {scan_info.get('location', 'Móvil')}</p>
                                        
                                        <p style="color: #155724; font-weight: bold; font-size: 1.2em; margin-top: 15px;">
                                        {result.get('message', 'Registro exitoso')}
                                        </p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Efectos de éxito
                                    st.balloons()
                                    time.sleep(1)  # Pausa para que se vea la celebración
                                    
                                else:
                                    # ❌ VALIDACIÓN FALLIDA
                                    error_msg = result.get('message', 'Error desconocido') if success else result.get('error', 'Error de conexión')
                                    
                                    st.markdown(f"""
                                    <div class="error-message">
                                        <h3>❌ ACCESO DENEGADO</h3>
                                        <p style="font-size: 1.1em; font-weight: bold;">{error_msg}</p>
                                        
                                        <hr>
                                        <p><strong>🔍 Posibles causas:</strong></p>
                                        <ul>
                                            <li>Asistente no registrado en el sistema</li>
                                            <li>Código QR dañado o ilegible</li>
                                            <li>Tipo de acceso no autorizado</li>
                                            <li>Problema de conexión con el servidor</li>
                                        </ul>
                                    </div>
                                    """, unsafe_allow_html=True)
                else:
                    st.warning("⚠️ **No se detectó código QR** en la imagen")
                    st.markdown("""
                    **💡 Consejos para mejor detección:**
                    - Asegúrate de que el QR esté bien iluminado
                    - Mantén el código QR centrado en la imagen
                    - Evita reflejos o sombras sobre el código
                    - Verifica que el código no esté borroso
                    """)
    
    with tab2:
        st.markdown("**📎 Subir desde galería**")
        
        uploaded_file = st.file_uploader(
            "Seleccionar imagen con código QR",
            type=['jpg', 'jpeg', 'png'],
            help="Sube una foto que contenga el código QR a validar"
        )
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(image, caption="📁 Imagen subida", use_column_width=True)
            
            # Procesamiento similar al de cámara
            with st.spinner("🔍 Procesando imagen..."):
                qr_results = decode_qr_from_image(image)
                
                if qr_results:
                    for i, qr_result in enumerate(qr_results):
                        qr_data = qr_result['data']
                        
                        if st.button(f"✅ Validar QR #{i+1} (Archivo)", key=f"validate_upload_{i}", use_container_width=True):
                            # Lógica similar a la cámara en vivo...
                            with st.spinner("⏳ Validando..."):
                                success, result = send_qr_to_server(
                                    st.session_state.server_host,
                                    server_port,
                                    qr_data,
                                    get_device_info()
                                )
                                
                                # Agregar al historial y mostrar resultado...
                                
                                if success and result.get('success'):
                                    st.success("✅ ¡Validación exitosa!")
                                    attendee = result.get('attendee', {})
                                    st.json({
                                        'Nombre': f"{attendee.get('nombre')} {attendee.get('apellido')}",
                                        'Empresa': attendee.get('empresa'),
                                        'Tipo': attendee.get('tipo'),
                                        'Mensaje': result.get('message')
                                    })
                                    st.balloons()
                                else:
                                    st.error(f"❌ {result.get('message') if success else result.get('error')}")
    
    with tab3:
        st.markdown("**📊 Historial de escaneos**")
        
        if st.session_state.scan_history:
            for i, record in enumerate(st.session_state.scan_history):
                timestamp = time.strftime('%H:%M:%S', time.localtime(record['timestamp']))
                status = "✅" if record['success'] and record['result'].get('success') else "❌"
                
                with st.expander(f"{status} {timestamp} - Escaneo #{len(st.session_state.scan_history)-i}"):
                    st.text(f"Hora: {timestamp}")
                    st.text(f"QR: {record['qr_data']}")
                    
                    if record['success'] and record['result'].get('success'):
                        attendee = record['result'].get('attendee', {})
                        st.success(f"Válido: {attendee.get('nombre')} {attendee.get('apellido')}")
                    else:
                        error = record['result'].get('message') if record['success'] else record['result'].get('error')
                        st.error(f"Error: {error}")
            
            if st.button("🗑️ Limpiar Historial", use_container_width=True):
                st.session_state.scan_history = []
                st.success("Historial limpiado")
                
        else:
            st.info("📝 No hay escaneos en el historial aún")
    
    # ===========================
    # INFORMACIÓN ADICIONAL
    # ===========================
    
    st.markdown("---")
    st.markdown("### ℹ️ Información del Sistema")
    
    with st.expander("📋 Estado del Sistema"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("🔗 Estado Conexión", "Conectado" if st.session_state.connected else "Desconectado")
            st.metric("📱 Escaneos Realizados", len(st.session_state.scan_history))
        
        with col2:
            st.metric("🌐 Servidor", f"{st.session_state.server_host}:{server_port}")
            exitosos = len([r for r in st.session_state.scan_history if r['success'] and r['result'].get('success')])
            st.metric("✅ Escaneos Exitosos", exitosos)

else:
    # ===========================
    # ESTADO DESCONECTADO
    # ===========================
    
    st.error(f"❌ No conectado al servidor principal")
    
    st.markdown("""
    ### 🔧 Para conectarte:
    
    #### 🏠 MISMA RED WiFi:
    1. **🖥️ Ejecuta:** `python main.py`
    2. **🌐 Usa IP local** como `192.168.1.100:5000`
    3. **🔍 Presiona "Auto-detectar"**
    
    #### 🌍 ACCESO REMOTO (desde cualquier lugar):
    1. **🖥️ Ejecuta:** `USE_NGROK=true python main.py`  
    2. **📋 Copia la URL** que aparece (ej: `abc123.ngrok.io`)
    3. **🌐 Úsala SIN puerto** en el campo servidor
    4. **📱 Puerto:** `80` (automático)
    
    ### 💡 URLs de ejemplo:
    - **Local:** `192.168.1.100` + puerto `5000`
    - **Remoto:** `abc123.ngrok.io` + puerto `80`
    
    ### ⚠️ Si no puedes conectarte:
    - **Local:** Verifica que ambos estén en la misma WiFi
    - **Remoto:** Instala ngrok con `pip install pyngrok`
    - **Ambos:** Asegúrate de que la app tkinter esté ejecutándose
    """)

# ===========================
# AUTO-REFRESH Y FOOTER
# ===========================

# Botón manual de refresh
if st.session_state.connected:
    if st.button("🔄 Actualizar Datos", use_container_width=True):
        st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; margin-top: 2rem;'>
    📱 <strong>QR Scanner Móvil v1.0</strong><br>
    Desarrollado para Sistema de Gestión de Asistentes<br>
    <small>Optimizado para dispositivos móviles</small>
</div>
""", unsafe_allow_html=True)
import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
from utils.data_processor import DataProcessor
from components.vigilancia_tab import VigilanciaTab
from components.control_larvario_tab import ControlLarvarioTab
from components.cerco_tab import CercoTab
from components.inspector_tab import InspectorTab
from components.housing_management import HousingManagement
import requests
import re
import zipfile
import gzip
import io

# App Storage availability check (lazy loading)
APP_STORAGE_AVAILABLE = True
try:
    import replit.object_storage
except ImportError:
    APP_STORAGE_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Sistema de Vigilancia Epidemiológica",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure file upload size (200MB)
st.session_state.max_upload_size = 200 * 1024 * 1024  # 200MB

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = None
if 'data_processor' not in st.session_state:
    st.session_state.data_processor = None
if 'app_start_time' not in st.session_state:
    st.session_state.app_start_time = datetime.now()

def validate_url_security(url):
    """Validate URL for security (prevent SSRF)"""
    import urllib.parse
    
    parsed = urllib.parse.urlparse(url.lower())
    
    # Only allow HTTPS
    if parsed.scheme != 'https':
        raise Exception("Solo se permiten URLs HTTPS por seguridad")
    
    # Allowlist of domains
    allowed_domains = [
        'drive.google.com', 'docs.google.com',
        'dropbox.com', 'dl.dropboxusercontent.com',
        'onedrive.live.com', '1drv.ms', 'sharepoint.com',
        'amazonaws.com', 'storage.googleapis.com'
    ]
    
    hostname = parsed.hostname
    if not hostname or not any(domain in hostname for domain in allowed_domains):
        raise Exception(f"Dominio no permitido: {hostname}. Use Google Drive, Dropbox, OneDrive o servicios compatibles.")
    
    # Block private/local networks
    if any(blocked in hostname for blocked in ['localhost', '127.0.0.1', '0.0.0.0', '169.254', '192.168', '10.0', '172.16']):
        raise Exception("URLs locales/privadas no están permitidas")
    
    return True

def convert_to_download_url(url):
    """Convert sharing URLs to direct download URLs with enhanced Google Drive support"""
    # Validate URL first
    validate_url_security(url)
    
    # Google Drive with enhanced handling
    if 'drive.google.com' in url or 'docs.google.com' in url:
        # Extract file ID from various Google Drive URL formats
        if '/file/d/' in url:
            file_id = url.split('/file/d/')[1].split('/')[0]
        elif 'id=' in url:
            file_id = url.split('id=')[1].split('&')[0]
        elif '/open?id=' in url:
            file_id = url.split('/open?id=')[1].split('&')[0]
        else:
            return url  # Return as-is if can't parse
        
        # For Google Drive, we need to handle the confirmation flow for large files
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    # Dropbox
    elif 'dropbox.com' in url:
        # Convert Dropbox sharing URL to direct download
        if '?dl=0' in url:
            return url.replace('?dl=0', '?dl=1')
        elif '?dl=1' not in url:
            return url + ('&dl=1' if '?' in url else '?dl=1')
        return url
    
    # OneDrive
    elif 'onedrive.live.com' in url or '1drv.ms' in url:
        # OneDrive direct download needs specific conversion
        if 'redir?' in url:
            return url.replace('redir?', 'download?')
        return url
    
    # Return URL as-is for other services
    return url

def download_csv_from_url(url):
    """Download CSV file from URL with enhanced robustness for 200MB+ files"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Enhanced retry mechanism
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # For Google Drive, handle confirmation flow for large files
            if 'drive.google.com' in url:
                # Use requests.Session to handle cookies and redirects
                session = requests.Session()
                
                # First request to get the page and check for warnings
                response = session.get(url, headers=headers, timeout=60)
                response.raise_for_status()
                
                # Check if we got a confirmation page (HTML content)
                if response.headers.get('content-type', '').startswith('text/html'):
                    # Look for download confirmation URL in the HTML
                    import re
                    confirm_pattern = r'action="([^"]*)"[^>]*>.*?download'
                    matches = re.search(confirm_pattern, response.text, re.IGNORECASE | re.DOTALL)
                    
                    if matches:
                        # Extract confirm URL and try again
                        confirm_url = matches.group(1).replace('&amp;', '&')
                        if not confirm_url.startswith('http'):
                            confirm_url = 'https://drive.google.com' + confirm_url
                        
                        st.info("🔄 Archivo grande detectado, obteniendo enlace de descarga...")
                        response = session.get(confirm_url, headers=headers, stream=True, timeout=600)
                        response.raise_for_status()
                    else:
                        # Look for alternative download link pattern
                        download_pattern = r'<a[^>]*href="([^"]*)"[^>]*>.*?download'
                        matches = re.search(download_pattern, response.text, re.IGNORECASE | re.DOTALL)
                        
                        if matches:
                            download_url = matches.group(1).replace('&amp;', '&')
                            if not download_url.startswith('http'):
                                download_url = 'https://drive.google.com' + download_url
                            
                            response = session.get(download_url, headers=headers, stream=True, timeout=600)
                            response.raise_for_status()
                        else:
                            # If no download links found, try with confirm=t parameter
                            file_id = url.split('id=')[1].split('&')[0] if 'id=' in url else url.split('/file/d/')[1].split('/')[0]
                            fallback_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
                            response = session.get(fallback_url, headers=headers, stream=True, timeout=600)
                            response.raise_for_status()
                            
                # Check if response is still HTML (failed to get file)
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' in content_type and not response.content.startswith(b'PK'):
                    raise Exception("No se pudo acceder al archivo. Verifica que el enlace de Google Drive tenga permisos públicos o 'Cualquiera con el enlace'")
                    
            else:
                # Regular download for non-Google Drive URLs
                response = requests.get(url, headers=headers, stream=True, timeout=600)
                response.raise_for_status()
            
            # Check Content-Length for early size validation
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > 500:
                    raise Exception(f"Archivo demasiado grande: {size_mb:.1f}MB (límite: 500MB)")
                st.info(f"📥 Descargando archivo: ~{size_mb:.1f}MB")
            
            # Memory-efficient streaming to BytesIO
            content_buffer = io.BytesIO()
            size_limit = 500 * 1024 * 1024  # 500MB
            current_size = 0
            
            # Progress tracking for large downloads
            progress_bar = st.progress(0)
            
            for i, chunk in enumerate(response.iter_content(chunk_size=32768)):  # Larger chunks
                if chunk:
                    current_size += len(chunk)
                    if current_size > size_limit:
                        raise Exception("Archivo demasiado grande (>500MB)")
                    content_buffer.write(chunk)
                    
                    # Update progress every 100 chunks
                    if i % 100 == 0 and content_length:
                        progress = min(current_size / int(content_length), 1.0)
                        progress_bar.progress(progress)
            
            progress_bar.empty()  # Remove progress bar
            
            # Get content from buffer
            content = content_buffer.getvalue()
            content_buffer.close()
            
            # Handle different file types
            if content.startswith(b'PK'):  # ZIP file
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    csv_files = [f for f in z.namelist() if f.endswith('.csv')]
                    if not csv_files:
                        raise Exception("No se encontró archivo CSV en el ZIP")
                    
                    csv_content = z.read(csv_files[0])
                    return pd.read_csv(io.StringIO(csv_content.decode('utf-8')), low_memory=False)
            
            elif content.startswith(b'\x1f\x8b'):  # GZIP file
                csv_content = gzip.decompress(content)
                return pd.read_csv(io.StringIO(csv_content.decode('utf-8')), low_memory=False)
            
            else:  # Regular CSV
                # Try different encodings
                encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
                
                for encoding in encodings:
                    try:
                        csv_text = content.decode(encoding)
                        return pd.read_csv(
                            io.StringIO(csv_text), 
                            low_memory=False,
                            skipinitialspace=True,
                            na_values=['', 'NA', 'N/A', 'null', 'NULL', 'NaN']
                        )
                    except UnicodeDecodeError:
                        continue
                
                raise Exception("No se pudo decodificar el archivo con ninguna codificación válida")
            
            # If we reach here, success - break retry loop
            break
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                st.warning(f"⏱️ Timeout en intento {attempt + 1}. Reintentando...")
                continue
            raise Exception("Tiempo de espera agotado tras múltiples intentos. Archivo muy grande o conexión lenta.")
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                st.warning(f"🔄 Error de conexión en intento {attempt + 1}. Reintentando...")
                continue
            raise Exception(f"Error de conexión tras múltiples intentos: {str(e)}")
        except Exception as e:
            # Don't retry for other exceptions (parsing, validation, etc.)
            raise Exception(f"Error al procesar archivo: {str(e)}")
    
    # If all retries failed, this should not be reached
    raise Exception("Error inesperado: no se pudo descargar el archivo tras múltiples intentos")

def extract_filename_from_url(url):
    """Extract filename from URL"""
    if 'drive.google.com' in url:
        return "archivo_google_drive.csv"
    elif 'dropbox.com' in url:
        # Try to extract filename from Dropbox URL
        parts = url.split('/')
        for part in reversed(parts):
            if '.' in part and part.endswith('.csv'):
                return part.split('?')[0]
        return "archivo_dropbox.csv"
    else:
        # Generic extraction
        parts = url.split('/')
        for part in reversed(parts):
            if '.' in part:
                return part.split('?')[0][:50]  # Limit length
        return "archivo_url.csv"

# ==================== APP STORAGE FUNCTIONS ====================

def get_app_storage_client():
    """Get App Storage client with lazy loading"""
    if not APP_STORAGE_AVAILABLE:
        raise Exception("App Storage no está disponible en este entorno")
    
    # Lazy load the ObjectStorageClient
    try:
        from replit.object_storage import Client as ObjectStorageClient
        return ObjectStorageClient()
    except ImportError:
        raise Exception("App Storage no está disponible en este entorno")

def list_app_storage_files():
    """List all CSV files in App Storage"""
    try:
        client = get_app_storage_client()
        files = client.list()
        # Filter for CSV files only
        csv_files = [f for f in files if f.name.lower().endswith('.csv')]
        return csv_files
    except Exception as e:
        st.error(f"Error al listar archivos: {str(e)}")
        return []

def upload_file_to_app_storage(uploaded_file, filename=None):
    """Upload file to App Storage"""
    try:
        client = get_app_storage_client()
        
        # Use original filename or provided filename
        storage_filename = filename or uploaded_file.name
        
        # Ensure .csv extension
        if not storage_filename.lower().endswith('.csv'):
            storage_filename += '.csv'
        
        # Read file content
        file_content = uploaded_file.read()
        
        # Upload to App Storage
        with st.spinner(f"📤 Subiendo {storage_filename} al App Storage..."):
            client.upload_from_bytes(storage_filename, file_content)
        
        st.success(f"✅ Archivo {storage_filename} subido exitosamente al App Storage!")
        return storage_filename
        
    except Exception as e:
        st.error(f"❌ Error al subir archivo: {str(e)}")
        return None

def upload_file_to_app_storage_bytes(filename, file_bytes):
    """Upload bytes data directly to App Storage"""
    try:
        client = get_app_storage_client()
        
        # Ensure .csv extension
        storage_filename = filename
        if not storage_filename.lower().endswith('.csv'):
            storage_filename += '.csv'
        
        # Upload bytes to App Storage
        with st.spinner(f"📤 Guardando {storage_filename} en App Storage..."):
            client.upload_from_bytes(storage_filename, file_bytes)
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error al guardar: {str(e)}")
        return False

def download_file_from_app_storage(filename):
    """Download file from App Storage and return as pandas DataFrame"""
    try:
        client = get_app_storage_client()
        
        with st.spinner(f"📥 Descargando {filename} desde App Storage..."):
            # Download file content
            file_content = client.download_as_bytes(filename)
            
            # Try different encodings for CSV parsing
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    # Convert bytes to string
                    csv_text = file_content.decode(encoding)
                    
                    # Parse CSV
                    data = pd.read_csv(
                        io.StringIO(csv_text),
                        low_memory=False,
                        skipinitialspace=True,
                        na_values=['', 'NA', 'N/A', 'null', 'NULL', 'NaN'],
                        keep_default_na=True
                    )
                    
                    st.success(f"✅ Archivo {filename} descargado exitosamente desde App Storage!")
                    return data
                    
                except (UnicodeDecodeError, UnicodeError):
                    continue
                    
            raise Exception("No se pudo decodificar el archivo con ninguna codificación válida")
            
    except Exception as e:
        st.error(f"❌ Error al descargar archivo: {str(e)}")
        return None

def delete_file_from_app_storage(filename):
    """Delete file from App Storage"""
    try:
        client = get_app_storage_client()
        client.delete(filename)
        st.success(f"🗑️ Archivo {filename} eliminado del App Storage!")
        return True
    except Exception as e:
        st.error(f"❌ Error al eliminar archivo: {str(e)}")
        return False

# ==================== END APP STORAGE FUNCTIONS ====================

def health_check():
    """Ultra-fast health check endpoint for deployment monitoring"""
    try:
        # Ultra-minimal health check for fast response
        current_time = datetime.now()
        
        # Essential health data only
        health_data = {
            'status': 'healthy',
            'timestamp': current_time.isoformat(),
            'app_version': '1.0.0',
            'ready': True
        }
        
        # Only test session state availability (fastest test)
        if hasattr(st.session_state, 'app_start_time'):
            uptime = current_time - st.session_state.app_start_time
            health_data['uptime_seconds'] = int(uptime.total_seconds())
        else:
            health_data['uptime_seconds'] = 0
        
        return health_data
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'ready': False
        }

def main():
    """Main application with comprehensive error handling"""
    try:
        # Health check endpoint - check URL parameters
        query_params = st.query_params
        
        # Handle health check requests FIRST for fastest deployment response
        if 'health' in query_params or 'healthcheck' in query_params:
            health_data = health_check()
            
            # Return JSON response directly for automated health checks
            if health_data['status'] == 'healthy':
                st.success("✅ Application Ready")
            else:
                st.error("❌ Application Unhealthy")
            
            st.json(health_data)
            return  # Exit immediately for health checks
        
    except Exception as e:
        # Critical error handling for deployment
        st.error(f"🚨 Critical Application Error: {str(e)}")
        st.json({
            'status': 'unhealthy', 
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        return
        
    # Main application logic with error handling
    try:
        # Configuration section in sidebar
        st.sidebar.markdown("### ⚙️ Configuración")
        
        # Theme automatically managed by Streamlit - no custom CSS needed
        # Visual separators for better section differentiation
        st.markdown("""
        <style>
            /* Subtle section separators for better visual organization */
            .section-container {
                background-color: var(--background-color);
                border: 1px solid rgba(49, 51, 63, 0.2);
                border-radius: 8px;
                padding: 1rem;
                margin: 1rem 0;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }
            
            .section-header {
                font-weight: 600;
                margin-bottom: 0.5rem;
                border-bottom: 2px solid rgba(255, 75, 75, 0.3);
                padding-bottom: 0.3rem;
            }
            
            /* Enhanced expandable sections */
            .streamlit-expanderHeader {
                background-color: rgba(240, 242, 246, 0.5);
                border-radius: 6px;
                border: 1px solid rgba(49, 51, 63, 0.2);
            }
            
            .streamlit-expanderContent {
                border: 1px solid rgba(49, 51, 63, 0.15);
                border-top: none;
                background-color: rgba(248, 249, 251, 0.3);
            }
            
            /* Visual separation for different content sections */
            .stMarkdown h3 {
                border-left: 4px solid #1f77b4;
                padding-left: 12px;
                margin-top: 2rem;
                margin-bottom: 1rem;
            }
            
            .stMarkdown h4 {
                background-color: rgba(31, 119, 180, 0.1);
                padding: 8px 12px;
                border-radius: 6px;
                border-left: 3px solid #1f77b4;
                margin-top: 1.5rem;
                margin-bottom: 1rem;
            }
            
            /* Subtle dividers between main sections */
            .main-section-divider {
                height: 2px;
                background: linear-gradient(90deg, transparent, rgba(31, 119, 180, 0.3), transparent);
                margin: 2rem 0;
                border: none;
            }
            
            /* Enhanced selector robustness for better theme compatibility */
            div[data-testid='stMarkdown'] h3,
            .stMarkdown h3 {
                border-left: 4px solid #1f77b4;
                padding-left: 12px;
                margin-top: 2rem;
                margin-bottom: 1rem;
            }
            
            div[data-testid='stMarkdown'] h4,
            .stMarkdown h4 {
                background-color: rgba(31, 119, 180, 0.1);
                padding: 8px 12px;
                border-radius: 6px;
                border-left: 3px solid #1f77b4;
                margin-top: 1.5rem;
                margin-bottom: 1rem;
            }
        </style>
        """, unsafe_allow_html=True)
        
        st.title("📊 Sistema de Vigilancia Epidemiológica")
        st.markdown("---")
        
        # Sidebar for file upload
        with st.sidebar:
            st.markdown("---")
            st.header("📁 Cargar Datos")
        
            # File size info with production warning
            st.info("📋 **Requisitos del archivo:**\n"
                    "- Formato: CSV (UTF-8)\n"
                    "- Columnas: 91 campos\n"
                    "- Tamaño máximo: 150MB\n"
                    "- Registros: Hasta 150,000+")
        
            # Production environment warning
            import os
            is_production = any([
                os.getenv('REPL_DEPLOYMENT') == '1',
                os.getenv('HOSTNAME', '').startswith('app-'),
                'replit.app' in os.getenv('REPL_URL', ''),
            ])
        
            if is_production:
                st.error("🚨 **Entorno Publicado: Error 413 para archivos grandes**\n"
                        "⚠️ Archivos >150MB fallan por límites de proxy\n"
                        "✅ **SOLUCIÓN**: Use 'Cargar desde URL' abajo")
        
            # SOLUCIÓN COMPLETA PARA ERROR 413 - NO MÁS FILE UPLOADER
            st.markdown("### 📁 **Carga de Archivos**")
        
            st.markdown("#### 📤 **Upload Directo (Archivos Pequeños)**")
            st.info("✅ **Archivos hasta 150MB** - Sin Error 413\n"
                   "⚠️ **Archivos >150MB** - Use 'Cargar desde URL' abajo")
            
            # File uploader with size validation
            uploaded_file = st.file_uploader(
                "Seleccionar archivo CSV",
                type=['csv'],
                help="📏 Máximo 150MB • Para archivos mayores use 'Cargar desde URL'"
            )
            
            # CRITICAL: True file size validation to prevent AxiosError 413
            if uploaded_file is not None:
                file_size_mb = uploaded_file.size / (1024 * 1024)
                
                # STRICT validation to prevent 413 errors in production
                if file_size_mb > 150:
                    st.error(f"❌ **Archivo muy grande: {file_size_mb:.1f}MB**\n"
                           f"⚠️ **Límite máximo: 150MB para evitar Error 413**\n"
                           f"✅ **SOLUCIÓN**: Use 'Cargar desde URL' (sin límites)")
                    uploaded_file = None  # CRITICAL: Reset to prevent 413
                    # Force rerun to clear the file uploader state
                    st.rerun()
                elif file_size_mb > 100:
                    st.warning(f"⚠️ **Archivo grande: {file_size_mb:.1f}MB**\n"
                             f"🔄 **Procesamiento**: Puede tomar varios minutos\n"
                             f"💡 **Alternativa**: 'Cargar desde URL' es más rápido\n"
                             f"⚡ **Nota**: Riesgo de timeout en archivos muy grandes")
                elif file_size_mb > 50:
                    st.info(f"📁 **Archivo mediano: {file_size_mb:.1f}MB**\n"
                           f"✅ Procesamiento normal esperado")
                else:
                    st.success(f"✅ **Archivo válido: {file_size_mb:.1f}MB**")
            
            if is_production and uploaded_file is not None and uploaded_file.size > 150 * 1024 * 1024:
                st.markdown("#### ⚠️ **Para archivos >150MB:**")
                st.markdown("""
                1. **📤 Suba su archivo a la nube:**
                   - Google Drive, Dropbox, OneDrive, etc.
                
                2. **🔗 Copie el enlace público:**
                   - Google Drive: Botón Compartir → "Cualquiera con enlace" 
                   - Dropbox: Compartir → Crear enlace
                
                3. **📥 Use "Cargar desde URL" abajo**
                """)
        
            # URL Upload Alternative - SOLUCIÓN PARA ERROR 413
            st.markdown("---")
            st.markdown("### 🌐 **Alternativa: Cargar desde URL**")
            st.info("✅ **Sin límites de tamaño** - Evita error 413\n"
                    "📂 Suba su archivo a Google Drive, Dropbox, etc.\n"
                    "🔗 Pegue aquí el enlace público/compartido")
        
            url_input = st.text_input(
                "URL del archivo CSV",
                placeholder="https://drive.google.com/file/d/..., https://dropbox.com/..., etc.",
                help="Google Drive: Compartir → Cualquiera con enlace\nDropbox: Compartir → Crear enlace"
            )
        
            if st.button("📥 Descargar desde URL", type="primary"):
                if url_input.strip():
                    try:
                        with st.spinner("🌐 Descargando archivo desde URL... Esto puede tomar varios minutos para archivos grandes."):
                            # Convert sharing URLs to direct download URLs
                            download_url = convert_to_download_url(url_input.strip())
                            
                            # Download file with streaming
                            data = download_csv_from_url(download_url)
                        
                            if data is not None:
                                # OPTIMIZACIÓN CRÍTICA: Verificar tamaño y procesar inmediatamente para evitar AxiosError 413
                                memory_mb = data.memory_usage(deep=True).sum() / 1024 / 1024
                                st.success(f"✅ Archivo descargado: {len(data):,} registros, {len(data.columns)} columnas (~{memory_mb:.1f}MB)")
                                
                                st.info("🔄 Procesando datos inmediatamente para evitar AxiosError 413...")
                            
                                # CRÍTICO: Procesar inmediatamente SIN almacenar en session state temporal
                                try:
                                    # Limpiar session state ANTES del procesamiento
                                    session_keys_to_clean = ['url_data', 'app_storage_data', 'data', 'data_processor']
                                    for key in session_keys_to_clean:
                                        if key in st.session_state:
                                            del st.session_state[key]
                                
                                    # Procesar datos inmediatamente
                                    data_processor = DataProcessor(data)
                                    
                                    # Solo guardar datos optimizados en session state
                                    st.session_state.data_processor = data_processor
                                    st.session_state.data = data_processor.data
                                    st.session_state['url_filename'] = extract_filename_from_url(url_input)
                                
                                    # Forzar garbage collection
                                    import gc
                                    gc.collect()
                                    
                                    uploaded_file = "url_upload"  # Flag for processing
                                    
                                    st.success(f"🚀 Datos optimizados y listos! Memoria final: ~{data_processor.data.memory_usage(deep=True).sum() / 1024 / 1024:.1f}MB")
                                    
                                except Exception as proc_error:
                                    st.error(f"❌ Error al procesar datos: {str(proc_error)}")
                                    st.error("💡 Por favor intente nuevamente o use un archivo más pequeño")
                                    # NO guardar datos temporales para evitar AxiosError 413
                                    return
                    except Exception as e:
                        st.error(f"❌ Error al descargar archivo: {str(e)}")
                        st.markdown("**Posibles soluciones:**\n"
                                  "- Verifique que el enlace sea público/compartido\n"
                                  "- Para Google Drive: Compartir → Cualquiera con enlace\n" 
                                  "- Para Dropbox: Compartir → Crear enlace\n"
                                  "- Intente con otro servicio de almacenamiento")
                else:
                    st.warning("⚠️ Por favor ingrese una URL válida")
        
        # App Storage section removed for cleaner user interface
        
        # Handle file upload, URL upload, and App Storage upload
        # Process data if we have a new upload OR if we need to reprocess existing data
        should_process = (uploaded_file is not None or 
                         'url_data' in st.session_state or
                         'app_storage_data' in st.session_state or
                         (uploaded_file == "url_upload" and st.session_state.data is None) or
                         (uploaded_file == "app_storage_upload" and st.session_state.data is None))
        
        if should_process:
            
            # Check upload type: URL, App Storage, or regular file upload
            if (uploaded_file == "url_upload" and 'url_data' in st.session_state) or (uploaded_file == "url_upload" and st.session_state.data is not None):
                # URL upload case - use existing data if available
                if 'url_data' in st.session_state:
                    data = st.session_state['url_data']
                    filename = st.session_state['url_filename']
                elif st.session_state.data is not None:
                    # Use already processed data to maintain continuity
                    data = st.session_state.data
                    filename = st.session_state.get('url_filename', 'archivo_url.csv')
                else:
                    return
                    
                file_size = data.memory_usage(deep=True).sum() / 1024 / 1024  # Approximate size in MB
                
                st.info(f"📁 **{filename}** (desde URL)\n"
                       f"Registros: {len(data):,}\n"
                       f"Columnas: {len(data.columns)}\n"
                       f"Memoria: ~{file_size:.1f} MB")
                
            elif (uploaded_file == "app_storage_upload" and 'app_storage_data' in st.session_state) or (uploaded_file == "app_storage_upload" and st.session_state.data is not None):
                # App Storage upload case - use existing data if available
                if 'app_storage_data' in st.session_state:
                    data = st.session_state['app_storage_data']
                    filename = st.session_state['app_storage_filename']
                elif st.session_state.data is not None:
                    # Use already processed data to maintain continuity
                    data = st.session_state.data
                    filename = st.session_state.get('app_storage_filename', 'archivo_app_storage.csv')
                else:
                    return
                    
                file_size = data.memory_usage(deep=True).sum() / 1024 / 1024  # Approximate size in MB
                
                st.info(f"📁 **{filename}** (desde App Storage)\n"
                       f"Registros: {len(data):,}\n"
                       f"Columnas: {len(data.columns)}\n"
                       f"Memoria: ~{file_size:.1f} MB")
                
            elif uploaded_file is not None and uploaded_file != "url_upload" and uploaded_file != "app_storage_upload":
                # Regular file upload case
                file_size = uploaded_file.size / (1024 * 1024)  # MB
                st.info(f"📁 **{uploaded_file.name}**\n"
                       f"Tamaño: {file_size:.1f} MB")
                
                if file_size > 150:
                    st.error("⚠️ El archivo excede el límite de 150MB")
                    return
            else:
                return
                
            try:
                with st.spinner("🔄 Procesando archivo... Esto puede tomar unos minutos para archivos grandes."):
                    # Handle special upload cases differently
                    if uploaded_file == "url_upload":
                        # Use already downloaded and processed data from URL
                        if 'url_data' in st.session_state:
                            data = st.session_state['url_data']
                        elif st.session_state.data is not None:
                            # Data already processed and stored
                            data = st.session_state.data
                            # Skip reprocessing, just update the success message
                            st.success(f"✅ Archivo desde URL activo!")
                            # Continue to main interface instead of returning
                        else:
                            st.error("❌ No se encontraron datos cargados desde URL")
                            return
                        successful_encoding = 'utf-8'  # Already processed successfully
                    elif uploaded_file == "app_storage_upload":
                        # Use already downloaded and processed data from App Storage
                        if 'app_storage_data' in st.session_state:
                            data = st.session_state['app_storage_data']
                        elif st.session_state.data is not None:
                            # Data already processed and stored
                            data = st.session_state.data
                            # Skip reprocessing, just update the success message
                            st.success(f"✅ Archivo desde App Storage activo!")
                            # Continue to main interface instead of returning
                        else:
                            st.error("❌ No se encontraron datos cargados desde App Storage")
                            return
                        successful_encoding = 'utf-8'  # Already processed successfully
                    else:
                        # Regular file upload processing
                        data = None
                        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
                        successful_encoding = None
                        
                        for encoding in encodings:
                            try:
                                # Reset file pointer for each attempt (only for file uploads)
                                if hasattr(uploaded_file, 'seek'):
                                    uploaded_file.seek(0)
                                
                                # Load data with optimizations for large files
                                data = pd.read_csv(
                                    uploaded_file, 
                                    encoding=encoding,
                                    low_memory=False,
                                    skipinitialspace=True,  # Skip spaces after delimiter
                                    na_values=['', 'NA', 'N/A', 'null', 'NULL', 'NaN'],  # Handle missing values
                                    keep_default_na=True
                                )
                            
                                # If successful, store the encoding and break the loop
                                successful_encoding = encoding
                                break
                                
                            except (UnicodeDecodeError, UnicodeError) as e:
                                # Try next encoding
                                if encoding == encodings[-1]:  # Last encoding attempt
                                    st.error(f"❌ Error de codificación: {str(e)}")
                                    st.info("💡 Intenta guardar tu archivo CSV con codificación UTF-8")
                                    return
                                continue
                            except Exception as e:
                                # Other errors, show them but try next encoding
                                if encoding == encodings[-1]:  # Last encoding attempt
                                    st.error(f"❌ Error al procesar archivo: {str(e)}")
                                    return
                                continue
                    
                    # Validate that we got data
                    if data is None or data.empty:
                        st.error("❌ No se pudo cargar el archivo o está vacío")
                        return
                    
                    # Additional validation for epidemiological data structure
                    if len(data.columns) < 90:  # Should have 91 columns
                        st.warning(f"⚠️ El archivo tiene {len(data.columns)} columnas, se esperaban 91. Continuando con los datos disponibles...")
                    
                    st.session_state.data_processor = DataProcessor(data)
                    st.session_state.data = data
                    
                    # Preserve filename for URL and App Storage uploads
                    if uploaded_file == "url_upload" and 'url_filename' in st.session_state:
                        st.session_state.current_filename = st.session_state['url_filename']
                    elif uploaded_file == "app_storage_upload" and 'app_storage_filename' in st.session_state:
                        st.session_state.current_filename = st.session_state['app_storage_filename']
                    
                    # Gestión automática de viviendas totales
                    housing_mgmt = HousingManagement()
                    
                    # Aplicar automáticamente valores guardados de viviendas totales
                    data = housing_mgmt.apply_housing_totals_to_data(data)
                    
                    # Actualizar los datos en session state con valores aplicados
                    st.session_state.data = data
                    st.session_state.data_processor = DataProcessor(data)
                    
                    # CRÍTICO: Forzar recarga de health_facilities con datos actualizados de BD
                    # Esto asegura que los cálculos usen los datos más recientes
                    if 'calculations' in st.session_state:
                        # Recargar health_facilities si ya existe una instancia de cálculos
                        del st.session_state['calculations']
                    
                    # Detectar establecimientos con viviendas faltantes
                    missing_facilities = housing_mgmt.detect_missing_facilities(data)
                    
                    if missing_facilities:
                        # Mostrar diálogo para establecimientos faltantes
                        housing_mgmt.show_missing_facilities_dialog(missing_facilities)
                    
                st.success(f"✅ Archivo cargado exitosamente! (codificación: {successful_encoding})")
                st.metric("📈 Registros", f"{len(data):,}")
                st.metric("📋 Columnas", f"{len(data.columns)}")
                
                # Show data types summary
                with st.expander("📊 Resumen de Datos"):
                    activity_types = data['tipoActividadInspeccion'].value_counts()
                    st.write("**Tipos de Actividad:**")
                    for activity, count in activity_types.items():
                        st.write(f"- {activity}: {count:,} registros")
                
            except Exception as e:
                st.error(f"❌ Error al cargar el archivo: {str(e)}")
                st.info("💡 **Posibles soluciones:**\n"
                       "- Verifique que el archivo sea CSV válido\n"
                       "- Asegúrese de que esté codificado en UTF-8\n"
                       "- Verifique que tenga las 91 columnas requeridas")
                return
        
        # Main content area
        if st.session_state.data is not None:
            # Create tabs
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Vigilancia", "🦟 Control Larvario", "🔒 Cerco", "👤 Inspectores", "🏠 Gestión Viviendas"])
        
            with tab1:
                vigilancia_tab = VigilanciaTab(st.session_state.data_processor)
                vigilancia_tab.render()
            
            with tab2:
                control_larvario_tab = ControlLarvarioTab(st.session_state.data_processor)
                control_larvario_tab.render()
        
            with tab3:
                cerco_tab = CercoTab(st.session_state.data_processor)
                cerco_tab.render()
            
            with tab4:
                from utils.calculations import EpidemiologicalCalculations
                calculations = EpidemiologicalCalculations(st.session_state.data_processor)
                inspector_tab = InspectorTab(st.session_state.data_processor, calculations)
                inspector_tab.render()
        
            with tab5:
                housing_mgmt = HousingManagement()
                housing_mgmt.show_housing_management_interface()
        else:
            # Welcome screen
            st.markdown("""
            ## 👋 Bienvenido al Sistema de Vigilancia Epidemiológica
            
            Este sistema está diseñado para analizar y visualizar datos de inspecciones epidemiológicas.
            
            ### 📋 Características principales:
            - **Procesamiento de datos masivos**: Maneja más de 150,000 registros
            - **Filtros dinámicos**: Búsqueda y filtrado por múltiples criterios
            - **Cálculos especializados**: Índice Aédico y estadísticas de recipientes
            - **Visualizaciones interactivas**: Dashboards con gráficos dinámicos
            - **Tres módulos de análisis**: Vigilancia, Control Larvario y Cerco
            
            ### 🚀 Para comenzar:
            1. Cargue su archivo CSV usando el panel lateral
            2. Seleccione la pestaña de análisis deseada
            3. Configure los filtros según sus necesidades
            4. Explore los resultados en tiempo real
            
            ---
            **📁 Por favor, cargue un archivo CSV para comenzar el análisis.**
            
            ### 🔍 Health Check
            Para verificar el estado de la aplicación, visite: [Health Check](?health=true)
            """)
            
            # Add application status in sidebar
            with st.sidebar:
                st.markdown("---")
                st.markdown("### 🔋 Estado del Sistema")
                health_data = health_check()
                if health_data['status'] == 'healthy':
                    st.success("✅ Sistema Operativo")
                    uptime_hours = float(health_data['uptime_seconds']) / 3600
                    st.metric("⏱️ Tiempo Activo", f"{uptime_hours:.1f}h")
                else:
                    st.error("❌ Sistema con Problemas")
                
                # Developer Credits
                st.markdown("---")
                st.markdown("**Desarrollado por: Frank E. Melendez Yliquin**")

    except Exception as e:
        # Comprehensive error handling for main application
        st.error(f"🚨 Application Error: {str(e)}")
        st.markdown("### 🔧 Troubleshooting")
        st.markdown("- Check your data file format")
        st.markdown("- Try refreshing the page")
        st.markdown("- Contact support if the problem persists")
        
        # Show health status even during errors
        with st.expander("🔍 Error Details"):
            st.code(f"Error: {str(e)}")
            st.code(f"Timestamp: {datetime.now().isoformat()}")
        
        # Keep health check available
        with st.sidebar:
            st.markdown("---") 
            st.markdown("### 🔋 Sistema")
            health_data = health_check()
            if health_data['status'] == 'healthy':
                st.success("✅ Core System OK")
            else:
                st.error("❌ System Error")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Ultimate error fallback
        print(f"CRITICAL ERROR: {str(e)}")
        import sys
        sys.exit(1)

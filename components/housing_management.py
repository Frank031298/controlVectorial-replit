"""
Componente de gestión de datos de viviendas para establecimientos de salud
Permite detectar, agregar y modificar información de viviendas totales
"""
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
import os
import psycopg2
from utils.table_helpers import create_enhanced_dataframe, safe_dataframe

class HousingManagement:
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        self.db_available = self._check_database_availability()
    
    def _check_database_availability(self):
        """Verifica si la base de datos está disponible y configurada"""
        if not self.database_url:
            return False
        
        try:
            with psycopg2.connect(self.database_url) as conn:
                cursor = conn.cursor()
                # Verificar si la tabla existe y crearla si no existe
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS health_facilities (
                        cod_renipress INTEGER PRIMARY KEY,
                        nombre_establecimiento VARCHAR(255) NOT NULL,
                        total_viviendas INTEGER DEFAULT 0,
                        fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        usuario_actualizacion VARCHAR(100) DEFAULT 'sistema',
                        activo BOOLEAN DEFAULT TRUE
                    );
                """)
                conn.commit()
                return True
        except Exception as e:
            print(f"Database not available: {str(e)}")
            return False
    
    def get_connection(self):
        """Obtiene conexión a la base de datos con validación"""
        if not self.db_available:
            raise Exception("Base de datos no disponible")
        return psycopg2.connect(self.database_url)
    
    def detect_missing_facilities(self, data):
        """
        Detecta establecimientos de salud que están en los datos pero no tienen
        información de viviendas totales en la base de datos
        """
        if data.empty:
            return []
        
        # Si la BD no está disponible, retornar lista vacía sin causar error
        if not self.db_available:
            st.warning("⚠️ Base de datos no disponible. Funcionalidad de gestión de viviendas limitada.")
            return []
        
        try:
            # Obtener códigos únicos de los datos cargados
            data_facilities = set(data['cod_renipress'].unique())
            
            # Obtener códigos que existen en la base de datos
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT cod_renipress FROM health_facilities WHERE activo = TRUE")
                db_facilities = set(row[0] for row in cursor.fetchall())
            
            # Identificar faltantes
            missing_codes = data_facilities - db_facilities
            
            # Obtener información detallada de los faltantes
            missing_facilities = []
            if missing_codes:
                missing_data = data[data['cod_renipress'].isin(missing_codes)]
                for cod in missing_codes:
                    facility_data = missing_data[missing_data['cod_renipress'] == cod]
                    if not facility_data.empty:
                        nombre = facility_data['localidad_eess'].iloc[0]
                        missing_facilities.append({
                            'cod_renipress': cod,
                            'nombre': nombre,
                            'total_viviendas': 0  # Por defecto
                        })
            
            return missing_facilities
            
        except Exception as e:
            st.warning(f"⚠️ Error al verificar establecimientos faltantes: {str(e)}")
            return []
    
    def show_missing_facilities_dialog(self, missing_facilities):
        """
        Muestra diálogo profesional para ingresar datos de viviendas faltantes
        """
        if not missing_facilities or not self.db_available:
            return None
        
        st.warning(f"⚠️ Se detectaron {len(missing_facilities)} establecimientos de salud sin datos de viviendas totales.")
        
        with st.expander("🏠 Configurar Viviendas Totales de Establecimientos", expanded=True):
            st.markdown("""
            **Los siguientes establecimientos necesitan información de viviendas totales:**
            
            Para cada establecimiento, ingrese el número total de viviendas en su área de cobertura.
            Esta información es esencial para calcular correctamente los índices epidemiológicos.
            """)
            
            # Crear formulario para múltiples establecimientos
            with st.form("missing_facilities_form"):
                facilities_data = []
                
                # Mostrar en columnas para mejor visualización
                cols = st.columns(2)
                
                for i, facility in enumerate(missing_facilities):
                    col = cols[i % 2]
                    
                    with col:
                        st.markdown(f"**{facility['nombre']}**")
                        st.text(f"Código RENIPRESS: {facility['cod_renipress']}")
                        
                        # Input para total de viviendas
                        total_viviendas = st.number_input(
                            f"Total de viviendas",
                            key=f"viviendas_{facility['cod_renipress']}",
                            min_value=0,
                            value=0,
                            step=1,
                            help=f"Ingrese el total de viviendas para {facility['nombre']}"
                        )
                        
                        facilities_data.append({
                            'cod_renipress': facility['cod_renipress'],
                            'nombre': facility['nombre'],
                            'total_viviendas': total_viviendas
                        })
                        
                        st.markdown("---")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col2:
                    submitted = st.form_submit_button(
                        "💾 Guardar Información de Viviendas",
                        type="primary",
                        use_container_width=True
                    )
                
                if submitted:
                    return self._save_missing_facilities(facilities_data)
        
        return None
    
    def _save_missing_facilities(self, facilities_data):
        """Guarda los datos de establecimientos faltantes en la base de datos"""
        saved_count = 0
        errors = []
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for facility in facilities_data:
                    if facility['total_viviendas'] > 0:  # Solo guardar si tiene viviendas
                        try:
                            cursor.execute("""
                                INSERT INTO health_facilities 
                                (cod_renipress, nombre_establecimiento, total_viviendas, usuario_actualizacion)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (cod_renipress) 
                                DO UPDATE SET 
                                    nombre_establecimiento = EXCLUDED.nombre_establecimiento,
                                    total_viviendas = EXCLUDED.total_viviendas,
                                    fecha_actualizacion = CURRENT_TIMESTAMP,
                                    usuario_actualizacion = EXCLUDED.usuario_actualizacion;
                            """, (
                                facility['cod_renipress'],
                                facility['nombre'],
                                facility['total_viviendas'],
                                'usuario_manual'
                            ))
                            saved_count += 1
                        except Exception as e:
                            errors.append(f"Error con {facility['nombre']}: {str(e)}")
                
                conn.commit()
        
        except Exception as e:
            st.error(f"Error al guardar en la base de datos: {str(e)}")
            return False
        
        if saved_count > 0:
            st.success(f"✅ Se guardaron {saved_count} establecimientos exitosamente")
            
        if errors:
            st.warning("⚠️ Algunos establecimientos no se pudieron guardar:")
            for error in errors:
                st.text(f"• {error}")
        
        # CRÍTICO: Limpiar cache de cálculos para forzar recarga con datos actualizados
        if 'calculations' in st.session_state:
            del st.session_state['calculations']
        
        # Forzar recarga de la página para actualizar los datos
        st.rerun()
        return True
    
    def get_all_housing_totals(self):
        """Recupera todos los valores de viviendas totales de la base de datos como diccionario"""
        if not self.db_available:
            return {}
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT cod_renipress, total_viviendas
                    FROM health_facilities 
                    WHERE activo = TRUE AND total_viviendas > 0
                """)
                results = cursor.fetchall()
                return {int(cod): int(total) for cod, total in results}
        except Exception as e:
            st.warning(f"⚠️ Error al recuperar datos de viviendas: {str(e)}")
            return {}
    
    def apply_housing_totals_to_data(self, data):
        """Aplica automáticamente los valores de viviendas totales guardados a los datos cargados"""
        if not self.db_available or data.empty:
            return data
        
        try:
            # Obtener valores guardados
            housing_totals = self.get_all_housing_totals()
            
            if housing_totals:
                # Normalizar tipos de datos para mapeo correcto
                data['cod_renipress_normalized'] = pd.to_numeric(data['cod_renipress'], errors='coerce').fillna(0).astype(int)
                
                # Crear columna de viviendas totales si no existe
                if 'viviendas_totales_bd' not in data.columns:
                    data['viviendas_totales_bd'] = 0
                
                # Aplicar valores de la base de datos usando tipos normalizados
                data['viviendas_totales_bd'] = data['cod_renipress_normalized'].map(housing_totals).fillna(0)
                
                # Contar cuántos establecimientos tienen valores guardados
                facilities_with_data = len(data[data['viviendas_totales_bd'] > 0]['cod_renipress'].unique())
                total_facilities = len(data['cod_renipress'].unique())
                
                if facilities_with_data > 0:
                    st.info(f"✅ Se aplicaron valores de viviendas totales a {facilities_with_data} de {total_facilities} establecimientos desde la base de datos")
                    
                # Limpiar columna temporal
                data.drop('cod_renipress_normalized', axis=1, inplace=True)
                    
            return data
            
        except Exception as e:
            st.warning(f"⚠️ Error al aplicar datos de viviendas: {str(e)}")
            return data

    def show_housing_management_interface(self):
        """Interfaz principal de gestión de viviendas"""
        st.header("🏠 Gestión de Viviendas por Establecimiento")
        
        if not self.db_available:
            st.error("❌ **Base de datos no disponible**")
            st.info("""
            La funcionalidad de gestión de viviendas requiere una base de datos PostgreSQL configurada.
            
            **Para solucionar este problema:**
            1. Verifique que la variable DATABASE_URL esté configurada
            2. Asegúrese de que la base de datos PostgreSQL esté en funcionamiento
            3. Contacte al administrador del sistema si el problema persiste
            """)
            return
        
        tab1, tab2, tab3 = st.tabs([
            "👁️ Ver Establecimientos", 
            "✏️ Editar Individual", 
            "📊 Edición Masiva"
        ])
        
        with tab1:
            self._show_facilities_list()
        
        with tab2:
            self._show_individual_edit()
        
        with tab3:
            self._show_bulk_edit()
    
    def _show_facilities_list(self):
        """Muestra lista de todos los establecimientos con sus datos de viviendas"""
        st.subheader("📋 Lista de Establecimientos de Salud")
        
        try:
            with self.get_connection() as conn:
                df = pd.read_sql("""
                    SELECT 
                        cod_renipress as "Código RENIPRESS",
                        nombre_establecimiento as "Nombre del Establecimiento",
                        total_viviendas as "Total de Viviendas",
                        fecha_actualizacion as "Última Actualización",
                        usuario_actualizacion as "Actualizado por"
                    FROM health_facilities 
                    WHERE activo = TRUE
                    ORDER BY nombre_establecimiento
                """, conn)
            
            # Mostrar estadísticas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📍 Total Establecimientos", len(df))
            
            with col2:
                total_viviendas = df["Total de Viviendas"].sum()
                st.metric("🏠 Total Viviendas", f"{total_viviendas:,}")
            
            with col3:
                promedio_viviendas = df["Total de Viviendas"].mean()
                st.metric("📊 Promedio por Establecimiento", f"{promedio_viviendas:.0f}")
            
            with col4:
                sin_viviendas = len(df[df["Total de Viviendas"] == 0])
                st.metric("⚠️ Sin Datos de Viviendas", sin_viviendas)
            
            # Mostrar tabla con filtros
            st.markdown("### 🔍 Buscar Establecimientos")
            search_term = st.text_input(
                "Buscar por nombre o código",
                placeholder="Ejemplo: SAN JUAN o 1234"
            )
            
            if search_term:
                mask = (
                    df["Nombre del Establecimiento"].str.contains(search_term, case=False, na=False) |
                    df["Código RENIPRESS"].astype(str).str.contains(search_term, na=False)
                )
                df = df[mask]
            
            # Agregar fila de totales
            enhanced_df = create_enhanced_dataframe(
                df,
                label_column='Nombre del Establecimiento',
                exclude_from_total=['Código RENIPRESS']  # Excluir códigos
            )
            
            safe_dataframe(
                enhanced_df,
                use_container_width=True,
                hide_index=True
            )
            
        except Exception as e:
            st.error(f"Error al cargar los datos: {str(e)}")
    
    def _show_individual_edit(self):
        """Interfaz para editar un establecimiento individual"""
        st.subheader("✏️ Editar Establecimiento Individual")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT cod_renipress, nombre_establecimiento, total_viviendas
                    FROM health_facilities 
                    WHERE activo = TRUE
                    ORDER BY nombre_establecimiento
                """)
                facilities = cursor.fetchall()
            
            if not facilities:
                st.info("No hay establecimientos disponibles")
                return
            
            # Selector de establecimiento
            facility_options = [f"{f[0]} - {f[1]}" for f in facilities]
            selected_idx = st.selectbox(
                "Seleccionar establecimiento",
                range(len(facility_options)),
                format_func=lambda x: facility_options[x],
                key="individual_edit_selector"
            )
            
            selected_facility = facilities[selected_idx]
            cod_renipress, nombre, total_actual = selected_facility
            
            # Mostrar información actual
            st.info(f"**Establecimiento:** {nombre}\n\n**Código RENIPRESS:** {cod_renipress}\n\n**Viviendas actuales:** {total_actual}")
            
            # Formulario de edición
            with st.form("edit_individual_form"):
                nuevo_total = st.number_input(
                    "Nuevo total de viviendas",
                    value=int(total_actual),
                    min_value=0,
                    step=1
                )
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    submitted = st.form_submit_button(
                        "💾 Actualizar",
                        type="primary",
                        use_container_width=True
                    )
                
                if submitted and nuevo_total != total_actual:
                    self._update_facility_housing(cod_renipress, nuevo_total, nombre)
                    
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    def _show_bulk_edit(self):
        """Interfaz para edición masiva via Excel"""
        st.subheader("📊 Edición Masiva via Excel")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📥 Descargar Plantilla")
            st.markdown(
                "Descarga la plantilla Excel con todos los establecimientos "
                "para editarlos masivamente y luego importar los cambios."
            )
            
            try:
                excel_data = self._generate_excel_template()
                if excel_data:
                    st.download_button(
                        label="📄 Descargar Plantilla Excel",
                        data=excel_data,
                        file_name=f"establecimientos_salud_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True
                    )
                else:
                    st.error("No se pudo generar la plantilla Excel")
                    
            except Exception as e:
                st.error(f"Error al generar plantilla: {str(e)}")
                st.button("📄 Descargar Plantilla Excel", type="primary", disabled=True)
        
        with col2:
            st.markdown("### 📤 Importar Cambios")
            st.markdown(
                "Sube el archivo Excel modificado para actualizar "
                "los datos de viviendas masivamente."
            )
            
            uploaded_file = st.file_uploader(
                "Seleccionar archivo Excel",
                type=['xlsx'],
                key="bulk_upload"
            )
            
            if uploaded_file and st.button("🔄 Importar Cambios", type="secondary"):
                try:
                    self._import_excel_changes(uploaded_file)
                except Exception as e:
                    st.error(f"Error al importar: {str(e)}")
    
    def _update_facility_housing(self, cod_renipress, nuevo_total, nombre):
        """Actualiza el total de viviendas para un establecimiento"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE health_facilities 
                    SET total_viviendas = %s,
                        fecha_actualizacion = CURRENT_TIMESTAMP,
                        usuario_actualizacion = %s
                    WHERE cod_renipress = %s
                """, (nuevo_total, 'usuario_manual', cod_renipress))
                conn.commit()
            
            st.success(f"✅ Se actualizó {nombre} con {nuevo_total} viviendas")
            
            # CRÍTICO: Limpiar cache de cálculos para forzar recarga con datos actualizados
            if 'calculations' in st.session_state:
                del st.session_state['calculations']
            
            st.rerun()
            
        except Exception as e:
            st.error(f"Error al actualizar: {str(e)}")
    
    def _generate_excel_template(self):
        """Genera plantilla Excel con todos los establecimientos"""
        try:
            with self.get_connection() as conn:
                df = pd.read_sql("""
                    SELECT 
                        cod_renipress as "Código RENIPRESS",
                        nombre_establecimiento as "Nombre del Establecimiento",
                        total_viviendas as "Total de Viviendas"
                    FROM health_facilities 
                    WHERE activo = TRUE
                    ORDER BY nombre_establecimiento
                """, conn)
            
            # Generar archivo Excel en memoria
            output = BytesIO()
            
            # Crear el writer con el buffer
            writer = pd.ExcelWriter(output, engine='openpyxl')
            df.to_excel(writer, sheet_name='Establecimientos', index=False)
            
            # Agregar hoja de instrucciones
            instructions_df = pd.DataFrame({
                'INSTRUCCIONES': [
                    '1. No modificar la columna "Código RENIPRESS"',
                    '2. Puedes modificar el nombre del establecimiento si es necesario',
                    '3. Actualiza el "Total de Viviendas" según corresponda',
                    '4. Guarda el archivo y súbelo usando el botón "Importar Cambios"',
                    '5. El sistema validará y actualizará los datos automáticamente'
                ]
            })
            instructions_df.to_excel(writer, sheet_name='Instrucciones', index=False)
            
            # Cerrar el writer y obtener los datos
            writer.close()
            
            return output.getvalue()
            
        except Exception as e:
            st.error(f"Error al generar plantilla: {str(e)}")
            return None
    
    def _import_excel_changes(self, uploaded_file):
        """Importa cambios desde archivo Excel"""
        try:
            df = pd.read_excel(uploaded_file, sheet_name='Establecimientos')
            
            required_cols = ['Código RENIPRESS', 'Nombre del Establecimiento', 'Total de Viviendas']
            if not all(col in df.columns for col in required_cols):
                st.error(f"❌ El archivo debe contener las columnas: {required_cols}")
                return
            
            # Validar datos
            df = df.dropna(subset=['Código RENIPRESS', 'Total de Viviendas'])
            df['Total de Viviendas'] = pd.to_numeric(df['Total de Viviendas'], errors='coerce')
            df = df[df['Total de Viviendas'] >= 0]
            
            if df.empty:
                st.error("❌ No hay datos válidos para importar")
                return
            
            # Importar a la base de datos
            updated_count = 0
            errors = []
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for _, row in df.iterrows():
                    try:
                        cursor.execute("""
                            UPDATE health_facilities 
                            SET nombre_establecimiento = %s,
                                total_viviendas = %s,
                                fecha_actualizacion = CURRENT_TIMESTAMP,
                                usuario_actualizacion = %s
                            WHERE cod_renipress = %s
                        """, (
                            str(row['Nombre del Establecimiento']),
                            int(row['Total de Viviendas']),
                            'excel_import',
                            int(row['Código RENIPRESS'])
                        ))
                        
                        if cursor.rowcount > 0:
                            updated_count += 1
                        
                    except Exception as e:
                        errors.append(f"Código {row['Código RENIPRESS']}: {str(e)}")
                
                conn.commit()
            
            if updated_count > 0:
                st.success(f"✅ Se actualizaron {updated_count} establecimientos exitosamente")
                
                # CRÍTICO: Limpiar cache de cálculos para forzar recarga con datos actualizados
                if 'calculations' in st.session_state:
                    del st.session_state['calculations']
            
            if errors:
                st.warning("⚠️ Algunos registros no se pudieron actualizar:")
                for error in errors[:5]:  # Mostrar solo los primeros 5 errores
                    st.text(f"• {error}")
                    
                if len(errors) > 5:
                    st.text(f"... y {len(errors) - 5} errores más")
            
            st.rerun()
            
        except Exception as e:
            st.error(f"Error al procesar el archivo: {str(e)}")
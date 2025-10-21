import streamlit as st
import pandas as pd
from datetime import datetime, date
from utils.sector_similarity import SectorSimilarityDetector

class FilterComponent:
    def __init__(self, data_processor):
        self.data_processor = data_processor
        self.sector_detector = SectorSimilarityDetector(similarity_threshold=0.8)
    
    def render_filters(self, activity_type=None):
        """Render all filter components and return selected values"""
        filters = {}
        
        st.markdown("### 🔍 Filtros de Búsqueda")
        
        # Create filter columns with reordered filters
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Year filter
            years = self.data_processor.get_unique_values('year')
            if years:
                selected_year = st.selectbox(
                    "📅 Año",
                    options=['Todos'] + [str(year) for year in years if year],
                    help="Seleccione el año de inspección",
                    key=f"year_filter_{activity_type}"
                )
                if selected_year != 'Todos':
                    filters['year'] = int(selected_year)
            
            # Department filter
            departments = self.data_processor.get_unique_values('departamento_x')
            if departments:
                selected_dept = st.selectbox(
                    "🏛️ Departamento",
                    options=['Todos'] + [dept for dept in departments if dept],
                    help="Seleccione el departamento",
                    key=f"dept_filter_{activity_type}"
                )
                if selected_dept != 'Todos':
                    filters['departamento_x'] = selected_dept
        
        with col2:
            # Province filter
            provinces = self.data_processor.get_unique_values('nombre_prov')
            if provinces:
                selected_prov = st.selectbox(
                    "🏙️ Provincia",
                    options=['Todos'] + [prov for prov in provinces if prov],
                    help="Seleccione la provincia",
                    key=f"prov_filter_{activity_type}"
                )
                if selected_prov != 'Todos':
                    filters['nombre_prov'] = selected_prov
            
            # District filter
            districts = self.data_processor.get_unique_values('distrito')
            if districts:
                selected_dist = st.selectbox(
                    "🏘️ Distrito",
                    options=['Todos'] + [dist for dist in districts if dist],
                    help="Seleccione el distrito",
                    key=f"dist_filter_{activity_type}"
                )
                if selected_dist != 'Todos':
                    filters['distrito'] = selected_dist
        
        with col3:
            # Sector filter with similarity detection by province
            if 'sector' in self.data_processor.data.columns and 'nombre_prov' in self.data_processor.data.columns:
                # Detectar similitudes agrupadas por provincia
                similar_groups_by_province = self.sector_detector.find_similar_sectors_by_province(
                    self.data_processor.data, 'sector', 'nombre_prov'
                )
                
                # Crear key único para session state
                sector_unification_key = f"sector_unification_{activity_type}"
                
                # Mostrar interfaz de unificación si hay similitudes detectadas
                sector_unification_mapping_by_province = {}
                if similar_groups_by_province and len(similar_groups_by_province) > 0:
                    with st.expander("🔍 Unificar Sectores Similares por Provincia", expanded=False):
                        sector_unification_mapping_by_province = self.sector_detector.render_sector_unification_interface_by_province(
                            similar_groups_by_province, 
                            prefix=f"sector_{activity_type}"
                        )
                
                # Obtener sectores únicos para el filtro (considerando todas las provincias)
                sectors = self.data_processor.get_unique_values('sector')
                if sectors:
                    # Aplicar unificación si existe y obtener opciones finales
                    if sector_unification_mapping_by_province:
                        # Crear mapeo plano para las opciones de filtro
                        flat_mapping = {}
                        for province_mapping in sector_unification_mapping_by_province.values():
                            flat_mapping.update(province_mapping)
                        filter_options = self.sector_detector.get_sector_filter_options(
                            sectors, flat_mapping
                        )
                    else:
                        filter_options = sorted(list(set(sectors)))
                    
                    selected_sector = st.selectbox(
                        "🏢 Sector",
                        options=['Todos'] + filter_options,
                        help="Seleccione el sector (se detectan automáticamente errores ortográficos por provincia)",
                        key=f"sector_filter_{activity_type}"
                    )
                    
                    # Siempre incluir mapeo de unificación por provincia cuando existe
                    # independientemente de si se selecciona un sector específico
                    if sector_unification_mapping_by_province:
                        filters['sector_unification_mapping_by_province'] = sector_unification_mapping_by_province
                        # Mostrar confirmación de que la unificación se aplicará
                        total_provinces = len(sector_unification_mapping_by_province)
                        total_mappings = sum(len(mapping) for mapping in sector_unification_mapping_by_province.values())
                        st.info(f"✅ Unificación configurada: {total_mappings} sectores en {total_provinces} provincia(s)")
                    
                    if selected_sector != 'Todos':
                        filters['sector'] = selected_sector
        
        with col4:
            # RENIPRESS Code filter
            renipress_codes = self.data_processor.get_unique_values('cod_renipress')
            if renipress_codes:
                selected_renipress = st.selectbox(
                    "🏥 Código RENIPRESS",
                    options=['Todos'] + [str(code) for code in renipress_codes if code],
                    help="Seleccione el código RENIPRESS",
                    key=f"renipress_filter_{activity_type}"
                )
                if selected_renipress != 'Todos':
                    filters['cod_renipress'] = int(selected_renipress)
            
            # Health facility filter
            facilities = self.data_processor.get_unique_values('localidad_eess')
            if facilities:
                selected_facility = st.selectbox(
                    "🏥 Establecimiento de Salud",
                    options=['Todos'] + [facility for facility in facilities if facility],
                    help="Seleccione el establecimiento de salud",
                    key=f"facility_filter_{activity_type}"
                )
                if selected_facility != 'Todos':
                    filters['localidad_eess'] = selected_facility
        
        # Date range filter - Visual section separator
        st.markdown('<hr class="main-section-divider">', unsafe_allow_html=True)
        st.markdown("#### 📅 Filtro por Rango de Fechas")
        
        min_date, max_date = self.data_processor.get_date_range()
        if min_date and max_date:
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Fecha de inicio",
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date,
                    key=f"start_date_{activity_type}"
                )
            with col2:
                end_date = st.date_input(
                    "Fecha de fin",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date,
                    key=f"end_date_{activity_type}"
                )
            
            # Add date range to filters
            if start_date and end_date:
                filters['date_range'] = (start_date, end_date)
        
        return filters
    
    def apply_date_filter(self, data, date_range):
        """Apply date range filter to data"""
        if date_range and 'fecha_inspeccion' in data.columns:
            start_date, end_date = date_range
            data = data[
                (data['fecha_inspeccion'].dt.date >= start_date) & 
                (data['fecha_inspeccion'].dt.date <= end_date)
            ]
        return data
    
    def render_search_filter(self, options, label, key):
        """Render a searchable selectbox"""
        # Create a text input for search
        search_term = st.text_input(f"Buscar {label}", key=f"search_{key}")
        
        # Filter options based on search term
        if search_term:
            filtered_options = [opt for opt in options if search_term.lower() in str(opt).lower()]
        else:
            filtered_options = options
        
        # Show selectbox with filtered options
        selected = st.selectbox(
            label,
            options=['Todos'] + filtered_options,
            key=key
        )
        
        return selected if selected != 'Todos' else None

import streamlit as st
import pandas as pd
from components.filters import FilterComponent
from utils.calculations import EpidemiologicalCalculations
from utils.visualizations import VisualizationHelper
from utils.powerpoint_generator import PowerPointGenerator
import plotly.express as px
from utils.download_helper import create_excel_download_button
from utils.table_helpers import create_enhanced_dataframe, safe_dataframe

class ControlLarvarioTab:
    def __init__(self, data_processor):
        self.data_processor = data_processor
        self.filter_component = FilterComponent(data_processor)
        self.calculations = EpidemiologicalCalculations(data_processor)
        self.viz_helper = VisualizationHelper()
        self.ppt_generator = PowerPointGenerator(data_processor)
    
    def render(self):
        st.header("🦟 Módulo de Control Larvario")
        st.markdown("Análisis de datos de control larvario")
        
        # Render filters
        filters = self.filter_component.render_filters('control larvario')
        
        # Get filtered data for control larvario activity
        filtered_data = self.data_processor.get_filtered_data('control larvario', filters)
        
        # Apply date range filter if present
        if 'date_range' in filters:
            filtered_data = self.filter_component.apply_date_filter(filtered_data, filters['date_range'])
        
        # Show data summary
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🏠 Total Viviendas", f"{len(filtered_data):,}")
        
        with col2:
            total_larvicide = filtered_data['consumo_larvicida'].sum() if 'consumo_larvicida' in filtered_data.columns else 0
            st.metric("🧪 Consumo Total Larvicida", f"{total_larvicide:.2f} g")
        
        with col3:
            # Calculate inspected and positive containers
            containers_stats = self.calculate_container_statistics(filtered_data)
            inspected_containers = containers_stats.get('inspected', 0)
            positive_containers = containers_stats.get('positive', 0)
            st.metric("🔍 Recipientes Inspeccionados", f"{inspected_containers:,}")
        
        with col4:
            st.metric("⚠️ Recipientes Positivos", f"{positive_containers:,}")
        
        # Additional row of metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            treated_containers = self.calculate_treated_containers(filtered_data)
            st.metric("📦 Recipientes Tratados", f"{treated_containers:,}")
        
        with col2:
            facilities = filtered_data['localidad_eess'].nunique() if 'localidad_eess' in filtered_data.columns else 0
            st.metric("🏥 Establecimientos", facilities)
        
        with col3:
            # Container frequency by type - show most common type
            container_frequency = self.get_container_frequency(filtered_data)
            if container_frequency:
                most_common_type, count = container_frequency[0]
                st.metric("📊 Tipo Más Frecuente", f"{most_common_type}")
        
        with col4:
            if positive_containers > 0 and inspected_containers > 0:
                positivity_rate = (positive_containers / inspected_containers * 100)
                st.metric("📈 % Positividad", f"{positivity_rate:.1f}%")
        
        if len(filtered_data) == 0:
            st.warning("⚠️ No se encontraron datos con los filtros seleccionados.")
            return
        
        # Sector analysis section
        self.render_sector_analysis(filtered_data)
        
        # PowerPoint generation button
        st.markdown("---")
        col_ppt1, col_ppt2, col_ppt3 = st.columns([2, 1, 2])
        with col_ppt2:
            if st.button("📄 Generar PPT", key="control_larvario_ppt", help="Generar presentación PowerPoint organizada por redes de salud"):
                self.generate_powerpoint_presentation(filtered_data)
        
        # Create tabs for different visualizations
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Cobertura de Viviendas",
            "🧪 Análisis Larvicida", 
            "📦 Tratamiento de Recipientes", 
            "🤒 Casos Febriles",
            "📈 Tendencias",
            "📊 Índice Aédico Mensual"
        ])
        
        with tab1:
            self.render_coverage_analysis_tab(filtered_data)
        
        with tab2:
            self.render_larvicide_analysis_tab(filtered_data)
        
        with tab3:
            self.render_container_treatment_tab(filtered_data)
        
        with tab4:
            self.render_febril_cases_tab(filtered_data)
        
        with tab5:
            self.render_trends_tab(filtered_data)
        
        with tab6:
            self.render_monthly_aedic_analysis_tab(filtered_data)
    
    def calculate_treated_containers(self, data):
        """Calculate total number of treated containers (TQ + TF)"""
        containers = self.data_processor.get_container_columns()
        total_treated = 0
        
        for container_type, columns in containers.items():
            tq_columns = [col for col in columns if col.endswith('_TQ')]
            tf_columns = [col for col in columns if col.endswith('_TF')]
            
            for col in tq_columns + tf_columns:
                if col in data.columns:
                    total_treated += data[col].sum()
        
        return int(total_treated)
    
    def render_coverage_analysis_tab(self, filtered_data):
        st.subheader("📊 Análisis de Cobertura de Viviendas")
        
        # Calculate coverage percentages
        coverage_data = self.calculations.calculate_coverage_percentages(filtered_data)
        
        if not coverage_data.empty:
            # Display summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                avg_coverage = coverage_data['cobertura_total'].mean()
                st.metric("📈 Cobertura Promedio", f"{avg_coverage:.1f}%")
            
            with col2:
                total_inspected = coverage_data['viv_inspeccionadas'].sum()
                st.metric("🏠 Total Inspeccionadas", f"{total_inspected:,}")
            
            with col3:
                total_closed = coverage_data['viv_cerradas'].sum()
                st.metric("🚪 Total Cerradas", f"{total_closed:,}")
            
            with col4:
                total_reluctant = coverage_data['viv_renuentes'].sum()
                st.metric("🚫 Total Renuentes", f"{total_reluctant:,}")
            
            # Coverage visualization
            import plotly.express as px
            
            # Create stacked bar chart for coverage
            coverage_melted = coverage_data.melt(
                id_vars=['localidad_eess'],
                value_vars=['porc_inspeccionadas', 'porc_cerradas', 'porc_renuentes', 
                           'porc_deshabitadas', 'porc_no_intervenidas'],
                var_name='status_type',
                value_name='percentage'
            )
            
            # Rename categories for better display
            status_mapping = {
                'porc_inspeccionadas': 'Inspeccionadas',
                'porc_cerradas': 'Cerradas',
                'porc_renuentes': 'Renuentes',
                'porc_deshabitadas': 'Deshabitadas',
                'porc_no_intervenidas': 'No Intervenidas'
            }
            coverage_melted['status_type'] = coverage_melted['status_type'].replace(status_mapping)
            
            fig = px.bar(
                coverage_melted,
                x='localidad_eess',
                y='percentage',
                color='status_type',
                title='Porcentaje de Cobertura por Establecimiento y Tipo',
                labels={
                    'percentage': 'Porcentaje (%)',
                    'localidad_eess': 'Establecimiento de Salud',
                    'status_type': 'Tipo de Vivienda'
                },
                text='percentage'
            )
            
            # Add value labels
            fig.update_traces(
                texttemplate='%{text:.0f}%',
                textposition='inside'
            )
            
            fig.update_layout(
                xaxis={'tickangle': 45},
                height=600,
                barmode='stack'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display detailed table
            st.subheader("📋 Detalle de Cobertura por Establecimiento")
            coverage_table_data = coverage_data.round(2)
            
            # Agregar fila de totales
            enhanced_coverage_data = create_enhanced_dataframe(
                coverage_table_data,
                label_column='localidad_eess',
                exclude_from_total=['cod_renipress', 'cobertura_total', 'porc_inspeccionadas', 'porc_cerradas', 'porc_renuentes', 'porc_deshabitadas', 'porc_no_intervenidas']  # Excluir porcentajes
            )
            
            safe_dataframe(
                enhanced_coverage_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'cod_renipress': 'Código RENIPRESS',
                    'localidad_eess': 'Establecimiento',
                    'total_houses': 'Total Viviendas',
                    'cobertura_total': 'Cobertura Total (%)',
                    'porc_inspeccionadas': 'Inspeccionadas (%)',
                    'porc_cerradas': 'Cerradas (%)',
                    'porc_renuentes': 'Renuentes (%)',
                    'porc_deshabitadas': 'Deshabitadas (%)',
                    'porc_no_intervenidas': 'No Intervenidas (%)'
                }
            )
            
            # Botón de descarga XLSX
            create_excel_download_button(
                coverage_table_data, 
                "cobertura_establecimientos_control_larvario", 
                "📥 Descargar Cobertura XLSX",
                "coverage_control"
            )
        else:
            st.info("No hay suficientes datos para calcular la cobertura.")
    
    def render_febril_cases_tab(self, filtered_data):
        st.subheader("🤒 Análisis de Casos Febriles")
        
        # Calculate febril cases
        facility_febriles, total_febriles = self.calculations.calculate_febril_cases(filtered_data)
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.metric("🌡️ Total Casos Febriles", f"{total_febriles:,}")
            
            if not facility_febriles.empty:
                avg_febriles = facility_febriles['febriles'].mean()
                st.metric("📊 Promedio por Establecimiento", f"{avg_febriles:.1f}")
                
                max_febriles = facility_febriles['febriles'].max()
                st.metric("📈 Mayor Cantidad", f"{max_febriles:,}")
        
        with col2:
            if not facility_febriles.empty:
                # Display chart for top facilities with febril cases
                top_febriles = facility_febriles.head(15)
                
                import plotly.express as px
                fig = px.bar(
                    top_febriles,
                    x='febriles',
                    y='localidad_eess',
                    orientation='h',
                    title='Casos Febriles por Establecimiento (Top 15)',
                    labels={
                        'febriles': 'Casos Febriles',
                        'localidad_eess': 'Establecimiento de Salud'
                    },
                    color='febriles',
                    color_continuous_scale='Reds'
                )
                
                # Add value labels
                fig.update_traces(
                    texttemplate='%{x}',
                    textposition='outside'
                )
                
                fig.update_layout(height=500, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        # Display table
        if not facility_febriles.empty:
            st.subheader("📋 Casos Febriles por Establecimiento")
            
            # Agregar fila de totales
            enhanced_febriles = create_enhanced_dataframe(
                facility_febriles,
                label_column='localidad_eess',
                exclude_from_total=['cod_renipress']  # Solo excluir códigos - casos febriles sí se pueden sumar
            )
            
            safe_dataframe(
                enhanced_febriles,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'cod_renipress': 'Código RENIPRESS',
                    'localidad_eess': 'Establecimiento',
                    'febriles': 'Casos Febriles'
                }
            )
        else:
            st.info("No hay datos de casos febriles disponibles.")
    
    def render_trends_tab(self, filtered_data):
        st.subheader("📈 Tendencias de Control Larvario")
        
        # Calculate monthly trends
        monthly_data = self.calculations.calculate_monthly_trends(filtered_data)
        
        if not monthly_data.empty:
            # Display chart
            fig = self.viz_helper.create_monthly_trends_chart(monthly_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # Display table
            st.subheader("📋 Datos Mensuales")
            display_data = monthly_data.copy()
            display_data['aedic_index'] = display_data['aedic_index'].round(2)
            display_data['consumo_larvicida'] = display_data['consumo_larvicida'].round(2)
            
            # Agregar fila de totales
            enhanced_monthly_trends = create_enhanced_dataframe(
                display_data[['month_year_str', 'atencion_vivienda_indicador', 
                            'viv_positiva', 'aedic_index', 'consumo_larvicida']],
                label_column='month_year_str',
                exclude_from_total=['aedic_index']  # Excluir porcentajes
            )
            
            safe_dataframe(
                enhanced_monthly_trends,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'month_year_str': 'Mes/Año',
                    'atencion_vivienda_indicador': 'Viviendas Inspeccionadas',
                    'viv_positiva': 'Viviendas Positivas',
                    'aedic_index': 'Índice Aédico (%)',
                    'consumo_larvicida': 'Consumo Larvicida (g)'
                }
            )
        else:
            st.info("No hay datos suficientes para mostrar tendencias mensuales.")
    
    def render_larvicide_analysis_tab(self, filtered_data):
        st.subheader("🧪 Análisis de Consumo de Larvicida")
        
        # Calculate larvicide consumption
        facility_consumption, total_consumption = self.calculations.calculate_larvicide_consumption(filtered_data)
        
        # Display total consumption metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("💊 Consumo Total", f"{total_consumption:.2f} g")
        
        with col2:
            if not facility_consumption.empty:
                avg_consumption = facility_consumption['consumo_larvicida'].mean()
                st.metric("📊 Consumo Promedio", f"{avg_consumption:.2f} g")
        
        with col3:
            if not facility_consumption.empty:
                facilities_count = len(facility_consumption)
                st.metric("🏥 Establecimientos Activos", facilities_count)
        
        if not facility_consumption.empty:
            # Display consumption chart
            fig = self.viz_helper.create_larvicide_consumption_chart(facility_consumption)
            st.plotly_chart(fig, use_container_width=True)
            
            # Efficiency analysis
            st.subheader("📈 Análisis de Eficiencia")
            
            # Calculate efficiency metrics
            efficiency_data = facility_consumption.copy()
            efficiency_data['efficiency_score'] = efficiency_data['consumo_larvicida'] / (efficiency_data['consumo_larvicida'].max() if efficiency_data['consumo_larvicida'].max() > 0 else 1)
            
            # Display efficiency table
            
            # Agregar fila de totales
            enhanced_efficiency = create_enhanced_dataframe(
                efficiency_data.round(3),
                label_column='localidad_eess',
                exclude_from_total=['cod_renipress', 'efficiency_rating']  # Excluir códigos y ratings
            )
            
            safe_dataframe(
                enhanced_efficiency,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'cod_renipress': 'Código RENIPRESS',
                    'localidad_eess': 'Establecimiento',
                    'consumo_larvicida': 'Consumo Larvicida (g)',
                    'efficiency_score': 'Score de Eficiencia'
                }
            )
        else:
            st.info("No hay datos de consumo de larvicida disponibles.")
    
    def render_container_treatment_tab(self, filtered_data):
        st.subheader("📦 Análisis de Tratamiento de Recipientes")
        
        # Calculate treatment statistics
        treatment_stats = self.calculate_treatment_statistics(filtered_data)
        
        if treatment_stats:
            # Display treatment summary
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("🧪 Tratamiento Químico", f"{treatment_stats['chemical']:,}")
            
            with col2:
                st.metric("⚙️ Tratamiento Físico", f"{treatment_stats['physical']:,}")
            
            with col3:
                total_treated = treatment_stats['chemical'] + treatment_stats['physical']
                st.metric("✅ Total Tratados", f"{total_treated:,}")
            
            with col4:
                if total_treated > 0:
                    chemical_percentage = (treatment_stats['chemical'] / total_treated * 100)
                    st.metric("🧪 % Químico", f"{chemical_percentage:.1f}%")
            
            # Container type analysis
            container_treatment_data = self.calculate_container_type_treatment(filtered_data)
            
            if not container_treatment_data.empty:
                # Create visualization
                fig = self.viz_helper.create_container_statistics_chart(container_treatment_data)
                st.plotly_chart(fig, use_container_width=True)
                
                # Display detailed table
                st.subheader("📋 Detalle por Tipo de Recipiente")
                
                # Agregar fila de totales
                enhanced_container_treatment = create_enhanced_dataframe(
                    container_treatment_data,
                    label_column='container_type',
                    exclude_from_total=['treatment_effectiveness']  # Excluir efectividad si existe
                )
                
                safe_dataframe(
                    enhanced_container_treatment,
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("No hay datos de tratamiento de recipientes disponibles.")
    
    def render_facility_performance_tab(self, filtered_data):
        st.subheader("📈 Rendimiento por Establecimiento")
        
        # Calculate performance metrics by facility
        performance_data = self.calculate_facility_performance(filtered_data)
        
        if not performance_data.empty:
            # Display performance chart
            import plotly.express as px
            
            fig = px.bar(
                performance_data.sort_values('total_activities', ascending=True),
                x='total_activities',
                y='localidad_eess',
                orientation='h',
                title='Actividades de Control Larvario por Establecimiento',
                labels={
                    'total_activities': 'Total de Actividades',
                    'localidad_eess': 'Establecimiento de Salud'
                },
                color='efficiency_rating',
                color_continuous_scale='RdYlGn'
            )
            
            fig.update_layout(height=max(400, len(performance_data) * 25))
            st.plotly_chart(fig, use_container_width=True)
            
            # Display performance table
            st.subheader("📊 Tabla de Rendimiento")
            
            # Agregar fila de totales
            enhanced_performance = create_enhanced_dataframe(
                performance_data.round(2),
                label_column='localidad_eess',
                exclude_from_total=['cod_renipress', 'efficiency_rating']  # Excluir códigos y ratings
            )
            
            safe_dataframe(
                enhanced_performance,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'cod_renipress': 'Código RENIPRESS',
                    'localidad_eess': 'Establecimiento',
                    'total_activities': 'Total Actividades',
                    'larvicide_used': 'Larvicida Usado',
                    'containers_treated': 'Recipientes Tratados',
                    'efficiency_rating': 'Rating de Eficiencia'
                }
            )
        else:
            st.info("No hay suficientes datos para calcular el rendimiento por establecimiento.")
    
    def render_activity_summary_tab(self, filtered_data):
        st.subheader("📊 Resumen de Actividades de Control Larvario")
        
        # General statistics
        summary_stats = self.calculate_activity_summary(filtered_data)
        
        # Display summary metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Métricas Generales")
            for metric, value in summary_stats.items():
                if isinstance(value, (int, float)):
                    st.metric(metric, f"{value:,.2f}" if isinstance(value, float) else f"{value:,}")
        
        with col2:
            st.subheader("🎯 Distribución de Actividades")
            
            # Create pie chart for activity distribution
            if 'activity_distribution' in summary_stats:
                import plotly.express as px
                
                fig = px.pie(
                    values=list(summary_stats['activity_distribution'].values()),
                    names=list(summary_stats['activity_distribution'].keys()),
                    title='Distribución de Tipos de Tratamiento'
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        # Monthly trends for control larvario
        monthly_trends = self.calculations.calculate_monthly_trends(filtered_data)
        
        if not monthly_trends.empty:
            st.subheader("📈 Tendencias Mensuales")
            fig = self.viz_helper.create_monthly_trends_chart(monthly_trends)
            st.plotly_chart(fig, use_container_width=True)
    
    def calculate_treatment_statistics(self, data):
        """Calculate treatment statistics"""
        containers = self.data_processor.get_container_columns()
        
        chemical_treatment = 0
        physical_treatment = 0
        
        for container_type, columns in containers.items():
            for col in columns:
                if col in data.columns:
                    if col.endswith('_TQ'):
                        chemical_treatment += data[col].sum()
                    elif col.endswith('_TF'):
                        physical_treatment += data[col].sum()
        
        return {
            'chemical': int(chemical_treatment),
            'physical': int(physical_treatment)
        }
    
    def calculate_container_type_treatment(self, data):
        """Calculate treatment statistics by container type"""
        containers = self.data_processor.get_container_columns()
        results = []
        
        for container_type, columns in containers.items():
            stats = {'container_type': container_type}
            
            tq_cols = [col for col in columns if col.endswith('_TQ')]
            tf_cols = [col for col in columns if col.endswith('_TF')]
            
            stats['Tratamiento Químico'] = sum(data[col].sum() for col in tq_cols if col in data.columns)
            stats['Tratamiento Físico'] = sum(data[col].sum() for col in tf_cols if col in data.columns)
            
            results.append(stats)
        
        return pd.DataFrame(results)
    
    def calculate_facility_performance(self, data):
        """Calculate performance metrics by facility"""
        if data.empty:
            return pd.DataFrame()
        
        performance_data = []
        
        for facility in data['localidad_eess'].unique():
            facility_data = data[data['localidad_eess'] == facility]
            
            # Get RENIPRESS code
            renipress_code = facility_data['cod_renipress'].iloc[0] if len(facility_data) > 0 else 0
            
            # Calculate metrics
            total_activities = len(facility_data)
            larvicide_used = facility_data['consumo_larvicida'].sum() if 'consumo_larvicida' in facility_data.columns else 0
            containers_treated = self.calculate_treated_containers(facility_data)
            
            # Calculate efficiency rating (0-10 scale)
            efficiency_rating = min(10, (containers_treated / max(1, total_activities)) * 5)
            
            performance_data.append({
                'cod_renipress': renipress_code,
                'localidad_eess': facility,
                'total_activities': total_activities,
                'larvicide_used': larvicide_used,
                'containers_treated': containers_treated,
                'efficiency_rating': efficiency_rating
            })
        
        return pd.DataFrame(performance_data)
    
    def calculate_activity_summary(self, data):
        """Calculate summary statistics for activities"""
        summary = {}
        
        # Basic counts
        summary['Total Registros'] = len(data)
        summary['Establecimientos Únicos'] = data['localidad_eess'].nunique() if 'localidad_eess' in data.columns else 0
        
        # Treatment statistics
        treatment_stats = self.calculate_treatment_statistics(data)
        summary['Tratamiento Químico Total'] = treatment_stats['chemical']
        summary['Tratamiento Físico Total'] = treatment_stats['physical']
        
        # Larvicide consumption
        summary['Consumo Total Larvicida'] = data['consumo_larvicida'].sum() if 'consumo_larvicida' in data.columns else 0
        
        # Activity distribution
        total_treatments = treatment_stats['chemical'] + treatment_stats['physical']
        if total_treatments > 0:
            summary['activity_distribution'] = {
                'Químico': treatment_stats['chemical'],
                'Físico': treatment_stats['physical']
            }
        
        return summary

    def calculate_container_statistics(self, data):
        """Calculate total inspected and positive containers"""
        containers = self.data_processor.get_container_columns()
        
        total_inspected = 0
        total_positive = 0
        
        for container_type, columns in containers.items():
            # Count inspected containers (columns ending with _I)
            inspected_cols = [col for col in columns if col.endswith('_I') and col in data.columns]
            for col in inspected_cols:
                total_inspected += data[col].sum()
            
            # Count positive containers (columns ending with _P)
            positive_cols = [col for col in columns if col.endswith('_P') and col in data.columns]
            for col in positive_cols:
                total_positive += data[col].sum()
        
        return {
            'inspected': int(total_inspected),
            'positive': int(total_positive)
        }

    def get_container_frequency(self, data):
        """Get container frequency by type, sorted by most common"""
        containers = self.data_processor.get_container_columns()
        container_counts = []
        
        for container_type, columns in containers.items():
            # Count all containers for this type (sum all columns)
            total_count = 0
            for col in columns:
                if col in data.columns:
                    total_count += data[col].sum()
            
            if total_count > 0:
                container_counts.append((container_type, int(total_count)))
        
        # Sort by count (descending)
        container_counts.sort(key=lambda x: x[1], reverse=True)
        return container_counts
    
    def generate_powerpoint_presentation(self, filtered_data):
        """Genera presentación PowerPoint con datos organizados por redes de salud"""
        try:
            with st.spinner("🔄 Generando presentación PowerPoint..."):
                # Generar presentación
                presentation = self.ppt_generator.generate_presentation(filtered_data)
                
                # Guardar presentación
                filename = self.ppt_generator.save_presentation(presentation)
                
                st.success(f"✅ Presentación generada exitosamente: {filename}")
                
                # Leer archivo para descarga automática
                with open(filename, "rb") as file:
                    file_data = file.read()
                
                # Generar nombre de archivo para descarga
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                download_filename = f"reporte_control_larvario_{timestamp}.pptx"
                
                # Botón de descarga automática
                st.download_button(
                    label="📥 Descargar Presentación PowerPoint",
                    data=file_data,
                    file_name=download_filename,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    key="download_ppt_control_larvario",
                    help="Hacer clic para descargar automáticamente la presentación"
                )
                
                # Información adicional
                st.info(f"""
                📄 **Presentación PowerPoint creada**
                
                **Contenido incluido:**
                - 📋 Diapositiva de título con resumen general
                - 📊 Resumen estadístico del sistema
                - 🌐 Análisis por cada red de salud:
                  * RED UTCUBAMBA
                  * RED BAGUA  
                  * RED CONDORCANQUI
                  * RED CHACHAPOYAS
                - 🏥 Detalle por establecimientos de salud
                - 📈 Métricas de cobertura y eficiencia
                
                **Archivo guardado en:** `{filename}`
                **Haz clic en el botón de arriba para descargar automáticamente**
                """)
                
        except Exception as e:
            st.error(f"❌ Error al generar presentación: {str(e)}")
    
    def render_monthly_aedic_analysis_tab(self, filtered_data):
        """Renderiza análisis de índice aédico mensual por establecimiento"""
        st.subheader("📊 Análisis de Índice Aédico Mensual por Establecimiento")
        st.markdown("Evolución mensual del índice aédico en cada establecimiento de salud")
        
        if 'fecha_inspeccion' not in filtered_data.columns:
            st.error("❌ No se encontró la columna de fecha de inspección")
            return
        
        if len(filtered_data) == 0:
            st.warning("⚠️ No hay datos disponibles para el análisis mensual")
            return
        
        try:
            # Preparar datos para análisis mensual
            monthly_data = self._prepare_monthly_aedic_data(filtered_data)
            
            if monthly_data.empty:
                st.warning("⚠️ No se pudieron calcular índices aédicos mensuales")
                return
            
            # Selector de establecimiento
            establishments = sorted(monthly_data['establecimiento'].unique())
            selected_establishment = st.selectbox(
                "🏥 Seleccionar Establecimiento:",
                establishments,
                key="monthly_aedic_establishment_control"
            )
            
            # Filtrar datos del establecimiento seleccionado
            establishment_data = monthly_data[monthly_data['establecimiento'] == selected_establishment]
            
            # Métricas resumen del establecimiento
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                avg_aedic = establishment_data['indice_aedico'].mean()
                st.metric("📊 IA Promedio", f"{avg_aedic:.2f}%")
            
            with col2:
                max_aedic = establishment_data['indice_aedico'].max()
                st.metric("⚠️ IA Máximo", f"{max_aedic:.2f}%")
            
            with col3:
                min_aedic = establishment_data['indice_aedico'].min()
                st.metric("✅ IA Mínimo", f"{min_aedic:.2f}%")
            
            with col4:
                total_months = len(establishment_data)
                st.metric("📅 Meses Analizados", f"{total_months}")
            
            # Gráfico de evolución mensual
            st.subheader(f"📈 Evolución Mensual - {selected_establishment}")
            
            fig = px.line(
                establishment_data,
                x='mes_year',
                y='indice_aedico',
                title=f'Índice Aédico Mensual - {selected_establishment}',
                labels={
                    'indice_aedico': 'Índice Aédico (%)',
                    'mes_year': 'Mes'
                },
                markers=True
            )
            
            # Agregar línea de umbral (ejemplo: 4%)
            fig.add_hline(y=4, line_dash="dash", line_color="red", 
                         annotation_text="Umbral de riesgo (4%)")
            
            # Agregar valores en los puntos
            fig.update_traces(
                texttemplate='%{y:.1f}%',
                textposition='top center'
            )
            
            fig.update_layout(
                height=400,
                xaxis_title="Mes",
                yaxis_title="Índice Aédico (%)"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"❌ Error en el análisis mensual: {str(e)}")
    
    def _prepare_monthly_aedic_data(self, filtered_data):
        """Prepara datos para análisis de índice aédico mensual"""
        try:
            # Filtrar solo datos con fecha válida
            data_with_date = filtered_data.dropna(subset=['fecha_inspeccion'])
            
            if data_with_date.empty:
                return pd.DataFrame()
            
            # Crear columna de mes-año
            data_with_date = data_with_date.copy()
            data_with_date['mes_year'] = data_with_date['fecha_inspeccion'].dt.to_period('M').astype(str)
            
            # Obtener nombres de establecimientos
            establishment_names = {}
            for est_id, info in self.data_processor.health_facilities.items():
                establishment_names[est_id] = info['name']
            
            # Agrupar por establecimiento y mes
            monthly_aedic = []
            
            for establecimiento_id in data_with_date['cod_renipress'].unique():
                establecimiento_nombre = establishment_names.get(establecimiento_id, f"Establecimiento {establecimiento_id}")
                
                est_data = data_with_date[data_with_date['cod_renipress'] == establecimiento_id]
                
                # Agrupar por mes
                monthly_groups = est_data.groupby('mes_year')
                
                for mes, mes_data in monthly_groups:
                    # Calcular viviendas inspeccionadas y positivas
                    viviendas_inspeccionadas = len(mes_data[mes_data['atencion_vivienda_indicador'] == 1])
                    viviendas_positivas = len(mes_data[
                        (mes_data['atencion_vivienda_indicador'] == 1) & 
                        (mes_data['viv_positiva'] == 1)
                    ])
                    
                    # Calcular índice aédico
                    if viviendas_inspeccionadas > 0:
                        indice_aedico = (viviendas_positivas / viviendas_inspeccionadas) * 100
                    else:
                        indice_aedico = 0
                    
                    monthly_aedic.append({
                        'establecimiento_id': establecimiento_id,
                        'establecimiento': establecimiento_nombre,
                        'mes_year': mes,
                        'viviendas_inspeccionadas': viviendas_inspeccionadas,
                        'viviendas_positivas': viviendas_positivas,
                        'indice_aedico': indice_aedico
                    })
            
            return pd.DataFrame(monthly_aedic)
            
        except Exception as e:
            st.error(f"Error preparando datos mensuales: {str(e)}")
            return pd.DataFrame()
    
    def render_sector_analysis(self, filtered_data):
        """Render sector-specific analysis for Control Larvario"""
        if 'sector' not in filtered_data.columns:
            return
        
        # Check if there are sector data
        sectors = filtered_data['sector'].dropna()
        if len(sectors) == 0:
            return
        
        st.markdown("---")
        st.subheader("🏢 Análisis por Sector - Control Larvario")
        
        # Sector summary metrics for larval control
        agg_dict = {
            'atencion_vivienda_indicador': 'count',  # Total registros
            'viv_positiva': 'sum'  # Viviendas positivas
        }
        
        # Only include larvicide consumption if column exists
        if 'consumo_larvicida' in filtered_data.columns:
            agg_dict['consumo_larvicida'] = 'sum'
        
        sector_summary = filtered_data.groupby('sector').agg(agg_dict).reset_index()
        
        # Add larvicide columns if they exist, otherwise set to 0
        if 'consumo_larvicida' not in sector_summary.columns:
            sector_summary['consumo_larvicida'] = 0
        
        # Calculate coverage and effectiveness metrics
        sector_summary['consumo_promedio'] = (
            sector_summary['consumo_larvicida'] / sector_summary['atencion_vivienda_indicador']
        ).fillna(0)
        
        sector_summary['positividad_pct'] = (
            sector_summary['viv_positiva'] / sector_summary['atencion_vivienda_indicador'] * 100
        ).fillna(0)
        
        sector_summary = sector_summary.sort_values('atencion_vivienda_indicador', ascending=False)
        
        # Display sector metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🧪 Top 5 Sectores por Consumo de Larvicida**")
            top_larvicide = sector_summary.sort_values('consumo_larvicida', ascending=False).head(5)
            
            for _, row in top_larvicide.iterrows():
                sector_name = row['sector']
                total_consumption = row['consumo_larvicida']
                avg_consumption = row['consumo_promedio']
                total_records = int(row['atencion_vivienda_indicador'])
                
                st.markdown(f"""
                **{sector_name}**  
                🧪 {total_consumption:.1f}g total | 📊 {avg_consumption:.1f}g promedio | 🏠 {total_records:,} viviendas
                """)
        
        with col2:
            st.markdown("**⚡ Sectores con Mayor Eficiencia (Menor Positividad)**")
            efficient_sectors = sector_summary[sector_summary['atencion_vivienda_indicador'] >= 10].sort_values(
                'positividad_pct', ascending=True
            ).head(5)
            
            for _, row in efficient_sectors.iterrows():
                sector_name = row['sector']
                positivity = row['positividad_pct']
                consumption = row['consumo_promedio']
                
                color = "🟢" if positivity < 5 else "🟡" if positivity < 10 else "🔴"
                st.markdown(f"""
                **{sector_name}** {color}  
                📈 {positivity:.1f}% positividad | 🧪 {consumption:.1f}g promedio
                """)
        
        # Sector visualizations for larval control
        if len(sector_summary) > 1:
            st.markdown("---")
            st.subheader("📈 Visualización por Sector - Control Larvario")
            
            viz_col1, viz_col2 = st.columns(2)
            
            with viz_col1:
                # Bar chart of larvicide consumption by sector
                import plotly.express as px
                
                fig_larvicide = px.bar(
                    sector_summary.head(10),
                    x='sector',
                    y='consumo_larvicida',
                    title='Top 10 Sectores por Consumo de Larvicida',
                    labels={'consumo_larvicida': 'Consumo de Larvicida (g)', 'sector': 'Sector'},
                    color='consumo_larvicida',
                    color_continuous_scale='Greens'
                )
                fig_larvicide.update_layout(
                    xaxis_tickangle=-45,
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig_larvicide, use_container_width=True)
            
            with viz_col2:
                # Efficiency analysis: consumption vs positivity
                fig_efficiency = px.scatter(
                    sector_summary,
                    x='consumo_promedio',
                    y='positividad_pct',
                    hover_data=['sector', 'atencion_vivienda_indicador'],
                    title='Eficiencia: Consumo Promedio vs Positividad',
                    labels={
                        'consumo_promedio': 'Consumo Promedio de Larvicida (g)',
                        'positividad_pct': 'Porcentaje de Positividad',
                        'sector': 'Sector'
                    },
                    color='atencion_vivienda_indicador',
                    color_continuous_scale='Blues',
                    size='atencion_vivienda_indicador',
                    size_max=15
                )
                fig_efficiency.update_layout(height=400)
                st.plotly_chart(fig_efficiency, use_container_width=True)

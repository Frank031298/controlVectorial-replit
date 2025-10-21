import streamlit as st
import pandas as pd
from components.filters import FilterComponent
from utils.calculations import EpidemiologicalCalculations
from utils.visualizations import VisualizationHelper
from utils.powerpoint_generator import PowerPointGenerator
import plotly.express as px
from utils.download_helper import create_excel_download_button
from utils.table_helpers import create_enhanced_dataframe, safe_dataframe

class CercoTab:
    def __init__(self, data_processor):
        self.data_processor = data_processor
        self.filter_component = FilterComponent(data_processor)
        self.calculations = EpidemiologicalCalculations(data_processor)
        self.viz_helper = VisualizationHelper()
        self.ppt_generator = PowerPointGenerator(data_processor)
    
    def render(self):
        st.header("🔒 Módulo de Cerco")
        st.markdown("Análisis de datos de actividades de cerco epidemiológico")
        
        # Render filters
        filters = self.filter_component.render_filters('cerco')
        
        # Get filtered data for cerco activity
        filtered_data = self.data_processor.get_filtered_data('cerco', filters)
        
        # Apply date range filter if present
        if 'date_range' in filters:
            filtered_data = self.filter_component.apply_date_filter(filtered_data, filters['date_range'])
        
        # Show data summary
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total Registros", f"{len(filtered_data):,}")
        
        with col2:
            # Calculate houses under cerco intervention
            houses_cerco = len(filtered_data[filtered_data['atencion_vivienda_indicador'].isin([1, 2, 3, 4])])
            st.metric("🏠 Viviendas en Cerco", f"{houses_cerco:,}")
        
        with col3:
            # Calculate positive detections in cerco
            positive_cerco = len(filtered_data[
                (filtered_data['viv_positiva'] == 1) & 
                (filtered_data['atencion_vivienda_indicador'] == 1)
            ])
            st.metric("⚠️ Detecciones Positivas", f"{positive_cerco:,}")
        
        with col4:
            # Calculate cerco effectiveness
            if houses_cerco > 0:
                effectiveness = ((houses_cerco - positive_cerco) / houses_cerco * 100)
                st.metric("🎯 Efectividad", f"{effectiveness:.1f}%")
            else:
                st.metric("🎯 Efectividad", "0.0%")
        
        if len(filtered_data) == 0:
            st.warning("⚠️ No se encontraron datos con los filtros seleccionados.")
            return
        
        # Sector analysis section
        self.render_sector_analysis(filtered_data)
        
        # PowerPoint generation button
        st.markdown("---")
        col_ppt1, col_ppt2, col_ppt3 = st.columns([2, 1, 2])
        with col_ppt2:
            if st.button("📄 Generar PPT", key="cerco_ppt", help="Generar presentación PowerPoint organizada por redes de salud"):
                self.generate_powerpoint_presentation(filtered_data)
        
        # Create tabs for different visualizations
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Cobertura de Viviendas",
            "📦 Análisis de Recipientes",
            "🧪 Consumo Larvicida",
            "🤒 Casos Febriles",
            "📈 Tendencias",
            "📊 Índice Aédico Mensual"
        ])
        
        with tab1:
            self.render_coverage_analysis_tab(filtered_data)
        
        with tab2:
            self.render_container_analysis_tab(filtered_data)
        
        with tab3:
            self.render_larvicide_analysis_tab(filtered_data)
        
        with tab4:
            self.render_febril_cases_tab(filtered_data)
        
        with tab5:
            self.render_trends_tab(filtered_data)
        
        with tab6:
            self.render_monthly_aedic_analysis_tab(filtered_data)
    
    def render_coverage_analysis_tab(self, filtered_data):
        st.subheader("📊 Análisis de Cobertura de Viviendas - Cerco")
        
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
                title='Porcentaje de Cobertura por Establecimiento y Tipo - Cerco',
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
                exclude_from_total=['cod_renipress', 'cobertura_total', 'porc_inspeccionadas', 'porc_cerradas', 'porc_renuentes', 'porc_deshabitadas', 'porc_no_intervenidas']  # Excluir TODOS los porcentajes
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
                "cobertura_establecimientos_cerco", 
                "📥 Descargar Cobertura XLSX",
                "coverage_cerco"
            )
        else:
            st.info("No hay suficientes datos para calcular la cobertura.")

    def render_container_analysis_tab(self, filtered_data):
        st.subheader("📦 Análisis de Recipientes - Cerco")
        
        # Calculate container statistics
        container_data = self.calculations.calculate_container_statistics(filtered_data)
        
        if not container_data.empty:
            # Display chart
            fig = self.viz_helper.create_container_statistics_chart(container_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # Display table
            st.subheader("📋 Detalle por Tipo de Recipiente")
            
            # Agregar fila de totales
            enhanced_container_data = create_enhanced_dataframe(
                container_data,
                label_column='container_type',
                exclude_from_total=['container_index', 'porc_inspected', 'porc_positive', 'porc_treated', 'effectiveness_rating']  # Excluir porcentajes e índices
            )
            
            safe_dataframe(
                enhanced_container_data, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    'container_type': 'Tipo de Recipiente'
                }
            )
            
            # Container status legend
            st.subheader("📖 Leyenda de Estados")
            status_labels = self.data_processor.get_container_status_labels()
            
            cols = st.columns(len(status_labels))
            for i, (suffix, label) in enumerate(status_labels.items()):
                with cols[i]:
                    st.info(f"**{suffix}:** {label}")
        else:
            st.info("No hay datos de recipientes disponibles.")

    def render_larvicide_analysis_tab(self, filtered_data):
        st.subheader("🧪 Análisis de Consumo de Larvicida - Cerco")
        
        # Calculate larvicide consumption
        facility_consumption, total_consumption = self.calculations.calculate_larvicide_consumption(filtered_data)
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.metric("💊 Consumo Total", f"{total_consumption:.2f} g")
            
            if not facility_consumption.empty:
                avg_consumption = facility_consumption['consumo_larvicida'].mean()
                st.metric("📊 Consumo Promedio", f"{avg_consumption:.2f} g")
                
                max_consumption = facility_consumption['consumo_larvicida'].max()
                st.metric("📈 Consumo Máximo", f"{max_consumption:.2f} g")
        
        with col2:
            if not facility_consumption.empty:
                # Display chart
                fig = self.viz_helper.create_larvicide_consumption_chart(facility_consumption)
                st.plotly_chart(fig, use_container_width=True)
        
        # Display table
        if not facility_consumption.empty:
            st.subheader("📋 Consumo por Establecimiento")
            
            # Agregar fila de totales
            enhanced_consumption = create_enhanced_dataframe(
                facility_consumption.round(2),
                label_column='localidad_eess',
                exclude_from_total=['cod_renipress']
            )
            
            safe_dataframe(
                enhanced_consumption,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'cod_renipress': 'Código',
                    'localidad_eess': 'Establecimiento de Salud',
                    'consumo_larvicida': 'Consumo de Larvicida (g)'
                }
            )
        else:
            st.info("No hay datos de consumo de larvicida disponibles.")

    def render_febril_cases_tab(self, filtered_data):
        st.subheader("🤒 Análisis de Casos Febriles - Cerco")
        
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
                    title='Casos Febriles por Establecimiento (Top 15) - Cerco',
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
                exclude_from_total=['cod_renipress']
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
        st.subheader("📈 Tendencias de Cerco")
        
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
            enhanced_monthly_data = create_enhanced_dataframe(
                display_data[['month_year_str', 'atencion_vivienda_indicador', 
                            'viv_positiva', 'aedic_index', 'consumo_larvicida']],
                label_column='month_year_str',
                exclude_from_total=['aedic_index']  # Excluir porcentajes
            )
            
            safe_dataframe(
                enhanced_monthly_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'month_year_str': 'Mes/Año',
                    'atencion_vivienda_indicador': 'Viviendas Inspeccionadas',
                    'viv_positiva': 'Viviendas Positivas',
                    'aedic_index': 'Índice Aédico (%)',
                    'consumo_larvicida': 'Consumo Larvicida'
                }
            )
        else:
            st.info("No hay datos suficientes para mostrar tendencias mensuales.")
    
    def render_effectiveness_analysis_tab(self, filtered_data):
        st.subheader("🎯 Análisis de Efectividad del Cerco")
        
        # Calculate effectiveness metrics by facility
        effectiveness_data = self.calculate_cerco_effectiveness(filtered_data)
        
        if not effectiveness_data.empty:
            # Display effectiveness chart
            import plotly.express as px
            
            fig = px.bar(
                effectiveness_data.sort_values('effectiveness_percentage', ascending=True),
                x='effectiveness_percentage',
                y='localidad_eess',
                orientation='h',
                title='Efectividad del Cerco por Establecimiento (%)',
                labels={
                    'effectiveness_percentage': 'Efectividad (%)',
                    'localidad_eess': 'Establecimiento de Salud'
                },
                color='effectiveness_percentage',
                color_continuous_scale='RdYlGn'
            )
            
            # Add value labels
            fig.update_traces(
                texttemplate='%{x:.1f}%',
                textposition='outside'
            )
            
            fig.update_layout(height=max(400, len(effectiveness_data) * 25))
            st.plotly_chart(fig, use_container_width=True)
            
            # Display effectiveness table
            st.subheader("📊 Tabla de Efectividad")
            
            # Agregar fila de totales
            enhanced_effectiveness = create_enhanced_dataframe(
                effectiveness_data.round(2),
                label_column='localidad_eess',
                exclude_from_total=['cod_renipress', 'effectiveness_rating']  # Excluir códigos y ratings
            )
            
            safe_dataframe(
                enhanced_effectiveness,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'cod_renipress': 'Código RENIPRESS',
                    'localidad_eess': 'Establecimiento',
                    'total_houses': 'Total Viviendas',
                    'viviendas_positivas': 'Viviendas Positivas',
                    'effectiveness_percentage': 'Efectividad (%)',
                    'intervention_score': 'Score de Intervención'
                }
            )
            
            # Summary statistics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                avg_effectiveness = effectiveness_data['effectiveness_percentage'].mean()
                st.metric("📊 Efectividad Promedio", f"{avg_effectiveness:.1f}%")
            
            with col2:
                best_facility = effectiveness_data.loc[effectiveness_data['effectiveness_percentage'].idxmax(), 'localidad_eess']
                st.metric("🏆 Mejor Establecimiento", best_facility)
            
            with col3:
                total_interventions = effectiveness_data['total_houses'].sum()
                st.metric("🏠 Total Intervenciones", f"{total_interventions:,}")
        
        else:
            st.info("No hay suficientes datos para calcular la efectividad del cerco.")
    
    def render_geographic_coverage_tab(self, filtered_data):
        st.subheader("🗺️ Cobertura Geográfica del Cerco")
        
        # Geographic distribution analysis
        geographic_data = self.calculate_geographic_coverage(filtered_data)
        
        # Display map visualization
        fig = self.viz_helper.create_map_visualization(filtered_data)
        st.plotly_chart(fig, use_container_width=True)
        
        # Coverage statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Cobertura por Área")
            if geographic_data:
                for area, stats in geographic_data.items():
                    with st.expander(f"🏛️ {area}"):
                        st.metric("Establecimientos", stats['facilities'])
                        st.metric("Viviendas Intervenidas", stats['houses'])
                        st.metric("Efectividad", f"{stats['effectiveness']:.1f}%")
        
        with col2:
            st.subheader("🎯 Densidad de Intervención")
            
            # Calculate intervention density
            density_data = self.calculate_intervention_density(filtered_data)
            
            if not density_data.empty:
                import plotly.express as px
                
                fig = px.scatter(
                    density_data,
                    x='intervention_density',
                    y='effectiveness',
                    size='total_houses',
                    hover_data=['localidad_eess'],
                    title='Densidad vs Efectividad de Intervención',
                    labels={
                        'intervention_density': 'Densidad de Intervención',
                        'effectiveness': 'Efectividad (%)'
                    }
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    def render_cerco_indicators_tab(self, filtered_data):
        st.subheader("📈 Indicadores Específicos de Cerco")
        
        # Calculate cerco-specific indicators
        cerco_indicators = self.calculate_cerco_indicators(filtered_data)
        
        # Display key indicators
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🔍 Tasa de Detección",
                f"{cerco_indicators.get('detection_rate', 0):.2f}%"
            )
        
        with col2:
            st.metric(
                "⚡ Tiempo Respuesta Promedio",
                f"{cerco_indicators.get('avg_response_time', 0):.1f} días"
            )
        
        with col3:
            st.metric(
                "🎯 Cobertura de Cerco",
                f"{cerco_indicators.get('coverage_rate', 0):.1f}%"
            )
        
        with col4:
            st.metric(
                "🔄 Tasa de Reintervención",
                f"{cerco_indicators.get('reintervention_rate', 0):.1f}%"
            )
        
        # Cerco performance trends
        if 'fecha_inspeccion' in filtered_data.columns:
            monthly_trends = self.calculate_cerco_monthly_trends(filtered_data)
            
            if not monthly_trends.empty:
                st.subheader("📈 Tendencias de Indicadores de Cerco")
                
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots
                
                fig = make_subplots(
                    rows=2, cols=2,
                    subplot_titles=[
                        'Detecciones Mensuales',
                        'Efectividad Mensual',
                        'Cobertura Mensual',
                        'Tiempo de Respuesta'
                    ]
                )
                
                # Add traces for each indicator
                fig.add_trace(
                    go.Scatter(
                        x=monthly_trends['month_year'],
                        y=monthly_trends['detections'],
                        name='Detecciones',
                        line=dict(color='red')
                    ),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=monthly_trends['month_year'],
                        y=monthly_trends['effectiveness'],
                        name='Efectividad',
                        line=dict(color='green')
                    ),
                    row=1, col=2
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=monthly_trends['month_year'],
                        y=monthly_trends['coverage'],
                        name='Cobertura',
                        line=dict(color='blue')
                    ),
                    row=2, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=monthly_trends['month_year'],
                        y=monthly_trends['response_time'],
                        name='Tiempo Respuesta',
                        line=dict(color='orange')
                    ),
                    row=2, col=2
                )
                
                fig.update_layout(height=600, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
    
    def render_recovery_tracking_tab(self, filtered_data):
        st.subheader("🔄 Seguimiento y Recuperación")
        
        # Recovery analysis
        recovery_data = self.calculate_recovery_metrics(filtered_data)
        
        if recovery_data:
            # Display recovery metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "✅ Viviendas Recuperadas",
                    f"{recovery_data.get('recovered_houses', 0):,}"
                )
            
            with col2:
                st.metric(
                    "📈 Tasa de Recuperación",
                    f"{recovery_data.get('recovery_rate', 0):.1f}%"
                )
            
            with col3:
                st.metric(
                    "⏱️ Tiempo Promedio Recuperación",
                    f"{recovery_data.get('avg_recovery_time', 0):.1f} días"
                )
            
            # Recovery tracking table
            if 'recovery_details' in recovery_data:
                st.subheader("📋 Detalle de Recuperaciones")
                
                # Agregar fila de totales
                enhanced_recovery_details = create_enhanced_dataframe(
                    recovery_data['recovery_details'],
                    label_column='localidad_eess',
                    exclude_from_total=['cod_renipress']
                )
                
                safe_dataframe(
                    enhanced_recovery_details,
                    use_container_width=True,
                    hide_index=True
                )
        
        else:
            st.info("No hay datos de recuperación disponibles.")
        
        # Follow-up activities summary
        followup_summary = self.calculate_followup_summary(filtered_data)
        
        if followup_summary:
            st.subheader("📊 Resumen de Actividades de Seguimiento")
            
            # Display follow-up chart
            import plotly.express as px
            
            if 'activity_types' in followup_summary:
                fig = px.pie(
                    values=list(followup_summary['activity_types'].values()),
                    names=list(followup_summary['activity_types'].keys()),
                    title='Distribución de Actividades de Seguimiento'
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    def calculate_cerco_effectiveness(self, data):
        """Calculate cerco effectiveness by facility"""
        if data.empty:
            return pd.DataFrame()
        
        effectiveness_data = []
        
        for facility in data['localidad_eess'].unique():
            facility_data = data[data['localidad_eess'] == facility]
            
            # Get RENIPRESS code
            renipress_code = facility_data['cod_renipress'].iloc[0] if len(facility_data) > 0 else 0
            
            # Calculate metrics
            total_houses = len(facility_data[facility_data['atencion_vivienda_indicador'].isin([1, 2, 3, 4])])
            positive_houses = len(facility_data[
                (facility_data['viv_positiva'] == 1) & 
                (facility_data['atencion_vivienda_indicador'] == 1)
            ])
            
            # Calculate effectiveness (higher is better)
            effectiveness = ((total_houses - positive_houses) / total_houses * 100) if total_houses > 0 else 0
            
            # Calculate intervention score
            intervention_score = min(10, (total_houses / max(1, positive_houses)) * 2)
            
            effectiveness_data.append({
                'cod_renipress': renipress_code,
                'localidad_eess': facility,
                'total_houses': total_houses,
                'positive_houses': positive_houses,
                'effectiveness_percentage': effectiveness,
                'intervention_score': intervention_score
            })
        
        return pd.DataFrame(effectiveness_data)
    
    def calculate_geographic_coverage(self, data):
        """Calculate geographic coverage statistics"""
        coverage = {}
        
        if 'departamento_x' in data.columns:
            for dept in data['departamento_x'].unique():
                dept_data = data[data['departamento_x'] == dept]
                
                facilities = dept_data['localidad_eess'].nunique()
                houses = len(dept_data[dept_data['atencion_vivienda_indicador'].isin([1, 2, 3, 4])])
                positive = len(dept_data[
                    (dept_data['viv_positiva'] == 1) & 
                    (dept_data['atencion_vivienda_indicador'] == 1)
                ])
                
                effectiveness = ((houses - positive) / houses * 100) if houses > 0 else 0
                
                coverage[dept] = {
                    'facilities': facilities,
                    'houses': houses,
                    'effectiveness': effectiveness
                }
        
        return coverage
    
    def calculate_intervention_density(self, data):
        """Calculate intervention density metrics"""
        if data.empty:
            return pd.DataFrame()
        
        density_data = []
        
        for facility in data['localidad_eess'].unique():
            facility_data = data[data['localidad_eess'] == facility]
            
            # Calculate density (interventions per area unit - simplified)
            total_houses = len(facility_data[facility_data['atencion_vivienda_indicador'].isin([1, 2, 3, 4])])
            positive_houses = len(facility_data[
                (facility_data['viv_positiva'] == 1) & 
                (facility_data['atencion_vivienda_indicador'] == 1)
            ])
            
            # Simplified density calculation
            intervention_density = total_houses / max(1, len(facility_data.groupby('codigo_manzana')))
            effectiveness = ((total_houses - positive_houses) / total_houses * 100) if total_houses > 0 else 0
            
            density_data.append({
                'localidad_eess': facility,
                'intervention_density': intervention_density,
                'effectiveness': effectiveness,
                'total_houses': total_houses
            })
        
        return pd.DataFrame(density_data)
    
    def calculate_cerco_indicators(self, data):
        """Calculate cerco-specific indicators"""
        indicators = {}
        
        if not data.empty:
            # Detection rate
            total_inspected = len(data[data['atencion_vivienda_indicador'] == 1])
            positive_detected = len(data[
                (data['viv_positiva'] == 1) & 
                (data['atencion_vivienda_indicador'] == 1)
            ])
            
            indicators['detection_rate'] = (positive_detected / total_inspected * 100) if total_inspected > 0 else 0
            
            # Coverage rate (simplified)
            total_houses = len(data[data['atencion_vivienda_indicador'].isin([1, 2, 3, 4])])
            target_houses = len(data)  # Assuming all records are target houses
            indicators['coverage_rate'] = (total_houses / target_houses * 100) if target_houses > 0 else 0
            
            # Average response time (simplified - using days between creation and inspection)
            if 'fecha_inspeccion' in data.columns and '_createdAt_x' in data.columns:
                data_with_dates = data[
                    (data['fecha_inspeccion'].notna()) & 
                    (data['_createdAt_x'].notna())
                ]
                
                if not data_with_dates.empty:
                    response_times = (data_with_dates['fecha_inspeccion'] - data_with_dates['_createdAt_x']).dt.days
                    indicators['avg_response_time'] = response_times.mean()
                else:
                    indicators['avg_response_time'] = 0
            else:
                indicators['avg_response_time'] = 0
            
            # Reintervention rate (simplified)
            unique_addresses = data['dirección'].nunique() if 'dirección' in data.columns else 1
            total_interventions = len(data)
            indicators['reintervention_rate'] = ((total_interventions - unique_addresses) / unique_addresses * 100) if unique_addresses > 0 else 0
        
        return indicators
    
    def calculate_cerco_monthly_trends(self, data):
        """Calculate monthly trends for cerco indicators"""
        if 'fecha_inspeccion' not in data.columns:
            return pd.DataFrame()
        
        data['month_year'] = data['fecha_inspeccion'].dt.to_period('M')
        
        monthly_data = []
        
        for period in data['month_year'].unique():
            period_data = data[data['month_year'] == period]
            
            detections = len(period_data[
                (period_data['viv_positiva'] == 1) & 
                (period_data['atencion_vivienda_indicador'] == 1)
            ])
            
            total_houses = len(period_data[period_data['atencion_vivienda_indicador'].isin([1, 2, 3, 4])])
            effectiveness = ((total_houses - detections) / total_houses * 100) if total_houses > 0 else 0
            
            coverage = (total_houses / len(period_data) * 100) if len(period_data) > 0 else 0
            
            # Simplified response time calculation
            response_time = 5.0  # Placeholder value
            
            monthly_data.append({
                'month_year': str(period),
                'detections': detections,
                'effectiveness': effectiveness,
                'coverage': coverage,
                'response_time': response_time
            })
        
        return pd.DataFrame(monthly_data)
    
    def calculate_recovery_metrics(self, data):
        """Calculate recovery metrics"""
        recovery_data = {}
        
        if 'recuperada' in data.columns:
            # Count recovered houses
            recovered_houses = data['recuperada'].sum()
            total_positive = len(data[data['viv_positiva'] == 1])
            
            recovery_data['recovered_houses'] = int(recovered_houses)
            recovery_data['recovery_rate'] = (recovered_houses / total_positive * 100) if total_positive > 0 else 0
            
            # Calculate average recovery time
            if 'recuperacion_fecha' in data.columns and 'fecha_inspeccion' in data.columns:
                recovery_times_data = data[
                    (data['recuperacion_fecha'].notna()) & 
                    (data['fecha_inspeccion'].notna()) &
                    (data['recuperada'] == 1)
                ]
                
                if not recovery_times_data.empty:
                    recovery_times = (recovery_times_data['recuperacion_fecha'] - recovery_times_data['fecha_inspeccion']).dt.days
                    recovery_data['avg_recovery_time'] = recovery_times.mean()
                else:
                    recovery_data['avg_recovery_time'] = 0
            
            # Recovery details
            if recovered_houses > 0:
                recovery_details = data[data['recuperada'] == 1][
                    ['localidad_eess', 'dirección', 'fecha_inspeccion', 'recuperacion_fecha', 'recuperacion_usuario_asignado']
                ].copy()
                
                recovery_data['recovery_details'] = recovery_details
        
        return recovery_data
    
    def calculate_followup_summary(self, data):
        """Calculate follow-up activities summary"""
        summary = {}
        
        # Activity type distribution
        if 'atencion_vivienda_indicador' in data.columns:
            activity_counts = data['atencion_vivienda_indicador'].value_counts()
            
            activity_mapping = {
                1: "Inspección Completa",
                2: "Vivienda Cerrada", 
                3: "Vivienda Renuente",
                4: "Vivienda Deshabitada"
            }
            
            activity_types = {}
            for code, count in activity_counts.items():
                activity_name = activity_mapping.get(code, f"Código {code}")
                activity_types[activity_name] = count
            
            summary['activity_types'] = activity_types
        
        return summary
    
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
                download_filename = f"reporte_cerco_{timestamp}.pptx"
                
                # Botón de descarga automática
                st.download_button(
                    label="📥 Descargar Presentación PowerPoint",
                    data=file_data,
                    file_name=download_filename,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    key="download_ppt_cerco",
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
                key="monthly_aedic_establishment_cerco"
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
        """Render sector-specific analysis for Cerco"""
        if 'sector' not in filtered_data.columns:
            return
        
        # Check if there are sector data
        sectors = filtered_data['sector'].dropna()
        if len(sectors) == 0:
            return
        
        st.markdown("---")
        st.subheader("🏢 Análisis por Sector - Cerco Epidemiológico")
        
        # Sector summary metrics for cerco activities
        agg_dict = {
            'atencion_vivienda_indicador': 'count',  # Total registros
            'viv_positiva': 'sum'  # Viviendas positivas
        }
        
        # Only include larvicide consumption if column exists
        if 'consumo_larvicida' in filtered_data.columns:
            agg_dict['consumo_larvicida'] = 'sum'
        
        sector_summary = filtered_data.groupby('sector').agg(agg_dict).reset_index()
        
        # Add larvicide column if it doesn't exist
        if 'consumo_larvicida' not in sector_summary.columns:
            sector_summary['consumo_larvicida'] = 0
        
        # Calculate cerco effectiveness metrics
        sector_summary['positividad_pct'] = (
            sector_summary['viv_positiva'] / sector_summary['atencion_vivienda_indicador'] * 100
        ).fillna(0)
        
        sector_summary['effectiveness_pct'] = 100 - sector_summary['positividad_pct']  # Efectividad del cerco
        
        sector_summary = sector_summary.sort_values('atencion_vivienda_indicador', ascending=False)
        
        # Display sector metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🎯 Top 5 Sectores por Actividad de Cerco**")
            top_activity = sector_summary.head(5)
            
            for _, row in top_activity.iterrows():
                sector_name = row['sector']
                total_houses = int(row['atencion_vivienda_indicador'])
                positive = int(row['viv_positiva'])
                effectiveness = row['effectiveness_pct']
                
                st.markdown(f"""
                **{sector_name}**  
                🏠 {total_houses:,} viviendas | ⚠️ {positive:,} positivas | 🎯 {effectiveness:.1f}% efectividad
                """)
        
        with col2:
            st.markdown("**🏆 Sectores con Mayor Efectividad**")
            most_effective = sector_summary[sector_summary['atencion_vivienda_indicador'] >= 10].sort_values(
                'effectiveness_pct', ascending=False
            ).head(5)
            
            for _, row in most_effective.iterrows():
                sector_name = row['sector']
                effectiveness = row['effectiveness_pct']
                total_houses = int(row['atencion_vivienda_indicador'])
                
                color = "🟢" if effectiveness > 90 else "🟡" if effectiveness > 80 else "🔴"
                st.markdown(f"""
                **{sector_name}** {color}  
                🎯 {effectiveness:.1f}% efectividad | 🏠 {total_houses:,} viviendas
                """)
        
        # Sector visualizations for cerco
        if len(sector_summary) > 1:
            st.markdown("---")
            st.subheader("📈 Visualización por Sector - Cerco")
            
            viz_col1, viz_col2 = st.columns(2)
            
            with viz_col1:
                # Bar chart of cerco activity by sector
                import plotly.express as px
                
                fig_activity = px.bar(
                    sector_summary.head(10),
                    x='sector',
                    y='atencion_vivienda_indicador',
                    title='Top 10 Sectores por Actividad de Cerco',
                    labels={'atencion_vivienda_indicador': 'Viviendas Atendidas', 'sector': 'Sector'},
                    color='effectiveness_pct',
                    color_continuous_scale='RdYlGn'
                )
                fig_activity.update_layout(
                    xaxis_tickangle=-45,
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig_activity, use_container_width=True)
            
            with viz_col2:
                # Effectiveness analysis by sector
                fig_effectiveness = px.scatter(
                    sector_summary,
                    x='atencion_vivienda_indicador',
                    y='effectiveness_pct',
                    hover_data=['sector'],
                    title='Efectividad del Cerco por Sector',
                    labels={
                        'atencion_vivienda_indicador': 'Viviendas Atendidas',
                        'effectiveness_pct': 'Efectividad (%)',
                        'sector': 'Sector'
                    },
                    color='effectiveness_pct',
                    color_continuous_scale='RdYlGn',
                    size='atencion_vivienda_indicador',
                    size_max=15
                )
                fig_effectiveness.update_layout(height=400)
                st.plotly_chart(fig_effectiveness, use_container_width=True)

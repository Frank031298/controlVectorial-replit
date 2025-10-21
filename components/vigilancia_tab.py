import streamlit as st
import pandas as pd
from components.filters import FilterComponent
from utils.calculations import EpidemiologicalCalculations
from utils.visualizations import VisualizationHelper
from utils.powerpoint_generator import PowerPointGenerator
import plotly.express as px
from utils.download_helper import create_excel_download_button
from utils.table_helpers import create_enhanced_dataframe, safe_dataframe

class VigilanciaTab:
    def __init__(self, data_processor):
        self.data_processor = data_processor
        self.filter_component = FilterComponent(data_processor)
        self.calculations = EpidemiologicalCalculations(data_processor)
        self.viz_helper = VisualizationHelper()
        self.ppt_generator = PowerPointGenerator(data_processor)
    
    def render(self):
        st.header("🔍 Módulo de Vigilancia")
        st.markdown("Análisis de datos de vigilancia epidemiológica")
        
        # Render filters
        filters = self.filter_component.render_filters('vigilancia')
        
        # Get filtered data
        filtered_data = self.data_processor.get_filtered_data('vigilancia', filters)
        
        # Apply date range filter if present
        if 'date_range' in filters:
            filtered_data = self.filter_component.apply_date_filter(filtered_data, filters['date_range'])
        
        # Show data summary
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total Registros", f"{len(filtered_data):,}")
        
        with col2:
            inspected = len(filtered_data[filtered_data['atencion_vivienda_indicador'] == 1])
            st.metric("🏠 Viviendas Inspeccionadas", f"{inspected:,}")
        
        with col3:
            positive = len(filtered_data[
                (filtered_data['viv_positiva'] == 1) & 
                (filtered_data['atencion_vivienda_indicador'] == 1)
            ])
            st.metric("⚠️ Viviendas Positivas", f"{positive:,}")
        
        with col4:
            if inspected > 0:
                percentage = (positive / inspected * 100)
                st.metric("📈 % Positividad", f"{percentage:.2f}%")
            else:
                st.metric("📈 % Positividad", "0.00%")
        
        if len(filtered_data) == 0:
            st.warning("⚠️ No se encontraron datos con los filtros seleccionados.")
            return
        
        # Sector analysis section
        self.render_sector_analysis(filtered_data)
        
        # PowerPoint generation button
        st.markdown("---")
        col_ppt1, col_ppt2, col_ppt3 = st.columns([2, 1, 2])
        with col_ppt2:
            if st.button("📄 Generar PPT", key="vigilancia_ppt", help="Generar presentación PowerPoint organizada por redes de salud"):
                self.generate_powerpoint_presentation(filtered_data)
        
        # Create tabs for different visualizations
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "📊 Índices Entomológicos", 
            "📦 Recipientes", 
            "🧪 Larvicida", 
            "📈 Tendencias",
            "🗺️ Mapa",
            "📊 Índices Detalle",
            "📅 Días de Vigilancia",
            "📊 Índice Aédico Mensual"
        ])
        
        with tab1:
            self.render_entomological_indices_tab(filtered_data)
        
        with tab2:
            self.render_containers_tab(filtered_data)
        
        with tab3:
            self.render_larvicide_tab(filtered_data)
        
        with tab4:
            self.render_trends_tab(filtered_data)
        
        with tab5:
            self.render_map_tab(filtered_data)
        
        with tab6:
            self.render_indices_detail_tab(filtered_data)
        
        with tab7:
            self.render_surveillance_days_tab(filtered_data)
        
        with tab8:
            self.render_monthly_aedic_analysis_tab(filtered_data)
    
    def render_sector_analysis(self, filtered_data):
        """Render sector-specific analysis"""
        if 'sector' not in filtered_data.columns:
            return
        
        # Check if there are sector data
        sectors = filtered_data['sector'].dropna()
        if len(sectors) == 0:
            return
        
        st.markdown("---")
        st.subheader("🏢 Análisis por Sector")
        
        # Sector summary metrics
        sector_summary = filtered_data.groupby('sector').agg({
            'atencion_vivienda_indicador': 'count',  # Total registros
            'viv_positiva': 'sum'  # Viviendas positivas
        }).reset_index()
        
        sector_summary['positividad_pct'] = (
            sector_summary['viv_positiva'] / sector_summary['atencion_vivienda_indicador'] * 100
        ).fillna(0)
        
        sector_summary = sector_summary.sort_values('atencion_vivienda_indicador', ascending=False)
        
        # Display top sectors
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📊 Top 5 Sectores por Registros**")
            top_sectors = sector_summary.head(5)
            
            for _, row in top_sectors.iterrows():
                sector_name = row['sector']
                total_records = int(row['atencion_vivienda_indicador'])
                positive = int(row['viv_positiva'])
                positivity = row['positividad_pct']
                
                st.markdown(f"""
                **{sector_name}**  
                📊 {total_records:,} registros | ⚠️ {positive:,} positivas | 📈 {positivity:.1f}%
                """)
        
        with col2:
            st.markdown("**⚠️ Sectores con Mayor Positividad**")
            high_positivity = sector_summary[sector_summary['atencion_vivienda_indicador'] >= 10].sort_values(
                'positividad_pct', ascending=False
            ).head(5)
            
            for _, row in high_positivity.iterrows():
                sector_name = row['sector']
                total_records = int(row['atencion_vivienda_indicador'])
                positive = int(row['viv_positiva'])
                positivity = row['positividad_pct']
                
                color = "🔴" if positivity > 10 else "🟡" if positivity > 5 else "🟢"
                st.markdown(f"""
                **{sector_name}** {color}  
                📊 {total_records:,} registros | ⚠️ {positive:,} positivas | 📈 {positivity:.1f}%
                """)
        
        # Sector visualization
        if len(sector_summary) > 1:
            st.markdown("---")
            st.subheader("📈 Visualización por Sector")
            
            viz_col1, viz_col2 = st.columns(2)
            
            with viz_col1:
                # Bar chart of records by sector
                import plotly.express as px
                
                fig_records = px.bar(
                    sector_summary.head(10),
                    x='sector',
                    y='atencion_vivienda_indicador',
                    title='Top 10 Sectores por Número de Registros',
                    labels={'atencion_vivienda_indicador': 'Número de Registros', 'sector': 'Sector'},
                    color='atencion_vivienda_indicador',
                    color_continuous_scale='Blues'
                )
                fig_records.update_layout(
                    xaxis_tickangle=-45,
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig_records, use_container_width=True)
            
            with viz_col2:
                # Scatter plot of positivity vs records
                fig_scatter = px.scatter(
                    sector_summary,
                    x='atencion_vivienda_indicador',
                    y='positividad_pct',
                    hover_data=['sector'],
                    title='Positividad vs Número de Registros por Sector',
                    labels={
                        'atencion_vivienda_indicador': 'Número de Registros',
                        'positividad_pct': 'Porcentaje de Positividad',
                        'sector': 'Sector'
                    },
                    color='positividad_pct',
                    color_continuous_scale='Reds',
                    size='atencion_vivienda_indicador',
                    size_max=15
                )
                fig_scatter.update_layout(height=400)
                st.plotly_chart(fig_scatter, use_container_width=True)
    
    def render_entomological_indices_tab(self, filtered_data):
        st.subheader("📊 Índices Entomológicos - Resumen General")
        
        # Get summary data for all indices
        indices_summary = self.calculations.calculate_entomological_indices_summary(filtered_data)
        
        if indices_summary:
            # Display main metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### 🏠 Índice Aédico (IA)")
                st.markdown("*(Viviendas positivas / Viviendas inspeccionadas) × 100*")
                if 'IA_promedio' in indices_summary:
                    st.metric("📊 IA Promedio", f"{indices_summary['IA_promedio']:.2f}%")
                    st.metric("⚠️ IA Máximo", f"{indices_summary['IA_maximo']:.2f}%")
                else:
                    st.info("Sin datos disponibles")
            
            with col2:
                st.markdown("### 📦 Índice de Recipiente (IC)")
                st.markdown("*(Recipientes positivos / Recipientes inspeccionados) × 100*")
                if 'IC_promedio' in indices_summary:
                    st.metric("📊 IC Promedio", f"{indices_summary['IC_promedio']:.2f}%")
                    st.metric("⚠️ IC Máximo", f"{indices_summary['IC_maximo']:.2f}%")
                else:
                    st.info("Sin datos disponibles")
            
            with col3:
                st.markdown("### 🔢 Índice Breteau (IB)")
                st.markdown("*(Recipientes positivos / 100 viviendas inspeccionadas)*")
                if 'IB_promedio' in indices_summary:
                    st.metric("📊 IB Promedio", f"{indices_summary['IB_promedio']:.2f}")
                    st.metric("⚠️ IB Máximo", f"{indices_summary['IB_maximo']:.2f}")
                else:
                    st.info("Sin datos disponibles")
            
            st.markdown("---")
            st.markdown("### 📈 Interpretación de Índices")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Índice Aédico:**")
                ia_avg = indices_summary.get('IA_promedio', 0)
                if ia_avg > 5:
                    st.error("🔴 Alto riesgo (>5%)")
                elif ia_avg > 1:
                    st.warning("🟡 Riesgo moderado (1-5%)")
                else:
                    st.success("🟢 Riesgo bajo (<1%)")
            
            with col2:
                st.markdown("**Índice de Recipiente:**")
                ic_avg = indices_summary.get('IC_promedio', 0)
                if ic_avg > 20:
                    st.error("🔴 Alto riesgo (>20%)")
                elif ic_avg > 5:
                    st.warning("🟡 Riesgo moderado (5-20%)")
                else:
                    st.success("🟢 Riesgo bajo (<5%)")
            
            with col3:
                st.markdown("**Índice Breteau:**")
                ib_avg = indices_summary.get('IB_promedio', 0)
                if ib_avg > 50:
                    st.error("🔴 Alto riesgo (>50)")
                elif ib_avg > 5:
                    st.warning("🟡 Riesgo moderado (5-50)")
                else:
                    st.success("🟢 Riesgo bajo (<5)")
        else:
            st.info("No hay datos suficientes para calcular los índices entomológicos.")

    def render_indices_detail_tab(self, filtered_data):
        st.subheader("📊 Índices Entomológicos - Detalle por Establecimiento")
        
        # Calculate detailed data for each index
        aedic_data = self.calculations.calculate_aedic_index(filtered_data)
        container_data = self.calculations.calculate_container_index(filtered_data)
        breteau_data = self.calculations.calculate_breteau_index(filtered_data)
        
        # Create sub-tabs for each index
        detail_tab1, detail_tab2, detail_tab3 = st.tabs([
            "🏠 Índice Aédico (IA)",
            "📦 Índice de Recipiente (IC)", 
            "🔢 Índice Breteau (IB)"
        ])
        
        with detail_tab1:
            st.subheader("📊 Índice Aédico por Establecimiento")
            st.markdown("**Fórmula:** (Viviendas Positivas / Viviendas Inspeccionadas) × 100")
            
            if not aedic_data.empty:
                # Display chart
                fig = self.viz_helper.create_aedic_index_chart(aedic_data)
                st.plotly_chart(fig, use_container_width=True)
                
                # Display table
                st.subheader("📋 Detalle por Establecimiento")
                aedic_table_data = aedic_data.sort_values('aedic_index', ascending=False)
                
                # Agregar fila de totales
                enhanced_aedic_data = create_enhanced_dataframe(
                    aedic_table_data,
                    label_column='localidad_eess',
                    exclude_from_total=['cod_renipress', 'aedic_index']  # Excluir porcentajes
                )
                
                safe_dataframe(
                    enhanced_aedic_data,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'cod_renipress': 'Código',
                        'localidad_eess': 'Establecimiento de Salud',
                        'total_houses': 'Viv. Totales',
                        'inspected_houses': 'Viv. Inspeccionadas',
                        'viviendas_positivas': 'Viv. Positivas',
                        'aedic_index': 'IA (%)'
                    }
                )
                
                # Botón de descarga XLSX
                create_excel_download_button(
                    aedic_table_data, 
                    "indice_aedico_establecimientos", 
                    "📥 Descargar Índice Aédico XLSX",
                    "aedic"
                )
            else:
                st.info("No hay datos suficientes para calcular el Índice Aédico.")
        
        with detail_tab2:
            st.subheader("📦 Índice de Recipiente por Establecimiento")
            st.markdown("**Fórmula:** (Recipientes Positivos / Recipientes Inspeccionados) × 100")
            
            if not container_data.empty:
                # Create visualization for container index
                import plotly.express as px
                fig = px.bar(
                    container_data.sort_values('container_index', ascending=True),
                    x='container_index',
                    y='localidad_eess',
                    orientation='h',
                    title='Índice de Recipiente por Establecimiento',
                    labels={
                        'container_index': 'Índice de Recipiente (%)',
                        'localidad_eess': 'Establecimiento de Salud'
                    },
                    color='container_index',
                    color_continuous_scale='Reds'
                )
                
                # Add value labels
                fig.update_traces(
                    texttemplate='%{x:.1f}%',
                    textposition='outside'
                )
                
                fig.update_layout(height=max(400, len(container_data) * 25))
                st.plotly_chart(fig, use_container_width=True)
                
                # Display table
                st.subheader("📋 Detalle por Establecimiento")
                container_table_data = container_data.sort_values('container_index', ascending=False)
                
                # Agregar fila de totales
                enhanced_container_data = create_enhanced_dataframe(
                    container_table_data,
                    label_column='localidad_eess',
                    exclude_from_total=['cod_renipress', 'container_index']  # Excluir porcentajes
                )
                
                safe_dataframe(
                    enhanced_container_data,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'cod_renipress': 'Código',
                        'localidad_eess': 'Establecimiento de Salud',
                        'containers_inspected': 'Recipientes Inspeccionados',
                        'containers_positive': 'Recipientes Positivos',
                        'container_index': 'IC (%)'
                    }
                )
            else:
                st.info("No hay datos suficientes para calcular el Índice de Recipiente.")
        
        with detail_tab3:
            st.subheader("🔢 Índice Breteau por Establecimiento")
            st.markdown("**Fórmula:** (Recipientes Positivos / Viviendas Inspeccionadas) × 100")
            
            if not breteau_data.empty:
                # Create visualization for breteau index
                import plotly.express as px
                fig = px.bar(
                    breteau_data.sort_values('breteau_index', ascending=True),
                    x='breteau_index',
                    y='localidad_eess',
                    orientation='h',
                    title='Índice Breteau por Establecimiento',
                    labels={
                        'breteau_index': 'Índice Breteau',
                        'localidad_eess': 'Establecimiento de Salud'
                    },
                    color='breteau_index',
                    color_continuous_scale='Blues'
                )
                
                # Add value labels
                fig.update_traces(
                    texttemplate='%{x:.1f}',
                    textposition='outside'
                )
                
                fig.update_layout(height=max(400, len(breteau_data) * 25))
                st.plotly_chart(fig, use_container_width=True)
                
                # Display table
                st.subheader("📋 Detalle por Establecimiento")
                breteau_table_data = breteau_data.sort_values('breteau_index', ascending=False)
                
                # Agregar fila de totales
                enhanced_breteau_data = create_enhanced_dataframe(
                    breteau_table_data,
                    label_column='localidad_eess',
                    exclude_from_total=['cod_renipress', 'breteau_index']  # Excluir índices
                )
                
                safe_dataframe(
                    enhanced_breteau_data,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'cod_renipress': 'Código',
                        'localidad_eess': 'Establecimiento de Salud',
                        'houses_inspected': 'Viviendas Inspeccionadas',
                        'containers_positive': 'Recipientes Positivos',
                        'breteau_index': 'IB'
                    }
                )
            else:
                st.info("No hay datos suficientes para calcular el Índice Breteau.")
    
    def render_containers_tab(self, filtered_data):
        st.subheader("📦 Estadísticas de Recipientes")
        
        # Calculate container statistics
        container_data = self.calculations.calculate_container_statistics(filtered_data)
        
        if not container_data.empty:
            # Display chart
            fig = self.viz_helper.create_container_statistics_chart(container_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # Display table with Spanish column names
            st.subheader("📋 Detalle por Tipo de Recipiente")
            
            # Agregar fila de totales
            enhanced_container_stats = create_enhanced_dataframe(
                container_data,
                label_column='container_type'
            )
            
            safe_dataframe(
                enhanced_container_stats, 
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
    
    def render_larvicide_tab(self, filtered_data):
        st.subheader("🧪 Consumo de Larvicida")
        
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
        
        # Display table with Spanish column names
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
    
    def render_trends_tab(self, filtered_data):
        st.subheader("📈 Tendencias Mensuales")
        
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
            df_subset = display_data[['month_year_str', 'atencion_vivienda_indicador', 
                            'viv_positiva', 'aedic_index', 'consumo_larvicida']].copy()
            enhanced_monthly_data = create_enhanced_dataframe(
                df_subset,
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
    
    def render_map_tab(self, filtered_data):
        st.subheader("🗺️ Distribución Geográfica")
        
        # Display map
        fig = self.viz_helper.create_map_visualization(filtered_data)
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary by coordinates
        if 'georeferencia_X' in filtered_data.columns and 'georeferencia_Y' in filtered_data.columns:
            valid_coords = filtered_data[
                (filtered_data['georeferencia_X'].notna()) & 
                (filtered_data['georeferencia_Y'].notna())
            ]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📍 Puntos Georeferenciados", len(valid_coords))
            with col2:
                positive_coords = len(valid_coords[valid_coords['viv_positiva'] == 1])
                st.metric("⚠️ Puntos Positivos", positive_coords)
            with col3:
                if len(valid_coords) > 0:
                    percentage = (positive_coords / len(valid_coords) * 100)
                    st.metric("📈 % Positividad Geográfica", f"{percentage:.2f}%")
        else:
            st.info("No hay datos de georeferenciación disponibles.")
    
    def render_surveillance_days_tab(self, filtered_data):
        st.subheader("📅 Análisis de Días de Vigilancia por Semana")
        
        # Calculate weekly surveillance days
        weekly_data = self.calculations.calculate_weekly_surveillance_days(filtered_data)
        
        if not weekly_data.empty:
            # Display summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_weeks = len(weekly_data)
                st.metric("📊 Total Semanas", total_weeks)
            
            with col2:
                avg_days_per_week = weekly_data['dias_vigilancia'].mean()
                st.metric("📈 Promedio Días/Semana", f"{avg_days_per_week:.1f}")
            
            with col3:
                max_days_week = weekly_data['dias_vigilancia'].max()
                st.metric("🔝 Máx Días/Semana", int(max_days_week))
            
            with col4:
                total_surveillance_days = weekly_data['dias_vigilancia'].sum()
                st.metric("📅 Total Días de Vigilancia", total_surveillance_days)
            
            # Create chart
            import plotly.express as px
            
            fig = px.bar(
                weekly_data,
                x='week_display',
                y='dias_vigilancia',
                title='Días de Vigilancia por Semana',
                labels={
                    'dias_vigilancia': 'Días de Vigilancia',
                    'week_display': 'Semana'
                },
                hover_data=['inspecciones_totales', 'viviendas_positivas', 'intensity']
            )
            
            # Add value labels on bars
            fig.update_traces(
                texttemplate='%{y}',
                textposition='outside'
            )
            
            fig.update_layout(
                xaxis={'tickangle': 45},
                height=500,
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display detailed table
            st.subheader("📋 Detalle por Semana")
            display_data = weekly_data.copy()
            display_data['intensity'] = display_data['intensity'].round(1)
            
            # Agregar fila de totales
            df_subset = display_data[['week_display', 'dias_vigilancia', 'inspecciones_totales', 
                            'viviendas_positivas', 'intensity']].copy()
            enhanced_weekly_data = create_enhanced_dataframe(
                df_subset,
                label_column='week_display',
                exclude_from_total=['intensity']  # Excluir intensidad (métrica calculada)
            )
            
            safe_dataframe(
                enhanced_weekly_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'week_display': 'Semana',
                    'dias_vigilancia': 'Días de Vigilancia',
                    'inspecciones_totales': 'Total Inspecciones',
                    'viviendas_positivas': 'Viviendas Positivas',
                    'intensity': 'Intensidad (Insp/Día)'
                }
            )
            
            # Weekly analysis insights
            st.subheader("🔍 Análisis de Patrones")
            col1, col2 = st.columns(2)
            
            with col1:
                # Days distribution
                days_distribution = weekly_data['dias_vigilancia'].value_counts().sort_index()
                
                fig_pie = px.pie(
                    values=days_distribution.values,
                    names=[f"{day} días" for day in days_distribution.index],
                    title='Distribución de Días de Vigilancia por Semana'
                )
                
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Weekly effectiveness
                st.markdown("**📊 Métricas de Efectividad:**")
                
                # Most productive week
                most_productive_week = weekly_data.loc[weekly_data['inspecciones_totales'].idxmax()]
                st.info(f"🏆 **Semana más productiva:** {most_productive_week['week_display']} "
                       f"({most_productive_week['inspecciones_totales']} inspecciones)")
                
                # Most intensive week (inspections per day)
                most_intensive_week = weekly_data.loc[weekly_data['intensity'].idxmax()]
                st.info(f"⚡ **Semana más intensiva:** {most_intensive_week['week_display']} "
                       f"({most_intensive_week['intensity']:.1f} insp/día)")
                
                # Week with most surveillance days
                most_days_week = weekly_data.loc[weekly_data['dias_vigilancia'].idxmax()]
                st.info(f"📅 **Semana con más días:** {most_days_week['week_display']} "
                       f"({most_days_week['dias_vigilancia']} días)")
                
                # Coverage consistency
                consistency = (weekly_data['dias_vigilancia'] >= 5).mean() * 100
                if consistency >= 80:
                    st.success(f"✅ Cobertura consistente: {consistency:.0f}% de semanas con ≥5 días")
                elif consistency >= 50:
                    st.warning(f"⚠️ Cobertura moderada: {consistency:.0f}% de semanas con ≥5 días")
                else:
                    st.error(f"❌ Cobertura baja: {consistency:.0f}% de semanas con ≥5 días")
        
        else:
            st.info("No hay datos de fechas válidos para calcular días de vigilancia por semana.")
    
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
                download_filename = f"reporte_vigilancia_{timestamp}.pptx"
                
                # Botón de descarga automática
                st.download_button(
                    label="📥 Descargar Presentación PowerPoint",
                    data=file_data,
                    file_name=download_filename,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    key="download_ppt_vigilancia",
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
                key="monthly_aedic_establishment"
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
            
            # Gráfico de barras por meses
            st.subheader("📊 Comparación por Meses")
            
            fig_bars = px.bar(
                establishment_data,
                x='mes_year',
                y='indice_aedico',
                title=f'Índice Aédico por Mes - {selected_establishment}',
                labels={
                    'indice_aedico': 'Índice Aédico (%)',
                    'mes_year': 'Mes'
                },
                color='indice_aedico',
                color_continuous_scale='Reds'
            )
            
            # Agregar valores en las barras
            fig_bars.update_traces(
                texttemplate='%{y:.1f}%',
                textposition='outside'
            )
            
            st.plotly_chart(fig_bars, use_container_width=True)
            
            # Tabla de datos detallados
            st.subheader("📋 Datos Detallados")
            
            display_data = establishment_data.copy()
            display_data = display_data.round(2)
            
            # Agregar fila de totales
            df_subset = display_data[['mes_year', 'viviendas_inspeccionadas', 'viviendas_positivas', 'indice_aedico']].copy()
            enhanced_establishment_data = create_enhanced_dataframe(
                df_subset,
                label_column='mes_year',
                exclude_from_total=['indice_aedico']  # Excluir porcentajes
            )
            
            safe_dataframe(
                enhanced_establishment_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'mes_year': 'Mes',
                    'viviendas_inspeccionadas': 'Viviendas Inspeccionadas',
                    'viviendas_positivas': 'Viviendas Positivas',
                    'indice_aedico': 'Índice Aédico (%)'
                }
            )
            
            # Análisis comparativo con todos los establecimientos
            st.subheader("🔄 Comparación con Otros Establecimientos")
            
            # Gráfico comparativo del último mes
            latest_month = monthly_data['mes_year'].max()
            latest_month_data = monthly_data[monthly_data['mes_year'] == latest_month]
            if 'indice_aedico' in latest_month_data.columns:
                latest_month_data = latest_month_data.sort_values('indice_aedico', ascending=True)
            
            if not latest_month_data.empty:
                fig_comp = px.bar(
                    latest_month_data,
                    x='indice_aedico',
                    y='establecimiento',
                    orientation='h',
                    title=f'Comparación de Índice Aédico - {latest_month}',
                    labels={
                        'indice_aedico': 'Índice Aédico (%)',
                        'establecimiento': 'Establecimiento'
                    },
                    color='indice_aedico',
                    color_continuous_scale='Reds'
                )
                
                # Resaltar el establecimiento seleccionado
                fig_comp.update_traces(
                    texttemplate='%{x:.1f}%',
                    textposition='outside'
                )
                
                fig_comp.update_layout(
                    height=max(400, len(latest_month_data) * 30)
                )
                
                st.plotly_chart(fig_comp, use_container_width=True)
            
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

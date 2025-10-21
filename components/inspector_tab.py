import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.visualizations import VisualizationHelper
from utils.table_helpers import create_enhanced_dataframe, safe_dataframe

class InspectorTab:
    def __init__(self, data_processor, calculations):
        self.data_processor = data_processor
        self.calculations = calculations
        self.viz_helper = VisualizationHelper()
    
    def render(self):
        st.header("👤 Análisis por Inspector")
        
        # Check if data is available
        if st.session_state.data is None:
            st.warning("⚠️ Por favor, carga un archivo CSV primero.")
            return
        
        # Use processed data from data_processor
        filtered_data = self.data_processor.data
        
        # Inspector filter
        st.subheader("🔍 Filtrar por Inspector")
        
        # Get list of inspectors (DNI) and create DNI to name mapping
        # Convert usuario_registra to string to ensure consistent type handling
        filtered_data['usuario_registra'] = filtered_data['usuario_registra'].astype(str)
        
        inspector_mapping = {}
        if 'nombre_inspector' in filtered_data.columns:
            # Create mapping from DNI to full name
            for dni in filtered_data['usuario_registra'].dropna().unique():
                names = filtered_data[filtered_data['usuario_registra'] == dni]['nombre_inspector'].dropna().unique()
                if len(names) > 0 and names[0] != '':
                    inspector_mapping[str(dni)] = names[0]
                else:
                    inspector_mapping[str(dni)] = f"Inspector {dni}"
        
        inspectors = sorted(filtered_data['usuario_registra'].dropna().unique())
        
        if not inspectors:
            st.warning("No se encontraron datos de inspectores.")
            return
        
        # Sector analysis section for inspector data
        self.render_sector_analysis(filtered_data)
        
        # Inspector selection with names if available
        col1, col2 = st.columns([2, 1])
        
        # Initialize selected_inspector
        selected_inspector = inspectors[0] if inspectors else None
        
        with col1:
            # Create display options with both DNI and name
            inspector_options = []
            for dni in inspectors:
                dni_str = str(dni)
                if dni_str in inspector_mapping:
                    display_name = f"{inspector_mapping[dni_str]} (DNI: {dni})"
                else:
                    display_name = f"Inspector {dni}"
                inspector_options.append(display_name)
            
            selected_display = st.selectbox(
                "Selecciona el Inspector:",
                options=inspector_options,
                key="inspector_select"
            )
            
            # Extract DNI from selected display option and ensure string type
            if selected_display:
                if "(DNI: " in selected_display:
                    selected_inspector = str(selected_display.split("(DNI: ")[1].replace(")", ""))
                else:
                    selected_inspector = str(selected_display.replace("Inspector ", ""))
        
        with col2:
            st.metric("📋 Total Inspectores", len(inspectors))
        
        # Filter data by selected inspector
        inspector_data = filtered_data[filtered_data['usuario_registra'] == selected_inspector]
        
        if inspector_data.empty:
            st.warning(f"No se encontraron registros para el inspector {selected_inspector}")
            return
        
        # Display inspector summary
        self.display_inspector_summary(inspector_data, selected_inspector)
        
        # Create tabs for detailed analysis
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Resumen General",
            "🏠 Inspecciones por Fecha",
            "📦 Recipientes Analizados",
            "🗺️ Mapa de Inspecciones",
            "📈 Productividad"
        ])
        
        with tab1:
            self.render_general_summary_tab(inspector_data, selected_inspector)
        
        with tab2:
            self.render_daily_inspections_tab(inspector_data, selected_inspector)
        
        with tab3:
            self.render_containers_tab(inspector_data, selected_inspector)
        
        with tab4:
            self.render_map_tab(inspector_data, selected_inspector)
        
        with tab5:
            self.render_productivity_tab(inspector_data, selected_inspector)
    
    def display_inspector_summary(self, inspector_data, inspector_dni):
        """Display summary metrics for the selected inspector"""
        # Get inspector name if available
        inspector_name = "Inspector desconocido"
        if 'nombre_inspector' in inspector_data.columns:
            names = inspector_data['nombre_inspector'].dropna().unique()
            if len(names) > 0 and names[0] != '':
                inspector_name = names[0]
        
        st.subheader(f"📋 Resumen del Inspector: {inspector_name} (DNI: {inspector_dni})")
        
        # Calculate key metrics
        total_inspections = len(inspector_data)
        inspected_houses = len(inspector_data[inspector_data['atencion_vivienda_indicador'] == 1])
        positive_houses = len(inspector_data[
            (inspector_data['viv_positiva'] == 1) & 
            (inspector_data['atencion_vivienda_indicador'] == 1)
        ])
        total_larvicide = inspector_data['consumo_larvicida'].sum()
        total_febriles = inspector_data['febriles'].sum()
        
        # Date range
        if 'fecha_inspeccion' in inspector_data.columns:
            try:
                # Ensure dates are datetime objects
                dates = pd.to_datetime(inspector_data['fecha_inspeccion'], errors='coerce').dropna()
                if len(dates) > 0:
                    date_range = f"{dates.min().strftime('%Y-%m-%d')} a {dates.max().strftime('%Y-%m-%d')}"
                else:
                    date_range = "No disponible"
            except Exception as e:
                date_range = "No disponible"
        else:
            date_range = "No disponible"
        
        # Aedic index
        aedic_index = (positive_houses / inspected_houses * 100) if inspected_houses > 0 else 0
        
        # Display metrics in columns
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("🏠 Total Registros", f"{total_inspections:,}")
        
        with col2:
            st.metric("✅ Viviendas Inspeccionadas", f"{inspected_houses:,}")
        
        with col3:
            st.metric("⚠️ Viviendas Positivas", f"{positive_houses:,}")
        
        with col4:
            st.metric("📈 Índice Aédico", f"{aedic_index:.2f}%")
        
        with col5:
            st.metric("💊 Larvicida Total", f"{total_larvicide:.2f} g")
        
        # Additional info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🤒 Casos Febriles", f"{total_febriles:,}")
        
        with col2:
            unique_facilities = inspector_data['localidad_eess'].nunique()
            st.metric("🏥 Establecimientos", f"{unique_facilities}")
        
        with col3:
            st.info(f"📅 **Período:** {date_range}")
    
    def render_general_summary_tab(self, inspector_data, inspector_dni):
        """Render general summary tab"""
        # Get inspector name if available
        inspector_name = "Inspector desconocido"
        if 'nombre_inspector' in inspector_data.columns:
            names = inspector_data['nombre_inspector'].dropna().unique()
            if len(names) > 0 and names[0] != '':
                inspector_name = names[0]
        
        st.subheader(f"📊 Resumen General - {inspector_name} (DNI: {inspector_dni})")
        
        # House status breakdown
        status_mapping = {
            1: "Inspeccionada",
            2: "Cerrada", 
            3: "Renuente",
            4: "Deshabitada"
        }
        
        status_counts = inspector_data['atencion_vivienda_indicador'].value_counts()
        status_data = []
        
        for status_code, status_name in status_mapping.items():
            count = status_counts.get(status_code, 0)
            status_data.append({'Estado': status_name, 'Cantidad': count})
        
        status_df = pd.DataFrame(status_data)
        
        # Create pie chart
        fig = px.pie(
            status_df, 
            values='Cantidad', 
            names='Estado',
            title='Distribución de Estados de Vivienda'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Facilities worked on
        st.subheader("🏥 Establecimientos de Salud Trabajados")
        facility_counts = inspector_data['localidad_eess'].value_counts()
        
        facility_df = pd.DataFrame({
            'Establecimiento': facility_counts.index,
            'Registros': facility_counts.values
        })
        
        # Agregar fila de totales
        enhanced_facility_df = create_enhanced_dataframe(
            facility_df,
            label_column='Establecimiento'  # Primera columna para la etiqueta TOTAL
        )
        
        safe_dataframe(enhanced_facility_df, use_container_width=True, hide_index=True)
    
    def render_daily_inspections_tab(self, inspector_data, inspector_dni):
        """Render daily inspections analysis"""
        # Get inspector name if available
        inspector_name = "Inspector desconocido"
        if 'nombre_inspector' in inspector_data.columns:
            names = inspector_data['nombre_inspector'].dropna().unique()
            if len(names) > 0 and names[0] != '':
                inspector_name = names[0]
        
        st.subheader(f"🏠 Inspecciones por Fecha - {inspector_name} (DNI: {inspector_dni})")
        
        if 'fecha_inspeccion' not in inspector_data.columns:
            st.info("No hay datos de fecha disponibles.")
            return
        
        # Ensure dates are datetime objects
        try:
            inspector_data_copy = inspector_data.copy()
            inspector_data_copy['fecha_inspeccion'] = pd.to_datetime(inspector_data_copy['fecha_inspeccion'], errors='coerce')
            
            # Remove rows with invalid dates
            inspector_data_copy = inspector_data_copy.dropna(subset=['fecha_inspeccion'])
            
            if len(inspector_data_copy) == 0:
                st.info("No hay datos de fecha válidos disponibles.")
                return
            
            # Group by date
            daily_inspections = inspector_data_copy.groupby(inspector_data_copy['fecha_inspeccion'].dt.date).agg({
                'atencion_vivienda_indicador': [
                    lambda x: (x == 1).sum(),  # Viviendas Inspeccionadas
                    lambda x: (x == 2).sum(),  # Viviendas Cerradas
                    lambda x: (x == 3).sum()   # Viviendas Renuentes
                ],
                'viv_positiva': lambda x: ((x == 1) & (inspector_data_copy.loc[x.index, 'atencion_vivienda_indicador'] == 1)).sum(),
                'consumo_larvicida': 'sum'
            }).reset_index()
            
            # Flatten the multi-level column names
            daily_inspections.columns = [
                'Fecha', 
                'Viviendas_Inspeccionadas', 
                'Viviendas_Cerradas', 
                'Viviendas_Renuentes',
                'Viviendas_Positivas', 
                'Consumo_Larvicida'
            ]
        except Exception as e:
            st.error(f"Error al procesar fechas: {str(e)}")
            return
        
        daily_inspections['Indice_Aedico'] = (daily_inspections['Viviendas_Positivas'] / daily_inspections['Viviendas_Inspeccionadas'] * 100).fillna(0)
        
        # Line chart for daily productivity
        fig = px.line(
            daily_inspections,
            x='Fecha',
            y='Viviendas_Inspeccionadas',
            title='Productividad Diaria - Viviendas Inspeccionadas',
            markers=True
        )
        
        # Agregar valores numéricos encima de cada punto
        fig.update_traces(
            texttemplate='%{y}',
            textposition='top center'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display table
        st.subheader("📋 Detalle por Día")
        
        # Agregar fila de totales
        enhanced_daily_df = create_enhanced_dataframe(
            daily_inspections,
            label_column='Fecha'  # Primera columna para la etiqueta TOTAL
        )
        
        safe_dataframe(enhanced_daily_df, use_container_width=True, hide_index=True)
    
    def render_containers_tab(self, inspector_data, inspector_dni):
        """Render container analysis tab"""
        # Get inspector name if available
        inspector_name = "Inspector desconocido"
        if 'nombre_inspector' in inspector_data.columns:
            names = inspector_data['nombre_inspector'].dropna().unique()
            if len(names) > 0 and names[0] != '':
                inspector_name = names[0]
        
        st.subheader(f"📦 Recipientes Analizados - {inspector_name} (DNI: {inspector_dni})")
        
        # Calculate container statistics
        container_data = self.calculations.calculate_container_statistics(inspector_data)
        
        if not container_data.empty:
            # Display chart
            fig = self.viz_helper.create_container_statistics_chart(container_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # Display table
            st.subheader("📋 Detalle por Tipo de Recipiente")
            
            # Agregar fila de totales
            enhanced_container_df = create_enhanced_dataframe(container_data)
            
            safe_dataframe(enhanced_container_df, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos de recipientes disponibles.")
    
    def render_map_tab(self, inspector_data, inspector_dni):
        """Render map visualization for inspector"""
        # Get inspector name if available
        inspector_name = "Inspector desconocido"
        if 'nombre_inspector' in inspector_data.columns:
            names = inspector_data['nombre_inspector'].dropna().unique()
            if len(names) > 0 and names[0] != '':
                inspector_name = names[0]
        
        st.subheader(f"🗺️ Mapa de Inspecciones - {inspector_name} (DNI: {inspector_dni})")
        
        # Create map visualization
        fig = self.viz_helper.create_map_visualization(inspector_data)
        st.plotly_chart(fig, use_container_width=True)
        
        # Location summary
        if 'georeferencia_X' in inspector_data.columns and 'georeferencia_Y' in inspector_data.columns:
            valid_coords = inspector_data[
                (inspector_data['georeferencia_X'].notna()) & 
                (inspector_data['georeferencia_Y'].notna())
            ]
            
            st.info(f"📍 **Inspecciones georeferenciadas:** {len(valid_coords):,} de {len(inspector_data):,} total")
    
    def render_productivity_tab(self, inspector_data, inspector_dni):
        """Render productivity analysis"""
        # Get inspector name if available
        inspector_name = "Inspector desconocido"
        if 'nombre_inspector' in inspector_data.columns:
            names = inspector_data['nombre_inspector'].dropna().unique()
            if len(names) > 0 and names[0] != '':
                inspector_name = names[0]
        
        st.subheader(f"📈 Análisis de Productividad - {inspector_name} (DNI: {inspector_dni})")
        
        if 'fecha_inspeccion' not in inspector_data.columns:
            st.info("No hay datos de fecha para análisis de productividad.")
            return
        
        # Ensure dates are datetime objects
        try:
            inspector_data_copy = inspector_data.copy()
            inspector_data_copy['fecha_inspeccion'] = pd.to_datetime(inspector_data_copy['fecha_inspeccion'], errors='coerce')
            
            # Remove rows with invalid dates
            inspector_data_copy = inspector_data_copy.dropna(subset=['fecha_inspeccion'])
            
            if len(inspector_data_copy) == 0:
                st.info("No hay datos de fecha válidos disponibles.")
                return
            
            # Calculate working days
            working_days = inspector_data_copy['fecha_inspeccion'].dt.date.nunique()
            total_inspections = len(inspector_data_copy[inspector_data_copy['atencion_vivienda_indicador'] == 1])
            
            # Productivity metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                avg_daily = total_inspections / working_days if working_days > 0 else 0
                st.metric("📊 Promedio Diario", f"{avg_daily:.1f} viviendas")
            
            with col2:
                st.metric("📅 Días Trabajados", f"{working_days}")
            
            with col3:
                efficiency = (total_inspections / len(inspector_data_copy) * 100) if len(inspector_data_copy) > 0 else 0
                st.metric("⚡ Eficiencia", f"{efficiency:.1f}%")
            
            # Monthly productivity trend
            monthly_productivity = inspector_data_copy.groupby(inspector_data_copy['fecha_inspeccion'].dt.to_period('M')).agg({
                'atencion_vivienda_indicador': lambda x: (x == 1).sum()
            }).reset_index()
        except Exception as e:
            st.error(f"Error al procesar fechas: {str(e)}")
            return
        
        monthly_productivity['fecha_inspeccion'] = monthly_productivity['fecha_inspeccion'].astype(str)
        
        if not monthly_productivity.empty:
            fig = px.bar(
                monthly_productivity,
                x='fecha_inspeccion',
                y='atencion_vivienda_indicador',
                title='Productividad Mensual',
                labels={
                    'atencion_vivienda_indicador': 'Viviendas Inspeccionadas',
                    'fecha_inspeccion': 'Mes'
                }
            )
            
            # Add value labels
            fig.update_traces(
                texttemplate='%{y}',
                textposition='outside'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Performance comparison
        st.subheader("📊 Comparación de Rendimiento")
        
        # Get average performance of all inspectors for comparison
        all_inspectors_data = self.data_processor.data
        avg_performance = all_inspectors_data.groupby('usuario_registra').agg({
            'atencion_vivienda_indicador': lambda x: (x == 1).sum()
        }).mean().iloc[0]
        
        inspector_performance = total_inspections
        
        performance_comparison = inspector_performance / avg_performance if avg_performance > 0 else 0
        
        if performance_comparison > 1.2:
            st.success(f"🌟 Rendimiento superior al promedio ({performance_comparison:.1f}x)")
        elif performance_comparison > 0.8:
            st.info(f"📊 Rendimiento cercano al promedio ({performance_comparison:.1f}x)")
        else:
            st.warning(f"📉 Rendimiento por debajo del promedio ({performance_comparison:.1f}x)")
    
    def render_sector_analysis(self, filtered_data):
        """Render sector-specific analysis for Inspector data"""
        if 'sector' not in filtered_data.columns:
            return
        
        # Check if there are sector data
        sectors = filtered_data['sector'].dropna()
        if len(sectors) == 0:
            return
        
        st.markdown("---")
        st.subheader("🏢 Distribución de Inspectores por Sector")
        
        # Inspector-sector analysis
        inspector_sector_summary = filtered_data.groupby(['sector', 'usuario_registra']).agg({
            'atencion_vivienda_indicador': lambda x: (x == 1).sum(),
            'viv_positiva': 'sum'
        }).reset_index()
        
        # Sector summary
        sector_summary = filtered_data.groupby('sector').agg({
            'usuario_registra': 'nunique',  # Número de inspectores únicos
            'atencion_vivienda_indicador': lambda x: (x == 1).sum(),  # Total inspecciones
            'viv_positiva': 'sum'  # Viviendas positivas
        }).reset_index()
        
        sector_summary['inspecciones_por_inspector'] = (
            sector_summary['atencion_vivienda_indicador'] / sector_summary['usuario_registra']
        ).fillna(0)
        
        sector_summary['positividad_pct'] = (
            sector_summary['viv_positiva'] / sector_summary['atencion_vivienda_indicador'] * 100
        ).fillna(0)
        
        sector_summary = sector_summary.sort_values('atencion_vivienda_indicador', ascending=False)
        
        # Display sector-inspector metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**👥 Sectores con Más Inspectores**")
            top_inspectors = sector_summary.sort_values('usuario_registra', ascending=False).head(5)
            
            for _, row in top_inspectors.iterrows():
                sector_name = row['sector']
                num_inspectors = int(row['usuario_registra'])
                total_inspections = int(row['atencion_vivienda_indicador'])
                avg_per_inspector = row['inspecciones_por_inspector']
                
                st.markdown(f"""
                **{sector_name}**  
                👥 {num_inspectors} inspectores | 🏠 {total_inspections:,} inspecciones | 📊 {avg_per_inspector:.1f} prom/inspector
                """)
        
        with col2:
            st.markdown("**⚡ Sectores Más Productivos**")
            most_productive = sector_summary.sort_values('inspecciones_por_inspector', ascending=False).head(5)
            
            for _, row in most_productive.iterrows():
                sector_name = row['sector']
                avg_per_inspector = row['inspecciones_por_inspector']
                positivity = row['positividad_pct']
                
                color = "🟢" if avg_per_inspector > 100 else "🟡" if avg_per_inspector > 50 else "🔴"
                st.markdown(f"""
                **{sector_name}** {color}  
                📊 {avg_per_inspector:.1f} insp/inspector | 📈 {positivity:.1f}% positividad
                """)
        
        # Visualizations
        if len(sector_summary) > 1:
            st.markdown("---")
            st.subheader("📈 Análisis de Productividad por Sector")
            
            viz_col1, viz_col2 = st.columns(2)
            
            with viz_col1:
                # Inspector distribution by sector
                import plotly.express as px
                
                fig_inspectors = px.bar(
                    sector_summary.head(10),
                    x='sector',
                    y='usuario_registra',
                    title='Número de Inspectores por Sector',
                    labels={'usuario_registra': 'Número de Inspectores', 'sector': 'Sector'},
                    color='usuario_registra',
                    color_continuous_scale='Blues'
                )
                fig_inspectors.update_layout(
                    xaxis_tickangle=-45,
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig_inspectors, use_container_width=True)
            
            with viz_col2:
                # Productivity analysis
                fig_productivity = px.scatter(
                    sector_summary,
                    x='usuario_registra',
                    y='inspecciones_por_inspector',
                    hover_data=['sector'],
                    title='Productividad: Inspectores vs Inspecciones por Inspector',
                    labels={
                        'usuario_registra': 'Número de Inspectores',
                        'inspecciones_por_inspector': 'Inspecciones por Inspector',
                        'sector': 'Sector'
                    },
                    color='positividad_pct',
                    color_continuous_scale='Reds',
                    size='atencion_vivienda_indicador',
                    size_max=15
                )
                fig_productivity.update_layout(height=400)
                st.plotly_chart(fig_productivity, use_container_width=True)
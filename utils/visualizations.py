import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import pandas as pd

class VisualizationHelper:
    def __init__(self):
        self.color_palette = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]
    
    def apply_theme_to_figure(self, fig):
        """Apply current Streamlit theme to Plotly figure"""
        # Check if dark theme is selected (stored in session state)
        is_dark_theme = st.session_state.get('current_theme', 'Claro') == 'Oscuro'
        
        if is_dark_theme:
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='#0e1117',
                plot_bgcolor='#0e1117',
                font=dict(color='#fafafa')
            )
        else:
            fig.update_layout(
                template='plotly_white',
                paper_bgcolor='white',
                plot_bgcolor='white',
                font=dict(color='#262730')
            )
        
        return fig
    
    def create_aedic_index_chart(self, aedic_data):
        """Create Aedic Index bar chart"""
        if aedic_data.empty:
            return go.Figure().add_annotation(
                text="No hay datos disponibles",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        # Sort by Aedic Index descending
        aedic_data_sorted = aedic_data.sort_values('aedic_index', ascending=True)
        
        fig = px.bar(
            aedic_data_sorted,
            x='aedic_index',
            y='localidad_eess',
            orientation='h',
            title='Índice Aédico por Establecimiento de Salud',
            labels={
                'aedic_index': 'Índice Aédico (%)',
                'localidad_eess': 'Establecimiento de Salud'
            },
            color='aedic_index',
            color_continuous_scale='Reds'
        )
        
        # Add value labels on bars
        fig.update_traces(
            texttemplate='%{x:.1f}%',
            textposition='outside'
        )
        
        fig.update_layout(
            height=max(400, len(aedic_data_sorted) * 25),
            showlegend=False,
            xaxis_title="Índice Aédico (%)",
            yaxis_title="Establecimiento de Salud"
        )
        
        # Apply theme
        fig = self.apply_theme_to_figure(fig)
        
        return fig
    
    def create_container_statistics_chart(self, container_data):
        """Create container statistics stacked bar chart"""
        if container_data.empty:
            return go.Figure().add_annotation(
                text="No hay datos disponibles",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        # Prepare data for stacked bar chart
        status_columns = [col for col in container_data.columns if col != 'container_type']
        
        fig = go.Figure()
        
        for i, status in enumerate(status_columns):
            fig.add_trace(go.Bar(
                name=status,
                x=container_data['container_type'],
                y=container_data[status],
                marker_color=self.color_palette[i % len(self.color_palette)],
                text=container_data[status],
                textposition='inside'
            ))
        
        fig.update_layout(
            title='Estadísticas de Recipientes por Tipo y Estado',
            xaxis_title='Tipo de Recipiente',
            yaxis_title='Cantidad',
            barmode='stack',
            height=500,
            xaxis={'tickangle': 45}
        )
        
        # Apply theme
        fig = self.apply_theme_to_figure(fig)
        
        return fig
    
    def create_larvicide_consumption_chart(self, consumption_data):
        """Create larvicide consumption chart"""
        if consumption_data.empty:
            return go.Figure().add_annotation(
                text="No hay datos disponibles",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        # Top 15 facilities by consumption
        top_facilities = consumption_data.head(15)
        
        fig = px.bar(
            top_facilities,
            x='consumo_larvicida',
            y='localidad_eess',
            orientation='h',
            title='Consumo de Larvicida por Establecimiento (Top 15)',
            labels={
                'consumo_larvicida': 'Consumo de Larvicida (g)',
                'localidad_eess': 'Establecimiento de Salud'
            },
            color='consumo_larvicida',
            color_continuous_scale='Blues'
        )
        
        # Add value labels on bars
        fig.update_traces(
            texttemplate='%{x:.1f}',
            textposition='outside'
        )
        
        fig.update_layout(
            height=500,
            showlegend=False
        )
        
        # Apply theme
        fig = self.apply_theme_to_figure(fig)
        
        return fig
    
    def create_inspection_summary_pie(self, summary_data):
        """Create pie chart for inspection summary"""
        if not summary_data:
            return go.Figure().add_annotation(
                text="No hay datos disponibles",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        # Exclude percentage from pie chart
        pie_data = {k: v for k, v in summary_data.items() if 'Porcentaje' not in k}
        
        fig = px.pie(
            values=list(pie_data.values()),
            names=list(pie_data.keys()),
            title='Distribución de Estados de Vivienda'
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=400)
        
        # Apply theme
        fig = self.apply_theme_to_figure(fig)
        
        return fig
    
    def create_monthly_trends_chart(self, monthly_data):
        """Create monthly trends chart"""
        if monthly_data.empty:
            return go.Figure().add_annotation(
                text="No hay datos disponibles",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[
                'Viviendas Inspeccionadas por Mes',
                'Índice Aédico Mensual (%)',
                'Viviendas Positivas por Mes',
                'Consumo de Larvicida por Mes (g)'
            ],
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Inspected houses
        fig.add_trace(
            go.Scatter(
                x=monthly_data['month_year_str'],
                y=monthly_data['atencion_vivienda_indicador'],
                mode='lines+markers+text',
                name='Viviendas Inspeccionadas',
                line=dict(color='blue'),
                text=monthly_data['atencion_vivienda_indicador'],
                textposition='top center'
            ),
            row=1, col=1
        )
        
        # Aedic Index
        fig.add_trace(
            go.Scatter(
                x=monthly_data['month_year_str'],
                y=monthly_data['aedic_index'],
                mode='lines+markers+text',
                name='Índice Aédico',
                line=dict(color='red'),
                text=[f"{val:.1f}%" for val in monthly_data['aedic_index']],
                textposition='top center'
            ),
            row=1, col=2
        )
        
        # Positive houses
        fig.add_trace(
            go.Scatter(
                x=monthly_data['month_year_str'],
                y=monthly_data['viv_positiva'],
                mode='lines+markers+text',
                name='Viviendas Positivas',
                line=dict(color='orange'),
                text=monthly_data['viv_positiva'],
                textposition='top center'
            ),
            row=2, col=1
        )
        
        # Larvicide consumption
        fig.add_trace(
            go.Scatter(
                x=monthly_data['month_year_str'],
                y=monthly_data['consumo_larvicida'],
                mode='lines+markers+text',
                name='Consumo Larvicida (g)',
                line=dict(color='green'),
                text=[f"{val:.1f}g" for val in monthly_data['consumo_larvicida']],
                textposition='top center'
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=600,
            showlegend=False,
            title_text="Tendencias Mensuales"
        )
        
        # Update x-axis labels
        for i in range(1, 3):
            for j in range(1, 3):
                fig.update_xaxes(tickangle=45, row=i, col=j)
        
        # Apply theme
        fig = self.apply_theme_to_figure(fig)
        
        return fig
    
    def create_map_visualization(self, filtered_data):
        """Create map visualization with georeferenced data"""
        if filtered_data.empty or 'georeferencia_X' not in filtered_data.columns:
            return go.Figure().add_annotation(
                text="No hay datos de georeferenciación disponibles",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        # Filter data with valid coordinates
        map_data = filtered_data[
            (filtered_data['georeferencia_X'].notna()) & 
            (filtered_data['georeferencia_Y'].notna())
        ].copy()
        
        if map_data.empty:
            return go.Figure().add_annotation(
                text="No hay coordenadas válidas disponibles",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        # Create color coding based on positive houses
        map_data['color'] = map_data['viv_positiva'].map({0: 'green', 1: 'red'})
        map_data['status'] = map_data['viv_positiva'].map({0: 'Negativa', 1: 'Positiva'})
        
        fig = px.scatter_mapbox(
            map_data,
            lat='georeferencia_X',
            lon='georeferencia_Y',
            color='status',
            hover_data=['localidad_eess', 'direccion', 'persona_atiende'],
            title='Distribución Geográfica de Inspecciones',
            zoom=10,
            height=600,
            color_discrete_map={'Negativa': 'green', 'Positiva': 'red'}
        )
        
        # Enhanced map configuration with improved zoom controls
        fig.update_layout(
            mapbox_style="open-street-map",
            mapbox=dict(
                center=dict(
                    lat=map_data['georeferencia_X'].mean(),
                    lon=map_data['georeferencia_Y'].mean()
                ),
                zoom=12
            ),
            margin={"r":0,"t":50,"l":0,"b":0},
            # Enable zoom controls
            dragmode='zoom'
        )
        
        # Add zoom and pan controls
        fig.update_layout(
            modebar_add=['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomin2d', 'zoomout2d', 'autoScale2d', 'resetScale2d']
        )
        
        # Apply theme
        fig = self.apply_theme_to_figure(fig)
        
        return fig

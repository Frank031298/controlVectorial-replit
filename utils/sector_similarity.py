"""
Utilidad para detectar similitudes ortográficas en nombres de sectores
y proporcionar opciones de unificación para el análisis epidemiológico
"""
import pandas as pd
import streamlit as st
from difflib import SequenceMatcher
import re
from collections import defaultdict

class SectorSimilarityDetector:
    def __init__(self, similarity_threshold=0.8):
        """
        Inicializar detector de similitudes
        
        Args:
            similarity_threshold (float): Umbral de similitud (0.0 a 1.0)
        """
        self.similarity_threshold = similarity_threshold
        self.unification_mapping = {}
        
    def normalize_sector_name(self, sector_name):
        """Normalizar nombres de sectores para mejorar detección"""
        if pd.isna(sector_name) or sector_name == '':
            return ''
        
        # Convertir a string y limpiar
        sector = str(sector_name).strip().upper()
        
        # Eliminar caracteres especiales pero mantener espacios
        sector = re.sub(r'[^\w\s]', '', sector)
        
        # Normalizar espacios múltiples
        sector = re.sub(r'\s+', ' ', sector)
        
        return sector
    
    def calculate_similarity(self, sector1, sector2):
        """Calcular similitud entre dos nombres de sectores"""
        if not sector1 or not sector2:
            return 0.0
            
        norm1 = self.normalize_sector_name(sector1)
        norm2 = self.normalize_sector_name(sector2)
        
        if norm1 == norm2:
            return 1.0
            
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def find_similar_sectors(self, sectors_list):
        """
        Encontrar grupos de sectores similares
        
        Args:
            sectors_list (list): Lista de nombres de sectores
            
        Returns:
            dict: Grupos de sectores similares
        """
        if not sectors_list:
            return {}
            
        # Filtrar valores vacíos
        valid_sectors = [s for s in sectors_list if pd.notna(s) and str(s).strip() != '']
        
        if len(valid_sectors) < 2:
            return {}
        
        # Detectar grupos similares
        similar_groups = defaultdict(list)
        processed = set()
        
        for i, sector1 in enumerate(valid_sectors):
            if sector1 in processed:
                continue
                
            group = [sector1]
            processed.add(sector1)
            
            for j, sector2 in enumerate(valid_sectors[i+1:], i+1):
                if sector2 in processed:
                    continue
                    
                similarity = self.calculate_similarity(sector1, sector2)
                
                if similarity >= self.similarity_threshold:
                    group.append(sector2)
                    processed.add(sector2)
            
            # Solo agregar grupos con más de un elemento
            if len(group) > 1:
                # Usar el sector más común o el más corto como clave
                key_sector = min(group, key=len)
                similar_groups[key_sector] = group
        
        return dict(similar_groups)
    
    def find_similar_sectors_by_province(self, data_df, sector_col='sector', province_col='nombre_prov'):
        """
        Encontrar grupos de sectores similares agrupados por provincia
        
        Args:
            data_df (DataFrame): DataFrame con datos
            sector_col (str): Nombre de la columna de sectores
            province_col (str): Nombre de la columna de provincias
            
        Returns:
            dict: Grupos de sectores similares por provincia
        """
        if data_df.empty or sector_col not in data_df.columns or province_col not in data_df.columns:
            return {}
        
        # Obtener sectores únicos por provincia
        province_sectors = data_df.groupby(province_col)[sector_col].apply(
            lambda x: x.dropna().unique().tolist()
        ).to_dict()
        
        # Detectar similitudes dentro de cada provincia
        similar_groups_by_province = {}
        
        for province, sectors_in_province in province_sectors.items():
            if len(sectors_in_province) < 2:
                continue
                
            # Encontrar similitudes solo dentro de esta provincia
            similar_groups = self.find_similar_sectors(sectors_in_province)
            
            if similar_groups:
                similar_groups_by_province[province] = similar_groups
        
        return similar_groups_by_province
    
    def render_sector_unification_interface_by_province(self, similar_groups_by_province, prefix="sector"):
        """
        Renderizar interfaz para unificar sectores similares agrupados por provincia
        
        Args:
            similar_groups_by_province (dict): Grupos de sectores similares por provincia
            prefix (str): Prefijo para las keys de session state
            
        Returns:
            dict: Mapeo de unificaciones seleccionadas por provincia
        """
        if not similar_groups_by_province:
            return {}
        
        st.subheader("🔍 Sectores con Posibles Errores Ortográficos por Provincia")
        st.info("📝 Se detectaron sectores con nombres similares dentro de cada provincia. ¿Desea unificarlos para el análisis?")
        
        unification_mapping_by_province = {}
        
        for province, similar_groups in similar_groups_by_province.items():
            if not similar_groups:
                continue
                
            st.markdown(f"### 📍 Provincia: {province}")
            
            province_mapping = {}
            
            for i, (key_sector, similar_list) in enumerate(similar_groups.items()):
                with st.expander(f"📍 Grupo {i+1} en {province}: {key_sector} ({len(similar_list)} variantes)", expanded=True):
                    
                    # Mostrar todas las variantes encontradas
                    st.write("**Variantes encontradas:**")
                    for variant in similar_list:
                        st.write(f"• {variant}")
                    
                    # Opción de unificación
                    unify_key = f"{prefix}_unify_{province.replace(' ', '_')}_{i}"
                    should_unify = st.checkbox(
                        "✅ Unificar estas variantes",
                        key=unify_key,
                        help="Marca esta opción para tratar todas estas variantes como el mismo sector"
                    )
                    
                    if should_unify:
                        # Seleccionar nombre unificado
                        unified_name_key = f"{prefix}_unified_name_{province.replace(' ', '_')}_{i}"
                        
                        # Opciones: las variantes existentes + opción personalizada
                        name_options = ["Personalizado"] + similar_list
                        
                        selected_option = st.selectbox(
                            "Nombre unificado:",
                            options=name_options,
                            index=1,  # Por defecto usar el primer sector del grupo
                            key=f"{prefix}_name_option_{province.replace(' ', '_')}_{i}"
                        )
                        
                        if selected_option == "Personalizado":
                            unified_name = st.text_input(
                                "Escriba el nombre unificado:",
                                value=key_sector,
                                key=unified_name_key
                            )
                        else:
                            unified_name = selected_option
                        
                        if unified_name and unified_name.strip():
                            # Crear mapeo para todas las variantes en esta provincia
                            for variant in similar_list:
                                province_mapping[variant] = unified_name.strip()
            
            if province_mapping:
                unification_mapping_by_province[province] = province_mapping
        
        return unification_mapping_by_province
    
    def render_sector_unification_interface(self, similar_groups, prefix="sector"):
        """
        Renderizar interfaz para unificar sectores similares
        
        Args:
            similar_groups (dict): Grupos de sectores similares
            prefix (str): Prefijo para las keys de session state
            
        Returns:
            dict: Mapeo de unificaciones seleccionadas
        """
        if not similar_groups:
            return {}
        
        st.subheader("🔍 Sectores con Posibles Errores Ortográficos")
        st.info("📝 Se detectaron sectores con nombres similares. ¿Desea unificarlos para el análisis?")
        
        unification_mapping = {}
        
        for i, (key_sector, similar_list) in enumerate(similar_groups.items()):
            with st.expander(f"📍 Grupo {i+1}: {key_sector} ({len(similar_list)} variantes)", expanded=True):
                
                # Mostrar todas las variantes encontradas
                st.write("**Variantes encontradas:**")
                for variant in similar_list:
                    st.write(f"• {variant}")
                
                # Opción de unificación
                unify_key = f"{prefix}_unify_{i}"
                should_unify = st.checkbox(
                    "✅ Unificar estas variantes",
                    key=unify_key,
                    help="Marca esta opción para tratar todas estas variantes como el mismo sector"
                )
                
                if should_unify:
                    # Seleccionar nombre unificado
                    unified_name_key = f"{prefix}_unified_name_{i}"
                    
                    # Opciones: las variantes existentes + opción personalizada
                    name_options = ["Personalizado"] + similar_list
                    
                    selected_option = st.selectbox(
                        "Nombre unificado:",
                        options=name_options,
                        index=1,  # Por defecto usar el primer sector del grupo
                        key=f"{prefix}_name_option_{i}"
                    )
                    
                    if selected_option == "Personalizado":
                        unified_name = st.text_input(
                            "Escriba el nombre unificado:",
                            value=key_sector,
                            key=unified_name_key
                        )
                    else:
                        unified_name = selected_option
                    
                    if unified_name and unified_name.strip():
                        # Crear mapeo para todas las variantes
                        for variant in similar_list:
                            unification_mapping[variant] = unified_name.strip()
        
        return unification_mapping
    
    def apply_unification(self, data, column_name, unification_mapping):
        """
        Aplicar unificación de sectores a los datos
        
        Args:
            data (DataFrame): DataFrame con los datos
            column_name (str): Nombre de la columna de sectores
            unification_mapping (dict): Mapeo de unificaciones
            
        Returns:
            DataFrame: DataFrame con sectores unificados
        """
        if not unification_mapping or column_name not in data.columns:
            return data
        
        # Crear copia para no modificar original
        unified_data = data.copy()
        
        # Aplicar mapeo
        unified_data[column_name] = unified_data[column_name].replace(unification_mapping)
        
        return unified_data
    
    def get_sector_filter_options(self, sectors_list, unification_mapping=None):
        """
        Obtener opciones para filtro de sectores (con unificación aplicada)
        
        Args:
            sectors_list (list): Lista original de sectores
            unification_mapping (dict): Mapeo de unificaciones
            
        Returns:
            list: Lista de sectores únicos (unificados)
        """
        if unification_mapping:
            # Aplicar unificación
            unified_sectors = []
            for sector in sectors_list:
                if pd.notna(sector) and str(sector).strip() != '':
                    unified_name = unification_mapping.get(sector, sector)
                    unified_sectors.append(unified_name)
        else:
            unified_sectors = [s for s in sectors_list if pd.notna(s) and str(s).strip() != '']
        
        # Retornar lista única y ordenada
        return sorted(list(set(unified_sectors)))
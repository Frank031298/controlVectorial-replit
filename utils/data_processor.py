import pandas as pd
import numpy as np
from datetime import datetime
import os
import gc
import streamlit as st

class DataProcessor:
    def __init__(self, data):
        # DETECTAR ENTORNO PUBLICADO DE REPLIT
        self.is_production = self._detect_replit_production()
        
        # OPTIMIZACIÓN CRÍTICA PARA PRODUCCIÓN
        if self.is_production:
            data = self._optimize_for_production(data)
            
        self.data = data.copy()
        self._initialize_health_facilities()
        self.process_data()
        
        # Forzar limpieza de memoria
        if self.is_production:
            gc.collect()
    
    def _detect_replit_production(self):
        """Detecta si estamos en el entorno publicado de Replit"""
        # Replit establece variables de entorno específicas en producción
        replit_env_indicators = [
            os.getenv('REPL_DEPLOYMENT') == '1',
            os.getenv('REPL_ENVIRONMENT') == 'production',
            os.getenv('HOSTNAME', '').startswith('app-'),
            not os.path.exists('/home/runner/'),  # Path típico de desarrollo
            'replit.app' in os.getenv('REPL_URL', ''),
        ]
        return any(replit_env_indicators)
    
    def _optimize_for_production(self, data):
        """Optimizaciones críticas para entorno publicado - LÍMITES ULTRA ESTRICTOS PARA EVITAR AXIOS ERROR 413"""
        original_shape = data.shape
        
        # LÍMITE CRÍTICO: Replit Published Apps tienen límites de proxy más estrictos
        memory_mb = data.memory_usage(deep=True).sum() / 1024 / 1024
        
        # ACTUALIZADO: Procesar datos completos sin limitaciones de registros
        st.info(f"🚀 **Procesando dataset completo**: {len(data):,} registros, ~{memory_mb:.1f}MB memoria")
        
        # Solo advertir si es extremadamente grande
        if memory_mb > 500:  # Solo para archivos realmente masivos
            st.warning(f"🚨 **Archivo muy grande**: {len(data):,} registros (~{memory_mb:.1f}MB). El procesamiento puede tomar tiempo adicional.")
        
        # Comentario: Se removieron todas las limitaciones de registros a solicitud del usuario
        # para permitir el procesamiento completo de 285,785 registros
        
        # CRÍTICO: Eliminar columnas completamente vacías
        empty_cols = list(data.columns[data.isnull().all()])
        if empty_cols:
            data = data.drop(columns=empty_cols)
            st.info(f"🧹 Eliminadas {len(empty_cols)} columnas vacías para optimizar memoria.")
        
        # OPTIMIZACIÓN AGRESIVA: Convertir object a category para strings repetitivos
        category_savings = 0
        for col in data.select_dtypes(include=['object']):
            unique_ratio = data[col].nunique() / len(data)
            if unique_ratio < 0.3:  # Más agresivo: menos del 30% son valores únicos
                original_memory = data[col].memory_usage(deep=True)
                data[col] = data[col].astype('category')
                new_memory = data[col].memory_usage(deep=True)
                category_savings += (original_memory - new_memory) / 1024 / 1024
        
        if category_savings > 0:
            st.info(f"🗜️ Compresión categorica: {category_savings:.1f}MB ahorrados")
        
        # CRÍTICO: NO ELIMINAR COLUMNAS AUTOMÁTICAMENTE
        # Nota: Se removió optimización que eliminaba columnas con >95% valores únicos
        # ya que puede eliminar identificadores importantes como códigos RENIPRESS, IDs, etc.
        
        # CRÍTICO: Limpiar session state de datos temporales para evitar duplicación
        if 'url_data' in st.session_state:
            try:
                del st.session_state['url_data']
                st.info("🧹 Limpiado session state temporal (url_data) para evitar AxiosError 413")
            except:
                pass
        
        if 'app_storage_data' in st.session_state:
            try:
                del st.session_state['app_storage_data']
                st.info("🧹 Limpiado session state temporal (app_storage_data)")
            except:
                pass
        
        # Forzar garbage collection para liberar memoria inmediatamente
        gc.collect()
        
        final_memory = data.memory_usage(deep=True).sum() / 1024 / 1024
        memory_saved = memory_mb - final_memory
        
        if original_shape != data.shape or memory_saved > 1:
            st.success(f"✅ Optimización completa: {original_shape[0]:,}×{original_shape[1]} → {data.shape[0]:,}×{data.shape[1]}")
            st.success(f"💾 Memoria: {memory_mb:.1f}MB → {final_memory:.1f}MB (ahorrado: {memory_saved:.1f}MB)")
        
        return data
        
    def _initialize_health_facilities(self):
        """Initialize health facilities reference data"""
        self.health_facilities = {
            5060: {"name": "LA LIBERTAD", "total_houses": 136},
            5044: {"name": "GUSTAVO LANATTA LUJAN", "total_houses": 4282},
            7276: {"name": "LA PRIMAVERA", "total_houses": 1822},
            7435: {"name": "MESONES MURO", "total_houses": 426},
            7006: {"name": "SAN FRANCISCO", "total_houses": 188},
            5126: {"name": "MIRAFLORES", "total_houses": 206},
            5135: {"name": "VISTA ALEGRE", "total_houses": 41},
            5136: {"name": "LA VICTORIA", "total_houses": 486},
            5137: {"name": "PUEBLO LIBRE", "total_houses": 50},
            7225: {"name": "MORROPON", "total_houses": 90},
            7285: {"name": "SAN LUIS", "total_houses": 1874},
            5095: {"name": "SAN JUAN DE LA LIBERTAD", "total_houses": 456},
            5096: {"name": "JOSE OLAYA", "total_houses": 280},
            7258: {"name": "SANTA ISABEL", "total_houses": 138},
            7259: {"name": "LA UNION", "total_houses": 100},
            5066: {"name": "EL MILAGRO", "total_houses": 505},
            1720: {"name": "SAN RAFAEL", "total_houses": 804},
            1744: {"name": "LA VICTORIA", "total_houses": 7191},
            1659: {"name": "PROGRESO", "total_houses": 9674},
            1660: {"name": "LA UNION", "total_houses": 4576},
            1661: {"name": "SAN PEDRO", "total_houses": 11249},
            1662: {"name": "VICTOR RAUL", "total_houses": 2309},
            1663: {"name": "TUPAC AMARU", "total_houses": 1799},
            1664: {"name": "LA ESPERANZA", "total_houses": 2004},
            1715: {"name": "SAN JACINTO", "total_houses": 10725},
            1706: {"name": "VILLA MARIA", "total_houses": 5568},
            1681: {"name": "ALTO PERU", "total_houses": 374},
            2664: {"name": "BELLAVISTA", "total_houses": 3738},
            8828: {"name": "SAN MARTIN", "total_houses": 2213},
            2570: {"name": "SANTA ROSA", "total_houses": 350},
            1345: {"name": "SAN JOSE", "total_houses": 90},
            1368: {"name": "SANTA ROSA", "total_houses": 153},
            23961: {"name": "MIRAFLORES", "total_houses": 365},
            3760: {"name": "LECHEMAYO", "total_houses": 716},
            3749: {"name": "PALMAPAMPA", "total_houses": 1924}
        }
    
    def process_data(self):
        """Process and clean the data - OPTIMIZADO PARA REPLIT"""
        # CRÍTICO: Limpiar TODOS los valores vacíos que causan error 413
        self.data = self.data.replace('', np.nan)
        self.data = self.data.replace(' ', np.nan)
        self.data = self.data.replace('nan', np.nan)
        
        # Convert date columns
        date_columns = ['fecha_inspeccion', '_createdAt_x', '_createdAt_y', 'hora_ingreso', 
                       'hora_salida', 'fecha_creacion', 'recuperacion_fecha', 
                       'recuperacion_fecha_asignacion']
        
        for col in date_columns:
            if col in self.data.columns:
                self.data[col] = pd.to_datetime(self.data[col], errors='coerce')
        
        # Extract year from fecha_inspeccion
        if 'fecha_inspeccion' in self.data.columns:
            self.data['year'] = self.data['fecha_inspeccion'].dt.year
        
        # CRÍTICO: Manejar columnas numéricas específicas para evitar errores PyArrow
        critical_numeric_columns = ['cod_renipress', 'aedic_index', 'container_index', 
                                  'breteau_index', 'intensity', 'indice_aedico']
        
        for col in critical_numeric_columns:
            if col in self.data.columns:
                self.data[col] = pd.to_numeric(self.data[col], errors='coerce')
                self.data[col] = self.data[col].fillna(0)
        
        # Fill NaN values for numeric columns
        numeric_columns = self.data.select_dtypes(include=[np.number]).columns
        self.data[numeric_columns] = self.data[numeric_columns].fillna(0)
        
        # Fill NaN values for text columns - CRÍTICO para serialización
        text_columns = self.data.select_dtypes(include=['object']).columns
        for col in text_columns:
            if col not in date_columns:  # No tocar fechas convertidas
                self.data[col] = self.data[col].fillna('')
                self.data[col] = self.data[col].astype(str)
                self.data[col] = self.data[col].replace('nan', '')
                self.data[col] = self.data[col].replace('NaN', '')
                self.data[col] = self.data[col].replace('None', '')
        
        # OPTIMIZACIÓN ACTUALIZADA: Permitir procesamiento completo de datasets
        if len(self.data) > 200000:  # Solo advertir para datasets extremadamente grandes
            print(f"🚨 Dataset muy grande ({len(self.data):,} registros). Procesando completo, puede tomar tiempo adicional.")
        # Comentario: Se removió limitación de 100,000 registros a solicitud del usuario
    
    def get_filtered_data(self, activity_type=None, filters=None):
        """Filter data based on activity type and additional filters"""
        filtered_data = self.data.copy()
        
        # Apply sector unification if present (by province)
        if filters and 'sector_unification_mapping_by_province' in filters and 'sector' in filtered_data.columns and 'nombre_prov' in filtered_data.columns:
            unification_mapping_by_province = filters['sector_unification_mapping_by_province']
            if unification_mapping_by_province:
                from utils.sector_similarity import SectorSimilarityDetector
                detector = SectorSimilarityDetector()
                # Apply unification considering province context
                for province, mapping in unification_mapping_by_province.items():
                    province_mask = filtered_data['nombre_prov'] == province
                    if province_mask.any():
                        province_data = filtered_data[province_mask].copy()
                        province_data = detector.apply_unification(province_data, 'sector', mapping)
                        filtered_data.loc[province_mask] = province_data
        
        # Fallback to old mapping system for backward compatibility
        elif filters and 'sector_unification_mapping' in filters and 'sector' in filtered_data.columns:
            unification_mapping = filters['sector_unification_mapping']
            if unification_mapping:
                from utils.sector_similarity import SectorSimilarityDetector
                detector = SectorSimilarityDetector()
                filtered_data = detector.apply_unification(filtered_data, 'sector', unification_mapping)
        
        # Filter by activity type
        if activity_type:
            filtered_data = filtered_data[
                filtered_data['tipoActividadInspeccion'].str.lower() == activity_type.lower()
            ]
        
        # Apply additional filters (excluding the unification mapping which was already processed)
        if filters:
            for key, value in filters.items():
                if key in ['sector_unification_mapping', 'sector_unification_mapping_by_province']:
                    continue  # Skip these as they were already processed above
                    
                if value and key in filtered_data.columns:
                    if isinstance(value, list):
                        filtered_data = filtered_data[filtered_data[key].isin(value)]
                    else:
                        filtered_data = filtered_data[filtered_data[key] == value]
        
        return filtered_data
    
    def get_unique_values(self, column_name, sorted_order=True):
        """Get unique values from a column"""
        if column_name not in self.data.columns:
            return []
        
        unique_values = self.data[column_name].dropna().unique()
        
        if sorted_order:
            # Try to sort numerically first, then alphabetically
            try:
                unique_values = sorted(unique_values, key=lambda x: float(x) if str(x).replace('.', '').isdigit() else float('inf'))
            except:
                unique_values = sorted(unique_values, key=str)
        
        # Convert to list if it's a numpy array
        # Convertir a lista de forma segura
        return list(unique_values)
    
    def get_date_range(self):
        """Get min and max dates from fecha_inspeccion"""
        if 'fecha_inspeccion' in self.data.columns:
            dates = self.data['fecha_inspeccion'].dropna()
            if len(dates) > 0:
                return dates.min().date(), dates.max().date()
        return None, None
    
    def get_container_columns(self):
        """Get all container-related columns organized by type"""
        containers = {
            "Tanque Alto": ["tanque_alto_I", "tanque_alto_P", "tanque_alto_TQ", "tanque_alto_TF"],
            "Tanque Bajo": ["tanque_bajo_I", "tanque_bajo_P", "tanque_bajo_TQ", "tanque_bajo_TF"],
            "Barril/Cilindro": ["barril_cilindro_I", "barril_cilindro_P", "barril_cilindro_TQ", "barril_cilindro_TF"],
            "Sansón/Bidón": ["sanson_bidon_I", "sanson_bidon_P", "sanson_bidon_TQ", "sanson_bidon_TF"],
            "Baldes/Bateas/Tinajas": ["baldes_bateas_tinajas_I", "baldes_bateas_tinajas_P", "baldes_bateas_tinajas_TQ", "baldes_bateas_tinajas_TF"],
            "Llantas": ["llantas_I", "llantas_P", "llantas_TQ", "llantas_TF"],
            "Floreros/Maceteros": ["floreros_maceteros_I", "floreros_maceteros_P", "floreros_maceteros_TQ", "floreros_maceteros_TF"],
            "Latas/Botellas": ["latas_botellas_I", "latas_botellas_D", "latas_botellas_P", "latas_botellas_TQ", "latas_botellas_TF"],
            "Otros": ["otros_I", "otros_P", "otros_TQ", "otros_TF", "otros_D"],
            "Inservibles": ["inservibles_I", "inservibles_P", "inservibles_TQ", "inservibles_TF"]
        }
        return containers
    
    def get_container_status_labels(self):
        """Get container status labels"""
        return {
            "_I": "Inspeccionado(s)",
            "_P": "Positivo(s)",
            "_TQ": "Tratamiento Químico",
            "_TF": "Tratamiento Físico",
            "_D": "Desuso(s)"
        }

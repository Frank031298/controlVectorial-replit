"""
Utilidades para mejorar las tablas del sistema con funcionalidades adicionales
como filas de suma total, formateo mejorado, etc.
"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import List, Optional, Union

def safe_dataframe(df: pd.DataFrame, 
                  max_rows: int = 50000,  # Architect recommendation: >50k rows
                  max_memory_mb: float = 50.0,  # Architect recommendation: >50MB
                  use_container_width: bool = True,
                  hide_index: bool = True,
                  column_config: dict = None,
                  **kwargs) -> None:
    """
    CRITICAL: Safe DataFrame display to prevent AxiosError 413
    
    Automatically limits DataFrame size for frontend rendering:
    - If DataFrame is too large, shows only head(max_rows) + summary
    - Prevents frontend payload from exceeding limits
    
    Args:
        df: DataFrame to display
        max_rows: Maximum rows to show (default 50000 per Architect recommendation)
        max_memory_mb: Maximum memory in MB (default 50MB per Architect recommendation)
        use_container_width: Streamlit dataframe parameter
        hide_index: Streamlit dataframe parameter
        column_config: Streamlit dataframe parameter
        **kwargs: Additional streamlit dataframe parameters
    """
    if df is None or df.empty:
        st.info("No hay datos disponibles para mostrar.")
        return
    
    # Calculate DataFrame memory usage
    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    total_rows = len(df)
    
    # Determine if DataFrame is too large for safe frontend rendering
    is_too_large = total_rows > max_rows or memory_mb > max_memory_mb
    
    if is_too_large:
        # CRITICAL FIX: Calculate safe row count based on both memory AND row constraints
        if memory_mb > max_memory_mb:
            # Calculate safe row count based on memory limit
            memory_safe_rows = max(1000, int(max_memory_mb * total_rows / memory_mb))
            safe_row_count = min(max_rows, memory_safe_rows)
        else:
            safe_row_count = max_rows
        
        # Show warning and summary
        st.warning(f"🚨 **Dataset grande detectado**: {total_rows:,} filas, ~{memory_mb:.1f}MB\n"
                  f"📊 **Mostrando primeras {safe_row_count:,} filas** para evitar Error 413\n"
                  f"💡 **Use filtros** para ver subconjuntos específicos")
        
        # Display summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total de filas", f"{total_rows:,}")
        with col2:
            st.metric("💾 Memoria total", f"{memory_mb:.1f}MB")
        with col3:
            st.metric("👀 Mostrando", f"{safe_row_count:,} filas")
        
        # Display limited DataFrame with GUARANTEED memory-safe row count
        limited_df = df.head(safe_row_count)
        
        # CRITICAL: DETERMINISTIC memory enforcement - NO ITERATION LIMIT
        # Continue reducing until under memory limit with safety margin
        limited_memory_mb = limited_df.memory_usage(deep=True).sum() / (1024 * 1024)
        min_rows = 50  # Absolute minimum rows for any display
        
        while limited_memory_mb > max_memory_mb * 0.90 and safe_row_count > min_rows:
            # Use geometric reduction for efficiency
            safe_row_count = max(min_rows, int(safe_row_count * 0.75))
            limited_df = df.head(safe_row_count)
            limited_memory_mb = limited_df.memory_usage(deep=True).sum() / (1024 * 1024)
            
        # ULTIMATE ENFORCEMENT: Apply 90% margin even at minimum rows
        if limited_memory_mb > max_memory_mb * 0.90:
            st.error(f"⚠️ **Dataset extremadamente ancho**: Incluso {min_rows} filas (~{limited_memory_mb:.1f}MB) exceden el límite.\n"
                    f"📋 **Mostrando solo estructura de datos** para evitar Error 413.")
            
            # Display schema information only
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📋 Estructura del Dataset")
                schema_info = pd.DataFrame({
                    'Columna': df.columns,
                    'Tipo': [str(dtype) for dtype in df.dtypes],
                    'No Nulos': [df[col].count() for col in df.columns],
                    'Valores Únicos': [df[col].nunique() for col in df.columns]
                })
                st.dataframe(schema_info, use_container_width=True)
            
            with col2:
                st.subheader("📊 Estadísticas Básicas")
                st.write(f"**Total filas:** {len(df):,}")
                st.write(f"**Total columnas:** {len(df.columns):,}")
                st.write(f"**Memoria total:** ~{memory_mb:.1f}MB")
                st.write(f"**Memoria por fila:** ~{memory_mb/len(df)*1024:.1f}KB")
            
            return  # Exit without showing dataframe
            
        # Update the displayed row count after final enforcement
        col3.metric("👀 Mostrando", f"{safe_row_count:,} filas")
        st.dataframe(
            limited_df,
            use_container_width=use_container_width,
            hide_index=hide_index,
            column_config=column_config,
            **kwargs
        )
        
        # Show information about remaining data
        if total_rows > max_rows:
            st.info(f"⬇️ **{total_rows - max_rows:,} filas adicionales** no se muestran para evitar errores de memoria.\n"
                   f"💡 Use los filtros arriba para explorar datos específicos.")
    else:
        # Safe to display full DataFrame
        st.dataframe(
            df,
            use_container_width=use_container_width,
            hide_index=hide_index,
            column_config=column_config,
            **kwargs
        )

def add_total_row(df: pd.DataFrame, 
                  exclude_columns: Optional[List[str]] = None,
                  total_label: str = "TOTAL",
                  label_column: Optional[str] = None) -> pd.DataFrame:
    """
    Agrega una fila de suma total a un DataFrame.
    
    Args:
        df: DataFrame original
        exclude_columns: Lista de columnas a excluir del cálculo de suma
        total_label: Etiqueta para la fila total
        label_column: Columna donde colocar la etiqueta TOTAL (primera columna string por defecto)
    
    Returns:
        DataFrame con fila de suma total agregada
    """
    
    if df.empty:
        return df
    
    # Crear copia del DataFrame original
    df_copy = df.copy()
    
    # Identificar columnas numéricas
    numeric_columns = df_copy.select_dtypes(include=[np.number]).columns.tolist()
    
    # Remover columnas excluidas
    if exclude_columns:
        numeric_columns = [col for col in numeric_columns if col not in exclude_columns]
    
    # Si no hay columnas numéricas, retornar el DataFrame original
    if not numeric_columns:
        return df_copy
    
    # Crear fila de totales
    total_row = {}
    
    # Inicializar todas las columnas
    for col in df_copy.columns:
        if col in numeric_columns:
            # Sumar valores numéricos, ignorando NaN
            total_value = df_copy[col].sum()
            # Mantener el formato de la columna original
            if df_copy[col].dtype == 'int64':
                total_row[col] = int(total_value) if not pd.isna(total_value) else 0
            else:
                total_row[col] = round(total_value, 2) if not pd.isna(total_value) else 0.0
        else:
            # Para columnas no numéricas, usar string vacío
            total_row[col] = ""
    
    # Determinar dónde colocar la etiqueta TOTAL
    if label_column and label_column in df_copy.columns:
        total_row[label_column] = total_label
    else:
        # Buscar la primera columna de tipo string/object para colocar el TOTAL
        text_columns = df_copy.select_dtypes(include=['object', 'string']).columns
        if not text_columns.empty:
            total_row[text_columns[0]] = total_label
        elif df_copy.columns.any():
            # Si no hay columnas de texto, usar la primera columna
            total_row[df_copy.columns[0]] = total_label
    
    # Agregar la fila total al DataFrame
    total_df = pd.DataFrame([total_row])
    result_df = pd.concat([df_copy, total_df], ignore_index=True)
    
    return result_df

def format_dataframe_for_display(df: pd.DataFrame,
                                float_columns: Optional[List[str]] = None,
                                int_columns: Optional[List[str]] = None,
                                percentage_columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Formatea un DataFrame para mostrar con mejor legibilidad.
    
    Args:
        df: DataFrame a formatear
        float_columns: Columnas a formatear como flotante con 2 decimales
        int_columns: Columnas a formatear como enteros
        percentage_columns: Columnas a formatear como porcentajes
    
    Returns:
        DataFrame formateado
    """
    
    df_formatted = df.copy()
    
    # Formatear columnas de flotantes
    if float_columns:
        for col in float_columns:
            if col in df_formatted.columns:
                df_formatted[col] = df_formatted[col].round(2)
    
    # Formatear columnas de enteros
    if int_columns:
        for col in int_columns:
            if col in df_formatted.columns:
                df_formatted[col] = df_formatted[col].fillna(0).astype(int)
    
    # Formatear columnas de porcentajes
    if percentage_columns:
        for col in percentage_columns:
            if col in df_formatted.columns:
                df_formatted[col] = df_formatted[col].round(1)
    
    return df_formatted

def create_enhanced_dataframe(df: pd.DataFrame,
                             add_totals: bool = True,
                             total_label: str = "TOTAL",
                             exclude_from_total: Optional[List[str]] = None,
                             label_column: Optional[str] = None) -> pd.DataFrame:
    """
    Función principal para crear DataFrames mejorados con totales y formato.
    
    Args:
        df: DataFrame original
        add_totals: Si agregar fila de totales
        total_label: Etiqueta para la fila total
        exclude_from_total: Columnas a excluir del cálculo de suma
        label_column: Columna donde colocar la etiqueta TOTAL
    
    Returns:
        DataFrame mejorado
    """
    
    if df.empty:
        return df
    
    enhanced_df = df.copy()
    
    # Agregar fila de totales si se solicita
    if add_totals:
        enhanced_df = add_total_row(
            enhanced_df,
            exclude_columns=exclude_from_total,
            total_label=total_label,
            label_column=label_column
        )
    
    return enhanced_df
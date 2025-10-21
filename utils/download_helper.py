"""
Helper para descargas de archivos XLSX
"""
import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime

def create_excel_download_button(dataframe, filename_prefix, button_label="📥 Descargar XLSX", key_suffix=""):
    """
    Crea un botón de descarga XLSX para cualquier DataFrame
    
    Args:
        dataframe: DataFrame de pandas a descargar
        filename_prefix: Prefijo para el nombre del archivo
        button_label: Texto del botón
        key_suffix: Sufijo para hacer única la key del botón
    """
    if dataframe.empty:
        st.info("No hay datos disponibles para descargar")
        return
    
    # Generar archivo Excel en memoria
    output = BytesIO()
    
    # Crear el writer con el buffer
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        dataframe.to_excel(writer, sheet_name='Datos', index=False)
    
    # Obtener los datos del buffer
    excel_data = output.getvalue()
    
    # Generar nombre de archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.xlsx"
    
    # Botón de descarga
    st.download_button(
        label=button_label,
        data=excel_data,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_xlsx_{filename_prefix}_{key_suffix}",
        help="Hacer clic para descargar los datos en formato Excel"
    )

def create_multi_sheet_excel_download(data_dict, filename_prefix, button_label="📥 Descargar XLSX Completo", key_suffix=""):
    """
    Crea un archivo Excel con múltiples hojas
    
    Args:
        data_dict: Diccionario con {nombre_hoja: dataframe}
        filename_prefix: Prefijo para el nombre del archivo
        button_label: Texto del botón
        key_suffix: Sufijo para hacer única la key del botón
    """
    if not data_dict or all(df.empty for df in data_dict.values()):
        st.info("No hay datos disponibles para descargar")
        return
    
    # Generar archivo Excel en memoria
    output = BytesIO()
    
    # Crear el writer con el buffer
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, dataframe in data_dict.items():
            if not dataframe.empty:
                # Limpiar nombre de hoja (Excel tiene restricciones)
                clean_sheet_name = sheet_name.replace("/", "_").replace("\\", "_")[:31]
                dataframe.to_excel(writer, sheet_name=clean_sheet_name, index=False)
    
    # Obtener los datos del buffer
    excel_data = output.getvalue()
    
    # Generar nombre de archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.xlsx"
    
    # Botón de descarga
    st.download_button(
        label=button_label,
        data=excel_data,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_multi_xlsx_{filename_prefix}_{key_suffix}",
        help="Hacer clic para descargar el archivo Excel completo con múltiples hojas"
    )
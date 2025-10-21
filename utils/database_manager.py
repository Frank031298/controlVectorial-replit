"""
Gestor de base de datos para establecimientos de salud y datos de viviendas
"""
import os
import json
import psycopg2
import pandas as pd
from datetime import datetime
from housing_data_parser import parse_housing_data_file

class DatabaseManager:
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL no está configurada en las variables de entorno")
    
    def get_connection(self):
        """Obtiene conexión a la base de datos"""
        return psycopg2.connect(self.database_url)
    
    def initialize_database(self):
        """Inicializa las tablas necesarias en la base de datos"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Crear tabla de establecimientos de salud
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS health_facilities (
                    cod_renipress INTEGER PRIMARY KEY,
                    nombre_establecimiento VARCHAR(255) NOT NULL,
                    total_viviendas INTEGER NOT NULL DEFAULT 0,
                    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario_actualizacion VARCHAR(100) DEFAULT 'sistema',
                    activo BOOLEAN DEFAULT TRUE
                );
            """)
            
            # Crear índice para búsquedas por nombre
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_health_facilities_nombre 
                ON health_facilities (nombre_establecimiento);
            """)
            
            conn.commit()
    
    def load_housing_data_from_file(self, file_path):
        """Carga datos de viviendas desde archivo de texto al sistema"""
        housing_data = parse_housing_data_file(file_path)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insertar o actualizar datos
            for cod_renipress, data in housing_data.items():
                cursor.execute("""
                    INSERT INTO health_facilities 
                    (cod_renipress, nombre_establecimiento, total_viviendas, fecha_actualizacion, usuario_actualizacion)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (cod_renipress) 
                    DO UPDATE SET 
                        nombre_establecimiento = EXCLUDED.nombre_establecimiento,
                        total_viviendas = EXCLUDED.total_viviendas,
                        fecha_actualizacion = EXCLUDED.fecha_actualizacion,
                        usuario_actualizacion = EXCLUDED.usuario_actualizacion;
                """, (
                    cod_renipress,
                    data['nombre'],
                    data['total_viviendas'],
                    datetime.now(),
                    'carga_inicial'
                ))
            
            conn.commit()
            print(f"Se cargaron/actualizaron {len(housing_data)} establecimientos de salud")
    
    def get_health_facility_data(self, cod_renipress=None):
        """
        Obtiene datos de establecimientos de salud
        Si cod_renipress es None, retorna todos los datos
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if cod_renipress:
                cursor.execute("""
                    SELECT cod_renipress, nombre_establecimiento, total_viviendas
                    FROM health_facilities 
                    WHERE cod_renipress = %s AND activo = TRUE
                """, (cod_renipress,))
                result = cursor.fetchone()
                if result:
                    return {
                        'cod_renipress': result[0],
                        'nombre': result[1],
                        'total_houses': result[2]
                    }
                return None
            else:
                cursor.execute("""
                    SELECT cod_renipress, nombre_establecimiento, total_viviendas
                    FROM health_facilities 
                    WHERE activo = TRUE
                    ORDER BY nombre_establecimiento
                """)
                results = cursor.fetchall()
                return {
                    row[0]: {
                        'nombre': row[1],
                        'total_houses': row[2]
                    }
                    for row in results
                }
    
    def get_missing_facilities(self, data_facilities):
        """
        Identifica establecimientos que están en los datos pero no en la base de datos
        """
        # Obtener todos los códigos de la base de datos
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cod_renipress FROM health_facilities WHERE activo = TRUE")
            db_codes = set(row[0] for row in cursor.fetchall())
        
        # Identificar códigos faltantes
        data_codes = set(data_facilities)
        missing_codes = data_codes - db_codes
        
        return list(missing_codes)
    
    def add_missing_facility(self, cod_renipress, nombre, total_viviendas, usuario='manual'):
        """Añade un establecimiento faltante a la base de datos"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO health_facilities 
                (cod_renipress, nombre_establecimiento, total_viviendas, fecha_actualizacion, usuario_actualizacion)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (cod_renipress) 
                DO UPDATE SET 
                    nombre_establecimiento = EXCLUDED.nombre_establecimiento,
                    total_viviendas = EXCLUDED.total_viviendas,
                    fecha_actualizacion = EXCLUDED.fecha_actualizacion,
                    usuario_actualizacion = EXCLUDED.usuario_actualizacion;
            """, (cod_renipress, nombre, total_viviendas, datetime.now(), usuario))
            conn.commit()
    
    def update_facility_housing(self, cod_renipress, total_viviendas, usuario='manual'):
        """Actualiza el total de viviendas para un establecimiento"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE health_facilities 
                SET total_viviendas = %s, 
                    fecha_actualizacion = %s, 
                    usuario_actualizacion = %s
                WHERE cod_renipress = %s
            """, (total_viviendas, datetime.now(), usuario, cod_renipress))
            conn.commit()
    
    def export_facilities_to_excel(self):
        """Exporta datos de establecimientos a Excel para edición masiva"""
        with self.get_connection() as conn:
            df = pd.read_sql("""
                SELECT cod_renipress as "Código RENIPRESS", 
                       nombre_establecimiento as "Nombre del Establecimiento", 
                       total_viviendas as "Total de Viviendas"
                FROM health_facilities 
                WHERE activo = TRUE
                ORDER BY nombre_establecimiento
            """, conn)
            
            filename = f"establecimientos_salud_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(filename, index=False)
            return filename
    
    def import_facilities_from_excel(self, excel_path, usuario='excel_import'):
        """Importa datos de establecimientos desde Excel"""
        df = pd.read_excel(excel_path)
        
        # Validar columnas necesarias
        required_cols = ['Código RENIPRESS', 'Nombre del Establecimiento', 'Total de Viviendas']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"El archivo debe contener las columnas: {required_cols}")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO health_facilities 
                    (cod_renipress, nombre_establecimiento, total_viviendas, fecha_actualizacion, usuario_actualizacion)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (cod_renipress) 
                    DO UPDATE SET 
                        nombre_establecimiento = EXCLUDED.nombre_establecimiento,
                        total_viviendas = EXCLUDED.total_viviendas,
                        fecha_actualizacion = EXCLUDED.fecha_actualizacion,
                        usuario_actualizacion = EXCLUDED.usuario_actualizacion;
                """, (
                    int(row['Código RENIPRESS']),
                    str(row['Nombre del Establecimiento']),
                    int(row['Total de Viviendas']),
                    datetime.now(),
                    usuario
                ))
            
            conn.commit()
            return len(df)
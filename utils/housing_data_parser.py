"""
Parser para los datos de viviendas de establecimientos de salud
"""
import re
import json
import pandas as pd

def parse_housing_data_file(file_path):
    """
    Parsea el archivo de datos de viviendas y retorna un diccionario
    con la información de cada establecimiento de salud
    """
    housing_data = {}
    
    with open(file_path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            if not line:
                continue
                
            # Patrón para extraer datos: cod_renipress, nombre, total_viviendas
            pattern = r'Codigo Unico \(cod_renipress\) es: (\d+) y su nombre de establecimiento de salud \(localidad_eess\) es: (.+?) y su total de viviendas es: (\d+)'
            match = re.match(pattern, line)
            
            if match:
                cod_renipress = int(match.group(1))
                nombre = match.group(2).strip()
                total_viviendas = int(match.group(3))
                
                housing_data[cod_renipress] = {
                    'nombre': nombre,
                    'total_viviendas': total_viviendas,
                    'linea': line_num
                }
            else:
                print(f"Línea {line_num} no coincide con el patrón esperado: {line}")
    
    return housing_data

def save_housing_data_to_json(housing_data, output_path):
    """Guarda los datos de viviendas en un archivo JSON"""
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(housing_data, file, ensure_ascii=False, indent=2)

def load_housing_data_from_json(json_path):
    """Carga los datos de viviendas desde un archivo JSON"""
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def update_health_facilities_data(existing_facilities, new_housing_data):
    """
    Actualiza los datos de establecimientos de salud con la nueva información de viviendas
    """
    updated_facilities = existing_facilities.copy()
    
    # Convertir claves de string a int si es necesario
    for cod_renipress_str, data in new_housing_data.items():
        cod_renipress = int(cod_renipress_str) if isinstance(cod_renipress_str, str) else cod_renipress_str
        
        if cod_renipress not in updated_facilities:
            updated_facilities[cod_renipress] = {}
            
        updated_facilities[cod_renipress].update({
            'nombre': data['nombre'],
            'total_houses': data['total_viviendas']
        })
    
    return updated_facilities

if __name__ == "__main__":
    # Test del parser
    file_path = "../attached_assets/Pasted-Codigo-Unico-cod-renipress-es-5060-y-su-nombre-de-establecimiento-de-salud-localidad-eess-es-L-1757966895396_1757966895399.txt"
    housing_data = parse_housing_data_file(file_path)
    print(f"Datos procesados: {len(housing_data)} establecimientos")
    
    # Mostrar algunos ejemplos
    for i, (cod, data) in enumerate(housing_data.items()):
        if i < 5:
            print(f"Código {cod}: {data['nombre']} - {data['total_viviendas']} viviendas")
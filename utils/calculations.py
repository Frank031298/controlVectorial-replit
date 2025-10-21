import pandas as pd
import numpy as np
import os
import psycopg2

class EpidemiologicalCalculations:
    def __init__(self, data_processor):
        self.data_processor = data_processor
        self.database_url = os.environ.get('DATABASE_URL')
        # Cargar datos de establecimientos desde base de datos
        self.health_facilities = self._load_health_facilities_from_db()
        
    def _load_health_facilities_from_db(self):
        """Carga datos de establecimientos desde PostgreSQL"""
        if not self.database_url:
            # Fallback a datos hardcodeados si no hay base de datos
            return {
                # Fallback data in case database is not available
                5060: {'name': 'LA LIBERTAD', 'total_houses': 136},
            5044: {'name': 'GUSTAVO LANATTA LUJAN', 'total_houses': 4282},
            7276: {'name': 'LA PRIMAVERA', 'total_houses': 1822},
            7435: {'name': 'MESONES MURO', 'total_houses': 426},
            7006: {'name': 'SAN FRANCISCO', 'total_houses': 188},
            5126: {'name': 'MIRAFLORES', 'total_houses': 206},
            5135: {'name': 'VISTA ALEGRE', 'total_houses': 41},
            5136: {'name': 'LA VICTORIA', 'total_houses': 486},
            5137: {'name': 'PUEBLO LIBRE', 'total_houses': 50},
            7225: {'name': 'MORROPON', 'total_houses': 90},
            7285: {'name': 'SAN LUIS', 'total_houses': 1874},
            5095: {'name': 'SAN JUAN DE LA LIBERTAD', 'total_houses': 456},
            5096: {'name': 'JOSE OLAYA', 'total_houses': 280},
            7258: {'name': 'SANTA ISABEL', 'total_houses': 138},
            7259: {'name': 'LA UNION', 'total_houses': 100},
            5066: {'name': 'EL MILAGRO', 'total_houses': 505},
            1720: {'name': 'SAN RAFAEL', 'total_houses': 804},
            1744: {'name': 'LA VICTORIA', 'total_houses': 7191},
            1659: {'name': 'PROGRESO', 'total_houses': 9674},
            1660: {'name': 'LA UNION', 'total_houses': 4576},
            1661: {'name': 'SAN PEDRO', 'total_houses': 11249},
            1662: {'name': 'VICTOR RAUL', 'total_houses': 2309},
            1663: {'name': 'TUPAC AMARU', 'total_houses': 1799},
            1664: {'name': 'LA ESPERANZA', 'total_houses': 2004},
            1715: {'name': 'SAN JACINTO', 'total_houses': 10725},
            1706: {'name': 'VILLA MARIA', 'total_houses': 5568},
            1681: {'name': 'ALTO PERU', 'total_houses': 374},
            2664: {'name': 'BELLAVISTA', 'total_houses': 3738},
            8828: {'name': 'SAN MARTIN', 'total_houses': 2213},
            2570: {'name': 'SANTA ROSA', 'total_houses': 350},
            1345: {'name': 'SAN JOSE', 'total_houses': 90},
            1368: {'name': 'SANTA ROSA', 'total_houses': 153},
            23961: {'name': 'MIRAFLORES', 'total_houses': 365},
            3760: {'name': 'LECHEMAYO', 'total_houses': 716},
            3749: {'name': 'PALMAPAMPA', 'total_houses': 1924},
            3764: {'name': 'SANTA ROSA', 'total_houses': 3711},
            4230: {'name': 'SAN AGUSTIN', 'total_houses': 460},
            25858: {'name': 'NUEVO HORIZONTE', 'total_houses': 1327},
            4261: {'name': 'SANTA ROSA', 'total_houses': 579},
            4274: {'name': 'CHIRINOS', 'total_houses': 813},
            7411: {'name': 'BUENOS AIRES', 'total_houses': 198},
            10966: {'name': 'VISTA FLORIDA', 'total_houses': 62},
            10965: {'name': 'LA UNION', 'total_houses': 275},
            4267: {'name': 'SAN IGNACIO', 'total_houses': 6329},
            4270: {'name': 'NUEVA ESPERANZA', 'total_houses': 330},
            4272: {'name': 'SAN MARTIN', 'total_houses': 50},
            4273: {'name': 'SAN ANTONIO', 'total_houses': 143},
            6229: {'name': 'JOSE OLAYA', 'total_houses': 3391},
            6230: {'name': 'ACAPULCO', 'total_houses': 4412},
            6233: {'name': 'JUAN PABLO II', 'total_houses': 1855},
            6234: {'name': 'SANTA ROSA', 'total_houses': 1728},
            6235: {'name': 'MIGUEL GRAU', 'total_houses': 795},
            6246: {'name': 'EL ALAMO', 'total_houses': 4059},
            2355: {'name': 'LA QUEBRADA', 'total_houses': 689},
            2303: {'name': 'SANTA ROSA', 'total_houses': 56},
            2442: {'name': 'PUERTO RICO', 'total_houses': 99},
            8283: {'name': 'PUEBLO LIBRE', 'total_houses': 185},
            2460: {'name': 'SANTA MARIA', 'total_houses': 456},
            7113: {'name': 'NATIVIDAD', 'total_houses': 746},
            32211: {'name': 'NUEVO PROGRESO', 'total_houses': 1916},
            2468: {'name': 'SAN MARTIN', 'total_houses': 60},
            760: {'name': 'LA ESPERANZA', 'total_houses': 5637},
            775: {'name': 'ACOMAYO', 'total_houses': 1152},
            948: {'name': 'SAN ISIDRO', 'total_houses': 476},
            19199: {'name': 'SAN AGUSTIN', 'total_houses': 227},
            954: {'name': 'PUEBLO NUEVO', 'total_houses': 2865},
            956: {'name': 'LAS MERCEDES', 'total_houses': 272},
            958: {'name': 'TUPAC AMARU', 'total_houses': 183},
            27772: {'name': 'NUEVO PROGRESO', 'total_houses': 200},
            29172: {'name': 'LA PRIMAVERA', 'total_houses': 109},
            936: {'name': 'NARANJILLO', 'total_houses': 2653},
            940: {'name': 'MARONA', 'total_houses': 259},
            949: {'name': 'RICARDO PALMA', 'total_houses': 363},
            974: {'name': 'LAS PALMAS', 'total_houses': 509},
            18569: {'name': 'CONSUELO', 'total_houses': 416},
            28088: {'name': 'LA LOMA', 'total_houses': 220},
            942: {'name': 'HUASCAR', 'total_houses': 154},
            922: {'name': 'SEÑOR DE LOS MILAGROS', 'total_houses': 131},
            11071: {'name': 'EL DORADO', 'total_houses': 233},
            3442: {'name': 'SAN AGUSTIN', 'total_houses': 2579},
            7015: {'name': 'CRUZ BLANCA', 'total_houses': 2110},
            5193: {'name': 'C.S. EL PARCO', 'total_houses': 150}
        }
        
        try:
            # Intentar cargar desde base de datos
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cod_renipress, nombre_establecimiento, total_viviendas 
                FROM health_facilities 
                WHERE activo = TRUE
            """)
            results = cursor.fetchall()
            conn.close()
            
            # Convertir a diccionario en el formato esperado
            db_facilities = {}
            for cod_renipress, nombre, total_viviendas in results:
                db_facilities[cod_renipress] = {
                    'name': nombre,
                    'total_houses': total_viviendas
                }
                
            print(f"Cargados {len(db_facilities)} establecimientos desde base de datos")
            return db_facilities
            
        except Exception as e:
            print(f"Error al cargar desde base de datos, usando datos hardcodeados: {e}")
            return {
                # Fallback data in case database is not available
                5060: {'name': 'LA LIBERTAD', 'total_houses': 136},
                5044: {'name': 'GUSTAVO LANATTA LUJAN', 'total_houses': 4282}
            }
    
    def calculate_aedic_index(self, filtered_data):
        """
        Calculate Aedic Index for each health facility
        Formula: (Positive Houses / Inspected Houses) * 100
        """
        results = []
        
        # Group by health facility code
        grouped = filtered_data.groupby('cod_renipress')
        
        for renipress_code, group in grouped:
            # Count inspected houses (atencion_vivienda_indicador == 1)
            inspected_houses = len(group[group['atencion_vivienda_indicador'] == 1])
            
            # Count positive houses (viv_positiva == 1 and atencion_vivienda_indicador == 1)
            positive_houses = len(group[
                (group['viv_positiva'] == 1) & 
                (group['atencion_vivienda_indicador'] == 1)
            ])
            
            # Calculate Aedic Index
            aedic_index = (positive_houses / inspected_houses * 100) if inspected_houses > 0 else 0
            
            # Get health facility info
            facility_info = self.health_facilities.get(renipress_code, {})
            facility_name = group['localidad_eess'].iloc[0] if len(group) > 0 else "Desconocido"
            
            results.append({
                'cod_renipress': renipress_code,
                'localidad_eess': facility_name,
                'total_houses': facility_info.get('total_houses', 0),
                'inspected_houses': inspected_houses,
                'viviendas_positivas': positive_houses,
                'aedic_index': round(aedic_index, 2)
            })
        
        return pd.DataFrame(results)
    
    def calculate_container_statistics(self, filtered_data):
        """Calculate statistics for all container types"""
        containers = self.data_processor.get_container_columns()
        status_labels = self.data_processor.get_container_status_labels()
        
        results = []
        
        for container_type, columns in containers.items():
            container_stats = {'container_type': container_type}
            
            # Group by status suffix
            for suffix, label in status_labels.items():
                matching_columns = [col for col in columns if col.endswith(suffix)]
                if matching_columns:
                    total = filtered_data[matching_columns].sum().sum()
                    container_stats[label] = total
            
            results.append(container_stats)
        
        return pd.DataFrame(results)
    
    def calculate_larvicide_consumption(self, filtered_data):
        """Calculate total and per-facility larvicide consumption"""
        if 'consumo_larvicida' not in filtered_data.columns:
            return pd.DataFrame(), 0
        
        # Total consumption
        total_consumption = filtered_data['consumo_larvicida'].sum()
        
        # Consumption by health facility
        facility_consumption = filtered_data.groupby(['cod_renipress', 'localidad_eess'])['consumo_larvicida'].sum().reset_index()
        facility_consumption = facility_consumption.sort_values('consumo_larvicida', ascending=False)
        
        return facility_consumption, total_consumption
    
    def calculate_inspection_summary(self, filtered_data):
        """Calculate summary statistics for inspections"""
        if 'atencion_vivienda_indicador' not in filtered_data.columns:
            return {}
        
        # Count by inspection status
        status_counts = filtered_data['atencion_vivienda_indicador'].value_counts()
        
        status_mapping = {
            1: "Vivienda Inspeccionada",
            2: "Vivienda Cerrada", 
            3: "Vivienda Renuente",
            4: "Vivienda Deshabitada"
        }
        
        summary = {}
        for status_code, status_name in status_mapping.items():
            summary[status_name] = status_counts.get(status_code, 0)
        
        # Calculate positive houses percentage
        total_inspected = summary.get("Vivienda Inspeccionada", 0)
        positive_houses = len(filtered_data[
            (filtered_data['viv_positiva'] == 1) & 
            (filtered_data['atencion_vivienda_indicador'] == 1)
        ])
        
        summary['Viviendas Positivas'] = positive_houses
        summary['Porcentaje Positividad'] = (positive_houses / total_inspected * 100) if total_inspected > 0 else 0
        
        return summary
    
    def calculate_monthly_trends(self, filtered_data):
        """Calculate monthly trends for key metrics"""
        if 'fecha_inspeccion' not in filtered_data.columns:
            return pd.DataFrame()
        
        # Create monthly aggregation
        filtered_data['month_year'] = filtered_data['fecha_inspeccion'].dt.to_period('M')
        
        monthly_stats = filtered_data.groupby('month_year').agg({
            'atencion_vivienda_indicador': lambda x: (x == 1).sum(),  # Inspected houses
            'viv_positiva': lambda x: ((x == 1) & (filtered_data.loc[x.index, 'atencion_vivienda_indicador'] == 1)).sum(),  # Positive houses
            'consumo_larvicida': 'sum'
        }).reset_index()
        
        monthly_stats['month_year_str'] = monthly_stats['month_year'].astype(str)
        monthly_stats['aedic_index'] = (monthly_stats['viv_positiva'] / monthly_stats['atencion_vivienda_indicador'] * 100).fillna(0)
        
        return monthly_stats

    def calculate_coverage_percentages(self, filtered_data):
        """Calculate coverage percentages for each health facility"""
        results = []
        
        # Group by health facility code
        grouped = filtered_data.groupby('cod_renipress')
        
        for renipress_code, group in grouped:
            # Get facility info
            facility_info = self.health_facilities.get(renipress_code, {})
            facility_name = group['localidad_eess'].iloc[0] if len(group) > 0 else "Desconocido"
            total_houses = facility_info.get('total_houses', 0)
            
            # Count by house status
            inspected = len(group[group['atencion_vivienda_indicador'] == 1])
            closed = len(group[group['atencion_vivienda_indicador'] == 2])
            reluctant = len(group[group['atencion_vivienda_indicador'] == 3])
            uninhabited = len(group[group['atencion_vivienda_indicador'] == 4])
            
            # Calculate non-intervened houses
            total_intervened = inspected + closed + reluctant + uninhabited
            non_intervened = max(0, total_houses - total_intervened)
            
            # Calculate percentages
            def calc_percentage(value, total):
                return (value / total * 100) if total > 0 else 0
            
            results.append({
                'cod_renipress': renipress_code,
                'localidad_eess': facility_name,
                'total_houses': total_houses,
                'viv_inspeccionadas': inspected,
                'viv_cerradas': closed,
                'viv_renuentes': reluctant,
                'viv_deshabitadas': uninhabited,
                'viv_no_intervenidas': non_intervened,
                'porc_inspeccionadas': calc_percentage(inspected, total_houses),
                'porc_cerradas': calc_percentage(closed, total_houses),
                'porc_renuentes': calc_percentage(reluctant, total_houses),
                'porc_deshabitadas': calc_percentage(uninhabited, total_houses),
                'porc_no_intervenidas': calc_percentage(non_intervened, total_houses),
                'cobertura_total': calc_percentage(total_intervened, total_houses)
            })
        
        return pd.DataFrame(results)

    def calculate_febril_cases(self, filtered_data):
        """Calculate febril cases by health facility"""
        if 'febriles' not in filtered_data.columns:
            return pd.DataFrame(), 0
        
        # Total febril cases
        total_febriles = filtered_data['febriles'].sum()
        
        # Febril cases by health facility
        facility_febriles = filtered_data.groupby(['cod_renipress', 'localidad_eess'])['febriles'].sum().reset_index()
        facility_febriles = facility_febriles.sort_values('febriles', ascending=False)
        
        return facility_febriles, total_febriles

    def calculate_container_index(self, filtered_data):
        """
        Calculate Container Index for each health facility
        Formula: (Positive containers / Total containers inspected) * 100
        """
        results = []
        containers = self.data_processor.get_container_columns()
        
        # Group by health facility code
        grouped = filtered_data.groupby('cod_renipress')
        
        for renipress_code, group in grouped:
            total_containers_inspected = 0
            total_positive_containers = 0
            
            # Sum all container types
            for container_type, columns in containers.items():
                # Count inspected containers (columns ending with _I)
                inspected_cols = [col for col in columns if col.endswith('_I') and col in group.columns]
                for col in inspected_cols:
                    total_containers_inspected += group[col].sum()
                
                # Count positive containers (columns ending with _P) 
                positive_cols = [col for col in columns if col.endswith('_P') and col in group.columns]
                for col in positive_cols:
                    total_positive_containers += group[col].sum()
            
            # Calculate Container Index
            container_index = (total_positive_containers / total_containers_inspected * 100) if total_containers_inspected > 0 else 0
            
            # Get health facility info
            facility_name = group['localidad_eess'].iloc[0] if len(group) > 0 else "Desconocido"
            
            results.append({
                'cod_renipress': renipress_code,
                'localidad_eess': facility_name,
                'containers_inspected': int(total_containers_inspected),
                'containers_positive': int(total_positive_containers),
                'container_index': round(container_index, 2)
            })
        
        return pd.DataFrame(results)

    def calculate_breteau_index(self, filtered_data):
        """
        Calculate Breteau Index for each health facility
        Formula: (Positive containers / Houses inspected) * 100
        """
        results = []
        containers = self.data_processor.get_container_columns()
        
        # Group by health facility code
        grouped = filtered_data.groupby('cod_renipress')
        
        for renipress_code, group in grouped:
            # Count inspected houses (atencion_vivienda_indicador == 1)
            inspected_houses = len(group[group['atencion_vivienda_indicador'] == 1])
            
            total_positive_containers = 0
            
            # Sum all positive containers from all types
            for container_type, columns in containers.items():
                # Count positive containers (columns ending with _P)
                positive_cols = [col for col in columns if col.endswith('_P') and col in group.columns]
                for col in positive_cols:
                    total_positive_containers += group[col].sum()
            
            # Calculate Breteau Index
            breteau_index = (total_positive_containers / inspected_houses * 100) if inspected_houses > 0 else 0
            
            # Get health facility info
            facility_name = group['localidad_eess'].iloc[0] if len(group) > 0 else "Desconocido"
            
            results.append({
                'cod_renipress': renipress_code,
                'localidad_eess': facility_name,
                'houses_inspected': inspected_houses,
                'containers_positive': int(total_positive_containers),
                'breteau_index': round(breteau_index, 2)
            })
        
        return pd.DataFrame(results)
        
    def calculate_entomological_indices_summary(self, filtered_data):
        """Calculate summary of all entomological indices"""
        aedic_data = self.calculate_aedic_index(filtered_data)
        container_data = self.calculate_container_index(filtered_data)
        breteau_data = self.calculate_breteau_index(filtered_data)
        
        summary = {}
        
        if not aedic_data.empty:
            summary['IA_promedio'] = aedic_data['aedic_index'].mean()
            summary['IA_maximo'] = aedic_data['aedic_index'].max()
        
        if not container_data.empty:
            summary['IC_promedio'] = container_data['container_index'].mean()
            summary['IC_maximo'] = container_data['container_index'].max()
            
        if not breteau_data.empty:
            summary['IB_promedio'] = breteau_data['breteau_index'].mean()
            summary['IB_maximo'] = breteau_data['breteau_index'].max()
        
        return summary
    
    def calculate_weekly_surveillance_days(self, filtered_data):
        """Calculate surveillance days per week"""
        if 'fecha_inspeccion' not in filtered_data.columns:
            return pd.DataFrame()
        
        # Create a copy and ensure dates are datetime objects
        data_copy = filtered_data.copy()
        data_copy['fecha_inspeccion'] = pd.to_datetime(data_copy['fecha_inspeccion'], errors='coerce')
        
        # Remove rows with invalid dates
        data_copy = data_copy.dropna(subset=['fecha_inspeccion'])
        
        if data_copy.empty:
            return pd.DataFrame()
        
        # Calculate week start consistently (Monday as start of week)
        data_copy['week_start'] = data_copy['fecha_inspeccion'] - pd.to_timedelta(data_copy['fecha_inspeccion'].dt.weekday, unit='D')
        data_copy['week_start'] = data_copy['week_start'].dt.date  # Convert to date to normalize times
        
        # Create a unique week identifier using the week start date
        data_copy['week_year'] = data_copy['week_start'].astype(str)
        
        # Group by week_start only (more reliable than week_year + week_start)
        weekly_stats = data_copy.groupby('week_start').agg({
            'fecha_inspeccion': lambda x: x.dt.date.nunique(),  # Unique days per week
            'atencion_vivienda_indicador': lambda x: (x == 1).sum(),  # Total inspections
            'viv_positiva': lambda x: ((x == 1) & (data_copy.loc[x.index, 'atencion_vivienda_indicador'] == 1)).sum()  # Positive houses
        }).reset_index()
        
        weekly_stats.columns = ['semana_inicio', 'dias_vigilancia', 'inspecciones_totales', 'viviendas_positivas']
        
        # Convert semana_inicio back to datetime for display formatting
        weekly_stats['semana_inicio'] = pd.to_datetime(weekly_stats['semana_inicio'])
        
        # Format week display
        weekly_stats['week_display'] = weekly_stats['semana_inicio'].dt.strftime('%d/%m/%Y') + ' - ' + \
                                      (weekly_stats['semana_inicio'] + pd.Timedelta(days=6)).dt.strftime('%d/%m/%Y')
        
        # Calculate surveillance intensity (inspections per day)
        weekly_stats['intensity'] = weekly_stats['inspecciones_totales'] / weekly_stats['dias_vigilancia'].replace(0, 1)
        
        # Sort by week start date
        weekly_stats = weekly_stats.sort_values('semana_inicio')
        
        return weekly_stats

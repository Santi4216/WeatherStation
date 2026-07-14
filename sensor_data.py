"""
Sistema de Monitoreo - Estación Meteorológica
Gestión de datos y comunicación con ESP32
"""

import time
import requests
import numpy as np
from collections import deque
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from typing import Any, Dict, Optional, Tuple
from config import (SENSORS, GRAPH_MAX_POINTS, ESP32_IP, ESP32_PORT, 
                    CONNECTION_TIMEOUT, STATS_WINDOW_SECONDS)


class SensorDataManager:
    """Gestor de datos de sensores con estadísticas en tiempo real"""
    
    def __init__(self) -> None:
        # Almacenamiento de datos por sensor
        self.data = {}
        self.timestamps = {}
        self.start_time = time.time()
        
        # Inicializar estructuras para cada sensor
        for sensor_key in SENSORS.keys():
            self.data[sensor_key] = deque(maxlen=GRAPH_MAX_POINTS)
            self.timestamps[sensor_key] = deque(maxlen=GRAPH_MAX_POINTS)
            
        # Estadísticas
        self.stats = {}
        self.last_values = {}
        
    def add_data(self, sensor_key: str, value: float, timestamp: Optional[float] = None) -> None:
        """Agrega un nuevo dato para un sensor"""
        if sensor_key not in self.data:
            return
            
        # Usar timestamp proporcionado o generar uno
        if timestamp is None:
            timestamp = time.time() - self.start_time
        
        # Agregar datos
        self.data[sensor_key].append(float(value))
        self.timestamps[sensor_key].append(float(timestamp))
        self.last_values[sensor_key] = float(value)
        
        # Actualizar estadísticas
        self.update_stats(sensor_key)
        
    def get_plot_data(self, sensor_key: str) -> Tuple[np.ndarray, np.ndarray]:
        """Obtiene los datos para graficar"""
        if sensor_key not in self.data or len(self.data[sensor_key]) == 0:
            return np.array([]), np.array([])
            
        timestamps = np.array(list(self.timestamps[sensor_key]))
        values = np.array(list(self.data[sensor_key]))
        
        return timestamps, values
        
    def get_current_value(self, sensor_key: str) -> float:
        """Obtiene el valor actual de un sensor"""
        if sensor_key in self.last_values:
            return self.last_values[sensor_key]
        return 0.0
        
    def get_sensor_status(self, sensor_key: str) -> str:
        """Determina el estado del sensor"""
        if sensor_key not in self.last_values:
            return 'Sin datos'
            
        value = self.last_values[sensor_key]
        sensor_config = SENSORS[sensor_key]
        
        # Verificar umbrales de alarma
        if 'alarm_threshold_low' in sensor_config and value < sensor_config['alarm_threshold_low']:
            return 'BAJO'
        if 'alarm_threshold_high' in sensor_config and value > sensor_config['alarm_threshold_high']:
            return 'ALTO'
            
        return 'OK'
        
    def update_stats(self, sensor_key: str) -> None:
        """Actualiza estadísticas para un sensor"""
        if sensor_key not in self.data or len(self.data[sensor_key]) == 0:
            return
            
        # Obtener datos de la ventana de tiempo
        current_time = time.time() - self.start_time
        timestamps = np.array(list(self.timestamps[sensor_key]))
        values = np.array(list(self.data[sensor_key]))
        
        # Filtrar datos de la ventana de estadísticas
        window_mask = timestamps >= (current_time - STATS_WINDOW_SECONDS)
        window_values = values[window_mask]
        
        if len(window_values) > 0:
            self.stats[sensor_key] = {
                'min': float(np.min(window_values)),
                'max': float(np.max(window_values)),
                'avg': float(np.mean(window_values)),
                'std': float(np.std(window_values)),
                'current': float(values[-1]),
                'count': len(window_values)
            }
        else:
            self.stats[sensor_key] = {
                'min': 0.0,
                'max': 0.0,
                'avg': 0.0,
                'std': 0.0,
                'current': 0.0,
                'count': 0
            }
            
    def get_stats(self, sensor_key: str) -> Dict[str, Any]:
        """Obtiene las estadísticas de un sensor"""
        return self.stats.get(sensor_key, {
            'min': 0.0,
            'max': 0.0,
            'avg': 0.0,
            'std': 0.0,
            'current': 0.0,
            'count': 0
        })
        
    def clear_data(self) -> None:
        """Limpia todos los datos almacenados"""
        for sensor_key in SENSORS.keys():
            self.data[sensor_key].clear()
            self.timestamps[sensor_key].clear()
        self.last_values.clear()
        self.stats.clear()
        self.start_time = time.time()
        
    def export_data_csv(self, filename: str) -> bool:
        """Exporta datos a archivo CSV"""
        import csv
        
        # Encontrar el máximo número de puntos
        max_points = max([len(self.data[key]) for key in SENSORS.keys()])
        
        if max_points == 0:
            return False
            
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # Crear headers
                headers = ['Timestamp']
                for sensor_key, sensor_config in SENSORS.items():
                    headers.append(f"{sensor_config['name']} ({sensor_config['unit']})")
                
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                
                # Escribir datos
                for i in range(max_points):
                    row = []
                    # Timestamp del primer sensor que tenga datos en este índice
                    timestamp = None
                    for sensor_key in SENSORS.keys():
                        if i < len(self.timestamps[sensor_key]):
                            timestamp = self.timestamps[sensor_key][i]
                            break
                    
                    if timestamp is None:
                        continue
                        
                    row.append(f"{timestamp:.2f}")
                    
                    # Valores de cada sensor
                    for sensor_key in SENSORS.keys():
                        if i < len(self.data[sensor_key]):
                            row.append(f"{self.data[sensor_key][i]:.2f}")
                        else:
                            row.append('')
                    
                    writer.writerow(row)
                    
            return True
        except Exception as e:
            print(f"Error al exportar CSV: {e}")
            return False
            
    def export_data_json(self, filename: str) -> bool:
        """Exporta datos a archivo JSON"""
        import json
        
        try:
            export_data = {
                'metadata': {
                    'export_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'sensors': {key: config['name'] for key, config in SENSORS.items()}
                },
                'data': {}
            }
            
            for sensor_key, sensor_config in SENSORS.items():
                sensor_data = []
                for i in range(len(self.data[sensor_key])):
                    sensor_data.append({
                        'timestamp': float(self.timestamps[sensor_key][i]),
                        'value': float(self.data[sensor_key][i])
                    })
                
                export_data['data'][sensor_key] = {
                    'name': sensor_config['name'],
                    'unit': sensor_config['unit'],
                    'values': sensor_data,
                    'statistics': self.get_stats(sensor_key)
                }
            
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
                
            return True
        except Exception as e:
            print(f"Error al exportar JSON: {e}")
            return False


class ESP32Communicator(QThread):
    """Thread para comunicación con ESP32 vía WiFi"""
    
    data_received = pyqtSignal(dict)
    connection_status = pyqtSignal(bool, str)
    
    def __init__(self, ip: str, port: int) -> None:
        super().__init__()
        self.ip = ip
        self.port = port
        self.running = False
        self.connected = False
        self.session = requests.Session()
        self.url = f"http://{self.ip}:{self.port}/data"
        
    def run(self) -> None:
        """Loop principal de comunicación"""
        self.running = True
        consecutive_errors = 0
        
        while self.running:
            try:
                # Realizar petición HTTP GET
                response = self.session.get(self.url, timeout=CONNECTION_TIMEOUT)
                
                if response.status_code == 200:
                    # Parsear datos JSON - manejar valores NaN
                    import json
                    import math
                    
                    # Obtener texto y reemplazar NaN con null
                    json_text = response.text.replace('nan', 'null').replace('NaN', 'null')
                    data = json.loads(json_text)
                    
                    # Limpiar valores None/null y reemplazarlos con 0
                    for key in data:
                        if data[key] is None or (isinstance(data[key], float) and math.isnan(data[key])):
                            data[key] = 0.0
                    
                    # Agregar timestamp local
                    data['timestamp'] = time.time()
                    
                    # Emitir señal con los datos
                    self.data_received.emit(data)
                    
                    # Actualizar estado de conexión
                    if not self.connected:
                        self.connected = True
                        self.connection_status.emit(True, f"Conectado a ESP32 ({self.ip})")
                        consecutive_errors = 0
                    
                else:
                    consecutive_errors += 1
                    if consecutive_errors > 3 and self.connected:
                        self.connected = False
                        self.connection_status.emit(False, f"Error HTTP {response.status_code}")
                        
            except requests.exceptions.Timeout:
                consecutive_errors += 1
                if consecutive_errors > 3 and self.connected:
                    self.connected = False
                    self.connection_status.emit(False, "Timeout de conexión")
                    
            except requests.exceptions.ConnectionError:
                consecutive_errors += 1
                if consecutive_errors > 3 and self.connected:
                    self.connected = False
                    self.connection_status.emit(False, f"No se puede conectar a {self.ip}")
                    
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors > 3 and self.connected:
                    self.connected = False
                    self.connection_status.emit(False, f"Error: {str(e)}")
            
            # Pequeña pausa entre peticiones (100ms = 10 peticiones/segundo)
            self.msleep(100)
            
    def stop(self) -> None:
        """Detiene el thread de comunicación"""
        self.running = False
        self.wait()

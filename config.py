"""
Sistema de Monitoreo - Estación Meteorológica
Universidad Militar Nueva Granada
Asignatura: Sensores y Laboratorio
Docente: Paola Andrea Castiblanco Moreno

Integrantes:
- Karol Daniela Mosquera (7004097)
- David Santiago García Suárez (7004823)
- Santiago Rubiano Garzón (7004147)

Archivo de configuración global
"""

# ==================== INFORMACIÓN DEL PROYECTO ====================
PROJECT_INFO = {
    'titulo': 'ESTACIÓN METEOROLÓGICA',
    'universidad': 'Universidad Militar Nueva Granada',
    'asignatura': 'Sensores y Laboratorio',
    'docente': 'Paola Andrea Castiblanco Moreno',
    'integrantes': [
        {
            'nombre': 'Karol Daniela Mosquera',
            'programa': 'Ingeniería Mecatrónica',
            'codigo': '7004097',
            'email': 'est.karol.mosquera@unimilitar.edu.co'
        },
        {
            'nombre': 'David Santiago García Suárez',
            'programa': 'Ingeniería Mecatrónica',
            'codigo': '7004823',
            'email': 'est.davids.garcias@unimilitar.edu.co'
        },
        {
            'nombre': 'Santiago Rubiano Garzón',
            'programa': 'Ingeniería Mecatrónica',
            'codigo': '7004147',
            'email': 'est.santiago.rubia@unimilitar.edu.co'
        }
    ]
}

# ==================== CONFIGURACIÓN DE SENSORES ====================
SENSORS = {
    'heliografo': {
        'name': 'Intensidad de Luz',
        'icon': '💡',
        'unit': '%',
        'color': '#F6E58D',
        'min': 0,
        'max': 100,
        'resolution': 0.1,
        'tipo': 'Sensor Analógico',
        'alarm_threshold_low': 10,
        'descripcion': 'Medición de intensidad lumínica (Heliógrafo)',
        'grafica_color': '#FFC312'
    },
    'temperatura': {
        'name': 'Temperatura',
        'icon': '🌡️',
        'unit': '°C',
        'color': '#FF6B6B',
        'min': 10,
        'max': 50,
        'resolution': 0.1,
        'tipo': 'RTD Pt100',
        'alarm_threshold_low': 15,
        'alarm_threshold_high': 45,
        'descripcion': 'Sensor de temperatura tipo RTD (Resistance Temperature Detector)',
        'grafica_color': '#FF4757'
    },
    'anemometro': {
        'name': 'Velocidad del Viento',
        'icon': '🌪️',
        'unit': 'km/h',
        'color': '#95E1D3',
        'min': 0,
        'max': 150,
        'resolution': 0.01,  # Resolución mejorada: detecta cambios de 0.01 km/h
        'tipo': 'Anemómetro Digital (Alta Resolución)',
        'alarm_threshold_high': 120,
        'descripcion': 'Medición de velocidad del viento con resolución mejorada',
        'grafica_color': '#38D9A9'
    },
    'barometro': {
        'name': 'Altitud (Barómetro)',
        'icon': '⛰️',
        'unit': 'm',
        'color': '#4ECDC4',
        'min': 0,
        'max': 3000,
        'resolution': 1,
        'tipo': 'Barómetro Digital',
        'alarm_threshold_high': 2800,
        'descripcion': 'Medición de altitud mediante presión barométrica',
        'grafica_color': '#26D0CE'
    }
}

# ==================== COMUNICACIÓN ESP32 ====================
# IMPORTANTE: Cambia esta IP por la que aparece en el Monitor Serial del ESP32
# después de que se conecte a tu red WiFi
ESP32_IP = "192.168.137.177"  # IP del ESP32 en tu red local 
ESP32_PORT = 80              # Puerto del servidor HTTP
CONNECTION_TIMEOUT = 5      # Timeout de conexión en segundos
RECONNECT_INTERVAL = 3000   # Intervalo de reconexión en ms
REQUEST_INTERVAL = 100      # Intervalo entre peticiones en ms (100ms = 10Hz)

# ==================== CONFIGURACIÓN DE GRÁFICAS ====================
GRAPH_UPDATE_RATE = 100         # Actualización de gráfica en ms (100ms = 10Hz)
GRAPH_HISTORY_TIME = 300        # Tiempo de historia en segundos (5 minutos)
GRAPH_MAX_POINTS = 3000         # Máximo de puntos en memoria por sensor
GRAPH_DYNAMIC_RANGE = True      # Habilitar rango dinámico para mejor respuesta
GRAPH_RANGE_PADDING = 0.05      # 5% de padding para mejor ajuste (reducido desde 10%)

# Niveles de zoom disponibles
ZOOM_LEVELS = {
    'zoom_30s': {'label': '30s', 'seconds': 30},
    'zoom_1m': {'label': '1min', 'seconds': 60},
    'zoom_2m': {'label': '2min', 'seconds': 120},
    'zoom_5m': {'label': '5min', 'seconds': 300},
}

# ==================== ALARMAS ====================
ALARM_CHECK_INTERVAL = 500  # Verificar alarmas cada 500ms
ALARM_SOUND_FILE = 'assets/alarm.wav'  # Archivo de sonido de alarma

# ==================== COLORES - TEMA OSCURO ====================
DARK_THEME = {
    'background': '#000000',          # Negro absoluto (muy oscuro)
    'panel': '#0D1117',               # Panel secundario (negro oscuro)
    'panel_hover': '#161B22',         # Hover panel
    'border': '#30363D',              # Bordes
    'text_primary': '#F1F5F9',        # Texto principal
    'text_secondary': '#94A3B8',      # Texto secundario
    'accent_cyan': '#06B6D4',         # Acento cyan
    'accent_green': '#10B981',        # Acento verde
    'accent_red': '#EF4444',          # Acento rojo
    'accent_orange': '#F59E0B',       # Acento naranja
    'accent_blue': '#3B82F6',         # Acento azul
    'graph_bg': '#0D1117',            # Fondo gráfica (negro oscuro)
    'grid_alpha': 0.15                # Opacidad rejilla
}

# ==================== COLORES - TEMA CLARO ====================
LIGHT_THEME = {
    'background': '#F8FAFC',          # Gris muy claro
    'panel': '#FFFFFF',               # Blanco
    'panel_hover': '#F1F5F9',         # Hover panel
    'border': '#CBD5E1',              # Bordes
    'text_primary': '#0F172A',        # Texto principal
    'text_secondary': '#475569',      # Texto secundario
    'accent_cyan': '#0891B2',         # Acento cyan
    'accent_green': '#059669',        # Acento verde
    'accent_red': '#DC2626',          # Acento rojo
    'accent_orange': '#D97706',       # Acento naranja
    'accent_blue': '#2563EB',         # Acento azul
    'graph_bg': '#FFFFFF',            # Fondo gráfica
    'grid_alpha': 0.3                 # Opacidad rejilla
}

# Colores activos (se cambian con el tema)
COLORS = DARK_THEME.copy()

# ==================== EXPORTACIÓN DE DATOS ====================
EXPORT_FORMATS = ['CSV', 'JSON', 'XLSX']
DEFAULT_EXPORT_PATH = './exports/'

# ==================== UI SETTINGS ====================
WINDOW_MIN_WIDTH = 1400
WINDOW_MIN_HEIGHT = 900
SIDEBAR_WIDTH = 320
CARD_HEIGHT = 140
GRAPH_MIN_HEIGHT = 450

# ==================== ESTADÍSTICAS ====================
STATS_UPDATE_INTERVAL = 1000  # Actualizar estadísticas cada 1s
STATS_WINDOW_SECONDS = 60     # Ventana de cálculo de estadísticas (1 minuto)

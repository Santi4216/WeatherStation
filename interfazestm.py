"""
Sistema de Monitoreo - Estación Meteorológica
Interfaz Gráfica Principal - Versión Mejorada
Universidad Militar Nueva Granada

Integrantes:
- Karol Daniela Mosquera (N/A)
- David Santiago García Suárez (N/A)  
- Santiago Rubiano Garzón (N/A)

Para ejecutar: python interfazestm.py
"""

import sys
import os
import time
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFrame, QGridLayout,
                             QMessageBox, QDialog, QTextEdit, QGroupBox, QScrollArea,
                             QFileDialog, QTabWidget)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap
import pyqtgraph as pg

try:
    import pygame
    PYGAME_AVAILABLE = True
except Exception as e:
    PYGAME_AVAILABLE = False
    print(f"⚠️ pygame no disponible - alarmas sonoras desactivadas: {e}")

from sensor_data import SensorDataManager, ESP32Communicator
from config import (SENSORS, GRAPH_UPDATE_RATE, PROJECT_INFO, COLORS, DARK_THEME, 
                    LIGHT_THEME, ESP32_IP, ESP32_PORT, ZOOM_LEVELS, ALARM_CHECK_INTERVAL,
                    ALARM_SOUND_FILE, STATS_UPDATE_INTERVAL, DEFAULT_EXPORT_PATH,
                    SIDEBAR_WIDTH, CARD_HEIGHT)


class InfoDialog(QDialog):
    """Diálogo de información del proyecto"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Información del Proyecto")
        self.setModal(True)
        self.setMinimumSize(700, 550)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Título
        title = QLabel("⛅ ESTACIÓN METEOROLÓGICA")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {COLORS['accent_cyan']}; padding: 15px;")
        layout.addWidget(title)
        
        # Información del proyecto
        info_html = f"""
<div style='color: {COLORS["text_primary"]}; font-size: 13px; line-height: 1.6;'>
    <p style='font-size: 14px;'><b>🎓 Universidad:</b> {PROJECT_INFO['universidad']}</p>
    <p style='font-size: 14px;'><b>📚 Asignatura:</b> {PROJECT_INFO['asignatura']}</p>
    <p style='font-size: 14px;'><b>👩‍🏫 Docente:</b> {PROJECT_INFO['docente']}</p>
    <br>
    <p style='color: {COLORS["accent_green"]}; font-size: 16px; font-weight: bold;'>👥 INTEGRANTES:</p>
"""
        
        for integrante in PROJECT_INFO['integrantes']:
            info_html += f"""
    <div style='background-color: {COLORS["panel"]}; padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 4px solid {COLORS["accent_cyan"]};'>
        <p style='margin: 4px 0; font-size: 14px;'><b>{integrante['nombre']}</b></p>
        <p style='margin: 4px 0; font-size: 12px; color: {COLORS["text_secondary"]};'>{integrante['programa']}</p>
        <p style='margin: 4px 0; font-size: 12px;'>📋 Código: {integrante['codigo']}</p>
        <p style='margin: 4px 0; font-size: 12px;'>✉️ {integrante['email']}</p>
    </div>
"""
        
        info_html += f"""
    <br>
    <p style='color: {COLORS["accent_blue"]}; font-size: 16px; font-weight: bold;'>🔬 INSTRUMENTOS DE MEDIDA:</p>
    <ul style='font-size: 13px; line-height: 1.8;'>
        <li><b>🌡️ Termómetro RTD:</b> (10 - 50)°C, resolución 0.1°C</li>
        <li><b>📊 Barómetro:</b> (0 - 3000) metros de altura, resolución 1m</li>
        <li><b>💨 Anemómetro:</b> (0 - 150) km/h</li>
        <li><b>☀️ Heliógrafo:</b> (0 - 100)% intensidad lumínica</li>
    </ul>
</div>
"""
        
        info_text = QTextEdit()
        info_text.setHtml(info_html)
        info_text.setReadOnly(True)
        info_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['background']};
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
                padding: 15px;
            }}
        """)
        layout.addWidget(info_text)
        
        # Botón cerrar
        close_btn = QPushButton("✓ Cerrar")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumHeight(45)
        close_btn.setFont(QFont("Arial", 11, QFont.Bold))
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_cyan']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 35px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_green']};
            }}
        """)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)
        
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {COLORS['background']};")


class SensorCard(QFrame):
    """Tarjeta de sensor con estadísticas mejoradas"""
    
    def __init__(self, sensor_key, sensor_config, parent=None):
        super().__init__(parent)
        self.sensor_key = sensor_key
        self.sensor_config = sensor_config
        self.is_selected = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(3)
        layout.setContentsMargins(6, 6, 6, 6)
        
        # Icono y nombre en una sola línea más compacta
        header_layout = QHBoxLayout()
        header_layout.setSpacing(5)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel(self.sensor_config['icon'])
        icon_label.setFont(QFont("Arial", 16))
        icon_label.setFixedSize(30, 30)
        icon_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        icon_label.setStyleSheet("padding: 0; margin: 0;")
        
        name_label = QLabel(self.sensor_config['name'])
        name_label.setFont(QFont("Arial", 8, QFont.Bold))
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(32)
        name_label.setStyleSheet(f"color: #F1F5F9; line-height: 1.1; background: transparent;")
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(name_label, stretch=1)
        layout.addLayout(header_layout)
        
        # Línea separadora más fina
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {self.sensor_config['color']}; max-height: 1px; margin: 1px 0; border: none;")
        layout.addWidget(line)
        
        # Contenedor para valor y unidad
        value_container = QWidget()
        value_container.setStyleSheet("background: transparent;")
        value_layout = QVBoxLayout()
        value_layout.setSpacing(0)
        value_layout.setContentsMargins(0, 2, 0, 2)
        
        # Valor actual (grande y prominente)
        self.value_label = QLabel("--")
        self.value_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet(f"color: {self.sensor_config['color']}; padding: 0; margin: 0; background: transparent;")
        value_layout.addWidget(self.value_label)
        
        # Unidad
        unit_label = QLabel(self.sensor_config['unit'])
        unit_label.setFont(QFont("Arial", 7))
        unit_label.setAlignment(Qt.AlignCenter)
        unit_label.setStyleSheet(f"color: #94A3B8; margin: 0; padding: 0; background: transparent;")
        value_layout.addWidget(unit_label)
        
        value_container.setLayout(value_layout)
        layout.addWidget(value_container)
        
        # Estado
        self.status_label = QLabel("● Sin datos")
        self.status_label.setFont(QFont("Arial", 6))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"color: #94A3B8; padding: 0; margin: 0; background: transparent;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        self.setFixedHeight(CARD_HEIGHT)
        self.update_style(False)
        
    def update_value(self, value, stats, status):
        """Actualiza el valor y estado"""
        # Valor principal
        self.value_label.setText(f"{value:.1f}")
        
        # Estado
        if status == 'OK':
            self.status_label.setText(f"● Normal")
            self.status_label.setStyleSheet(f"color: #10B981; background: transparent;")
        elif status == 'ALTO':
            self.status_label.setText(f"⚠️ {status}")
            self.status_label.setStyleSheet(f"color: #EF4444; background: transparent;")
        elif status == 'BAJO':
            self.status_label.setText(f"⚠️ {status}")
            self.status_label.setStyleSheet(f"color: #F59E0B; background: transparent;")
        else:
            self.status_label.setText(f"● {status}")
            self.status_label.setStyleSheet(f"color: #94A3B8; background: transparent;")
            
    def update_style(self, selected):
        """Actualiza el estilo visual - siempre oscuro"""
        self.is_selected = selected
        
        # Siempre usar colores oscuros para las cards
        card_bg = '#0D1117'
        card_hover = '#161B22'
        card_border = '#30363D'
        
        if selected:
            # Cuando está seleccionado: solo borde con el color del sensor
            color = self.sensor_config['color']
            self.setStyleSheet(f"""
                SensorCard {{
                    background-color: {card_bg};
                    border: 2px solid {color};
                    border-radius: 10px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                SensorCard {{
                    background-color: {card_bg};
                    border: 2px solid {card_border};
                    border-radius: 10px;
                }}
                SensorCard:hover {{
                    background-color: {card_hover};
                    border: 2px solid {self.sensor_config['color']};
                }}
            """)
            
    def mousePressEvent(self, event):
        """Maneja el click"""
        # Buscar el MainWindow
        parent = self.parent()
        while parent and not isinstance(parent, MainWindow):
            parent = parent.parent()
        if parent:
            parent.select_sensor(self.sensor_key)


class MainWindow(QMainWindow):
    """Ventana principal mejorada"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⛅ Estación Meteorológica - UMNG")
        self.setGeometry(50, 50, 1600, 950)
        self.setMinimumSize(1400, 900)
        
        # Inicializar componentes
        self.data_manager = SensorDataManager()
        self.current_sensor = 'heliografo'  # Ahora el primero es intensidad de luz
        self.is_dark_theme = True  # Estado del tema actual
        self.current_zoom_level = 'zoom_1m'
        self.current_zoom_seconds = 60
        
        # Tiempo de inicio de la interfaz
        self.start_time = time.time()
        
        # Control de alarmas
        self.active_alarms = {}
        for sensor_key in SENSORS.keys():
            self.active_alarms[sensor_key] = {
                'active': False,
                'silenced': False
            }
        
        # Inicializar pygame para sonidos
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                self.alarm_sound = None
                if os.path.exists(ALARM_SOUND_FILE):
                    self.alarm_sound = pygame.mixer.Sound(ALARM_SOUND_FILE)
            except Exception as e:
                print(f"⚠️ No se pudo inicializar el sistema de audio: {e}")
                self.alarm_sound = None
        else:
            self.alarm_sound = None
        
        # Configurar interfaz
        self.setup_ui()
        
        # Iniciar comunicación
        self.setup_communication()
        
        # Timers
        self.setup_timers()
        
    def setup_ui(self):
        """Configura la interfaz mejorada con panel lateral"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal horizontal
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # === PANEL LATERAL IZQUIERDO ===
        self.sidebar = self.create_sidebar()
        main_layout.addWidget(self.sidebar)
        
        # === ÁREA PRINCIPAL DERECHA ===
        right_panel = QWidget()
        right_panel.setStyleSheet(f"background-color: {COLORS['background']};")
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header superior
        header = self.create_header()
        right_layout.addWidget(header)
        
        # Área de gráficas con tabs
        self.graph_tabs = self.create_graph_tabs()
        right_layout.addWidget(self.graph_tabs, stretch=1)
        
        # Panel de control inferior
        controls = self.create_controls()
        right_layout.addWidget(controls)
        
        right_panel.setLayout(right_layout)
        main_layout.addWidget(right_panel, stretch=1)
        
        central_widget.setLayout(main_layout)
        
        # Estilo general
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['background']};
            }}
        """)
        
    def create_sidebar(self):
        """Crea el panel lateral con sensores - SIEMPRE NEGRO"""
        sidebar = QFrame()
        sidebar.setMaximumWidth(SIDEBAR_WIDTH)
        sidebar.setMinimumWidth(SIDEBAR_WIDTH)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: #000000;
                border-right: 2px solid #1C2128;
            }}
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(15, 20, 15, 20)
        
        # Logo y título
        # Logo de la Universidad Militar Nueva Granada
        logo_label = QLabel()
        # Obtener ruta absoluta del directorio del script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "assets", "logo_umng.png")
        
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Escalar el logo manteniendo la proporción
            scaled_pixmap = pixmap.scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("padding: 10px; background-color: #000000;")
        else:
            # Si no existe el logo, usar el emoji como fallback
            logo_label.setText("⛅")
            logo_label.setFont(QFont("Arial", 48))
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("background-color: #000000;")
        
        layout.addWidget(logo_label)
        
        title_label = QLabel("ESTACIÓN\nMETEOROLÓGICA")
        title_label.setFont(QFont("Arial", 13, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)
        # Título con degradado cyan vibrante
        title_label.setStyleSheet(f"""
            color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                stop:0 #06B6D4, stop:1 #0EA5E9);
            padding: 8px;
            font-weight: bold;
        """)
        layout.addWidget(title_label)
        
        # Separador con color cyan
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: #06B6D4; max-height: 2px;")
        layout.addWidget(line)
        
        # Scroll área para sensores
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #000000;
            }
            QScrollBar:vertical {
                background-color: #0A0A0A;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #06B6D4;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #0EA5E9;
            }
        """)
        
        sensors_widget = QWidget()
        sensors_widget.setStyleSheet("background-color: #000000;")
        sensors_layout = QVBoxLayout()
        sensors_layout.setSpacing(10)
        sensors_layout.setContentsMargins(0, 0, 5, 0)
        
        # Crear cards de sensores
        self.sensor_cards = {}
        for sensor_key, sensor_config in SENSORS.items():
            card = SensorCard(sensor_key, sensor_config)
            card.setCursor(Qt.PointingHandCursor)
            self.sensor_cards[sensor_key] = card
            sensors_layout.addWidget(card)
        
        sensors_widget.setLayout(sensors_layout)
        scroll.setWidget(sensors_widget)
        layout.addWidget(scroll, stretch=1)
        
        # Botones de acción
        action_layout = QVBoxLayout()
        action_layout.setSpacing(10)
        
        # Botón exportar
        export_btn = QPushButton("📊 Exportar Datos")
        export_btn.clicked.connect(self.export_data)
        export_btn.setMinimumHeight(45)
        export_btn.setStyleSheet(self.get_action_button_style('#06B6D4'))
        action_layout.addWidget(export_btn)
        
        # Botón info
        info_btn = QPushButton("ℹ️ Información")
        info_btn.clicked.connect(self.show_info_dialog)
        info_btn.setMinimumHeight(45)
        info_btn.setStyleSheet(self.get_action_button_style('#EF4444'))  # Rojo vibrante
        action_layout.addWidget(info_btn)
        
        layout.addLayout(action_layout)
        
        # Estado de conexión con mejor diseño
        self.connection_label = QLabel("⚠️ Desconectado")
        self.connection_label.setFont(QFont("Arial", 9, QFont.Bold))
        self.connection_label.setAlignment(Qt.AlignCenter)
        self.connection_label.setStyleSheet(f"""
            QLabel {{
                color: #F59E0B;
                padding: 10px;
                background-color: #161B22;
                border-radius: 8px;
                border: 2px solid #F59E0B;
            }}
        """)
        layout.addWidget(self.connection_label)
        
        sidebar.setLayout(layout)
        return sidebar
        
    def get_action_button_style(self, color):
        """Retorna el estilo para botones de acción"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #10B981;
            }}
            QPushButton:pressed {{
                background-color: #161B22;
            }}
        """
        
    def create_header(self):
        """Crea el header con título y controles"""
        header = QFrame()
        header.setMaximumHeight(80)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['panel']};
                border-radius: 10px;
                border: 2px solid {COLORS['border']};
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 12, 20, 12)
        
        # Título del sensor actual
        self.sensor_title = QLabel(f"{SENSORS['heliografo']['icon']} {SENSORS['heliografo']['name']}")
        self.sensor_title.setFont(QFont("Arial", 18, QFont.Bold))
        self.sensor_title.setStyleSheet(f"color: {COLORS['accent_cyan']};")
        layout.addWidget(self.sensor_title, stretch=1)
        
        # Reloj y tiempo de ejecución (centro)
        time_container = QWidget()
        time_layout = QVBoxLayout()
        time_layout.setSpacing(2)
        time_layout.setContentsMargins(0, 0, 0, 0)
        
        self.clock_label = QLabel("00:00:00")
        self.clock_label.setFont(QFont("Arial", 10))
        self.clock_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.clock_label.setAlignment(Qt.AlignCenter)
        time_layout.addWidget(self.clock_label)
        
        self.uptime_label = QLabel("⏱️ 00:00:00")
        self.uptime_label.setFont(QFont("Arial", 9))
        self.uptime_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.uptime_label.setAlignment(Qt.AlignCenter)
        time_layout.addWidget(self.uptime_label)
        
        time_container.setLayout(time_layout)
        layout.addWidget(time_container)
        
        # Botón tema
        self.theme_btn = QPushButton("🌙 Oscuro")
        self.theme_btn.setMinimumSize(100, 40)
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.theme_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_orange']};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_cyan']};
            }}
        """)
        layout.addWidget(self.theme_btn)
        
        header.setLayout(layout)
        return header
        
    def create_graph_tabs(self):
        """Crea las pestañas de gráficas"""
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                background-color: {COLORS['panel']};
                top: -1px;
            }}
            QTabBar::tab {{
                background-color: {COLORS['background']};
                color: {COLORS['text_primary']};
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['accent_cyan']};
                color: white;
            }}
            QTabBar::tab:hover {{
                background-color: {COLORS['panel_hover']};
            }}
        """)
        
        # Tab 1: Vista individual
        self.single_view_tab = self.create_single_graph_view()
        tabs.addTab(self.single_view_tab, "📈 Vista Individual")
        
        # Tab 2: Vista comparativa
        self.multi_view_tab = self.create_multi_graph_view()
        tabs.addTab(self.multi_view_tab, "📊 Vista Comparativa")
        
        # Tab 3: Dashboard completo
        self.dashboard_tab = self.create_dashboard_view()
        tabs.addTab(self.dashboard_tab, "🎛️ Dashboard")
        
        return tabs
        
    def create_single_graph_view(self):
        """Vista de gráfica individual"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Configurar gráfica
        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground(COLORS['graph_bg'])
        self.plot_widget.setMinimumHeight(400)
        self.plot_widget.showGrid(x=True, y=True, alpha=COLORS['grid_alpha'])
        self.plot_widget.setLabel('left', 'Valor')
        self.plot_widget.setLabel('bottom', 'Tiempo', units='s')
        
        # Configurar ejes con formato numérico simple
        axis_left = self.plot_widget.getAxis('left')
        axis_bottom = self.plot_widget.getAxis('bottom')
        axis_left.setPen(pg.mkPen(color=COLORS['text_primary'], width=2))
        axis_bottom.setPen(pg.mkPen(color=COLORS['text_primary'], width=2))
        axis_left.setTextPen(COLORS['text_primary'])
        axis_bottom.setTextPen(COLORS['text_primary'])
        axis_left.enableAutoSIPrefix(False)  # Desactivar prefijos SI
        axis_bottom.enableAutoSIPrefix(False)  # Desactivar prefijos SI
        
        # Curva de datos con optimizaciones para mejor respuesta
        self.plot_curve = self.plot_widget.plot(
            pen=pg.mkPen(color=SENSORS['heliografo']['color'], width=3),
            clipToView=True,  # Optimización: solo dibuja lo visible
            autoDownsample=True  # Optimización: submuestreo automático
        )
        
        layout.addWidget(self.plot_widget)
        
        # Panel de estadísticas debajo
        stats_panel = self.create_stats_panel()
        layout.addWidget(stats_panel)
        
        widget.setLayout(layout)
        return widget
        
    def create_stats_panel(self):
        """Panel de estadísticas en tiempo real"""
        panel = QFrame()
        panel.setMaximumHeight(85)
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border-radius: 8px;
                border: 2px solid {COLORS['border']};
            }}
        """)
        
        layout = QGridLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        
        # Crear labels para estadísticas
        self.stats_labels = {}
        self.stats_title_labels = {}  # Guardar labels de título para actualizar tema
        stats_items = [
            ('current', 'Actual', 0, 0),
            ('min', 'Mínimo', 0, 1),
            ('max', 'Máximo', 0, 2),
            ('avg', 'Promedio', 0, 3),
        ]
        
        for key, title, row, col in stats_items:
            container = QWidget()
            container_layout = QVBoxLayout()
            container_layout.setSpacing(2)
            container_layout.setContentsMargins(5, 0, 5, 0)
            
            title_label = QLabel(title)
            title_label.setFont(QFont("Arial", 8))
            title_label.setAlignment(Qt.AlignCenter)
            # Color negro siempre (se actualizará con apply_theme)
            title_label.setStyleSheet(f"color: #000000; background: transparent;")
            
            value_label = QLabel("--")
            value_label.setFont(QFont("Arial", 14, QFont.Bold))
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet(f"color: {COLORS['accent_cyan']}; background: transparent;")
            
            container_layout.addWidget(title_label)
            container_layout.addWidget(value_label)
            container.setLayout(container_layout)
            
            layout.addWidget(container, row, col)
            self.stats_labels[key] = value_label
            self.stats_title_labels[key] = title_label  # Guardar referencia
        
        panel.setLayout(layout)
        return panel
        
    def create_multi_graph_view(self):
        """Vista comparativa de múltiples sensores"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Gráfica normalizada
        self.multi_plot_widget = pg.PlotWidget()
        self.multi_plot_widget.setBackground(COLORS['graph_bg'])
        self.multi_plot_widget.setMinimumHeight(450)
        self.multi_plot_widget.showGrid(x=True, y=True, alpha=COLORS['grid_alpha'])
        self.multi_plot_widget.setLabel('left', 'Valor Normalizado (%)')
        self.multi_plot_widget.setLabel('bottom', 'Tiempo', units='s')
        
        # Configurar ejes con formato numérico simple
        axis_left = self.multi_plot_widget.getAxis('left')
        axis_bottom = self.multi_plot_widget.getAxis('bottom')
        axis_left.setPen(pg.mkPen(color=COLORS['text_primary'], width=2))
        axis_bottom.setPen(pg.mkPen(color=COLORS['text_primary'], width=2))
        axis_left.setTextPen(COLORS['text_primary'])
        axis_bottom.setTextPen(COLORS['text_primary'])
        axis_left.enableAutoSIPrefix(False)  # Desactivar prefijos SI
        axis_bottom.enableAutoSIPrefix(False)  # Desactivar prefijos SI
        self.multi_plot_widget.setYRange(0, 100)
        
        # Crear curvas para cada sensor con optimizaciones
        self.multi_curves = {}
        legend = self.multi_plot_widget.addLegend()
        for sensor_key, sensor_config in SENSORS.items():
            curve = self.multi_plot_widget.plot(
                pen=pg.mkPen(color=sensor_config['grafica_color'], width=2),
                name=f"{sensor_config['icon']} {sensor_config['name']}",
                clipToView=True,  # Optimización: solo dibuja lo visible
                autoDownsample=True  # Optimización: submuestreo automático
            )
            self.multi_curves[sensor_key] = curve
        
        layout.addWidget(self.multi_plot_widget)
        widget.setLayout(layout)
        return widget
        
    def create_dashboard_view(self):
        """Vista de dashboard con mini-gráficas"""
        widget = QWidget()
        layout = QGridLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Crear mini-gráfica para cada sensor
        self.mini_plots = {}
        row, col = 0, 0
        max_cols = 2
        
        for sensor_key, sensor_config in SENSORS.items():
            mini_plot = pg.PlotWidget()
            mini_plot.setBackground(COLORS['graph_bg'])
            mini_plot.setMinimumHeight(180)
            mini_plot.setMaximumHeight(240)
            mini_plot.showGrid(x=True, y=True, alpha=0.2)
            mini_plot.setTitle(
                f"{sensor_config['icon']} {sensor_config['name']}",
                color=sensor_config['color'],
                size='10pt'
            )
            mini_plot.setLabel('left', sensor_config['unit'])
            mini_plot.getAxis('left').setTextPen(COLORS['text_primary'])
            mini_plot.getAxis('bottom').setTextPen(COLORS['text_primary'])
            
            curve = mini_plot.plot(pen=pg.mkPen(color=sensor_config['grafica_color'], width=2))
            
            self.mini_plots[sensor_key] = {
                'widget': mini_plot,
                'curve': curve
            }
            
            layout.addWidget(mini_plot, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        widget.setLayout(layout)
        return widget
        
    def create_controls(self):
        """Panel de controles inferior"""
        panel = QFrame()
        panel.setMaximumHeight(85)
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['panel']};
                border-radius: 10px;
                border: 2px solid {COLORS['border']};
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)
        
        # Label de zoom
        zoom_label = QLabel("🔍 Ventana de tiempo:")
        zoom_label.setFont(QFont("Arial", 10, QFont.Bold))
        zoom_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(zoom_label)
        
        # Botones de zoom
        self.zoom_buttons = {}
        for zoom_key, zoom_info in ZOOM_LEVELS.items():
            btn = QPushButton(zoom_info['label'])
            btn.setMinimumSize(75, 45)
            btn.setFont(QFont("Arial", 9, QFont.Bold))
            btn.clicked.connect(lambda checked, key=zoom_key: self.set_zoom_level(key))
            btn.setProperty('zoom_key', zoom_key)
            
            if zoom_key == self.current_zoom_level:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['accent_green']};
                        color: white;
                        border: none;
                        border-radius: 8px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['background']};
                        color: {COLORS['text_primary']};
                        border: 2px solid {COLORS['border']};
                        border-radius: 8px;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['panel_hover']};
                        border: 2px solid {COLORS['accent_cyan']};
                    }}
                """)
            
            self.zoom_buttons[zoom_key] = btn
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # Botón limpiar datos
        clear_btn = QPushButton("🗑️ Limpiar")
        clear_btn.setMinimumSize(110, 45)
        clear_btn.setFont(QFont("Arial", 9, QFont.Bold))
        clear_btn.clicked.connect(self.clear_data)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_red']};
                color: white;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_orange']};
            }}
        """)
        layout.addWidget(clear_btn)
        
        panel.setLayout(layout)
        return panel
        
    def setup_communication(self):
        """Configura comunicación con ESP32"""
        print(f"🔌 Conectando a ESP32...")
        print(f"   📡 IP: {ESP32_IP}")
        print(f"   🔌 Puerto: {ESP32_PORT}")
        
        self.communicator = ESP32Communicator(ESP32_IP, ESP32_PORT)
        self.communicator.data_received.connect(self.on_data_received)
        self.communicator.connection_status.connect(self.on_connection_status)
        self.communicator.start()
        
    def setup_timers(self):
        """Configura los timers"""
        # Timer para gráficas
        self.graph_timer = QTimer()
        self.graph_timer.timeout.connect(self.update_graphs)
        self.graph_timer.start(GRAPH_UPDATE_RATE)
        
        # Timer para estadísticas
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(STATS_UPDATE_INTERVAL)
        
        # Timer para alarmas
        self.alarm_timer = QTimer()
        self.alarm_timer.timeout.connect(self.check_alarms)
        self.alarm_timer.start(ALARM_CHECK_INTERVAL)
        
        # Timer para reloj y tiempo de ejecución
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)  # Actualizar cada segundo
        
    def on_data_received(self, data):
        """Procesa datos recibidos del ESP32"""
        # NO usar el timestamp del ESP32, usar tiempo relativo
        # timestamp = data.get('timestamp', None)
        
        for sensor_key in SENSORS.keys():
            if sensor_key in data:
                value = data[sensor_key]
                # Pasar None para que use tiempo relativo desde el inicio
                self.data_manager.add_data(sensor_key, value, None)
        
    def on_connection_status(self, connected, message):
        """Actualiza estado de conexión con colores vibrantes"""
        if connected:
            self.connection_label.setText(f"✓ {message}")
            self.connection_label.setStyleSheet(f"""
                QLabel {{
                    color: #10B981;
                    padding: 10px;
                    background-color: #161B22;
                    border-radius: 8px;
                    border: 2px solid #10B981;
                    font-weight: bold;
                }}
            """)
        else:
            self.connection_label.setText(f"✗ {message}")
            self.connection_label.setStyleSheet(f"""
                QLabel {{
                    color: #EF4444;
                    padding: 10px;
                    background-color: #161B22;
                    border-radius: 8px;
                    border: 2px solid #EF4444;
                    font-weight: bold;
                }}
            """)
            
    def update_graphs(self):
        """Actualiza todas las gráficas"""
        current_tab_index = self.graph_tabs.currentIndex()
        
        # Vista individual
        if current_tab_index == 0:
            self.update_single_graph()
        
        # Vista comparativa
        elif current_tab_index == 1:
            self.update_multi_graph()
        
        # Dashboard
        elif current_tab_index == 2:
            self.update_dashboard_graphs()
            
    def update_single_graph(self):
        """Actualiza gráfica individual"""
        timestamps, values = self.data_manager.get_plot_data(self.current_sensor)
        
        if len(timestamps) > 1:
            # Aplicar zoom
            max_time = timestamps[-1]
            min_time = max_time - self.current_zoom_seconds
            mask = timestamps >= min_time
            timestamps = timestamps[mask]
            values = values[mask]
            
            if len(timestamps) > 0:
                self.plot_curve.setData(timestamps, values)
                self.plot_widget.setXRange(timestamps[0], timestamps[-1], padding=0.02)
                
                # Ajustar grid según zoom
                time_range = timestamps[-1] - timestamps[0]
                if time_range > 0:
                    # Calcular espaciado óptimo del grid
                    if time_range <= 30:  # 30 segundos o menos
                        x_grid_spacing = 5  # cada 5 segundos
                    elif time_range <= 60:  # 1 minuto
                        x_grid_spacing = 10  # cada 10 segundos
                    elif time_range <= 120:  # 2 minutos
                        x_grid_spacing = 20  # cada 20 segundos
                    else:  # más de 2 minutos
                        x_grid_spacing = 30  # cada 30 segundos
                    
                    # Actualizar grid con espaciado dinámico
                    axis_bottom = self.plot_widget.getAxis('bottom')
                    axis_bottom.setTickSpacing(major=x_grid_spacing, minor=x_grid_spacing/5)
                
                # Auto-ajustar Y con mejor respuesta ante cambios abruptos
                if len(values) > 0:
                    non_zero = values[values != 0]
                    if len(non_zero) > 0:
                        data_min = float(np.min(non_zero))
                        data_max = float(np.max(non_zero))
                        # Reducir padding para mejor ajuste ante cambios
                        data_range = data_max - data_min
                        padding = max(data_range * 0.05, 0.5)  # 5% en lugar de 10%
                        
                        # Agregar margen adicional para cambios abruptos
                        y_min = max(0, data_min - padding)
                        y_max = data_max + padding
                        
                        self.plot_widget.setYRange(
                            y_min,
                            y_max,
                            padding=0
                        )
                        
    def update_multi_graph(self):
        """Actualiza gráfica comparativa"""
        max_time_found = None
        
        for sensor_key, curve in self.multi_curves.items():
            timestamps, values = self.data_manager.get_plot_data(sensor_key)
            
            if len(timestamps) > 1:
                # Aplicar zoom
                max_time = timestamps[-1]
                if max_time_found is None or max_time > max_time_found:
                    max_time_found = max_time
                
                min_time = max_time - self.current_zoom_seconds
                mask = timestamps >= min_time
                timestamps = timestamps[mask]
                values = values[mask]
                
                if len(timestamps) > 0 and len(values) > 0:
                    # Normalizar (0-100%)
                    sensor_config = SENSORS[sensor_key]
                    min_val = sensor_config.get('min', 0)
                    max_val = sensor_config.get('max', 100)
                    
                    if max_val - min_val != 0:
                        normalized = ((values - min_val) / (max_val - min_val)) * 100.0
                        normalized = np.clip(normalized, 0, 100)
                        curve.setData(timestamps, normalized)
                    else:
                        curve.setData(timestamps, values)
        
        # Ajustar grid según zoom (solo una vez)
        if max_time_found is not None:
            time_range = self.current_zoom_seconds
            if time_range <= 30:
                x_grid_spacing = 5
            elif time_range <= 60:
                x_grid_spacing = 10
            elif time_range <= 120:
                x_grid_spacing = 20
            else:
                x_grid_spacing = 30
            
            axis_bottom = self.multi_plot_widget.getAxis('bottom')
            axis_bottom.setTickSpacing(major=x_grid_spacing, minor=x_grid_spacing/5)
                        
    def update_dashboard_graphs(self):
        """Actualiza mini-gráficas del dashboard"""
        for sensor_key, plot_data in self.mini_plots.items():
            timestamps, values = self.data_manager.get_plot_data(sensor_key)
            
            if len(timestamps) > 1:
                # Aplicar zoom
                max_time = timestamps[-1]
                min_time = max_time - self.current_zoom_seconds
                mask = timestamps >= min_time
                timestamps = timestamps[mask]
                values = values[mask]
                
                if len(timestamps) > 0:
                    plot_data['curve'].setData(timestamps, values)
                    plot_data['widget'].setXRange(timestamps[0], timestamps[-1], padding=0.02)
                    
    def update_stats(self):
        """Actualiza estadísticas y cards de sensores"""
        for sensor_key, card in self.sensor_cards.items():
            value = self.data_manager.get_current_value(sensor_key)
            stats = self.data_manager.get_stats(sensor_key)
            status = self.data_manager.get_sensor_status(sensor_key)
            
            card.update_value(value, stats, status)
        
        # Actualizar panel de estadísticas del sensor actual
        if self.current_sensor:
            stats = self.data_manager.get_stats(self.current_sensor)
            sensor_config = SENSORS[self.current_sensor]
            
            if stats and stats.get('count', 0) > 0:
                self.stats_labels['current'].setText(f"{stats['current']:.1f} {sensor_config['unit']}")
                self.stats_labels['min'].setText(f"{stats['min']:.1f} {sensor_config['unit']}")
                self.stats_labels['max'].setText(f"{stats['max']:.1f} {sensor_config['unit']}")
                self.stats_labels['avg'].setText(f"{stats['avg']:.1f} {sensor_config['unit']}")
    
    def update_clock(self):
        """Actualiza reloj y tiempo de ejecución"""
        from datetime import datetime
        
        # Hora actual
        current_time = datetime.now().strftime("%H:%M:%S")
        self.clock_label.setText(f"🕐 {current_time}")
        
        # Tiempo de ejecución
        elapsed = time.time() - self.start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        self.uptime_label.setText(f"⏱️ {hours:02d}:{minutes:02d}:{seconds:02d}")
                
    def check_alarms(self):
        """Verifica y gestiona alarmas"""
        any_alarm_active = False
        
        for sensor_key, sensor_config in SENSORS.items():
            value = self.data_manager.get_current_value(sensor_key)
            alarm_triggered = False
            
            # Verificar umbrales
            if value > 0:
                if 'alarm_threshold_low' in sensor_config and value < sensor_config['alarm_threshold_low']:
                    alarm_triggered = True
                if 'alarm_threshold_high' in sensor_config and value > sensor_config['alarm_threshold_high']:
                    alarm_triggered = True
            
            # Gestionar estado de alarma
            if alarm_triggered and not self.active_alarms[sensor_key]['silenced']:
                if not self.active_alarms[sensor_key]['active']:
                    self.activate_alarm(sensor_key, value)
                any_alarm_active = True
            else:
                if self.active_alarms[sensor_key]['active']:
                    self.deactivate_alarm(sensor_key)
                if not alarm_triggered:
                    self.active_alarms[sensor_key]['silenced'] = False
        
        # Controlar sonido
        if any_alarm_active and self.alarm_sound:
            try:
                if not pygame.mixer.get_busy():
                    self.alarm_sound.play(-1)
            except Exception as e:
                print(f"⚠️ Error al reproducir alarma: {e}")
        else:
            if self.alarm_sound:
                try:
                    self.alarm_sound.stop()
                except Exception as e:
                    print(f"⚠️ Error al detener alarma: {e}")
                    
    def activate_alarm(self, sensor_key, value):
        """Activa una alarma"""
        self.active_alarms[sensor_key]['active'] = True
        
    def deactivate_alarm(self, sensor_key):
        """Desactiva una alarma"""
        self.active_alarms[sensor_key]['active'] = False
        
    def select_sensor(self, sensor_key):
        """Selecciona un sensor"""
        self.current_sensor = sensor_key
        sensor_config = SENSORS[sensor_key]
        
        # Actualizar título
        self.sensor_title.setText(f"{sensor_config['icon']} {sensor_config['name']}")
        
        # Actualizar estilos de cards
        for key, card in self.sensor_cards.items():
            card.update_style(key == sensor_key)
        
        # Actualizar color de curva
        self.plot_curve.setPen(pg.mkPen(color=sensor_config['grafica_color'], width=3))
        self.plot_widget.setLabel('left', sensor_config['unit'])
        
    def set_zoom_level(self, zoom_key):
        """Cambia el nivel de zoom"""
        self.current_zoom_level = zoom_key
        self.current_zoom_seconds = ZOOM_LEVELS[zoom_key]['seconds']
        
        # Actualizar estilos de botones
        self.update_zoom_buttons_style()
    
    def update_zoom_buttons_style(self):
        """Actualiza los estilos de los botones de zoom"""
        # En tema claro, usar colores oscuros para los botones
        button_bg = DARK_THEME['background'] if not self.is_dark_theme else COLORS['background']
        button_text = DARK_THEME['text_primary'] if not self.is_dark_theme else COLORS['text_primary']
        button_border = DARK_THEME['border'] if not self.is_dark_theme else COLORS['border']
        button_hover_bg = DARK_THEME['panel_hover'] if not self.is_dark_theme else COLORS['panel_hover']
        
        for key, btn in self.zoom_buttons.items():
            if key == self.current_zoom_level:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['accent_green']};
                        color: white;
                        border: none;
                        border-radius: 8px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {button_bg};
                        color: {button_text};
                        border: 2px solid {button_border};
                        border-radius: 8px;
                    }}
                    QPushButton:hover {{
                        background-color: {button_hover_bg};
                        border: 2px solid {COLORS['accent_cyan']};
                    }}
                """)
                
    def toggle_theme(self):
        """Cambia entre tema claro y oscuro"""
        global COLORS
        
        self.is_dark_theme = not self.is_dark_theme
        
        if self.is_dark_theme:
            COLORS.update(DARK_THEME)
            self.theme_btn.setText("🌙 Oscuro")
        else:
            COLORS.update(LIGHT_THEME)
            self.theme_btn.setText("☀️ Claro")
        
        # Actualizar todos los estilos
        self.apply_theme()
        
    def apply_theme(self):
        """Aplica el tema a toda la interfaz"""
        # Actualizar ventana principal
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['background']};
            }}
        """)
        
        # Actualizar sidebar (SIEMPRE NEGRO PURO en ambos temas)
        sidebar_bg = '#000000'  # Negro absoluto siempre
        sidebar_border = '#1C2128'  # Borde gris azulado oscuro
        
        self.sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {sidebar_bg};
                border-right: 2px solid {sidebar_border};
            }}
        """)
        
        # Actualizar título en sidebar
        for child in self.sidebar.findChildren(QLabel):
            if "ESTACIÓN" in child.text():
                child.setStyleSheet(f"color: {COLORS['accent_cyan']}; padding: 8px;")
        
        # Actualizar área principal
        right_panel = self.centralWidget().findChildren(QWidget)[0]
        if len(self.centralWidget().findChildren(QWidget)) > 1:
            right_panel = [w for w in self.centralWidget().findChildren(QWidget) if w.parent() == self.centralWidget()][1]
            right_panel.setStyleSheet(f"background-color: {COLORS['background']};")
        
        # Actualizar header
        self.sensor_title.setStyleSheet(f"color: {COLORS['accent_cyan']};")
        self.theme_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_orange']};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_cyan']};
            }}
        """)
        
        # Actualizar gráficas
        self.plot_widget.setBackground(COLORS['graph_bg'])
        self.plot_widget.showGrid(x=True, y=True, alpha=COLORS['grid_alpha'])
        self.plot_widget.getAxis('left').setPen(pg.mkPen(color=COLORS['text_primary'], width=2))
        self.plot_widget.getAxis('bottom').setPen(pg.mkPen(color=COLORS['text_primary'], width=2))
        self.plot_widget.getAxis('left').setTextPen(COLORS['text_primary'])
        self.plot_widget.getAxis('bottom').setTextPen(COLORS['text_primary'])
        
        self.multi_plot_widget.setBackground(COLORS['graph_bg'])
        self.multi_plot_widget.showGrid(x=True, y=True, alpha=COLORS['grid_alpha'])
        self.multi_plot_widget.getAxis('left').setPen(pg.mkPen(color=COLORS['text_primary'], width=2))
        self.multi_plot_widget.getAxis('bottom').setPen(pg.mkPen(color=COLORS['text_primary'], width=2))
        self.multi_plot_widget.getAxis('left').setTextPen(COLORS['text_primary'])
        self.multi_plot_widget.getAxis('bottom').setTextPen(COLORS['text_primary'])
        
        # Actualizar mini-plots del dashboard
        for sensor_key, plot_data in self.mini_plots.items():
            plot_data['widget'].setBackground(COLORS['graph_bg'])
            plot_data['widget'].getAxis('left').setTextPen(COLORS['text_primary'])
            plot_data['widget'].getAxis('bottom').setTextPen(COLORS['text_primary'])
        
        # Actualizar sensor cards
        for card in self.sensor_cards.values():
            card.update_style(card.is_selected)
        
        # Actualizar stats labels (valores)
        for label in self.stats_labels.values():
            label.setStyleSheet(f"color: {COLORS['accent_cyan']}; background: transparent;")
        
        # Actualizar stats title labels (Actual, Mínimo, Máximo, Promedio)
        # En tema claro: negro completo
        # En tema oscuro: gris secundario
        title_color = '#000000' if not self.is_dark_theme else COLORS['text_secondary']
        if hasattr(self, 'stats_title_labels'):
            for label in self.stats_title_labels.values():
                label.setStyleSheet(f"color: {title_color}; background: transparent; font-weight: bold;")
        
        # Actualizar panel de controles (siempre oscuro)
        control_bg = DARK_THEME['panel'] if not self.is_dark_theme else COLORS['panel']
        control_border = DARK_THEME['border'] if not self.is_dark_theme else COLORS['border']
        control_text = DARK_THEME['text_primary'] if not self.is_dark_theme else COLORS['text_primary']
        
        # Buscar y actualizar panel de controles
        for frame in self.centralWidget().findChildren(QFrame):
            if frame.maximumHeight() == 90 and frame != self.sidebar:
                frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {control_bg};
                        border-radius: 10px;
                        border: 2px solid {control_border};
                    }}
                """)
                
                # Actualizar labels dentro del control panel
                for label in frame.findChildren(QLabel):
                    if "Ventana" in label.text():
                        label.setStyleSheet(f"color: {control_text};")
        
        # Actualizar botones de zoom (siempre oscuros)
        self.update_zoom_buttons_style()
        
    def clear_data(self):
        """Limpia todos los datos"""
        reply = QMessageBox.question(
            self,
            'Confirmar',
            '¿Seguro que deseas limpiar todos los datos?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.data_manager.clear_data()
            
    def export_data(self):
        """Exporta datos a archivo"""
        # Crear directorio de exportación si no existe
        export_dir = "exports"
        if not os.path.exists(export_dir):
            try:
                os.makedirs(export_dir)
            except Exception as e:
                print(f"⚠️ No se pudo crear el directorio de exportación: {e}")
                export_dir = "."  # Usar directorio actual si falla
        
        default_filename = os.path.join(export_dir, f"estacion_{time.strftime('%Y%m%d_%H%M%S')}")
        
        filename, filter_type = QFileDialog.getSaveFileName(
            self,
            "Exportar Datos",
            default_filename,
            "CSV (*.csv);;JSON (*.json)"
        )
        
        if filename:
            try:
                if 'csv' in filter_type.lower():
                    success = self.data_manager.export_data_csv(filename)
                else:
                    success = self.data_manager.export_data_json(filename)
                
                if success:
                    QMessageBox.information(self, "Éxito", f"Datos exportados a:\n{filename}")
                else:
                    QMessageBox.warning(self, "Error", "No se pudieron exportar los datos")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al exportar datos:\n{str(e)}")
                
    def show_info_dialog(self):
        """Muestra diálogo de información"""
        dialog = InfoDialog(self)
        dialog.exec_()
        
    def closeEvent(self, event):
        """Maneja el cierre"""
        if hasattr(self, 'communicator'):
            self.communicator.stop()
        
        if self.alarm_sound:
            try:
                self.alarm_sound.stop()
            except Exception as e:
                print(f"⚠️ Error al detener alarma al cerrar: {e}")
        
        event.accept()


def main():
    """Función principal"""
    app = QApplication(sys.argv)
    app.setFont(QFont("Arial", 10))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

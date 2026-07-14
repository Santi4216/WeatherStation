/*
 * =====================================================================
 * ESTACIÓN METEOROLÓGICA - ESP32
 * Universidad Militar Nueva Granada
 * Asignatura: Sensores y Laboratorio
 * =====================================================================
 * 
 * Integrantes:
 * - Karol Daniela Mosquera
 * - David Santiago García Suárez
 * - Santiago Rubiano Garzón
 * 
 * Descripción:
 * Este código lee datos de los siguientes sensores y los envía por WiFi:
 * 1. Intensidad de Luz (Sensor analógico) - GPIO 35
 * 2. Temperatura (RTD Pt100 con lectura de voltaje) - GPIO 36
 * 3. Velocidad del Viento (Anemómetro) - GPIO 34
 * 4. Altitud/Presión (BMP280/BME280) - I2C
 * 
 * Calibración PT100: 18°C -> 0.34V, 20°C -> 0.39V
 * Ecuación lineal: T(°C) = 40 * V + 4.4
 * 
 * =====================================================================
 */

// ==================== LIBRERÍAS ====================
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <SPI.h>
#include <Adafruit_BMP280.h>    // Para barómetro
// #include <Adafruit_MAX31865.h>  // Deshabilitado - usando lectura directa de voltaje

// ==================== CONFIGURACIÓN WIFI ====================
// Modo Cliente - La ESP32 se conecta a tu red WiFi
const char* ssid = "TU_SSID_AQUI";          // Reemplaza con el nombre de tu red WiFi
const char* password = "TU_PASSWORD_AQUI";  // Reemplaza con la contraseña de tu red WiFi

WebServer server(80);
unsigned long ultimoIntentoReconexionWiFi = 0;
const unsigned long INTERVALO_RECONEXION_WIFI = 10000;

// ==================== PINES GPIO ====================
#define PIN_LUZ 35              // Sensor de luz analógico
#define PIN_ANEMOMETRO 34       // Anemómetro (entrada analógica en mV)
#define PIN_PT100 33            // Sensor PT100 (entrada analógica para voltaje)

// SPI para MAX31865 (RTD Pt100) - DESHABILITADO, usando lectura directa de voltaje
// #define MAX31865_CS 5
// #define MAX31865_SDI 23
// #define MAX31865_SDO 19
// #define MAX31865_CLK 18

// I2C para BMP280 (Barómetro)
#define I2C_SDA 21
#define I2C_SCL 22

// ==================== OBJETOS DE SENSORES ====================
// Adafruit_MAX31865 rtd = Adafruit_MAX31865(MAX31865_CS, MAX31865_SDI, MAX31865_SDO, MAX31865_CLK);
Adafruit_BMP280 bmp;

// Calibración PT100 basada en voltaje analógico
// Datos de calibración: 18°C -> 0.34V, 20°C -> 0.39V
// Ecuación lineal: T = m * V + b
// m = (T2 - T1) / (V2 - V1) = (20 - 18) / (0.39 - 0.34) = 2 / 0.05 = 40
// b = T1 - m * V1 = 18 - 40 * 0.34 = 18 - 13.6 = 4.4
#define PT100_PENDIENTE 40.0     // Pendiente de la recta (°C/V)
#define PT100_ORDENADA 4.4       // Ordenada al origen (°C)

// ==================== FILTRO KALMAN PARA PT100 ====================
// Variables del filtro Kalman para temperatura (OPTIMIZADO para reducir oscilaciones)
float kalman_x = 20.0;      // Estado estimado (temperatura estimada)
float kalman_P = 1.0;       // Incertidumbre del estado
float kalman_Q = 0.0005;    // Ruido del proceso (MUY reducido para máximo suavizado)
float kalman_R = 3.0;       // Ruido de la medición (aumentado para ignorar más el ruido)

// Buffer para promedio móvil adicional
#define BUFFER_SIZE 10
float temp_buffer[BUFFER_SIZE];
int buffer_index = 0;
bool buffer_lleno = false;

/**
 * Filtro Kalman de 1 dimensión para suavizar temperatura
 * @param medicion: Valor medido de temperatura
 * @return: Valor filtrado de temperatura
 */
float filtroKalman(float medicion) {
  // Predicción
  float x_pred = kalman_x;
  float P_pred = kalman_P + kalman_Q;
  
  // Actualización
  float K = P_pred / (P_pred + kalman_R);  // Ganancia de Kalman
  kalman_x = x_pred + K * (medicion - x_pred);
  kalman_P = (1 - K) * P_pred;
  
  return kalman_x;
}

/**
 * Promedio móvil para suavizado adicional
 * @param valor: Valor a agregar al buffer
 * @return: Promedio de los últimos BUFFER_SIZE valores
 */
float promedioMovil(float valor) {
  // Agregar nuevo valor al buffer circular
  temp_buffer[buffer_index] = valor;
  buffer_index = (buffer_index + 1) % BUFFER_SIZE;
  
  if (buffer_index == 0) {
    buffer_lleno = true;
  }
  
  // Calcular promedio
  float suma = 0;
  int count = buffer_lleno ? BUFFER_SIZE : buffer_index;
  
  for (int i = 0; i < count; i++) {
    suma += temp_buffer[i];
  }
  
  return suma / count;
}

// ==================== VARIABLES GLOBALES ====================
// Datos de sensores
float intensidadLuz = 0.0;      // % (0-100)
float temperatura = 0.0;         // °C
float velocidadViento = 0.0;     // km/h
float altitud = 0.0;             // metros

// Control de tiempo
unsigned long ultimaLectura = 0;
const unsigned long INTERVALO_LECTURA = 100; // 100ms = 10Hz

// Tabla de calibración del anemómetro (mV -> km/h) - RESOLUCIÓN MEJORADA
// Basada en datos de caracterización del sensor con más puntos intermedios
const int TABLA_ANEMOMETRO_SIZE = 21;
const float TABLA_MV[] = {10, 71, 132, 196, 260, 308.5, 357, 384.5, 412, 464, 516, 563, 610, 669, 728, 789, 850, 918, 986, 1019, 1052};
const float TABLA_KMH[] = {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100};

// Variables para BMP280
#define BMP280_I2C_ADDRESS 0x76  // Dirección I2C del BMP280 (cambiar a 0x77 si es necesario)
const float PRESION_NIVEL_MAR = 1007.2;  // Presión a nivel del mar en hPa (ajustar según clima local)
bool bmp_inicializado = false;

// ==================== FUNCIONES DE CONVERSIÓN ====================

/**
 * Convierte voltaje (mV) a velocidad del viento (km/h) usando interpolación lineal
 * Basado en la tabla de calibración del sensor
 */
float convertirMvAKmh(float voltaje_mv) {
  // Si está por debajo del valor mínimo
  if (voltaje_mv <= TABLA_MV[0]) {
    return TABLA_KMH[0];
  }
  
  // Si está por encima del valor máximo
  if (voltaje_mv >= TABLA_MV[TABLA_ANEMOMETRO_SIZE - 1]) {
    return TABLA_KMH[TABLA_ANEMOMETRO_SIZE - 1];
  }
  
  // Buscar entre qué dos puntos está el voltaje
  for (int i = 0; i < TABLA_ANEMOMETRO_SIZE - 1; i++) {
    if (voltaje_mv >= TABLA_MV[i] && voltaje_mv <= TABLA_MV[i + 1]) {
      // Interpolación lineal
      float mv1 = TABLA_MV[i];
      float mv2 = TABLA_MV[i + 1];
      float kmh1 = TABLA_KMH[i];
      float kmh2 = TABLA_KMH[i + 1];
      
      // y = y1 + (x - x1) * (y2 - y1) / (x2 - x1)
      float velocidad = kmh1 + (voltaje_mv - mv1) * (kmh2 - kmh1) / (mv2 - mv1);
      return velocidad;
    }
  }
  
  return 0.0;
}

// ==================== FUNCIONES DE LECTURA ====================

/**
 * Lee la intensidad de luz del sensor analógico
 * Rango: 0-100%
 */
float leerIntensidadLuz() {
  int valorADC = analogRead(PIN_LUZ);
  // Convertir ADC (0-4095) a porcentaje (0-100)
  float porcentaje = (valorADC / 4095.0) * 100.0;
  return porcentaje;
}

/**
 * Lee la temperatura del RTD Pt100 mediante voltaje analógico
 * Calibración: 18°C -> 0.34V, 20°C -> 0.39V
 * Ecuación: T = 40 * V + 4.4
 * Aplica filtro Kalman para reducir ruido
 * Rango: 10-50°C
 */
float leerTemperatura() {
  // Leer valor ADC (0-4095 para ESP32 de 12 bits)
  int valorADC = analogRead(PIN_PT100);
  
  // Convertir ADC a voltaje (0-3.3V)
  // Voltaje = (ADC / 4095) * 3.3
  float voltaje = (valorADC / 4095.0) * 3.3;
  
  // Aplicar ecuación de calibración lineal
  // T = m * V + b
  float temperatura_raw = PT100_PENDIENTE * voltaje + PT100_ORDENADA;
  
  // Aplicar filtro Kalman para suavizar el ruido
  float temperatura_filtrada = filtroKalman(temperatura_raw);
  
  // Limitar a rango esperado (10-50°C)
  temperatura_filtrada = constrain(temperatura_filtrada, 10.0, 50.0);
  
  return temperatura_filtrada;
}

/**
 * Calcula la velocidad del viento del anemómetro
 * Lee voltaje analógico y lo convierte a km/h usando tabla de calibración
 * Incluye promediado de múltiples lecturas para mayor precisión
 */
float leerVelocidadViento() {
  // Promediar 5 lecturas ADC para reducir ruido y aumentar resolución
  const int NUM_LECTURAS = 5;
  long suma_ADC = 0;
  
  for (int i = 0; i < NUM_LECTURAS; i++) {
    suma_ADC += analogRead(PIN_ANEMOMETRO);
    delayMicroseconds(100);  // Pequeña pausa entre lecturas
  }
  
  float valorADC_promedio = suma_ADC / (float)NUM_LECTURAS;
  
  // Convertir ADC a mV
  // ESP32: ADC de 3.3V y 12 bits (0-4095)
  // Voltaje = (ADC / 4095) * 3300 mV
  float voltaje_mv = (valorADC_promedio / 4095.0) * 3300.0;
  
  // Convertir mV a km/h usando tabla de calibración mejorada
  float velocidad = convertirMvAKmh(voltaje_mv);
  
  // Limitar a rango 0-150 km/h
  velocidad = constrain(velocidad, 0.0, 150.0);
  
  return velocidad;
}

/**
 * Lee la altitud del barómetro BMP280
 * Usa la presión a nivel del mar para calcular altitud absoluta
 */
float leerAltitud() {
  if (!bmp_inicializado) {
    return 0.0; // BMP no disponible
  }
  
  // Leer altitud directamente usando la presión de referencia a nivel del mar
  // La función readAltitude calcula la altitud usando la fórmula barométrica estándar
  float altitud = bmp.readAltitude(PRESION_NIVEL_MAR);
  
  // Limitar rango a 0-3000 metros
  altitud = constrain(altitud, 0.0, 3000.0);
  
  return altitud;
}

// ==================== SERVIDOR WEB ====================

/**
 * Maneja la petición HTTP GET para obtener datos de sensores
 * Formato JSON: {"heliografo":50.5, "temperatura":25.2, ...}
 */
void handleGetData() {
  // Crear respuesta JSON
  String json = "{";
  json += "\"heliografo\":" + String(intensidadLuz, 1) + ",";
  json += "\"temperatura\":" + String(temperatura, 1) + ",";
  json += "\"anemometro\":" + String(velocidadViento, 1) + ",";
  json += "\"barometro\":" + String(altitud, 1) + ",";
  json += "\"timestamp\":" + String(millis());
  json += "}";
  
  // Enviar respuesta con headers CORS
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", json);
  
  // Log en consola con valor de altitud
  Serial.print("✓ Datos enviados - Altitud: ");
  Serial.println(altitud, 1);
}

/**
 * Maneja peticiones a la raíz (información del sistema)
 */
void handleRoot() {
  String html = "<html><head><meta charset='UTF-8'>";
  html += "<title>Estación Meteorológica UMNG</title>";
  html += "<style>body{font-family:Arial;margin:40px;background:#0A0E1A;color:#F1F5F9;}";
  html += "h1{color:#06B6D4;}table{border-collapse:collapse;width:100%;margin-top:20px;}";
  html += "td,th{border:1px solid #30363D;padding:12px;text-align:left;}";
  html += "th{background:#0D1117;}</style></head><body>";
  html += "<h1>⛅ Estación Meteorológica UMNG</h1>";
  html += "<h3>Datos en Tiempo Real</h3>";
  html += "<table>";
  html += "<tr><th>Sensor</th><th>Valor</th><th>Unidad</th></tr>";
  html += "<tr><td>💡 Intensidad de Luz</td><td>" + String(intensidadLuz, 1) + "</td><td>%</td></tr>";
  html += "<tr><td>🌡️ Temperatura</td><td>" + String(temperatura, 1) + "</td><td>°C</td></tr>";
  html += "<tr><td>🌪️ Velocidad del Viento</td><td>" + String(velocidadViento, 1) + "</td><td>km/h</td></tr>";
  html += "<tr><td>⛰️ Altitud</td><td>" + String(altitud, 0) + "</td><td>m</td></tr>";
  html += "</table>";
  html += "<p style='margin-top:30px;color:#94A3B8;'>Endpoint API: <code>http://" + WiFi.localIP().toString() + "/data</code></p>";
  html += "<script>setTimeout(()=>location.reload(),2000);</script>";
  html += "</body></html>";
  
  server.send(200, "text/html", html);
}

/**
 * Maneja rutas no encontradas
 */
void handleNotFound() {
  server.send(404, "text/plain", "404: Ruta no encontrada");
}

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n");
  Serial.println("=============================================");
  Serial.println("  ESTACIÓN METEOROLÓGICA - ESP32");
  Serial.println("  Universidad Militar Nueva Granada");
  Serial.println("=============================================\n");
  
  // Configurar pines de entrada
  pinMode(PIN_LUZ, INPUT);
  pinMode(PIN_ANEMOMETRO, INPUT);  // Entrada analógica para anemómetro
  pinMode(PIN_PT100, INPUT);       // Entrada analógica para PT100
  
  Serial.println("✓ Pines GPIO configurados");
  
  // Configurar resolución del ADC para mejor precisión
  analogSetAttenuation(ADC_11db);  // Rango completo de 0-3.3V
  
  // Inicializar I2C
  Wire.begin(I2C_SDA, I2C_SCL);
  Serial.println("✓ I2C inicializado");
  
  // Inicializar RTD Pt100 (lectura directa de voltaje)
  Serial.println("🌡️ RTD Pt100 configurado (lectura analógica)");
  Serial.println("   Calibración: 18°C -> 0.34V, 20°C -> 0.39V");
  Serial.println("   Ecuación: T = 40*V + 4.4");
  
  // Inicializar BMP280
  Serial.println("⛰️ Inicializando BMP280...");
  
  // Intentar inicializar con la dirección definida
  if (bmp.begin(BMP280_I2C_ADDRESS)) {
    bmp_inicializado = true;
    Serial.print("   ✓ BMP280 encontrado en 0x");
    Serial.println(BMP280_I2C_ADDRESS, HEX);
  }
  // Si falla, intentar la otra dirección común
  else {
    uint8_t direccion_alternativa = (BMP280_I2C_ADDRESS == 0x76) ? 0x77 : 0x76;
    if (bmp.begin(direccion_alternativa)) {
      bmp_inicializado = true;
      Serial.print("   ✓ BMP280 encontrado en 0x");
      Serial.println(direccion_alternativa, HEX);
    }
    else {
      Serial.println("   ✗ BMP280 no encontrado en 0x76 ni 0x77");
      bmp_inicializado = false;
    }
  }
  
  if (bmp_inicializado) {
    // Configurar sensor (modo y filtrado)
    bmp.setSampling(
      Adafruit_BMP280::MODE_NORMAL,     // Modo normal
      Adafruit_BMP280::SAMPLING_X2,     // Sobremuestreo temperatura
      Adafruit_BMP280::SAMPLING_X16,    // Sobremuestreo presión
      Adafruit_BMP280::FILTER_X16,      // Filtro IIR
      Adafruit_BMP280::STANDBY_MS_500   // Tiempo de espera
    );
    
    Serial.print("   Presión de referencia (nivel del mar): ");
    Serial.print(PRESION_NIVEL_MAR, 1);
    Serial.println(" hPa");
    Serial.println("   ✓ BMP280 configurado correctamente");
  }
  
  // Configurar WiFi en modo Cliente (Station)
  Serial.println("\n📡 Configurando WiFi...");
  WiFi.mode(WIFI_STA);
  WiFi.persistent(false);
  WiFi.setAutoReconnect(true);
  WiFi.begin(ssid, password);
  
  Serial.print("Conectando a WiFi");
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 30) {
    delay(500);
    Serial.print(".");
    intentos++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi conectado");
    Serial.print("   SSID: ");
    Serial.println(ssid);
    Serial.print("   IP: ");
    Serial.println(WiFi.localIP());
    Serial.println("   Puerto: 80");
  } else {
    Serial.println("\n✗ ERROR: No se pudo conectar al WiFi");
    Serial.println("Verifica SSID y contraseña");
  }
  
  // Configurar rutas del servidor
  server.on("/", handleRoot);
  server.on("/data", handleGetData);
  server.onNotFound(handleNotFound);
  
  // Iniciar servidor
  server.begin();
  Serial.println("✓ Servidor HTTP iniciado\n");
  
  Serial.println("=============================================");
  Serial.println("Sistema listo para operar");
  Serial.println("Abre en el navegador:");
  Serial.print("  http://");
  Serial.println(WiFi.localIP());
  Serial.println("=============================================\n");
}

void manejarReconexionWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  unsigned long tiempoActual = millis();
  if (tiempoActual - ultimoIntentoReconexionWiFi < INTERVALO_RECONEXION_WIFI) {
    return;
  }

  ultimoIntentoReconexionWiFi = tiempoActual;
  Serial.println("⚠️ WiFi desconectado, intentando reconectar...");
  WiFi.disconnect(false);
  WiFi.begin(ssid, password);
}

// ==================== LOOP ====================
void loop() {
  manejarReconexionWiFi();

  // Manejar peticiones del servidor web
  server.handleClient();
  
  // Leer sensores cada INTERVALO_LECTURA ms (100ms = 10Hz)
  unsigned long tiempoActual = millis();
  if (tiempoActual - ultimaLectura >= INTERVALO_LECTURA) {
    ultimaLectura = tiempoActual;
    
    // Leer todos los sensores
    intensidadLuz = leerIntensidadLuz();
    temperatura = leerTemperatura();
    velocidadViento = leerVelocidadViento();
    altitud = leerAltitud();
    
    // Mostrar datos en consola (cada 1 segundo = 10 lecturas)
    static int contador = 0;
    contador++;
    if (contador >= 10) {
      contador = 0;
      Serial.println("--- Lecturas ---");
      Serial.print("💡 Luz: ");
      Serial.print(intensidadLuz, 1);
      Serial.println(" %");
      
      Serial.print("🌡️ Temperatura: ");
      Serial.print(temperatura, 1);
      Serial.println(" °C");
      
      Serial.print("🌪️ Viento: ");
      Serial.print(velocidadViento, 1);
      Serial.println(" km/h");
      
      Serial.print("⛰️ Altitud: ");
      Serial.print(altitud, 0);
      Serial.println(" m");
      Serial.println();
    }
  }
}

#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP280.h>

Adafruit_BMP280 bmp;

// Altitud real de Cajicá, Cundinamarca (msnm)
#define ALTITUD_REAL 2558.0

void setup() {
  Serial.begin(115200);
  Serial.println(F("=== Prueba BMP280 - Lectura coherente de altitud ==="));

  if (!bmp.begin(0x76)) {  // usa 0x77 si no detecta el sensor
    Serial.println(F("Error: No se encontró el BMP280. Verifica conexiones."));
    while (1);
  }
  
  // Configuración de muestreo
  bmp.setSampling(
    Adafruit_BMP280::MODE_NORMAL,
    Adafruit_BMP280::SAMPLING_X2,
    Adafruit_BMP280::SAMPLING_X16,
    Adafruit_BMP280::FILTER_X16,
    Adafruit_BMP280::STANDBY_MS_500);
}

void loop() {
  // Lecturas básicas
  float temperatura = bmp.readTemperature();
  float presion = bmp.readPressure() / 100.0F; // en hPa

  // Calcular presión a nivel del mar (ajustando con la altitud real del lugar)
  float presion_nivel_mar = bmp.seaLevelForAltitude(ALTITUD_REAL, presion);

  // Calcular altitud relativa según esa presión de referencia
  float altitud_relativa = bmp.readAltitude(presion_nivel_mar);

  Serial.println(F("----------------------------------"));
  Serial.print("Temperatura: ");
  Serial.print(temperatura);
  Serial.println(" *C");

  Serial.print("Presión local: ");
  Serial.print(presion);
  Serial.println(" hPa");

  Serial.print("Presión nivel del mar (ajustada): ");
  Serial.print(presion_nivel_mar);
  Serial.println(" hPa");

  Serial.print("Altitud calculada sobre el nivel del mar: ");
  Serial.print(ALTITUD_REAL + altitud_relativa);
  Serial.println(" m");

  delay(2000);
}

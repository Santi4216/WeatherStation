"""
Script de prueba para verificar conexión con ESP32
"""

import requests
import json

# Configuración
ESP32_IP = "192.168.137.125"
ESP32_PORT = 80

print("=" * 60)
print("PRUEBA DE CONEXIÓN ESP32")
print("=" * 60)
print(f"\nIntentando conectar a: http://{ESP32_IP}:{ESP32_PORT}")
print("-" * 60)

# Prueba 1: Conectar a la raíz
print("\n1. Probando endpoint raíz (/)...")
try:
    response = requests.get(f"http://{ESP32_IP}:{ESP32_PORT}/", timeout=5)
    print(f"   ✓ Respuesta recibida - Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✓ Conexión exitosa")
except requests.exceptions.Timeout:
    print(f"   ✗ TIMEOUT - La ESP32 no responde en 5 segundos")
except requests.exceptions.ConnectionError:
    print(f"   ✗ ERROR DE CONEXIÓN - No se puede alcanzar {ESP32_IP}")
    print(f"   Verifica que:")
    print(f"   - La ESP32 esté encendida")
    print(f"   - Esté conectada a tu red WiFi")
    print(f"   - La IP {ESP32_IP} sea correcta")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

# Prueba 2: Endpoint de datos
print("\n2. Probando endpoint de datos (/data)...")
try:
    response = requests.get(f"http://{ESP32_IP}:{ESP32_PORT}/data", timeout=5)
    print(f"   ✓ Respuesta recibida - Status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"   ✓ Datos recibidos correctamente")
        data = response.json()
        print(f"\n   Datos JSON recibidos:")
        print(json.dumps(data, indent=4, ensure_ascii=False))
    else:
        print(f"   ✗ Error HTTP: {response.status_code}")
        
except requests.exceptions.Timeout:
    print(f"   ✗ TIMEOUT - La ESP32 no responde")
except requests.exceptions.ConnectionError:
    print(f"   ✗ ERROR DE CONEXIÓN")
except json.JSONDecodeError:
    print(f"   ✗ ERROR: La respuesta no es JSON válido")
    print(f"   Respuesta recibida: {response.text[:200]}")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

print("\n" + "=" * 60)
print("DIAGNÓSTICO:")
print("=" * 60)

# Verificar conectividad básica
print("\n3. Verificando conectividad de red (ping)...")
import subprocess
import platform

param = '-n' if platform.system().lower() == 'windows' else '-c'
command = ['ping', param, '1', ESP32_IP]

try:
    result = subprocess.run(command, capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print(f"   ✓ Ping exitoso - La ESP32 está en la red")
    else:
        print(f"   ✗ Ping fallido - La ESP32 no responde")
        print(f"   SOLUCIÓN: Verifica la IP en el Monitor Serial de Arduino")
except Exception as e:
    print(f"   ? No se pudo hacer ping: {e}")

print("\n" + "=" * 60)
print("PASOS SIGUIENTES:")
print("=" * 60)
print("\nSi hay errores de conexión:")
print("1. Abre el Monitor Serial del Arduino IDE (115200 baudios)")
print("2. Busca la línea que dice: 'IP: 192.168.X.XXX'")
print("3. Copia esa IP y actualízala en config.py")
print("4. Verifica que tu PC esté conectado a la misma red WiFi que la ESP32")
print("\n" + "=" * 60)

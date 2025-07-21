# ===============================================
# CAMBIOS PRINCIPALES (RESUMEN)
# ===============================================

# 1. Configuración externa con JSON:
#    - Ahora las API keys y parámetros (símbolo, niveles de grid, tamaño de trade, fee)
#      se cargan desde "config.json" en lugar de estar hardcodeados.
#    - Esto permite cambiar configuraciones sin tocar el código.

# 2. Logs automáticos (errores_bot.log):
#    - Cada vez que el bot se cierra por pérdida de capital o error inesperado,
#      se escribe un registro con fecha, motivo y balance final.
#    - Esto facilita diagnosticar por qué se detuvo.

# 3. Historial de operaciones (operaciones_grid.csv):
#    - Cada compra o venta se guarda con timestamp, precio, balances y profit acumulado.
#    - El CSV permite analizar resultados más tarde o graficar.

# 4. Gráfico automático (grafico_balance.png):
#    - Al finalizar la sesión (por cierre manual o por error), se genera un gráfico PNG
#      que muestra cómo evolucionó el capital total (USDT + XRP).
#    - Permite ver visualmente el rendimiento del bot sin revisar toda la consola.

# 5. Reconexión y modo 24/7:
#    - Si Binance Testnet da timeout (por problemas de conexión), el bot espera 5s y reintenta.
#    - Si ocurre un error inesperado (excepción no manejada), el bot:
#        a) Guarda un log del error y balance.
#        b) Genera el gráfico.
#        c) Espera 10s y se reinicia automáticamente (modo 24/7).

# 6. Eliminada la necesidad de "sudo":
#    - Todos los archivos (config, logs, CSV) se crean con permisos normales.
#    - Ya no se necesita ejecutar el bot como root.

# 7. Grid dinámico:
#    - El rango de la cuadrícula (grid_low, grid_high) se ajusta automáticamente
#      en función del mínimo y máximo de las últimas 24 horas, con un 2% extra de margen.
#    - Se recalcula cada 10 minutos para adaptarse al mercado.

# ===============================================



import json
import time
import csv
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL
from requests.exceptions import ReadTimeout
import os
import traceback

# ==== CARGAR CONFIGURACIÓN DESDE JSON ====
with open("config.json", "r") as f:
    config = json.load(f)

API_KEY = config["API_KEY"]
API_SECRET = config["API_SECRET"]
SYMBOL = config["SYMBOL"]
GRID_LEVELS = config["GRID_LEVELS"]
TRADE_SIZE = config["TRADE_SIZE"]
FEE_RATE = config["FEE_RATE"]

client = Client(API_KEY, API_SECRET, testnet=True)

# Archivos de estado
SESSIONS_FILE = "registro_sesiones.json"
OPERATIONS_FILE = "operaciones_grid.csv"
LOG_FILE = "errores_bot.log"

# ==== FUNCIONES DE LOG, SESIONES Y CSV ====
def registrar_error(motivo, balance):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} | Motivo: {motivo} | Balance final: {balance:.2f} USDT\n")

def cargar_sesion():
    try:
        with open(SESSIONS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"balance": 0.0, "sesiones": 0, "ganancias": 0, "perdidas": 0}

def guardar_sesion(balance, sesion_ganancia):
    data = cargar_sesion()
    data["balance"] = balance
    data["sesiones"] += 1
    if sesion_ganancia:
        data["ganancias"] += 1
    else:
        data["perdidas"] += 1
    with open(SESSIONS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def registrar_operacion(timestamp, operacion, precio, usdt_balance, xrp_balance, profit):
    nueva = not os.path.exists(OPERATIONS_FILE)
    with open(OPERATIONS_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if nueva:
            writer.writerow(["timestamp", "operacion", "precio", "usdt_balance", "xrp_balance", "profit"])
        writer.writerow([timestamp, operacion, f"{precio:.4f}", f"{usdt_balance:.2f}", f"{xrp_balance:.2f}", f"{profit:.2f}"])

# ==== GENERAR GRÁFICO DE BALANCE ====
def generar_grafico():
    if not os.path.exists(OPERATIONS_FILE):
        return
    timestamps, balances = [], []
    with open(OPERATIONS_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
            usdt = float(row["usdt_balance"])
            xrp = float(row["xrp_balance"])
            price = float(row["precio"])
            balances.append(usdt + xrp * price)
            timestamps.append(ts)

    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, balances, marker="o")
    plt.title("Evolución del Balance (USDT + XRP)")
    plt.xlabel("Tiempo")
    plt.ylabel("Balance Total (USDT)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("grafico_balance.png")
    plt.close()

# ==== FUNCIONES DE TRADING ====
def get_price():
    """Obtiene el precio actual, reintenta si hay timeout."""
    while True:
        try:
            ticker = client.get_symbol_ticker(symbol=SYMBOL)
            return float(ticker["price"])
        except ReadTimeout:
            print("Timeout al conectar con Binance. Reintentando en 5 segundos...")
            time.sleep(5)

def get_dynamic_grid():
    stats = client.get_ticker(symbol=SYMBOL)
    low_24h = float(stats["lowPrice"])
    high_24h = float(stats["highPrice"])
    grid_low = low_24h * 0.98
    grid_high = high_24h * 1.02
    grid_prices = np.linspace(grid_low, grid_high, GRID_LEVELS)
    return grid_low, grid_high, grid_prices

def place_order(side, price, usdt_balance, xrp_balance, total_profit):
    cost = TRADE_SIZE * price
    fee = cost * FEE_RATE
    profit = 0.0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if side == SIDE_BUY and usdt_balance >= (cost + fee):
        usdt_balance -= (cost + fee)
        xrp_balance += TRADE_SIZE
        registrar_operacion(timestamp, "BUY", price, usdt_balance, xrp_balance, total_profit)
        print(f"BUY {TRADE_SIZE} @ {price:.4f} (Fee: {fee:.4f})")

    elif side == SIDE_SELL and xrp_balance >= TRADE_SIZE:
        usdt_balance += (cost - fee)
        xrp_balance -= TRADE_SIZE
        profit = (cost - fee)
        total_profit += profit
        registrar_operacion(timestamp, "SELL", price, usdt_balance, xrp_balance, total_profit)
        print(f"SELL {TRADE_SIZE} @ {price:.4f} (Fee: {fee:.4f})")

    return usdt_balance, xrp_balance, total_profit

# ==== PROCESO PRINCIPAL ====
def grid_trading():
    sesion = cargar_sesion()
    balance_previo = sesion["balance"]

    monto_inicial = float(input(f"Ingrese monto a invertir (USD) [balance previo {balance_previo:.2f}]: "))
    usdt_balance = monto_inicial + balance_previo
    xrp_balance = 0.0
    total_profit = 0.0

    print(f"\nIniciando Grid Trading para {SYMBOL} con {usdt_balance:.2f} USDT...")
    last_price = get_price()
    grid_low, grid_high, grid_prices = get_dynamic_grid()
    print(f"Grid inicial: Low={grid_low:.4f}, High={grid_high:.4f}, Niveles={GRID_LEVELS}")

    try:
        while True:
            price = get_price()

            # Recalcular grid cada 10 minutos
            if int(time.time()) % 600 < 5:
                grid_low, grid_high, grid_prices = get_dynamic_grid()
                print(f"\nGrid actualizado: Low={grid_low:.4f}, High={grid_high:.4f}")

            # Revisar cruces de niveles
            for grid_price in grid_prices:
                if last_price < grid_price <= price:
                    usdt_balance, xrp_balance, total_profit = place_order(SIDE_SELL, grid_price, usdt_balance, xrp_balance, total_profit)
                elif last_price > grid_price >= price:
                    usdt_balance, xrp_balance, total_profit = place_order(SIDE_BUY, grid_price, usdt_balance, xrp_balance, total_profit)

            last_price = price
            total_value = usdt_balance + (xrp_balance * price)
            print(f"Precio: {price:.4f} | USDT: {usdt_balance:.2f} | XRP: {xrp_balance:.2f} | Valor Total: {total_value:.2f}")

            # Si se pierde todo el capital, cerrar sesión
            if total_value <= 0:
                print("\nHas perdido todo el capital. Cerrando sesión.")
                registrar_error("Capital perdido (Balance 0)", 0.0)
                guardar_sesion(0.0, False)
                generar_grafico()
                break

            time.sleep(5)

    except KeyboardInterrupt:
        total_value = usdt_balance + (xrp_balance * price)
        sesion_ganancia = total_value > (monto_inicial + balance_previo)
        guardar_sesion(total_value, sesion_ganancia)
        generar_grafico()
        print(f"\nSesión cerrada manualmente. Balance final: {total_value:.2f} USDT (Ganancia: {sesion_ganancia})")

    except Exception as e:
        total_value = usdt_balance + (xrp_balance * price)
        registrar_error(f"Error inesperado: {e}\n{traceback.format_exc()}", total_value)
        guardar_sesion(total_value, False)
        generar_grafico()
        print(f"\nERROR inesperado: {e}. Registrado en {LOG_FILE}. Reiniciando en 10s...")
        time.sleep(10)
        grid_trading()  # Reinicia el bot automáticamente

if __name__ == "__main__":
    grid_trading()

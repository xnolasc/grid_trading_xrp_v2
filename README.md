# Grid Trading Bot (Binance Testnet) – XRP/USDT

## Español

### Motivación
Este proyecto es un **ejercicio práctico de trading automatizado**, creado para simular **estrategias de Grid Trading** en Binance Testnet usando Python.  
El objetivo es **aprender cómo funcionan los bots de trading** y practicar sin arriesgar dinero real, replicando un escenario cercano a la realidad.

### ¿Qué es el Grid Trading?
El **Grid Trading** es una estrategia donde:
1. Se define un **rango de precios (mínimo y máximo)**.
2. Se divide ese rango en **niveles (grids)**.
3. El bot **coloca órdenes de compra y venta automáticamente** cada vez que el precio cruza un nivel.

Así, el bot compra barato y vende caro de forma repetitiva, generando ganancias aunque el mercado esté lateral (sin tendencia clara).  
En este bot, el rango se ajusta automáticamente cada 10 minutos usando el **mínimo y máximo de las últimas 24 horas** con un margen de 2%.

### Funcionalidades del bot
- Conexión con **Binance Testnet (operaciones virtuales)**.
- **Lectura de claves API y parámetros desde `config.json`** (seguro, no se sube a GitHub).
- **Registro de operaciones en CSV (`operaciones_grid.csv`)**.
- **Log de errores (`errores_bot.log`)** si el bot se cierra solo.
- **Generación de gráfico (`grafico_balance.png`)** al finalizar cada sesión.
- **Modo 24/7 con reconexión automática** en caso de caídas o errores inesperados.

### Requisitos
- Python 3.9+
- Librerías: `binance`, `numpy`, `matplotlib`, `requests`

Instalación:
```bash
pip install python-binance numpy matplotlib requests

git clone https://github.com/xnolasc/grid_trading_xrp_v2.git
cd grid_trading_xrp_v2

Copia y configura config.json usando la plantilla:
{
    "API_KEY": "TU_API_KEY_DE_BINANCE_TESTNET",
    "API_SECRET": "TU_API_SECRET_DE_BINANCE_TESTNET",
    "SYMBOL": "XRPUSDT",
    "GRID_LEVELS": 30,
    "TRADE_SIZE": 10,
    "FEE_RATE": 0.001
}

python3 grid_xrp_bot_v2.py

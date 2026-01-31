# MP-DH415 - Sistema di Trading Automatizzato Forex

## Indice

1. [Panoramica del Sistema](#panoramica-del-sistema)
2. [Architettura](#architettura)
3. [Struttura dei File](#struttura-dei-file)
4. [Strategia di Trading](#strategia-di-trading)
5. [Moduli Principali](#moduli-principali)
6. [Database](#database)
7. [Integrazioni Esterne](#integrazioni-esterne)
8. [Flusso di Esecuzione](#flusso-di-esecuzione)
9. [Configurazione e Deployment](#configurazione-e-deployment)
10. [API e Parametri](#api-e-parametri)
11. [Gestione del Rischio](#gestione-del-rischio)
12. [Diagrammi di Flusso](#diagrammi-di-flusso)

---

## Panoramica del Sistema

**MP-DH415** è un sistema di trading algoritmico automatizzato progettato per operare sul mercato Forex. Il sistema implementa una strategia basata su:

- **Analisi Multi-Timeframe** (Daily, H4, M15)
- **Indicatore Kijun-sen** (Ichimoku Kinko Hyo - periodo 26)
- **Zone di Supporto e Resistenza**
- **Pattern di Prezzo** (Engulfing, candele consecutive)
- **Livelli di Fibonacci** (78.6%)

### Caratteristiche Principali

| Caratteristica | Descrizione |
|----------------|-------------|
| **Coppie Forex** | 28 coppie valutarie principali e cross |
| **Timeframe** | Daily (D1), 4 ore (H4), 15 minuti (M15) |
| **Broker** | FXCM (via ForexConnect API) |
| **Esecuzione** | MetaTrader 5 |
| **Notifiche** | Slack |
| **Database** | SQLite |

---

## Architettura

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SISTEMA MP-DH415                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │    FXCM      │    │ MetaTrader 5 │    │    Slack     │          │
│  │  (Dati)      │    │ (Esecuzione) │    │ (Notifiche)  │          │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘          │
│         │                   │                   │                   │
│         ▼                   ▼                   ▼                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      martina.py                              │   │
│  │                   (Script Principale)                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│         │                   │                   │                   │
│         ▼                   ▼                   ▼                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   utils.py   │    │  db_utils.py │    │common_samples│          │
│  │  (Calcoli)   │    │  (Database)  │    │   (FXCM)     │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│                             │                                       │
│                             ▼                                       │
│                    ┌──────────────┐                                 │
│                    │   SQLite     │                                 │
│                    │   Database   │                                 │
│                    └──────────────┘                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Struttura dei File

```
MP-DH415/
├── martina.py              # Script principale di trading
├── utils.py                # Funzioni di utilità e calcoli tecnici
├── db_utils.py             # Gestione database e operazioni MT5
├── kijun.py                # Calcolo indicatore Kijun-sen
├── combined_script.py      # Orchestratore multi-coppia
├── slack_begin.py          # Inizializzazione notifiche Slack
├── cmd_utils.py            # Utility da riga di comando
├── worker.py               # API Worker per operazioni remote
├── trades.bat              # Script batch per esecuzione Windows
├── my_database.db          # Database SQLite
├── .env                    # Variabili d'ambiente (SLACK_BOT_TOKEN)
├── combined_script.spec    # Configurazione PyInstaller
│
├── common_samples/         # Libreria FXCM ForexConnect
│   ├── __init__.py
│   ├── common.py           # Parsing argomenti e utility
│   ├── OrderMonitor.py     # Monitoraggio ordini
│   ├── OrderMonitorNetting.py
│   ├── BatchOrderMonitor.py
│   └── TableListenerContainer.py
│
├── build/                  # File di build PyInstaller
└── dist/                   # Eseguibile compilato
    └── combined_script.exe
```

---

## Strategia di Trading

### Filosofia

La strategia implementa un approccio **multi-timeframe** basato su zone di supporto/resistenza validate e pattern di prezzo con entry su ritracciamento Fibonacci 78.6%.

### Fasi della Strategia

#### Fase 1: Identificazione Zone Daily (D1)

1. Calcolo della **Kijun-sen** a 26 periodi
2. Identificazione delle **zone di supporto/resistenza** basate su:
   - Pattern di inversione (candele bearish seguite da bullish per supporti)
   - Minimi/massimi significativi dell'ultimo anno
3. Validazione della zona: il prezzo deve toccare la zona dopo essere stato dall'altro lato della Kijun

#### Fase 2: Conferma su H4

1. Ricerca di zone H4 **all'interno** della zona Daily validata
2. La zona H4 deve essere anch'essa validata (tocco dopo attraversamento Kijun)
3. Verifica che la chiusura H4 sia sopra (per supporti) o sotto (per resistenze) la zona

#### Fase 3: Pattern M15

Ricerca di pattern di inversione sul timeframe M15:

**Pattern Supporto (LONG):**
```
- 2 candele ribassiste + 2 candele rialziste
- Engulfing ribassista + 2 candele rialziste
- Engulfing + Engulfing
- 2 candele rialziste + Engulfing ribassista
```

**Pattern Resistenza (SHORT):**
```
- 2 candele rialziste + 2 candele ribassiste
- Engulfing rialzista + 2 candele ribassiste
- Engulfing + Engulfing
- 2 candele ribassiste + Engulfing rialzista
```

#### Fase 4: Entry e Gestione

1. **Entry**: Al ritracciamento **Fibonacci 78.6%** del movimento di breakout
2. **Stop Loss**: Calcolato dinamicamente in base ai pips (con regole di arrotondamento)
3. **Target**: Kijun H4 (dinamico, si aggiorna)
4. **Risk/Reward minimo**: 2:1

### Regole di Stop Loss

| Pips Calcolati | Stop Loss Finale |
|----------------|------------------|
| ≤ 8 | 15 pips |
| 9-11 | 20 pips |
| 12-18 | +10 pips |
| 19-20 | 30 pips |
| 21-24 | 35 pips |
| 25-29 | 40 pips |
| 30 | 45 pips |
| 31-39 | 50 pips |
| 40 | 55 pips |
| 41-49 | 60 pips |
| 50-59 | 70 pips |
| 60-69 | 80 pips |
| 70-79 | 90 pips |
| ≥ 80 | Arrotondamento alla decina + 10 |

---

## Moduli Principali

### martina.py

**Script principale** che coordina l'intera logica di trading.

#### Funzioni Principali

```python
def main():
    # Connessione a FXCM
    # Recupero dati storici (DLY, H4, M15)
    # Esecuzione strategia
    # Gestione trade in corso
```

#### Flusso di Esecuzione

1. **Parsing argomenti** (login, password, strumento, date)
2. **Connessione FXCM** via ForexConnect
3. **Download dati storici** su 3 timeframe
4. **Verifica trade esistenti**:
   - Trade "IN RETEST" → gestisci retest
   - Trade "IN PROGRESS" → gestisci posizione aperta
5. **Ricerca nuove opportunità**:
   - Zone Daily → Zone H4 → Pattern M15 → Entry
6. **Notifica Slack** dello stato
7. **Pulizia ordini** obsoleti

### utils.py

**Modulo di calcolo** con tutte le funzioni matematiche e di analisi tecnica.

#### Funzioni Chiave

| Funzione | Descrizione |
|----------|-------------|
| `format_history()` | Formatta i dati OHLCV da FXCM |
| `calculate_kijun()` | Calcola la Kijun-sen a 26 periodi |
| `get_zones()` | Identifica zone di supporto/resistenza |
| `validate_support()` | Valida una zona di supporto |
| `validate_resistence()` | Valida una zona di resistenza |
| `get_pattern_m15_SUP()` | Cerca pattern bullish su M15 |
| `get_pattern_m15_RES()` | Cerca pattern bearish su M15 |
| `fibonacci_78_6()` | Calcola il livello 78.6% di Fibonacci |
| `calculate_risk_reward_ratio()` | Calcola il rapporto R:R |
| `calculate_stop_loss_LONG/SHORT()` | Calcola lo stop loss |
| `calculate_target_price_LONG/SHORT()` | Calcola il target |
| `process_trades_LONG()` | Gestisce trade long in corso |
| `process_trades_SHORT()` | Gestisce trade short in corso |

#### Calcolo Kijun-sen

```python
def calculate_kijun(history, kijun_period):
    """
    Kijun-sen = (Highest High + Lowest Low) / 2
    Calcolato sugli ultimi 26 periodi
    """
    for i in range(kijun_period, len(history)):
        highestBidHigh = max(h["BidHigh"] for h in history[i-kijun_period:i])
        lowestBidLow = min(h["BidLow"] for h in history[i-kijun_period:i])
        kijun_value = (highestBidHigh + lowestBidLow) / 2
```

#### Identificazione Zone

```python
def get_zones(history, kijun_h4, index, timerange, type, dlyZoneDate):
    """
    Identifica zone di supporto se prezzo < Kijun
    Identifica zone di resistenza se prezzo > Kijun
    
    Criteri per zona di supporto:
    - Candela bearish seguita da candela bullish
    - Minimo locale sotto le chiusure precedenti
    
    Restituisce: rectX1, rectX2, rectY1, rectY2, final_zones, zone_type
    """
```

### db_utils.py

**Gestione database SQLite** e **integrazione MetaTrader 5**.

#### Operazioni Database

| Funzione | Descrizione |
|----------|-------------|
| `initialize_db()` | Crea tabella trades |
| `check_in_progress_trade()` | Verifica trade aperti |
| `check_in_retest_trade()` | Verifica trade in attesa retest |
| `upsert_order_waiting_retest()` | Inserisce/aggiorna ordine pendente |
| `update_trade_in_progress()` | Aggiorna stato a "IN PROGRESS" |
| `update_trade_closed()` | Chiude un trade |
| `update_trade_stoploss()` | Aggiorna stop loss |
| `update_trade_target()` | Aggiorna target |

#### Operazioni MetaTrader 5

| Funzione | Descrizione |
|----------|-------------|
| `mt5_place_order()` | Piazza ordine pendente |
| `mt5_close_order()` | Cancella ordine pendente |
| `mt5_close_positions()` | Chiude posizioni aperte |
| `close_mt5_partial_positions()` | Chiude posizioni parziali |
| `calculate_trade_size()` | Calcola size posizione (0.5% rischio) |

#### Calcolo Size Posizione

```python
def calculate_trade_size(symbol, entry_price, risk_per_trade, stop_loss_price):
    """
    Calcola la size della posizione basandosi su:
    - Balance fisso: 10,000
    - Rischio per trade: 0.5%
    
    Formula:
    position_size = (balance * risk_per_trade) / (ticks_at_risk * tick_value)
    """
    balance = 10000.0
    risk_per_trade = 0.005  # 0.5%
    ticks_at_risk = abs(entry_price - stop_loss_price) / tick_size
    position_size = (balance * risk_per_trade) / (ticks_at_risk * tick_value)
```

### combined_script.py

**Orchestratore** che esegue `martina.py` su tutte le 28 coppie valutarie.

```python
params_list = [
    # 28 configurazioni per ogni coppia forex
    ["-l", "LOGIN", "-p", "PASSWORD", "-u", "URL", "-i", "EUR/USD", ...],
    ["-l", "LOGIN", "-p", "PASSWORD", "-u", "URL", "-i", "AUD/USD", ...],
    # ... altre 26 coppie
]

for params in params_list:
    run_martina(params)
    time.sleep(1)  # Delay tra esecuzioni
```

---

## Database

### Schema Tabella `trades`

```sql
CREATE TABLE trades (
    pair TEXT,                    -- Coppia valutaria (es. "EUR/USD")
    status TEXT,                  -- Stato: IN RETEST, IN PROGRESS, CLOSED
    trade_type TEXT,              -- Tipo: FULL, PARTIAL
    entry_date TEXT,              -- Data entry
    close_date TEXT,              -- Data chiusura
    entry_price REAL,             -- Prezzo di entry
    entry_price_index INTEGER,    -- Indice candela entry
    stop_loss REAL,               -- Stop loss
    target REAL,                  -- Target price
    direction TEXT,               -- LONG o SHORT
    initial_risk_reward REAL,     -- R:R iniziale
    final_risk_reward REAL,       -- R:R finale
    profit TEXT,                  -- Profitto
    result TEXT,                  -- TARGET o STOP LOSS
    zones_rectX1_DLY TEXT,        -- Data zona Daily
    zones_rectY1_DLY REAL,        -- Livello sup. zona Daily
    zones_rectY2_DLY REAL,        -- Livello inf. zona Daily
    zones_rectX1_H4 TEXT,         -- Data zona H4
    zones_rectY1_H4 REAL,         -- Livello sup. zona H4
    zones_rectY2_H4 REAL,         -- Livello inf. zona H4
    pattern_x1 TEXT,              -- Data pattern M15
    pattern_y1 REAL,              -- Livello sup. pattern
    pattern_y2 REAL,              -- Livello inf. pattern
    breakup_date TEXT             -- Data breakout pattern
);
```

### Stati del Trade

```
┌─────────────┐     Entry          ┌─────────────┐
│  IN RETEST  │ ─────────────────► │ IN PROGRESS │
└─────────────┘                    └─────────────┘
       │                                  │
       │ No Retest                        │ Target/SL
       │ Zone Broken                      │
       ▼                                  ▼
┌─────────────┐                    ┌─────────────┐
│   CLOSED    │ ◄────────────────  │   CLOSED    │
│ (No Trade)  │                    │ (Win/Loss)  │
└─────────────┘                    └─────────────┘
```

---

## Integrazioni Esterne

### FXCM (ForexConnect)

**Uso**: Download dati storici OHLCV

```python
from forexconnect import ForexConnect, fxcorepy

with ForexConnect() as fx:
    fx.login(user_id, password, url, connection, session_id, pin)
    
    # Download dati
    history_DLY = fx.get_history(instrument, 'D1', date_from, date_to)
    history_H4 = fx.get_history(instrument, 'H4', date_from, date_to)
    history_m15 = fx.get_history(instrument, 'm15', date_from, date_to)
```

### MetaTrader 5

**Uso**: Esecuzione ordini

```python
import MetaTrader5 as mt5

# Inizializzazione
mt5.initialize()

# Piazzamento ordine pendente
request = {
    "action": mt5.TRADE_ACTION_PENDING,
    "symbol": symbol,
    "volume": lot,
    "type": mt5.ORDER_TYPE_BUY_LIMIT,  # o SELL_LIMIT
    "price": entry_price,
    "sl": stop_loss,
    "tp": target,
    "deviation": 20,
    "type_time": mt5.ORDER_TIME_GTC,
}
result = mt5.order_send(request)

# Modifica SL/TP
request = {
    "action": mt5.TRADE_ACTION_SLTP,
    "sl": new_sl,
    "tp": new_tp,
    "position": position.ticket
}
mt5.order_send(request)
```

### Slack

**Uso**: Notifiche real-time

```python
from slack_sdk import WebClient

def send_slack_message(channel, message):
    client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
    response = client.chat_postMessage(
        channel=channel,
        text=message
    )
```

**Messaggi tipici**:
- `:ballot_box_with_check: In attesa della zona H4 su: EUR/USD`
- `:ballot_box_with_check: In attesa di un pattern: EUR/USD`
- `:ballot_box_with_check: A mercato: EUR/USD`

---

## Flusso di Esecuzione

### Flusso Principale

```
                    ┌─────────────────────┐
                    │  combined_script.py │
                    │    (Orchestratore)  │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Per ogni coppia   │
                    │   forex (28 total)  │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    martina.py       │
                    │  (per coppia)       │
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Trade IN RETEST │  │Trade IN PROGRESS│  │ Nuova Ricerca   │
│    esistente?   │  │   esistente?    │  │   opportunità   │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                     │
         ▼                    ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│process_trade_   │  │ process_trades_ │  │  Zone DLY →     │
│  in_retest()    │  │  LONG/SHORT()   │  │  Zone H4 →      │
│                 │  │                 │  │  Pattern M15    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Dettaglio Ricerca Opportunità

```
1. DAILY TIMEFRAME
   ├── Calcola Kijun H4 (26 periodi)
   ├── Determina direzione (Close vs Kijun)
   │   ├── Close < Kijun → Cerca SUPPORTI (LONG)
   │   └── Close > Kijun → Cerca RESISTENZE (SHORT)
   ├── Identifica zone nell'ultimo anno
   └── Valida zone (tocco dopo attraversamento Kijun)
   
2. H4 TIMEFRAME
   ├── Cerca zone dentro la zona Daily validata
   ├── Verifica chiusura H4 rispetto alla zona
   └── Valida zona H4
   
3. M15 TIMEFRAME
   ├── Cerca pattern di inversione
   │   ├── 2+2 candele
   │   ├── Engulfing + 2 candele
   │   └── Engulfing + Engulfing
   └── Verifica breakout pattern
   
4. ENTRY
   ├── Calcola Fibonacci 78.6% del movimento
   ├── Calcola Stop Loss (regole pips)
   ├── Calcola Target (Kijun H4)
   ├── Verifica R:R ≥ 2
   └── Piazza ordine pendente su MT5
```

---

## Configurazione e Deployment

### Modalità Simulazione (SIMULATION_MODE)

Il sistema supporta una **modalità simulazione** per lo sviluppo su macchine senza MetaTrader 5 installato (es. Mac).

#### Configurazione

In `db_utils.py`, modificare la variabile:

```python
# True  = Sviluppo su Mac (senza MT5) - scrive segnali su SQLite
# False = Produzione su Windows (con MT5) - esegue ordini reali
SIMULATION_MODE = True
```

#### Funzionamento

Quando `SIMULATION_MODE = True`:
- **Nessuna chiamata a MT5** viene effettuata
- I segnali di trading vengono **registrati su SQLite** in 3 tabelle:
  - `mt5_signals` - Ordini che sarebbero stati piazzati
  - `mt5_modifications` - Modifiche a SL/TP
  - `mt5_closures` - Chiusure di posizioni/ordini
- I calcoli (position size, pips, ecc.) usano **valori simulati**

#### Tabelle dei Segnali

```sql
-- Segnali di trading (ordini pendenti)
CREATE TABLE mt5_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    signal_type TEXT,        -- PLACE_ORDER
    pair TEXT,               -- EUR/USD
    symbol TEXT,             -- EURUSD
    action TEXT,             -- PENDING
    order_type TEXT,         -- BUY_LIMIT, SELL_LIMIT
    volume REAL,             -- Lot size
    price REAL,              -- Entry price
    stop_loss REAL,
    take_profit REAL,
    deviation INTEGER,
    comment TEXT,            -- FULL, PARTIAL
    status TEXT,             -- PENDING
    ticket INTEGER,
    processed INTEGER        -- 0/1
);

-- Modifiche agli ordini
CREATE TABLE mt5_modifications (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    pair TEXT,
    action TEXT,             -- UPDATE_SL, UPDATE_TARGET, UPDATE_TARGET_ALL
    old_sl REAL, new_sl REAL,
    old_tp REAL, new_tp REAL,
    position_ticket INTEGER,
    comment TEXT,
    processed INTEGER
);

-- Chiusure
CREATE TABLE mt5_closures (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    pair TEXT,
    action TEXT,             -- CANCEL_PENDING_ORDERS, CLOSE_PARTIAL_POSITIONS, etc.
    volume REAL,
    close_price REAL,
    comment TEXT,
    processed INTEGER
);
```

#### Comandi per Visualizzare i Segnali

```bash
# Mostra gli ultimi segnali registrati
python cmd_utils.py -c signals

# Pulisce tutte le tabelle dei segnali
python cmd_utils.py -c clear_signals
```

#### Output in Modalità Simulazione

```
============================================================
  RUNNING IN SIMULATION MODE (No MT5)
  Signals will be logged to SQLite database
============================================================
[SIMULATION] Order would be placed: LONG EURUSD @ 1.08500
[SIMULATION] SL: 1.08200, TP: 1.09000, Lot: 0.15
[SIMULATION] Signal logged: PLACE_ORDER - EUR/USD - PENDING @ 1.085
```

### Requisiti

**Modalità Simulazione (Mac/Linux):**
```
Python 3.7+
Account FXCM (Demo o Real) - per dati storici
Slack Workspace con Bot Token (opzionale)
```

**Modalità Produzione (Windows):**
```
Python 3.7+
MetaTrader 5 (installato e configurato)
Account FXCM (Demo o Real)
Slack Workspace con Bot Token
```

### Dipendenze Python

```
pandas
MetaTrader5
forexconnect
slack_sdk
python-dotenv
certifi
requests
```

### File .env

```env
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
```

### Esecuzione

**Singola coppia:**
```bash
python martina.py -l LOGIN -p PASSWORD -u http://www.fxcorporate.com/Hosts.jsp \
    -i "EUR/USD" -c "Demo" -datefrom "04.10.2022 00:00:00" -session Trade
```

**Tutte le coppie:**
```bash
python combined_script.py
```

**Windows (batch):**
```bash
trades.bat
```

### Build Eseguibile

```bash
pyinstaller --onefile combined_script.py
```

---

## API e Parametri

### Parametri martina.py

| Parametro | Descrizione | Obbligatorio |
|-----------|-------------|--------------|
| `-l` | Login FXCM | Sì |
| `-p` | Password FXCM | Sì |
| `-u` | URL server FXCM | Sì |
| `-i` | Strumento (es. EUR/USD) | Sì |
| `-c` | Tipo connessione (Demo/Real) | Sì |
| `-datefrom` | Data inizio storico | No |
| `-dateto` | Data fine storico | No |
| `-session` | Tipo sessione (Trade/BT/BTLOG) | No |
| `-pin` | PIN (se richiesto) | No |
| `-quotescount` | Max barre da scaricare | No |

### cmd_utils.py

```bash
# Verifica balance MT5
python cmd_utils.py -c balance

# Pulisci tabella trades
python cmd_utils.py -c clean

# Aggiorna posizione MT5
python cmd_utils.py -c update
```

### worker.py (API REST)

```python
# Endpoint per apertura posizione
POST http://3.70.230.123:8000/api/open_position/

# Payload
{
    "pair": "EUR/USD",
    "operation": "open",
    "volume": 1.0,
    "direction": "long"
}
```

---

## Gestione del Rischio

### Regole di Risk Management

1. **Rischio per Trade**: 0.5% del capitale (su base fissa 10,000)
2. **Risk/Reward Minimo**: 2:1
3. **Trade Parziale**: Chiusura 50% posizione a R:R 1:1
4. **Trailing Stop**:
   - A R:R 3:1 → SL spostato a R:R 1
   - A R:R 4:1 → SL spostato a R:R 2
   - E così via...

### Gestione Breakeven

```python
if history['BidHigh'] >= target_1_1:  # Target 1:1 raggiunto
    # Chiudi posizione parziale
    update_trade_closed(pair, 'TARGET', 'PARTIAL', date, 1)
    close_mt5_partial_positions(pair)
    
    # Sposta SL a breakeven
    update_trade_stoploss(pair, entry_price, index, 0)
```

### Trailing Stop Dinamico

```python
def get_rr_range(risk_reward):
    """
    Genera livelli per trailing stop
    Es: R:R 5 → [3, 4] (sposta SL a 1, poi a 2)
    """
    if risk_reward > 3:
        return list(range(3, math.ceil(risk_reward)))
    return []
```

### Chiusura Forzata

Il trade viene chiuso al prezzo corrente se:
- La zona H4 viene "rotta" (prezzo chiude oltre)
- La zona Daily viene "rotta"

```python
if h4BidClose < zone_rectY1_H4:  # Zona H4 rotta
    update_trade_target_ALL(pair, entry_price, 0)  # Target = Entry (breakeven)
```

---

## Diagrammi di Flusso

### Processo di Validazione Zona

```
           ┌─────────────────┐
           │  Zona Trovata   │
           │   (DLY o H4)    │
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────┐
           │ Prezzo tocca la │
           │   zona dopo     │
           │ aver attraversato│
           │   la Kijun?     │
           └────────┬────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
        Sì                    No
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌─────────────────┐
│  ZONA VALIDA    │   │ ZONA NON VALIDA │
└─────────────────┘   └─────────────────┘
```

### Processo Entry Trade

```
    ┌─────────────────┐
    │ Pattern trovato │
    │   e validato    │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Breakout pattern│
    │  (Close oltre   │
    │   pattern_Y1)   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Calcola Entry   │
    │ Fib 78.6% del   │
    │   movimento     │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  Calcola SL     │
    │  (regole pips)  │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Calcola Target  │
    │   (Kijun H4)    │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │   R:R ≥ 2 ?     │
    └────────┬────────┘
             │
    ┌────────┴────────┐
    │                 │
   Sì                No
    │                 │
    ▼                 ▼
┌─────────┐    ┌─────────────┐
│ ORDINE  │    │ NO TRADE    │
│ PENDENTE│    │ Chiudi tutto│
│  su MT5 │    └─────────────┘
└─────────┘
```

### Ciclo di Vita Trade

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  ┌─────────┐   Breakout    ┌───────────┐                    │
│  │ Pattern │ ───────────►  │ IN RETEST │                    │
│  │ Trovato │               │ (Ordine   │                    │
│  └─────────┘               │ Pendente) │                    │
│                            └─────┬─────┘                    │
│                                  │                          │
│                    ┌─────────────┼─────────────┐            │
│                    │             │             │            │
│              Prezzo tocca   Kijun tocca    Zona rotta       │
│               entry         prima del      prima del        │
│                             retest         retest           │
│                    │             │             │            │
│                    ▼             ▼             ▼            │
│             ┌───────────┐  ┌─────────┐   ┌─────────┐       │
│             │    IN     │  │ CLOSED  │   │ CLOSED  │       │
│             │ PROGRESS  │  │(No Win) │   │(No Win) │       │
│             └─────┬─────┘  └─────────┘   └─────────┘       │
│                   │                                         │
│       ┌───────────┼───────────┐                            │
│       │           │           │                            │
│    Target      Stop Loss   Zona Rotta                      │
│   raggiunto    raggiunto   (Breakeven)                     │
│       │           │           │                            │
│       ▼           ▼           ▼                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                       │
│  │ CLOSED  │ │ CLOSED  │ │ CLOSED  │                       │
│  │  (WIN)  │ │ (LOSS)  │ │(B.E./?) │                       │
│  └─────────┘ └─────────┘ └─────────┘                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Coppie Forex Supportate

Il sistema opera su 28 coppie valutarie:

### Major Pairs
- EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, NZD/USD, USD/CAD

### Cross Pairs
- EUR/GBP, EUR/JPY, EUR/AUD, EUR/CAD, EUR/NZD, EUR/CHF
- GBP/JPY, GBP/AUD, GBP/CAD, GBP/NZD, GBP/CHF
- AUD/JPY, AUD/CAD, AUD/NZD, AUD/CHF
- NZD/JPY, NZD/CAD, NZD/CHF
- CAD/JPY, CAD/CHF, CHF/JPY

---

## Note Tecniche

### Gestione Timezone

I dati FXCM sono in UTC. Il sistema gestisce:
- Esclusione sabato per timeframe Daily
- Gestione fascia oraria 21:00-01:00 per allineamento candele

### Precisione Prezzi

```python
symbol_info = mt5.symbol_info(symbol)
price_precision = symbol_info.digits
adjusted_entry_price = round(entry_price, price_precision)
```

### Gestione Errori

```python
try:
    # Operazioni trading
except Exception as e:
    common_samples.print_exception(e)
```

### Logging

Il sistema utilizza logging su file (`martina.py.log`) e console.

---

## Changelog e Versioning

Il sistema è in fase di sviluppo attivo. Le credenziali visibili nel codice sono per ambiente Demo FXCM.

---

## Autore

Sistema sviluppato per trading automatizzato sul mercato Forex con strategia multi-timeframe basata su Ichimoku e pattern di prezzo.

---

*Documentazione generata automaticamente dall'analisi del codice sorgente MP-DH415.*

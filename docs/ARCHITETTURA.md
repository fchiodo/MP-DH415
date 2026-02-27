# MP-DH415 — Architettura del Progetto

Documento di architettura generato dall'analisi del codebase. Descrive componenti, flussi dati e relazioni tra backend, frontend, API e integrazioni esterne.

---

## Indice

1. [Panoramica](#1-panoramica)
2. [Architettura ad alto livello](#2-architettura-ad-alto-livello)
3. [Backend (Trading Bot)](#3-backend-trading-bot)
4. [API (Flask)](#4-api-flask)
5. [Frontend (React Dashboard)](#5-frontend-react-dashboard)
6. [Database](#6-database)
7. [Integrazioni esterne](#7-integrazioni-esterne)
8. [Flussi di dati principali](#8-flussi-di-dati-principali)
9. [Struttura delle cartelle](#9-struttura-delle-cartelle)
10. [Stack tecnologico](#10-stack-tecnologico)
11. [Modalità simulazione vs produzione](#11-modalità-simulazione-vs-produzione)

---

## 1. Panoramica

**MP-DH415** (Trading Bot Pro) è un sistema di **trading algoritmico Forex** che combina:

- **Bot Python** per analisi multi-timeframe, segnali e (opzionale) esecuzione ordini
- **Dashboard React** per monitoraggio, configurazione e log in tempo reale
- **API Flask** come ponte tra UI e dati/controllo del bot
- **SQLite** come unico database (trade, segnali simulazione, activity log)

### Funzionalità principali

| Area | Funzionalità |
|------|--------------|
| **Strategia** | Multi-timeframe (D1, H4, M15), Kijun-sen, zone S/R, pattern (engulfing, 2+2), Fibonacci 78.6% |
| **Esecuzione** | MetaTrader 5 (produzione) o solo log su SQLite (simulazione) |
| **Dati** | FXCM ForexConnect per storico OHLCV |
| **Notifiche** | Slack (eventi trade e messaggi di stato) |
| **UI** | Dashboard, Performance, Simulation, Settings, Start/Stop bot, Activity Log (SSE) |

---

## 2. Architettura ad alto livello

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              MP-DH415 - Sistema                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│   │   FXCM      │     │ MetaTrader5 │     │   Slack     │     │   React     │  │
│   │ (Dati OHLC) │     │ (Ordini)    │     │ (Notifiche) │     │  Dashboard  │  │
│   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘  │
│          │                   │                   │                   │          │
│          │                   │                   │                   │ HTTP/SSE│
│          ▼                   ▼                   ▼                   ▼          │
│   ┌──────────────────────────────────────────────────────────────────────────┐  │
│   │                         backend/ (Python)                                  │  │
│   │   martina.py ◄── bot_runner.py (loop) / combined_script.py (batch)     │  │
│   │        │                                                                   │  │
│   │        ├── utils.py      (calcoli, zone, pattern, SL/TP, process_trades)  │  │
│   │        ├── db_utils.py   (SQLite, MT5/simulazione, activity_log)          │  │
│   │        ├── kijun.py      (Kijun-sen)                                      │  │
│   │        └── common_samples/ (ForexConnect, ordini FXCM)                     │  │
│   └──────────────────────────────────────────────────────────────────────────┘  │
│          │                                                                       │
│          │  Legge/scrive                                                         │
│          ▼                                                                       │
│   ┌──────────────────────────────────────────────────────────────────────────┐  │
│   │                    frontend/api/app.py (Flask)                             │  │
│   │   REST: /api/config, /api/trades, /api/performance, /api/signals,         │  │
│   │         /api/bot/start|stop|status, /api/logs, /api/test/fxcm|slack       │  │
│   │   SSE:  /api/logs/stream (activity log in tempo reale)                    │  │
│   └──────────────────────────────────────────────────────────────────────────┘  │
│          │                              │                                         │
│          │  Legge .env, DB              │  Avvia/ferma bot (subprocess)          │
│          ▼                              ▼                                         │
│   ┌──────────────────┐         ┌──────────────────┐                             │
│   │  my_database.db   │         │  bot_runner.py    │                             │
│   │  (SQLite)        │         │  (subprocess)      │                             │
│   └──────────────────┘         └──────────────────┘                             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

- **React** parla solo con l’API Flask (localhost:5001).
- **Bot** (martina.py) usa FXCM, opzionalmente MT5 e Slack, e scrive su SQLite (e activity_log).
- **Flask** espone dati e comandi (config, trades, performance, signals, bot start/stop, logs, SSE).

---

## 3. Backend (Trading Bot)

### 3.1 Ruolo dei moduli

| Modulo | Ruolo |
|--------|--------|
| **martina.py** | Script principale: connessione FXCM, download D1/H4/M15, gestione trade IN RETEST / IN PROGRESS, ricerca nuove zone/pattern, entry (Fib 78.6), notifiche Slack. |
| **bot_runner.py** | Esecuzione continua: legge `ACTIVE_PAIRS` da .env, in loop lancia `martina.py` per ogni coppia con `--from-runner`, intervallo configurabile (`--interval`). Scrive su activity_log. |
| **combined_script.py** | Esecuzione batch: lancia martina.py per una lista fissa di 28 coppie (una dopo l’altra). |
| **utils.py** | Calcoli e logica: `format_history`, `calculate_kijun`, `get_zones` / `get_resistences`, `validate_support` / `validate_resistence`, `get_pattern_m15_SUP/RES`, `fibonacci_78_6`, risk/reward, SL/TP LONG/SHORT, `process_trades_LONG/SHORT`, `process_trade_in_retest`. |
| **db_utils.py** | Persistenza e esecuzione: init DB, trades (CRUD), activity_log (init, add, get, clear), segnali simulazione (mt5_signals, mt5_modifications, mt5_closures), wrapper MT5 (place_order, close_order, close_positions, update SL/TP) o log in simulazione. |
| **kijun.py** | Calcolo Kijun-sen (Ichimoku, periodo 26). |
| **cmd_utils.py** | CLI: balance, clean, update, signals, clear_signals. |
| **common_samples/** | Wrapper FXCM ForexConnect: login, get_history, parsing argomenti, OrderMonitor, BatchOrderMonitor. |

### 3.2 Flusso logico in martina.py

1. Parse args (strumento, date, session, ecc.).
2. Init activity_log DB; se `SIMULATION_MODE`, init tabelle segnali.
3. Login FXCM, download D1, H4, M15, format e calcolo Kijun H4.
4. **Trade IN RETEST?** → `process_trade_in_retest` (aggiorna ordine/retest o chiude).
5. **Trade IN PROGRESS?** → `process_trades_LONG` o `process_trades_SHORT` (target, SL, partial, zone DLY/H4 rotta).
6. Se non bloccato da 4–5: **ricerca nuove opportunità**  
   - Daily: `get_zones` → validazione supporto/resistenza  
   - H4: zone dentro zona Daily, validate  
   - M15: `get_pattern_m15_SUP` / `get_pattern_m15_RES` → breakout → entry Fib 78.6, SL/TP, R:R ≥ 2 → `upsert_order_waiting_retest` (e MT5 o log simulazione).
7. Slack summary, pulizia ordini obsoleti (`close_mt5_orders_already_processed`).

### 3.3 Punti di integrazione

- **FXCM**: solo in `martina.py` (e test in API), tramite `forexconnect` e `common_samples`.
- **MT5**: solo in `db_utils.py` (import condizionale se non `SIMULATION_MODE`).
- **Slack**: `db_utils.send_slack_message` (e in utils esiste una copia; usata dal bot).
- **Database**: tutto in `db_utils.py`; path DB = `parent.parent / 'my_database.db'` (root progetto).

---

## 4. API (Flask)

**File**: `frontend/api/app.py`  
**Porta**: 5001, host `0.0.0.0`  
**CORS**: permessi per localhost:3000, 3001, 127.0.0.1.

### 4.1 Endpoint per area

| Area | Metodo | Endpoint | Descrizione |
|------|--------|----------|-------------|
| Config | GET/PUT | `/api/config` | Lettura/aggiornamento config da .env (FXCM, risk, Slack, activePairs). |
| Trades | GET | `/api/trades` | Tutti i trade (attivi/chiusi). |
| Trades | GET | `/api/trades/active` | Trade attivi formattati per la tabella coppie (status, direction, entryPrice, riskReward). |
| Trades | GET | `/api/trades/stats` | Statistiche: activeTrades, waitingRetest, todayProfit, totalTrades, winRate. |
| Performance | GET | `/api/performance` | Statistiche performance, recentTrades, pairPerformance, equityCurve (parametri: period, direction). |
| Signals | GET | `/api/signals` | Segnali simulazione (mt5_signals, mt5_modifications, mt5_closures). |
| Signals | POST | `/api/signals/clear` | Svuota le tre tabelle segnali. |
| Bot | GET | `/api/bot/status` | Stato bot (running/stopped, pid, simulationMode, startTime). |
| Bot | POST | `/api/bot/start` | Avvia bot (subprocess `bot_runner.py`, interval/pairs da body o env). |
| Bot | POST | `/api/bot/stop` | Termina processo bot. |
| Test | POST | `/api/test/fxcm` | Test connessione FXCM (credenziali da body o env). |
| Test | POST | `/api/test/slack` | Test connessione Slack. |
| Health | GET | `/api/health` | Stato API, esistenza DB e .env. |
| Logs | GET | `/api/logs` | Ultimi N log (parametro limit, include_debug per TRADER). |
| Logs | GET | `/api/logs/stream` | **SSE**: stream in tempo reale dei nuovi activity_log (parametro include_debug). |
| Logs | POST | `/api/logs/clear` | Svuota activity_log. |
| Logs | POST | `/api/logs/add` | Inserisce un log (type, message, pair, details). |

### 4.2 Database e .env

- **DB**: `Path(__file__).resolve().parent.parent.parent / 'my_database.db'` (root repo).
- **.env**: stesso parent della root, cioè root repo.  
Flask legge/scrive sia il DB sia il .env (es. `set_key` per aggiornare la config).

---

## 5. Frontend (React Dashboard)

### 5.1 Stack

- **React 18**, **Vite**, **React Router 6**
- **Tailwind CSS** (theme dark/light)
- Nessun backend Node: i dati arrivano solo dall’API Flask (porta 5001)

### 5.2 Struttura sorgente

```
frontend/src/
├── App.jsx                 # Routes: /, /pair/:symbol, /settings, /performance, /simulation
├── main.jsx
├── index.css
├── context/
│   └── AppContext.jsx      # Stato globale: theme, sidebar, bot, trades, stats, activityLogs, SSE
├── hooks/
│   └── useApi.js           # fetch generico verso API (trades, signals, performance, bot start/stop)
├── components/
│   ├── layout/
│   │   ├── Layout.jsx      # Layout con sidebar + outlet
│   │   ├── Sidebar.jsx
│   │   └── Header.jsx
│   ├── dashboard/
│   │   ├── PairsTable.jsx  # Tabella coppie attive
│   │   └── ActivityLog.jsx # Lista log + toggle debug, SSE
│   └── common/
│       ├── Button.jsx
│       └── StatsCard.jsx
└── pages/
    ├── Dashboard.jsx       # Overview: stats, tabella coppie, activity log
    ├── PairDetail.jsx      # Dettaglio singola coppia
    ├── Settings.jsx        # Config FXCM, risk, Slack, coppie attive, test connessioni
    ├── Performance.jsx     # Statistiche, recent trades, pair performance, equity curve
    └── Simulation.jsx      # Segnali MT5 (simulazione)
```

### 5.3 Stato e dati (AppContext)

- **Theme**: dark/light, persistito in `localStorage`.
- **Bot**: `botStatus` (running/stopped), `startBot` / `stopBot` via `/api/bot/start` e `/api/bot/stop`.
- **Trades**: `activeTrades` da `/api/trades/active`, `fetchTrades` (anche periodica quando bot running).
- **Stats**: da `/api/trades/stats`, refresh insieme ai trades.
- **Activity Log**:
  - Fetch iniziale: `/api/logs?limit=500`.
  - **SSE**: `EventSource` su `/api/logs/stream` per aggiornamento in tempo reale.
  - Toggle “include debug”: ri-fetch e riconnessione SSE con `include_debug=true`.
- **Config**: Settings legge/scrive tramite `/api/config` (GET/PUT).

L’API base usata dal frontend è definita in `AppContext` (`API_URL = 'http://localhost:5001'`) e in `useApi.js` (`VITE_API_URL` o localhost:5001).

---

## 6. Database

**File unico**: `my_database.db` (root del progetto), SQLite.

### 6.1 Tabelle principali

| Tabella | Scopo |
|---------|--------|
| **trades** | Trade aperti e chiusi: pair, status (IN RETEST, IN PROGRESS, CLOSED), trade_type (FULL, PARTIAL), entry/close date, entry_price, stop_loss, target, direction, initial/final_risk_reward, profit, result (TARGET, STOP LOSS), zone DLY/H4 e pattern (rectX1/Y1/Y2), breakup_date, ecc. |
| **activity_logs** | Log per la UI: id, timestamp, type (INFO, SUCCESS, WARNING, ERROR, SYSTEM, TRADE, SIGNAL, TRADER), message, pair, details. Usata da bot (db_utils), API (logs + SSE) e opzionalmente da bot_runner/Flask per start/stop. |
| **mt5_signals** | Simulazione: ordini che sarebbero stati inviati a MT5 (timestamp, pair, symbol, action, order_type, volume, price, stop_loss, take_profit, comment, status, ticket, processed). |
| **mt5_modifications** | Simulazione: modifiche SL/TP (pair, action, old_sl, new_sl, old_tp, new_tp, position_ticket, comment). |
| **mt5_closures** | Simulazione: chiusure ordini/posizioni (pair, action, volume, close_price, comment). |

### 6.2 Chi scrive/legge

- **Backend (martina, bot_runner, db_utils)**: inizializza e scrive su tutte le tabelle; legge trades e activity_log.
- **Flask**: legge tutte; scrive su `activity_logs` (e in start/stop bot può inserire log); per clear segnali scrive (DELETE) su mt5_*.

---

## 7. Integrazioni esterne

| Sistema | Uso | Dove |
|---------|-----|------|
| **FXCM ForexConnect** | Dati storici OHLC (D1, H4, M15) e login | martina.py, common_samples; test in `/api/test/fxcm`. |
| **MetaTrader 5** | Ordini pendenti, modifiche SL/TP, chiusura posizioni | db_utils.py (solo se `SIMULATION_MODE = False`). |
| **Slack** | Messaggi di stato e notifiche trade | db_utils.send_slack_message (e analoga in utils); test in `/api/test/slack`. |

Credenziali e flag (FXCM, Slack, ACTIVE_PAIRS, RISK_*, REFERENCE_BALANCE, ecc.) sono in `.env`; l’API espone lettura/scrittura tramite `/api/config`.

---

## 8. Flussi di dati principali

### 8.1 Avvio bot dalla UI

1. Utente clicca “Start” in Dashboard.
2. Frontend chiama `POST /api/bot/start` (body opzionale: interval, pairs).
3. Flask avvia subprocess: `python2 backend/bot_runner.py --interval N [--pairs ...]`.
4. bot_runner inizializza DB activity_log (e segnali se simulazione), poi in loop per ogni coppia in ACTIVE_PAIRS esegue `martina.py --from-runner`.
5. martina.py per ogni run: FXCM → logica trade → aggiornamenti su DB (trades, activity_log, eventualmente mt5_*).
6. Dashboard riceve nuovi log via SSE (`/api/logs/stream`) e aggiorna stats/trades con polling (es. ogni 10s quando bot running).

### 8.2 Activity log in tempo reale

1. Bot (o API) chiama `add_activity_log()` in db_utils → INSERT in `activity_logs`.
2. Client React ha EventSource aperto su `/api/logs/stream`.
3. Flask in loop (polling DB ogni ~0.5s) invia solo righe con `id > last_id` (e opzionalmente esclude type TRADER).
4. Client riceve eventi SSE e aggiorna `activityLogs` nello stato (prepend, max 500).

### 8.3 Configurazione

1. Settings carica `GET /api/config` → legge .env e restituisce fxcm, risk, slack, activePairs.
2. Salvataggio: `PUT /api/config` con stesso shape → Flask usa `set_key(ENV_PATH, ...)` e ricarica dotenv.
3. Test FXCM/Slack: `POST /api/test/fxcm` e `POST /api/test/slack` (credenziali da body o env).

---

## 9. Struttura delle cartelle

```
MP-DH415/
├── .env                    # Credenziali e config (non in git)
├── .env.example
├── my_database.db         # SQLite (generato a runtime)
├── README.md
├── commands.md
├── supabase.md
│
├── backend/               # Trading bot Python
│   ├── martina.py         # Script principale
│   ├── bot_runner.py       # Loop continuo (coppie da ACTIVE_PAIRS)
│   ├── combined_script.py  # Batch 28 coppie
│   ├── utils.py           # Calcoli, zone, pattern, gestione trade
│   ├── db_utils.py        # DB, MT5/simulazione, activity log, Slack
│   ├── kijun.py
│   ├── cmd_utils.py       # CLI (balance, clean, signals, clear_signals, update)
│   ├── slack_begin.py
│   ├── worker.py
│   ├── test_simulation.py
│   ├── requirements.txt
│   └── common_samples/    # FXCM ForexConnect
│       ├── __init__.py
│       ├── common.py
│       ├── OrderMonitor.py
│       ├── OrderMonitorNetting.py
│       ├── BatchOrderMonitor.py
│       └── TableListenerContainer.py
│
├── frontend/               # React + Vite
│   ├── api/
│   │   ├── app.py         # Flask API (port 5001)
│   │   └── requirements.txt
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── index.css
│   │   ├── context/
│   │   ├── hooks/
│   │   ├── components/
│   │   └── pages/
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
└── docs/
    ├── DOCUMENTAZIONE.md   # Documentazione tecnica dettagliata (strategia, DB, flussi)
    └── ARCHITETTURA.md     # Questo file
```

---

## 10. Stack tecnologico

| Livello | Tecnologie |
|--------|------------|
| **Backend bot** | Python 3.10+, pandas, numpy, python-dotenv, slack_sdk, certifi; forexconnect (FXCM); MetaTrader5 (solo Windows, produzione). |
| **API** | Python 3, Flask 3, flask-cors, python-dotenv. |
| **Frontend** | React 18, Vite 6, React Router 6, Tailwind CSS 3. |
| **Database** | SQLite 3 (un file, my_database.db). |
| **Esecuzione bot** | Subprocess da Flask (bot_runner.py); combinazione con martina.py via CLI. |

---

## 11. Modalità simulazione vs produzione

Configurazione in **db_utils.py**: `SIMULATION_MODE = True | False`.

| Aspetto | Simulazione (`True`) | Produzione (`False`) |
|--------|----------------------|----------------------|
| **MT5** | Non usato; nessuna chiamata a MetaTrader5. | Ordini e modifiche inviati a MT5. |
| **Ordini** | Scritti in mt5_signals, mt5_modifications, mt5_closures. | Eseguiti su MT5. |
| **Position size / pips** | `calculate_trade_size_simulation` e logica semplificata in db_utils. | `calculate_trade_size` con symbol_info MT5. |
| **Piattaforma** | macOS/Linux (senza MT5). | Windows con MetaTrader 5 installato. |
| **FXCM** | Usato per dati storici in entrambe le modalità. | Idem. |
| **Slack** | Opzionale, come in produzione. | Opzionale. |
| **Dashboard/API** | Stessi endpoint; pagina Simulation mostra i segnali registrati. | Stessi endpoint; Simulation può essere vuota o storica. |

---

*Documento generato dall’analisi del codice del progetto MP-DH415.*

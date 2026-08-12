# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Cosa è questo progetto

**MP-DH415 ("Trading Bot Pro")** — bot di trading algoritmico Forex con dashboard React.

- **Dati storici** (D1/H4/M15): API **FXCM ForexConnect**.
- **Esecuzione ordini**: **MetaTrader 5** (solo Windows, produzione). In sviluppo il bot gira in **modalità simulazione** e scrive i comandi MT5 su SQLite invece di eseguirli.
- **Strategia**: multi-timeframe a cascata D1 → H4 → M15 — zone S/R validate sulla Kijun-sen (Ichimoku, 26 periodi su H4), pattern di inversione M15, entry su ritracciamento Fibonacci 78,6%, target sulla Kijun H4, filtro hard `risk_reward >= 2`. Stati trade: `IN RETEST` → `IN PROGRESS` → `CLOSED`.
- **Notifiche**: Slack (canale default `mt-bot`).

Esiste un progetto gemello di **backtesting** in `../MP-DH415-BT` (repo separato, codice divergente): non confondere i due path. Le funzioni di analisi (`utils.py` vs `utils_BT.py`) hanno origine comune ma NON sono sincronizzate.

## Documentazione interna (leggere prima di modifiche sostanziali)

- `docs/ARCHITETTURA.md` — architettura completa dei componenti
- `docs/DOCUMENTAZIONE.md` — dettaglio strategia, schema DB, flussi
- `docs/DEPLOY.md` (Render) e `docs/DEPLOY_GCP.md` (GCP e2-micro, target principale attuale)

Questo file non duplica quei contenuti: riporta comandi, vincoli e gotcha.

## Vincolo critico: Python 3.10

La libreria `forexconnect` funziona **solo con Python 3.10**. Su questa macchina il `python3` di default è più recente: usare sempre `python3.10` (`/opt/homebrew/bin/python3.10`).

Su macOS Apple Silicon installare il wheel locale:

```bash
pip install forexconnect-1.6.43-cp310-cp310-macosx_11_0_arm64.whl
```

Su Linux/Windows `forexconnect` si installa normalmente da pip (vedi commento in `backend/requirements.txt`).

## Comandi

### Setup

```bash
cp .env.example .env          # poi compilare credenziali FXCM e Slack
pip install -r backend/requirements.txt
pip install -r frontend/api/requirements.txt
cd frontend && npm install
```

Non esiste un `requirements.txt` in root (il README su questo è obsoleto).

### Sviluppo locale (due terminali)

```bash
# Terminale 1 — API Flask (porta 5001)
cd frontend/api && python3.10 app.py

# Terminale 2 — Frontend React (porta 3000)
cd frontend && npm run dev
```

### Bot

```bash
# Loop continuo (modo consigliato: è quello usato da systemd e dalla UI)
python3.10 backend/bot_runner.py --interval 300
python3.10 backend/bot_runner.py --interval 60 --pairs "EUR/USD,GBP/USD"
python3.10 backend/bot_runner.py --single-run   # una passata sola

# Singola coppia (run diretta)
python3.10 backend/martina.py -l LOGIN -p PASSWORD -u http://www.fxcorporate.com/Hosts.jsp \
  -i EUR/USD -c Demo -datefrom "04.10.2022 00:00:00" -session Trade
```

### CLI di manutenzione (`backend/cmd_utils.py`)

Usa il path relativo `my_database.db`: **lanciarlo dalla root del repo**, non da `backend/`.

```bash
python3.10 backend/cmd_utils.py -c balance        # balance MT5 (simulato: 10000.0)
python3.10 backend/cmd_utils.py -c clean          # ATTENZIONE: DELETE FROM trades
python3.10 backend/cmd_utils.py -c signals        # ultimi 20 segnali simulati
python3.10 backend/cmd_utils.py -c clear_signals  # svuota tabelle mt5_*
```

### Test

Non esiste una test suite (né pytest né test frontend). L'unico smoke test è procedurale e **scrive realmente sul DB**:

```bash
cd backend && python3.10 test_simulation.py   # esce con errore se SIMULATION_MODE=False
```

### Frontend (`frontend/package.json`)

```bash
npm run dev      # Vite, porta 3000
npm run build    # output in frontend/dist
npm run lint     # ESLint 9
```

### Deploy GCP (produzione attuale)

**Topologia reale sul server `34.171.150.136` (VM `mp-dh415-vm`)** — diversa da quella descritta in `docs/DEPLOY_GCP.md` e nei file `deploy/`:

- Il repo servito è `/home/fabio_chiodo86/apps/MP-DH415` (utente `fabio_chiodo86`); la copia in `/home/fabiochiodo/MP-DH415` NON è usata da nginx/systemd.
- Unit systemd: **`mp-dh415-api`** (gunicorn :5001) e **`mp-dh415-bot`** — non `flask-api`/`trading-bot` come nei file in `deploy/`.
- nginx serve `frontend/dist` su :80 e :443 (certificato self-signed) con proxy `/api` → :5001.
- **Buildare sempre con `VITE_API_URL=` (vuoto → URL relativi)**: `frontend/.env.production` sul server ora lo imposta già; un URL assoluto `https://…` rompe l'API nei browser che non hanno accettato il cert self-signed.
- Si accede via SSH come `fabiochiodo` (chiave `google_compute_engine`), che ha sudo NOPASSWD; i comandi sul repo vanno eseguiti con `sudo -u fabio_chiodo86`.

```bash
# Aggiornamento (dal server):
sudo -u fabio_chiodo86 bash -c 'cd /home/fabio_chiodo86/apps/MP-DH415 && git pull && cd frontend && npm run build'
sudo systemctl restart mp-dh415-api
journalctl -u mp-dh415-api -f
```

## Architettura

```
FXCM ForexConnect ──(storico D1/H4/M15)──┐
MetaTrader5 (solo prod Windows) ─────────┤
Slack (notifiche) ───────────────────────┤
                                         ▼
   bot_runner.py (loop, --interval) ──subprocess──> martina.py (una run per coppia)
                                             │   utils.py / db_utils.py / kijun.py
                                             ▼
                                  my_database.db (SQLite, root repo)
                                             ▲
                        frontend/api/app.py (Flask :5001) — REST + SSE
                                             ▲
                              frontend/src (React + Vite :3000)
```

- **`backend/martina.py`** — entry point per singola coppia: login FXCM, scarica lo storico, gestisce i trade `IN RETEST`/`IN PROGRESS`, cerca nuove zone+pattern, crea setup, notifica Slack.
- **`backend/bot_runner.py`** — runner continuo: legge `ACTIVE_PAIRS` dal `.env` e lancia `martina.py` per ogni coppia via subprocess (timeout 120 s). Nessun cron/celery: lo scheduling è questo loop.
- **`backend/utils.py`** — tutta la logica di analisi (zone, validazione Kijun, pattern M15, Fibonacci, stop loss, risk/reward, gestione trade).
- **`backend/db_utils.py`** — persistenza SQLite + wrapper MT5 + Slack + sizing. Qui vivono `DB_PATH` (root del repo), gli schemi tabelle (`trades`, `activity_logs`, `mt5_signals`/`mt5_modifications`/`mt5_closures`) e la costante `SIMULATION_MODE`.
- **`frontend/api/app.py`** — API Flask (porta 5001): config (legge/scrive il `.env`), trades, performance, signals, start/stop bot, log con streaming **SSE** su `/api/logs/stream`. Lo stato "running" del bot è determinato con `pgrep -f 'bot_runner\.py'`, non da variabili globali (più worker gunicorn). Include anche gli endpoint **`/api/backtest/*`** (pagina "Backtest" della UI): lettura read-only dei DB SQLite prodotti da MP-DH415-BT, cercati in `$BACKTEST_DB_DIR`, poi `backtest/` nella root del repo, poi `../MP-DH415-BT/` (vedi `backtest/README.md`; sul server GCP i `.db` vanno copiati a mano in `/home/fabio_chiodo86/apps/MP-DH415/backtest/` perché gitignorati).
- **`backend/backtest_runner.py`** — avviato da `POST /api/backtest/run` (pagina Backtest → "Run Backtest"): esegue `martina_BT.py` del progetto BT in sequenza sulle coppie scelte, con cwd = directory BT (i risultati finiscono nel suo `my_database.db` = database "Latest" della UI). Logga il progresso nella tabella **`backtest_logs`** (stream SSE su `/api/backtest/logs/stream`). Env: `BACKTEST_ENGINE_DIR` (default `../MP-DH415-BT`), `BACKTEST_PYTHON` (interprete col pacchetto forexconnect; sul server è il `.venv37` del bot), `BACKTEST_PAIR_TIMEOUT`. Output verboso del motore in `backtest/engine_output.log` (troncato a ogni run). Richiede il progetto BT sul filesystem e le credenziali FXCM nel `.env`.
- **Start/stop bot dall'API, tre livelli**: su Render → 503 (il bot è un Background Worker); se esiste l'unit systemd (`BOT_SERVICE`, default `trading-bot`) → `sudo -n systemctl start|stop`; altrimenti fallback dev → `subprocess.Popen(bot_runner.py)`.
- **`frontend/src/config.js`** — unico punto di configurazione dell'URL API (`VITE_API_URL`; in produzione URL relativi dietro nginx). `context/AppContext.jsx` tiene lo stato globale (polling status ogni 5 s, log via `EventSource`).
- **`backend/common_samples/`** — codice vendor Gehtsoft/FXCM (parsing argomenti CLI, session status, order monitor). **Non modificare.**

## Gotcha e convenzioni

- **`SIMULATION_MODE` è una costante hardcoded** in `backend/db_utils.py`, NON una variabile d'ambiente. L'API (`app.py`) e `docs/DEPLOY.md` fanno riferimento a una env var `SIMULATION_MODE` che **non ha effetto sul bot**: per passare al reale bisogna modificare il sorgente. Il toggle nella UI (`ModeToggle.jsx`) è solo stato visivo.
- **`.env` e `my_database.db` vivono nella root del repo** (path risolti risalendo da `backend/db_utils.py` e `frontend/api/app.py`). Il file `backend/my_database.db` è un residuo storico non più usato.
- **`martina.py` fa `os.chdir(script_dir)` e `from utils import *`**: `calculate_kijun` esiste sia in `kijun.py` sia in `utils.py` e vince quella di `utils.py`.
- **Mai hardcodare path di interprete o filesystem** (`sys.executable`, path relativi alla root): il codice gira su macOS ARM in dev e Linux in produzione; il bug storico più grosso era proprio un path Python macOS hardcoded (commit `6beb448`).
- **File `.log` di ForexConnect** (`martina.py.log`, `bot_runner.py.log`) e cartelle `History/`: cache/log generati dalla libreria FXCM, gitignorati, crescono senza rotazione. Non toccarli, non committarli.
- **`README.md` e `commands.md` contengono path e istruzioni parzialmente obsoleti** (vecchia struttura con file in root, path assoluti `~/Documents/MP-DH415`). In caso di conflitto fa fede il codice.
- Le variabili `DB_NAME/DB_USER/DB_PASS/...` (PostgreSQL) nel `.env.example` **non sono usate dal codice**: il DB è solo SQLite.
- **`backend/worker.py` e `backend/slack_begin.py` sono codice morto** (tracciati in git ma non integrati).
- **Su Render API e Worker hanno filesystem separati** → due SQLite distinti che non condividono i dati.
- **VM GCP e2-micro (1 GB RAM)**: con troppe coppie in `ACTIVE_PAIRS` va in OOM — ridurre le coppie o alzare `--interval`.
- **Lingua**: commenti/docstring/messaggi Slack in italiano; nomi di funzioni e messaggi di activity_log in inglese. Mantenere questa convenzione. Commit brevi e informali su branch `main` (nessuna convenzione tipo Conventional Commits).
- **Log `activity_logs`**: tipi `INFO, SUCCESS, WARNING, ERROR, SYSTEM, TRADE, SIGNAL, TRADER` — `TRADER` è il livello debug, nascosto di default nella UI.
- **Sicurezza**: la dashboard espone credenziali FXCM (pagina Settings) e i pulsanti Start/Stop; su nginx l'`auth_basic` è commentato e va attivato a mano. Non aggiungere mai credenziali in file tracciati.

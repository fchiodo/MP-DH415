"""
Backtest Runner
Esegue il motore di backtesting MP-DH415-BT (martina_BT.py) in sequenza sulle
coppie richieste, loggando il progresso nella tabella backtest_logs del
database live (esposta dalla UI via /api/backtest/logs).

Il motore gira con cwd = backtest/years/<anno>/ nel repo: ogni anno ha il suo
my_database.db dedicato, che la UI espone come tab "<anno>". Il DB viene
creato dal runner con lo schema completo a 25 colonne (initialize_db() del
progetto BT non è mai chiamata dal motore e ha comunque uno schema obsoleto).

Uso:
  python backtest_runner.py --pairs "EUR/USD,GBP/USD" \
      --datefrom "01.01.2024 00:00:00" --dateto "12.31.2024 23:00:00" [--clean]

Env (dal .env della root o dall'ambiente del processo):
  FXCM_LOGIN_ID / FXCM_PASSWORD / FXCM_URL / FXCM_CONNECTION  credenziali motore
  BACKTEST_ENGINE_DIR   directory del progetto BT (default: ../MP-DH415-BT)
  BACKTEST_PYTHON       interprete per il motore (default: lo stesso del runner)
  BACKTEST_PAIR_TIMEOUT timeout per coppia in secondi (default: 7200)
"""

import argparse
import os
import signal
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / '.env')

DB_PATH = _REPO_ROOT / 'my_database.db'  # ospita la tabella backtest_logs
ENGINE_DIR = Path(os.getenv('BACKTEST_ENGINE_DIR', str(_REPO_ROOT.parent / 'MP-DH415-BT')))
ENGINE_PYTHON = os.getenv('BACKTEST_PYTHON', sys.executable)
ENGINE_OUTPUT_LOG = _REPO_ROOT / 'backtest' / 'engine_output.log'
YEARS_DIR = _REPO_ROOT / 'backtest' / 'years'
PAIR_TIMEOUT = int(os.getenv('BACKTEST_PAIR_TIMEOUT', 21600))
HEARTBEAT_SECONDS = 60

ERROR_MARKERS = ('Traceback', 'Exception', 'exception', 'LOGIN_FAILED', 'failed', 'Error:')

# Schema reale della tabella trades (25 colonne): rispecchia i DB prodotti
# storicamente dal motore. Gli INSERT di db_utils.py (BT) scrivono anche
# breakup_date e fibonacci100, assenti dalla initialize_db() del progetto BT.
TRADES_DDL = '''
    CREATE TABLE IF NOT EXISTS trades (
        "pair" TEXT, status TEXT, trade_type TEXT,
        entry_date TEXT, close_date TEXT,
        entry_price REAL, entry_price_index INTEGER,
        stop_loss REAL, target REAL, direction TEXT,
        initial_risk_reward REAL, final_risk_reward REAL,
        profit TEXT, result TEXT,
        zones_rectX1_DLY TEXT, zones_rectY1_DLY REAL, zones_rectY2_DLY REAL,
        zones_rectX1_H4 TEXT, zones_rectY1_H4 REAL, zones_rectY2_H4 REAL,
        pattern_x1 TEXT, pattern_y1 REAL, pattern_y2 REAL,
        breakup_date TEXT, fibonacci100 REAL
    )
'''

stop_requested = False
current_child = None
work_dir = None  # backtest/years/<anno>, impostata in main()
work_db = None   # working DB del run corrente


def log(log_type, message, pair=None, details=None):
    """Scrive una riga in backtest_logs (creando la tabella se serve)."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                pair TEXT,
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            INSERT INTO backtest_logs (timestamp, type, message, pair, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), log_type, message, pair, details))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"[backtest_runner] cannot write log: {e}", flush=True)
    print(f"[{log_type}] {f'[{pair}] ' if pair else ''}{message}", flush=True)


def init_work_db():
    """Crea (se serve) il working DB dell'anno con lo schema completo.
    Necessario: il motore non crea mai la tabella e su un DB nuovo di zecca
    i suoi INSERT a 25 colonne fallirebbero."""
    conn = sqlite3.connect(str(work_db))
    conn.execute(TRADES_DDL)
    conn.commit()
    conn.close()


def count_pair_trades(pair):
    """Numero di righe in trades per la coppia nel working DB (0 se assente)."""
    if not work_db or not work_db.exists():
        return 0
    try:
        conn = sqlite3.connect(str(work_db))
        n = conn.execute('SELECT COUNT(*) FROM trades WHERE pair = ?', (pair,)).fetchone()[0]
        conn.close()
        return n
    except sqlite3.Error:
        return 0


def clean_pairs(pairs):
    """Rimuove dal working DB i trade esistenti delle coppie selezionate."""
    if not work_db.exists():
        return
    try:
        conn = sqlite3.connect(str(work_db))
        placeholders = ','.join('?' for _ in pairs)
        deleted = conn.execute(
            f'DELETE FROM trades WHERE pair IN ({placeholders})', pairs).rowcount
        conn.commit()
        conn.close()
        if deleted:
            log('SYSTEM', f'Cleared {deleted} existing trades for {len(pairs)} pair(s)')
    except sqlite3.Error as e:
        log('WARNING', f'Could not clean working database: {e}')


def handle_stop(signum, frame):
    global stop_requested
    stop_requested = True
    if current_child and current_child.poll() is None:
        current_child.terminate()


def run_pair(pair, datefrom, dateto, credentials):
    """Esegue martina_BT.py su una coppia. Ritorna (ok, new_trades)."""
    global current_child

    before = count_pair_trades(pair)
    log('INFO', f'Starting backtest ({datefrom[6:10]}: {datefrom[:5]} -> {dateto[:5]})', pair)

    cmd = [
        ENGINE_PYTHON, str(ENGINE_DIR / 'martina_BT.py'),
        '-l', credentials['login'],
        '-p', credentials['password'],
        '-u', credentials['url'],
        '-c', credentials['connection'],
        '-i', pair,
        '-datefrom', datefrom,
        '-dateto', dateto,
        '-session', 'Trade',
    ]

    started = time.time()
    output_offset = ENGINE_OUTPUT_LOG.stat().st_size if ENGINE_OUTPUT_LOG.exists() else 0
    with open(ENGINE_OUTPUT_LOG, 'ab') as out:
        out.write(f'\n===== {pair} {datefrom} -> {dateto} @ {datetime.now()} =====\n'.encode())
        out.flush()
        # cwd = cartella dell'anno: il motore apre 'my_database.db' relativo
        # alla cwd, quindi scrive nel DB dedicato all'anno
        current_child = subprocess.Popen(
            cmd, cwd=str(work_dir), stdout=out, stderr=subprocess.STDOUT)

        last_heartbeat = started
        while current_child.poll() is None:
            if time.time() - started > PAIR_TIMEOUT:
                current_child.kill()
                log('ERROR', f'Timed out after {PAIR_TIMEOUT // 60} minutes, skipping pair', pair)
                current_child = None
                return False, 0
            if time.time() - last_heartbeat >= HEARTBEAT_SECONDS:
                elapsed = int((time.time() - started) / 60)
                so_far = count_pair_trades(pair) - before
                log('INFO', f'Still running ({elapsed}m elapsed, {so_far} trades so far)', pair)
                last_heartbeat = time.time()
            time.sleep(3)

    returncode = current_child.returncode
    current_child = None
    elapsed = int(time.time() - started)
    new_trades = count_pair_trades(pair) - before

    # martina_BT.py esce con 0 anche in caso di eccezione (try/except interno):
    # ispeziona la coda dell'output per capire se qualcosa è andato storto
    tail = ''
    try:
        with open(ENGINE_OUTPUT_LOG, 'rb') as f:
            f.seek(output_offset)
            tail = f.read().decode(errors='replace')[-4000:]
    except OSError:
        pass
    had_errors = any(marker in tail for marker in ERROR_MARKERS)

    if stop_requested:
        log('WARNING', 'Backtest interrupted by user', pair)
        return False, new_trades
    if returncode != 0:
        log('ERROR', f'Engine exited with code {returncode}',
            pair, details='\n'.join(tail.splitlines()[-5:]))
        return False, new_trades
    if had_errors and new_trades == 0:
        log('ERROR', 'Engine reported errors and produced no trades',
            pair, details='\n'.join(tail.splitlines()[-5:]))
        return False, 0
    if had_errors:
        log('WARNING', f'Completed with warnings in {elapsed // 60}m {elapsed % 60}s '
                       f'({new_trades} new trades) — check backtest/engine_output.log', pair)
        return True, new_trades

    log('SUCCESS', f'Completed in {elapsed // 60}m {elapsed % 60}s ({new_trades} new trades)', pair)
    return True, new_trades


def main():
    parser = argparse.ArgumentParser(description='MP-DH415-BT backtest runner')
    parser.add_argument('--pairs', required=True, help='Comma-separated pairs, e.g. "EUR/USD,GBP/USD"')
    parser.add_argument('--datefrom', required=True, help='MM.DD.YYYY HH:MM:SS')
    parser.add_argument('--dateto', required=True, help='MM.DD.YYYY HH:MM:SS')
    parser.add_argument('--clean', action='store_true',
                        help='Delete existing trades for the selected pairs before running')
    args = parser.parse_args()

    pairs = [p.strip() for p in args.pairs.split(',') if p.strip()]

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    if not (ENGINE_DIR / 'martina_BT.py').exists():
        log('ERROR', f'Backtest engine not found in {ENGINE_DIR} '
                     '(set BACKTEST_ENGINE_DIR or place the MP-DH415-BT project there)')
        sys.exit(1)

    # Un working DB per anno (dall'anno di --datefrom): backtest/years/<anno>/
    global work_dir, work_db
    year = args.datefrom.split(' ')[0].split('.')[2]
    work_dir = YEARS_DIR / year
    work_dir.mkdir(parents=True, exist_ok=True)
    work_db = work_dir / 'my_database.db'
    init_work_db()

    credentials = {
        'login': os.getenv('FXCM_LOGIN_ID', ''),
        'password': os.getenv('FXCM_PASSWORD', ''),
        'url': os.getenv('FXCM_URL', 'http://www.fxcorporate.com/Hosts.jsp'),
        'connection': os.getenv('FXCM_CONNECTION', 'Demo'),
    }
    if not credentials['login'] or not credentials['password']:
        log('ERROR', 'FXCM credentials not configured (Settings page / .env)')
        sys.exit(1)

    ENGINE_OUTPUT_LOG.parent.mkdir(exist_ok=True)
    # L'output del motore è molto verboso (una riga per candela m15):
    # tronca il file a ogni run per non riempire il disco
    ENGINE_OUTPUT_LOG.write_bytes(b'')

    log('SYSTEM', f'Backtest started: {len(pairs)} pair(s), '
                  f'{args.datefrom[:10]} -> {args.dateto[:10]} (database: {year})'
                  + (' (cleaning selected pairs first)' if args.clean else ''))

    if args.clean:
        clean_pairs(pairs)

    completed, failed, total_trades = 0, 0, 0
    for index, pair in enumerate(pairs, start=1):
        if stop_requested:
            break
        log('INFO', f'Pair {index}/{len(pairs)}', pair)
        ok, new_trades = run_pair(pair, args.datefrom, args.dateto, credentials)
        total_trades += new_trades
        if ok:
            completed += 1
        else:
            failed += 1

    if stop_requested:
        log('WARNING', f'Backtest stopped: {completed} completed, '
                       f'{len(pairs) - completed - failed} skipped ({total_trades} new trades)')
    elif failed:
        log('WARNING', f'Backtest finished: {completed} completed, {failed} failed '
                       f'({total_trades} new trades)')
    else:
        log('SUCCESS', f'Backtest finished: {completed}/{len(pairs)} pairs completed '
                       f'({total_trades} new trades)')


if __name__ == '__main__':
    main()

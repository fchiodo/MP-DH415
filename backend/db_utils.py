import sqlite3
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import os
from pathlib import Path
import certifi
import ssl
from ssl import SSLContext

# Database path - always in the project root (parent of backend/)
DB_PATH = str(Path(__file__).resolve().parent.parent / 'my_database.db')

# ============================================================================
# CONFIGURAZIONE MODALITÀ SIMULAZIONE
# ============================================================================
# True  = Sviluppo su Mac (senza MT5) - scrive segnali su SQLite
# False = Produzione su Windows (con MT5) - esegue ordini reali
# ============================================================================
SIMULATION_MODE = True
# ============================================================================

# Import condizionale di MetaTrader5
if not SIMULATION_MODE:
    import MetaTrader5 as mt5
else:
    mt5 = None  # MT5 non disponibile in modalità simulazione

def initialize_db():
    # Create a database file named 'my_database.db'
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create table
    c.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            pair TEXT,
            status TEXT,
            trade_type TEXT,
            entry_date TEXT,
            close_date TEXT,
            entry_price REAL,
            entry_price_index INTEGER,
            stop_loss REAL, 
            target REAL,
            direction TEXT,
            initial_risk_reward REAL,
            final_risk_reward REAL,
            profit TEXT,
            result TEXT,
            zones_rectX1_DLY TEXT,
            zones_rectY1_DLY REAL, 
            zones_rectY2_DLY REAL,
            zones_rectX1_H4 TEXT,
            zones_rectY1_H4 REAL, 
            zones_rectY2_H4 REAL,
            pattern_x1 TEXT,
            pattern_y1 REAL, 
            pattern_y2 REAL,
            breakup_date TEXT
        )
    ''')

    # Save (commit) the changes
    conn.commit()
    conn.close()

    print(f"DB initialized.")

    return conn


def initialize_signals_db():
    """
    Inizializza la tabella per i segnali MT5 in modalità simulazione.
    Questa tabella registra tutti i comandi che sarebbero stati inviati a MT5.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Tabella per i segnali di trading (ordini pendenti)
    c.execute('''
        CREATE TABLE IF NOT EXISTS mt5_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            signal_type TEXT,
            pair TEXT,
            symbol TEXT,
            action TEXT,
            order_type TEXT,
            volume REAL,
            price REAL,
            stop_loss REAL,
            take_profit REAL,
            deviation INTEGER,
            comment TEXT,
            status TEXT,
            ticket INTEGER,
            processed INTEGER DEFAULT 0
        )
    ''')

    # Tabella per le modifiche agli ordini/posizioni
    c.execute('''
        CREATE TABLE IF NOT EXISTS mt5_modifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            pair TEXT,
            symbol TEXT,
            action TEXT,
            old_sl REAL,
            new_sl REAL,
            old_tp REAL,
            new_tp REAL,
            position_ticket INTEGER,
            comment TEXT,
            processed INTEGER DEFAULT 0
        )
    ''')

    # Tabella per le chiusure
    c.execute('''
        CREATE TABLE IF NOT EXISTS mt5_closures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            pair TEXT,
            symbol TEXT,
            action TEXT,
            volume REAL,
            close_price REAL,
            comment TEXT,
            processed INTEGER DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()
    print("MT5 Signals DB initialized (SIMULATION MODE).")


def log_mt5_signal(signal_type, pair, action, order_type=None, volume=None, 
                   price=None, stop_loss=None, take_profit=None, 
                   deviation=None, comment=None, ticket=None):
    """
    Registra un segnale MT5 nel database SQLite (modalità simulazione).
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    symbol = pair.replace("/", "") if pair else None
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    c.execute('''
        INSERT INTO mt5_signals 
        (timestamp, signal_type, pair, symbol, action, order_type, volume, 
         price, stop_loss, take_profit, deviation, comment, status, ticket)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, signal_type, pair, symbol, action, order_type, volume,
          price, stop_loss, take_profit, deviation, comment, 'PENDING', ticket))
    
    conn.commit()
    signal_id = c.lastrowid
    conn.close()
    
    print(f"[SIMULATION] Signal logged: {signal_type} - {pair} - {action} @ {price}")
    return signal_id


def log_mt5_modification(pair, action, old_sl=None, new_sl=None, 
                         old_tp=None, new_tp=None, position_ticket=None, comment=None):
    """
    Registra una modifica MT5 nel database SQLite (modalità simulazione).
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    symbol = pair.replace("/", "") if pair else None
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    c.execute('''
        INSERT INTO mt5_modifications 
        (timestamp, pair, symbol, action, old_sl, new_sl, old_tp, new_tp, 
         position_ticket, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, pair, symbol, action, old_sl, new_sl, old_tp, new_tp,
          position_ticket, comment))
    
    conn.commit()
    conn.close()
    
    print(f"[SIMULATION] Modification logged: {pair} - {action} - SL: {old_sl}->{new_sl}, TP: {old_tp}->{new_tp}")


def log_mt5_closure(pair, action, volume=None, close_price=None, comment=None):
    """
    Registra una chiusura MT5 nel database SQLite (modalità simulazione).
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    symbol = pair.replace("/", "") if pair else None
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    c.execute('''
        INSERT INTO mt5_closures 
        (timestamp, pair, symbol, action, volume, close_price, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, pair, symbol, action, volume, close_price, comment))
    
    conn.commit()
    conn.close()
    
    print(f"[SIMULATION] Closure logged: {pair} - {action}")


def get_pending_signals():
    """
    Recupera tutti i segnali pendenti (non ancora processati).
    Utile quando si passa da SIMULATION_MODE a produzione.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM mt5_signals WHERE processed = 0 ORDER BY timestamp")
    signals = c.fetchall()
    
    conn.close()
    return signals


def mark_signal_processed(signal_id):
    """
    Marca un segnale come processato.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("UPDATE mt5_signals SET processed = 1 WHERE id = ?", (signal_id,))
    
    conn.commit()
    conn.close()


# ============================================================================
# ACTIVITY LOG SYSTEM - Real-time logging for UI
# ============================================================================

def initialize_activity_logs_db():
    """
    Inizializza la tabella activity_logs per il sistema di logging in tempo reale.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            pair TEXT,
            details TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Crea indice per query veloci sui log recenti
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp 
        ON activity_logs(timestamp DESC)
    ''')
    
    conn.commit()
    conn.close()
    print("[DB] Activity logs table initialized")


def add_activity_log(log_type, message, pair=None, details=None):
    """
    Aggiunge un log all'activity log.
    
    Args:
        log_type: 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'SYSTEM', 'TRADE', 'SIGNAL'
        message: Il messaggio del log
        pair: Coppia forex opzionale (es. 'EUR/USD')
        details: Dettagli aggiuntivi opzionali (JSON string)
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    c.execute('''
        INSERT INTO activity_logs (timestamp, type, message, pair, details)
        VALUES (?, ?, ?, ?, ?)
    ''', (timestamp, log_type, message, pair, details))
    
    conn.commit()
    log_id = c.lastrowid
    conn.close()
    
    # Stampa anche su console per debug
    print(f"[{log_type}] {message}")
    
    return log_id


def get_recent_logs(limit=100):
    """
    Recupera i log più recenti.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
        SELECT id, timestamp, type, message, pair, details
        FROM activity_logs
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    
    logs = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return logs


def get_logs_after_id(last_id):
    """
    Recupera i log con ID maggiore di last_id (per SSE streaming).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
        SELECT id, timestamp, type, message, pair, details
        FROM activity_logs
        WHERE id > ?
        ORDER BY id ASC
    ''', (last_id,))
    
    logs = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return logs


def clear_activity_logs():
    """
    Pulisce tutti i log (opzionale, per manutenzione).
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('DELETE FROM activity_logs')
    
    conn.commit()
    conn.close()
    print("[DB] Activity logs cleared")


def get_latest_log_id():
    """
    Ottiene l'ID dell'ultimo log (per inizializzare SSE).
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT MAX(id) FROM activity_logs')
    result = c.fetchone()[0]
    
    conn.close()
    return result or 0


# ============================================================================
# LOGGING HELPER FUNCTIONS - Per uso nel bot
# ============================================================================

def log_bot_start(mode='SIMULATION'):
    """Log avvio bot"""
    add_activity_log('SYSTEM', f'Trading bot starting in {mode} mode...')
    add_activity_log('INFO', 'Initializing FXCM API connection...')


def log_bot_stop():
    """Log stop bot"""
    add_activity_log('WARNING', 'Stop signal received...')
    add_activity_log('INFO', 'Closing open connections...')
    add_activity_log('SYSTEM', 'Trading bot stopped successfully')


def log_pair_scan(pair, timeframe='M15'):
    """Log scansione pair"""
    add_activity_log('INFO', f'Scanning {pair} for entry signals on {timeframe} timeframe...', pair=pair)


def log_zone_detected(pair, zone_type, price_level):
    """Log zona rilevata"""
    add_activity_log('INFO', f'{pair}: {zone_type} zone detected at {price_level:.5f}', pair=pair)


def log_pattern_detected(pair, pattern_type, timeframe):
    """Log pattern rilevato"""
    add_activity_log('SUCCESS', f'{pair}: {pattern_type} pattern detected on {timeframe}', pair=pair)


def log_trade_signal(pair, direction, entry_price, stop_loss, target, rr):
    """Log segnale di trade"""
    import json
    details = json.dumps({
        'entry': entry_price,
        'sl': stop_loss,
        'tp': target,
        'rr': rr
    })
    add_activity_log('SIGNAL', f'{pair}: {direction} signal at {entry_price:.5f} (R:R {rr:.1f})', pair=pair, details=details)


def log_trade_opened(pair, direction, entry_price, volume):
    """Log trade aperto"""
    import json
    details = json.dumps({
        'entry': entry_price,
        'volume': volume
    })
    add_activity_log('TRADE', f'{pair}: {direction} position opened at {entry_price:.5f} (Vol: {volume})', pair=pair, details=details)


def log_trade_closed(pair, result, profit_r):
    """Log trade chiuso"""
    log_type = 'SUCCESS' if result == 'TARGET' else 'WARNING'
    add_activity_log(log_type, f'{pair}: Position closed - {result} ({profit_r:+.1f} R)', pair=pair)


def log_sl_updated(pair, old_sl, new_sl):
    """Log aggiornamento stop loss"""
    add_activity_log('INFO', f'{pair}: Stop loss updated from {old_sl:.5f} to {new_sl:.5f}', pair=pair)


def log_tp_updated(pair, old_tp, new_tp):
    """Log aggiornamento take profit"""
    add_activity_log('INFO', f'{pair}: Take profit updated to {new_tp:.5f}', pair=pair)


def log_retest_waiting(pair, entry_level):
    """Log attesa retest"""
    add_activity_log('INFO', f'{pair}: Waiting for retest at {entry_level:.5f}', pair=pair)


def log_rr_rejected(pair, rr, min_rr):
    """Log R:R insufficiente"""
    add_activity_log('WARNING', f'{pair}: Risk/Reward below minimum threshold ({rr:.1f} < {min_rr})', pair=pair)


def log_kijun_alignment(pair, timeframe, aligned):
    """Log allineamento Kijun"""
    status = 'aligned' if aligned else 'not aligned'
    add_activity_log('INFO', f'{pair}: Kijun-sen {status} on {timeframe}', pair=pair)


def log_api_connection(status, api_name='FXCM'):
    """Log connessione API"""
    if status == 'connected':
        add_activity_log('SUCCESS', f'Connected to {api_name} API successfully')
    elif status == 'disconnected':
        add_activity_log('WARNING', f'Disconnected from {api_name} API')
    else:
        add_activity_log('ERROR', f'Failed to connect to {api_name} API: {status}')


def log_heartbeat():
    """Log heartbeat"""
    add_activity_log('SYSTEM', 'Heartbeat: Connection to FXCM API stable')


def log_trader(message, pair=None):
    """Log trader debug message - for detailed trading flow"""
    add_activity_log('TRADER', message, pair=pair)


def check_in_progress_trade(pair):
    conn = sqlite3.connect(DB_PATH)
    # Set the row_factory attribute to sqlite3.Row
    conn.row_factory = sqlite3.Row
    
    c = conn.cursor()

    # Execute a SQL statement to find trades with the given 'pair' and 'IN PROGRESS' status
    c.execute("SELECT * FROM trades WHERE pair = ? AND status = 'IN PROGRESS' and trade_type = 'FULL'", (pair,))

    

    # Fetch the first record
    record = c.fetchone()
    conn.close()

    return record

def check_in_retest_trade(pair):
    conn = sqlite3.connect(DB_PATH)
    # Set the row_factory attribute to sqlite3.Row
    conn.row_factory = sqlite3.Row

    c = conn.cursor()
    # Execute a SQL statement to find trades with the given 'pair' and 'IN PROGRESS' status
    c.execute("SELECT * FROM trades WHERE pair = ? AND status = 'IN RETEST'", (pair,))

    # Fetch the first record
    record = c.fetchone()
    conn.close()

    return record

def fetch_trades_from_db(pair):
    conn = sqlite3.connect(DB_PATH)
    # Set the row_factory attribute to sqlite3.Row
    conn.row_factory = sqlite3.Row

    c = conn.cursor()
    # Execute a SQL statement to find trades with the given 'pair' 
    c.execute("SELECT * FROM trades WHERE pair = ?", (pair,))

    # Fetch all rows from the executed query
    records = c.fetchall()

    conn.close()
    return records

def fetch_trades_from_mt5(pair):
    
    orders = None
    positions = None
    
    if SIMULATION_MODE:
        print(f"[SIMULATION] fetch_trades_from_mt5({pair}) - Returning empty (no MT5)")
        return orders, positions
    
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
    else:
        # Get the list of pending orders
        symbol = pair.replace("/", "")
        positions = mt5.positions_get(symbol=symbol)
        orders = mt5.orders_get(symbol=symbol)

    mt5.shutdown()  # Don't forget to shut down the MT5 connection after using it
    return orders, positions

def check_in_closed_trade(pair, pattern_rectX1):
    conn = sqlite3.connect(DB_PATH)
    # Set the row_factory attribute to sqlite3.Row
    conn.row_factory = sqlite3.Row

    status = 'CLOSED'
    c = conn.cursor()
    # Execute a SQL statement to find trades with the given 'pair' and 'IN PROGRESS' status
    c.execute("SELECT * FROM trades WHERE pair = ? AND pattern_x1 = ? AND status = ?", (pair,pattern_rectX1, status))

    # Fetch the first record
    record = c.fetchone()
    conn.close()

    return record

def get_closed_trades_after_date(pair, pattern_rectX1):
    conn = sqlite3.connect(DB_PATH)
    # Set the row_factory attribute to sqlite3.Row
    conn.row_factory = sqlite3.Row

    status = 'CLOSED'
    c = conn.cursor()
    # Execute a SQL statement to find trades with the given 'pair' and 'IN PROGRESS' status
    c.execute("SELECT * FROM trades WHERE pair = ? AND status = ? AND close_date > ?", (pair,status, pattern_rectX1))

    # Fetch the first record
    record = c.fetchone()
    conn.close()

    return record

def drop_all_tables():
    # Connect to SQLite database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Fetch all table names
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()

    # Drop each table
    for table_name in tables:
        c.execute(f'DROP TABLE {table_name[0]}')

    # Commit changes and close connection
    conn.commit()
    conn.close()

    print("All tables dropped.")

def drop_table(table_name):
    # Connect to SQLite database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Drop table
    c.execute(f'DROP TABLE IF EXISTS {table_name}')

    # Commit changes and close connection
    conn.commit()
    conn.close()

    print(f"Table {table_name} dropped.")

def clean_table(table_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # SQL statement to delete all records from the table
    delete_all_records_sql = f'DELETE FROM {table_name}'
    
    c.execute(delete_all_records_sql)
    conn.commit()
    conn.close()

    print(f"Table {table_name} cleaned.")

def update_trade_in_progress(pair, entry_price_index, entry_price_date):

    conn = sqlite3.connect(DB_PATH)
    table = 'trades'
    status = 'IN PROGRESS'
    status_to_check = 'IN RETEST'
    with conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE {table} 
            SET status = ?, entry_price_index = ?, entry_date = ?
            WHERE rowid IN (
                SELECT rowid 
                FROM {table} 
                WHERE pair = ? AND status = ? 
            )
        """, (status, entry_price_index, entry_price_date, pair, status_to_check))
        conn.commit()
    conn.close()

def update_trade_stoploss(pair, new_stop_loss, entry_price_index, rr):
    conn = sqlite3.connect(DB_PATH)

    table = 'trades'
    status_to_check = 'IN PROGRESS'
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE {table} 
        SET stop_loss = ?, entry_price_index = ?, final_risk_reward = ?
        WHERE rowid = (
            SELECT rowid 
            FROM {table} 
            WHERE pair = ? AND status = ? AND trade_type = 'FULL'
            LIMIT 1
            )
    """, (new_stop_loss, entry_price_index, rr, pair, status_to_check))
    
    conn.commit()
    conn.close()
    
    # Alzo stoploss
    if SIMULATION_MODE:
        log_mt5_modification(pair, 'UPDATE_SL', new_sl=new_stop_loss, 
                           comment=f'RR={rr}, index={entry_price_index}')
        return
    
    # establish connection to the MetaTrader 5 terminal
    if not mt5.initialize():
        print("initialize() failed, error code =",mt5.last_error())
    else:

        # Get the list of pending orders
        symbol = pair.replace("/", "")
        positions = mt5.positions_get(symbol=symbol)

        # Check if there are any pending orders
        for position in positions:
        
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "sl": new_stop_loss,
                "tp": position.tp,
                "position": position.ticket
            }

            # send a trading request
            result = mt5.order_send(request)
            send_slack_message('general', str(result))

def upsert_order_waiting_retest(trade_setup,target_1_1):
    print('upsert_order_waiting_retest')
    print('target_1_1: '+str(target_1_1))
    print('target: '+str(trade_setup['target_price']))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check if a trade for the instrument with status 'IN RETEST' already exists
    c.execute("SELECT * FROM trades WHERE pair = ? AND status = 'IN RETEST'", (trade_setup['pair'],))
    existing_trade = c.fetchone()
    #print("trade in retest: "+str(existing_trade))
    # If not, create two new trades
    if not existing_trade:
        #insert full trade

        adjusted_entry_price_full = mt5_place_order(trade_setup)
        trade_setup['entry_price'] = adjusted_entry_price_full  # Update entry_price for database insert

        c.execute("""
            INSERT INTO trades (pair, status, trade_type, entry_price, stop_loss, target, direction, initial_risk_reward, zones_rectX1_DLY, zones_rectY1_DLY, zones_rectY2_DLY, zones_rectX1_H4, zones_rectY1_H4, zones_rectY2_H4, pattern_x1, pattern_y1, pattern_y2, breakup_date, fibonacci100)
            VALUES (:pair, :status, :trade_type, :entry_price, :stop_loss, :target, :direction, :initial_risk_reward, :zones_rectX1_DLY, :zones_rectY1_DLY, :zones_rectY2_DLY, :zones_rectX1_H4, :zones_rectY1_H4, :zones_rectY2_H4, :pattern_x1, :pattern_y1, :pattern_y2, :breakup_date, :fibonacci100)
        """, {
            'pair': trade_setup['pair'],
            'status': 'IN RETEST',
            'trade_type': 'FULL',
            'entry_price': trade_setup['entry_price'],
            'stop_loss': trade_setup['stop_loss_price'],
            'target': trade_setup['target_price'],
            'direction': trade_setup['direction'],
            'initial_risk_reward': trade_setup['risk_reward'],
            'zones_rectX1_DLY': trade_setup['zones_rectX1_DLY'],
            'zones_rectY1_DLY': trade_setup['zones_rectY1_DLY'],
            'zones_rectY2_DLY': trade_setup['zones_rectY2_DLY'],
            'zones_rectX1_H4': trade_setup['zones_rectX1_H4'],
            'zones_rectY1_H4': trade_setup['zones_rectY1_H4'],
            'zones_rectY2_H4': trade_setup['zones_rectY2_H4'],
            'pattern_x1': trade_setup['pattern_x1'],
            'pattern_y1': trade_setup['pattern_y1'],
            'pattern_y2': trade_setup['pattern_y2'],
            'breakup_date': trade_setup['breakup_date'],
            'fibonacci100': trade_setup['fibonacci100']
        })
        
        # mt5_place_order(trade_setup)

        #insert partial trade

        trade_setup['target_price'] = target_1_1
        trade_setup['type'] = 'PARTIAL'
        adjusted_entry_price_partial = mt5_place_order(trade_setup)
        trade_setup['entry_price'] = adjusted_entry_price_partial  # Update entry_price for partial trade

        c.execute("""
            INSERT INTO trades (pair, status, trade_type, entry_price, stop_loss, target, direction, initial_risk_reward, zones_rectX1_DLY, zones_rectY1_DLY, zones_rectY2_DLY, zones_rectX1_H4, zones_rectY1_H4, zones_rectY2_H4, pattern_x1, pattern_y1, pattern_y2, breakup_date, fibonacci100)
            VALUES (:pair, :status, :trade_type, :entry_price, :stop_loss, :target, :direction, :initial_risk_reward, :zones_rectX1_DLY, :zones_rectY1_DLY, :zones_rectY2_DLY, :zones_rectX1_H4, :zones_rectY1_H4, :zones_rectY2_H4, :pattern_x1, :pattern_y1, :pattern_y2, :breakup_date, :fibonacci100)
        """, {
            'pair': trade_setup['pair'],
            'status': 'IN RETEST',
            'trade_type': 'PARTIAL',
            'entry_price': trade_setup['entry_price'],
            'stop_loss': trade_setup['stop_loss_price'],
            'target': target_1_1,
            'direction': trade_setup['direction'],
            'initial_risk_reward': 1,
            'final_risk_reward': 1,
            'zones_rectX1_DLY': trade_setup['zones_rectX1_DLY'],
            'zones_rectY1_DLY': trade_setup['zones_rectY1_DLY'],
            'zones_rectY2_DLY': trade_setup['zones_rectY2_DLY'],
            'zones_rectX1_H4': trade_setup['zones_rectX1_H4'],
            'zones_rectY1_H4': trade_setup['zones_rectY1_H4'],
            'zones_rectY2_H4': trade_setup['zones_rectY2_H4'],
            'pattern_x1': trade_setup['pattern_x1'],
            'pattern_y1': trade_setup['pattern_y1'],
            'pattern_y2': trade_setup['pattern_y2'],
            'breakup_date': trade_setup['breakup_date'],
            'fibonacci100':trade_setup['fibonacci100']
        })
        
        # trade_setup['target_price'] = target_1_1
        # trade_setup['type'] = 'PARTIAL'
        # mt5_place_order(trade_setup)
        
    else:
        print('trade direction: '+str(trade_setup['direction']))
        mt5_close_order(trade_setup['pair'])

        # Update full trade
        adjusted_entry_price_update = mt5_place_order(trade_setup)
        trade_setup['entry_price'] = adjusted_entry_price_update

        c.execute("""
            UPDATE trades 
            SET entry_price = :entry_price, 
                stop_loss = :stop_loss_price, 
                target = :target_price,  
                direction = :direction, 
                initial_risk_reward = :risk_reward,
                zones_rectX1_DLY = :zones_rectX1_DLY, 
                zones_rectY1_DLY = :zones_rectY1_DLY, 
                zones_rectY2_DLY = :zones_rectY2_DLY,
                zones_rectX1_H4 = :zones_rectX1_H4, 
                zones_rectY1_H4 = :zones_rectY1_H4, 
                zones_rectY2_H4 = :zones_rectY2_H4,
                pattern_x1 = :pattern_x1, 
                pattern_y1 = :pattern_y1, 
                pattern_y2 = :pattern_y2,
                breakup_date = :breakup_date
            WHERE pair = :pair AND status = 'IN RETEST' AND trade_type = 'FULL'
        """, trade_setup)
        
        # mt5_place_order(trade_setup)

        # Update partial trade
        partial_trade_setup = trade_setup.copy()
        partial_trade_setup['target_price'] = target_1_1
        partial_trade_setup['initial_risk_reward'] = 1
        partial_trade_setup['final_risk_reward'] = 1
        c.execute("""
            UPDATE trades 
            SET entry_price = :entry_price, 
                stop_loss = :stop_loss_price, 
                target = :target_price,  
                direction = :direction, 
                initial_risk_reward = :initial_risk_reward,
                final_risk_reward = :final_risk_reward,
                zones_rectX1_DLY = :zones_rectX1_DLY, 
                zones_rectY1_DLY = :zones_rectY1_DLY, 
                zones_rectY2_DLY = :zones_rectY2_DLY,
                zones_rectX1_H4 = :zones_rectX1_H4, 
                zones_rectY1_H4 = :zones_rectY1_H4, 
                zones_rectY2_H4 = :zones_rectY2_H4,
                pattern_x1 = :pattern_x1, 
                pattern_y1 = :pattern_y1, 
                pattern_y2 = :pattern_y2,
                breakup_date = :breakup_date
            WHERE pair = :pair AND status = 'IN RETEST' AND trade_type = 'PARTIAL'
        """, partial_trade_setup)

        trade_setup['target_price'] = target_1_1
        trade_setup['type'] = 'PARTIAL'
        mt5_place_order(trade_setup)

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

def update_trade_closed(pair, result, trade_type, close_date, risk_reward):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    with conn:
        cursor = conn.cursor()

        if trade_type == 'FULL' and result == 'TARGET':
            cursor.execute("""
                SELECT * FROM trades WHERE pair = ? AND status = 'IN PROGRESS'
            """, (pair,))

            trades_in_progress = cursor.fetchall()
            for trade in trades_in_progress:
                final_risk_reward = risk_reward
                initial_risk_reward = trade['initial_risk_reward']
                profit = str(risk_reward)

                # if trade type is 'PARTIAL' update with 1 on final_risk_reward and profit columns
                if trade[2] == 'PARTIAL':
                    initial_risk_reward = 1
                    if risk_reward > 0:
                        final_risk_reward = 1
                        profit = '1'
                    else:
                        final_risk_reward = 0
                        profit = '0'
                
                cursor.execute("""
                    UPDATE trades 
                    SET status = 'CLOSED', 
                        result = ?, 
                        close_date = ?, 
                        initial_risk_reward = ?,
                        final_risk_reward = ?, 
                        profit = ?
                    WHERE pair = ? AND status = 'IN PROGRESS'
                """, (result, str(close_date), initial_risk_reward, final_risk_reward, profit, pair))

        elif trade_type == 'PARTIAL' and result == 'TARGET':
            cursor.execute("""
                UPDATE trades 
                SET status = 'CLOSED', 
                    result = ?, 
                    close_date = ?, 
                    initial_risk_reward = ?,
                    final_risk_reward = ?, 
                    profit = ?
                WHERE pair = ? AND status = 'IN PROGRESS' AND trade_type = 'PARTIAL'
            """, (result, str(close_date), risk_reward, risk_reward, str(risk_reward), pair))

        elif result == 'STOP LOSS':
            cursor.execute("""
                UPDATE trades 
                SET status = 'CLOSED', 
                    result = ?, 
                    close_date = ?, 
                    profit = ? 
                WHERE pair = ? AND status = 'IN PROGRESS'
            """, (result, str(close_date), str(risk_reward), pair))

        conn.commit()
    conn.close()

def get_partial_trade_closed(pair, entry_date):
    conn = sqlite3.connect(DB_PATH)
    # Set the row_factory attribute to sqlite3.Row
    conn.row_factory = sqlite3.Row

    c = conn.cursor()
    # Execute a SQL statement to find trades with the given 'pair' and 'IN PROGRESS' status
    c.execute("SELECT * FROM trades WHERE pair = ? AND entry_date = ? AND trade_type = 'PARTIAL'", (pair,entry_date))

    # Fetch the first record
    record = c.fetchone()
    conn.close()

    return record

def get_partial_trade(pair):
    conn = sqlite3.connect(DB_PATH)
    # Set the row_factory attribute to sqlite3.Row
    conn.row_factory = sqlite3.Row

    c = conn.cursor()
    # Execute a SQL statement to find trades with the given 'pair' and 'IN PROGRESS' status
    c.execute("SELECT * FROM trades WHERE pair = ? AND status = 'IN PROGRESS' AND trade_type = 'PARTIAL'", (pair,))

    # Fetch the first record
    record = c.fetchone()
    conn.close()

    return record

def remove_closed_trades(pair, entry_date, pattern_x1, pattern_y1, pattern_y2):
    conn = sqlite3.connect(DB_PATH)

    table = 'trades'
    status_to_check = 'CLOSED'
    cursor = conn.cursor()

    cursor.execute(f"""
        DELETE FROM {table} 
        WHERE pair = ? AND entry_date = ? AND pattern_x1 = ? AND pattern_y1 = ? AND pattern_y2 = ? AND status = ?
    """, (pair, entry_date, pattern_x1, pattern_y1, pattern_y2, status_to_check))

    conn.commit()
    conn.close()

def close_trade_in_retest(pair):
    print('close_trade_in_retest')
    conn = sqlite3.connect(DB_PATH)
    table = 'trades'
    status = 'CLOSED'
    status_to_check = 'IN RETEST'
    with conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE {table} 
            SET status = ?
            WHERE rowid IN (
                SELECT rowid 
                FROM {table} 
                WHERE pair = ? AND status = ? 
            )
        """, (status, pair, status_to_check))
        conn.commit()
    conn.close()
    mt5_close_order(pair)
    mt5_close_positions(pair)

def get_stop_loss(pair, entry_date):
    # Connect to SQLite database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # SQL statement to select the stop_loss
    c.execute("SELECT stop_loss FROM trades WHERE pair = ? AND entry_date = ? AND trade_type = 'PARTIAL'", (pair, entry_date))

    # Fetch the first result
    result = c.fetchone()

    # If the result is not None, return the stop_loss value
    if result is not None:
        stop_loss = result[0]
    else:
        stop_loss = None

    # Close the database connection
    conn.close()

    return stop_loss

def mt5_place_order(trade):
    symbol = trade['pair'].replace("/", "")
    
    # SIMULATION MODE: log signal to SQLite instead of MT5
    if SIMULATION_MODE:
        # Simula la precisione del prezzo (5 decimali per major, 3 per JPY)
        if 'JPY' in trade['pair']:
            price_precision = 3
        else:
            price_precision = 5
        
        adjusted_entry_price = round(trade['entry_price'], price_precision)
        
        # Calcola lot size simulato
        risk_per_trade = 0.005
        lot = calculate_trade_size_simulation(symbol, adjusted_entry_price, risk_per_trade, trade['stop_loss_price'], trade['pair'])
        
        order_type_str = 'BUY_LIMIT' if trade['direction'] == 'LONG' else 'SELL_LIMIT'
        
        log_mt5_signal(
            signal_type='PLACE_ORDER',
            pair=trade['pair'],
            action='PENDING',
            order_type=order_type_str,
            volume=lot,
            price=adjusted_entry_price,
            stop_loss=trade['stop_loss_price'],
            take_profit=trade['target_price'],
            deviation=20,
            comment=trade.get('type', 'FULL')
        )
        
        print(f"[SIMULATION] Order would be placed: {trade['direction']} {symbol} @ {adjusted_entry_price}")
        print(f"[SIMULATION] SL: {trade['stop_loss_price']}, TP: {trade['target_price']}, Lot: {lot}")
        
        return adjusted_entry_price
    
    # PRODUCTION MODE: use MT5
    # connect to MetaTrader 5
    if not mt5.initialize():
        print("initialize() failed")
        mt5.shutdown()
        return None  # Return None if initialization fails

    adjusted_entry_price = None  # Initialize as None to have a return value in case of early exit

    # check if there is already a trade in progress 
    positions = mt5.positions_get(symbol=symbol)

    if positions is None or len(positions) == 0:
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(symbol, "not found, can not call order_check()")
            mt5.shutdown()
            return None  # Return None if symbol info is not found

        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(symbol,True):
                print("symbol_select({}}) failed, exit",symbol)
                mt5.shutdown()
                return None  # Return None if symbol info is not found
        
        # Get the account info
        balance = None
        account_info = mt5.account_info()
        if account_info is not None:
            # Access the balance property
            balance = account_info.balance
            print("Balance:", balance)
        else:
            print("Failed to retrieve account info.")
            mt5.shutdown()
            return None  # Return None if account info retrieval fails
        

        symbol_info = mt5.symbol_info(symbol)
        price_precision = symbol_info.digits
        adjusted_entry_price = round(trade['entry_price'], price_precision)

        risk_per_trade = 0.005
        lot = calculate_trade_size(symbol, adjusted_entry_price, risk_per_trade, trade['stop_loss_price'])

        order_type = None
        if trade['direction'] == 'LONG':
            order_type = mt5.ORDER_TYPE_BUY_LIMIT
        elif trade['direction'] == 'SHORT':
            order_type = mt5.ORDER_TYPE_SELL_LIMIT
        
        deviation = 20
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "price": adjusted_entry_price,
            "sl": trade['stop_loss_price'],
            "tp": trade['target_price'],
            "deviation": deviation,
            #"magic": 234000,
            "comment": trade['type'],
            "type_time": mt5.ORDER_TIME_GTC,
        }

        # send a trading request
        result = mt5.order_send(request)
        # check the execution result
        print("1. order_send(): {} - by {} {} lots at {} with deviation={} points".format(order_type,symbol,lot,adjusted_entry_price,deviation));
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print("2. order_send failed, retcode={}".format(result.retcode))
            # request the result as a dictionary and display it element by element
            result_dict=result._asdict()
            for field in result_dict.keys():
                print("   {}={}".format(field,result_dict[field]))
                # if this is a trading request structure, display it element by element as well
                if field=="request":
                    traderequest_dict=result_dict[field]._asdict()
                    for tradereq_filed in traderequest_dict:
                        print("traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
            print("shutdown() and quit")
            mt5.shutdown()
            
    # Return the adjusted entry price regardless of trade execution outcome
    return adjusted_entry_price

def mt5_close_order(pair):

    symbol = pair.replace("/", "")
    
    # SIMULATION MODE
    if SIMULATION_MODE:
        log_mt5_closure(pair, 'CANCEL_PENDING_ORDERS', comment=f'Cancel all pending orders for {symbol}')
        print(f"[SIMULATION] All pending orders for {symbol} would be cancelled")
        return
    
    # PRODUCTION MODE
    # establish connection to the MetaTrader 5 terminal
    if not mt5.initialize():
        print("initialize() failed, error code =",mt5.last_error())
        #quit()
    
    orders=mt5.orders_get(symbol=symbol)
    if orders is None or len(orders)==0:
        print("No orders on {}, error code={}".format(symbol,mt5.last_error()))
    else:
        print("Total orders{}:",len(orders))
        # display all active orders
        for order in orders:
            print(order)
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": order.ticket
            }
            # send a trading request
            result = mt5.order_send(request)
    print()

def calculate_stop_loss_pips(symbol, entry_price, stop_loss_price):
    # SIMULATION MODE
    if SIMULATION_MODE:
        # Simula point value: 0.00001 per major, 0.001 per JPY
        if 'JPY' in symbol:
            point = 0.001
        else:
            point = 0.00001
        
        stop_loss_points = abs((stop_loss_price - entry_price) / point)
        stop_loss_pips = stop_loss_points / 10
        print(f"[SIMULATION] stop_loss_pips: {stop_loss_pips}")
        return stop_loss_pips
    
    # PRODUCTION MODE
    symbol_info = mt5.symbol_info(symbol)

    if symbol_info is None:
        print("not found, can't calculate stop loss in pips")

    print("symbol_info.point: "+str(symbol_info.point))
    if symbol_info.point == 0:  # Avoid division by zero
        print("Invalid point value")

    stop_loss_points = abs((stop_loss_price - entry_price) / symbol_info.point)
    stop_loss_pips = stop_loss_points / 10
    print("stop_loss_pips: "+str(stop_loss_pips))
    return stop_loss_pips

def calculate_trade_size_simulation(symbol, entry_price, risk_per_trade, stop_loss_price, pair):
    """
    Calcola la size della posizione in modalità simulazione (senza MT5).
    Usa valori approssimati per tick_size e tick_value.
    """
    balance = 10000.0
    
    # Simula tick_size e tick_value in base alla coppia
    if 'JPY' in pair:
        tick_size = 0.001
        tick_value = 0.01  # Valore approssimato
    else:
        tick_size = 0.00001
        tick_value = 0.1  # Valore approssimato per coppie USD
    
    ticks_at_risk = abs(entry_price - stop_loss_price) / tick_size
    
    if ticks_at_risk == 0:
        return 0.01  # Lot minimo
    
    position_size = round((balance * risk_per_trade) / (ticks_at_risk * tick_value), 2)
    
    # Limita tra 0.01 e 10 lotti
    position_size = max(0.01, min(position_size, 10.0))
    
    print(f"[SIMULATION] position_size: {position_size}")
    return position_size


def calculate_trade_size(symbol, entry_price, risk_per_trade, stop_loss_price):
    
    # SIMULATION MODE - non dovrebbe mai essere chiamata direttamente in simulation
    if SIMULATION_MODE:
        print("[SIMULATION] calculate_trade_size called - use calculate_trade_size_simulation instead")
        return 0.01
    
    # PRODUCTION MODE
    #fixed balance
    balance = 10000.0

    mt5.symbol_select(symbol, True)
    symbol_info_tick = mt5.symbol_info_tick(symbol)
    symbol_info = mt5.symbol_info(symbol)

    tick_size = symbol_info.trade_tick_size

    #balance = mt5.account_info().balance
    #risk_per_trade = 0.01
    ticks_at_risk = abs(entry_price - stop_loss_price) / tick_size
    tick_value = symbol_info.trade_tick_value

    position_size = round((balance * risk_per_trade) / (ticks_at_risk * tick_value),2)
    print("position_size: "+str(position_size))

    return position_size

def close_mt5_orders_already_processed():
    # SIMULATION MODE
    if SIMULATION_MODE:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query the database for closed trades
        cursor.execute("SELECT * FROM trades WHERE status = 'CLOSED'")
        closed_trades = cursor.fetchall()
        
        conn.close()
        
        if closed_trades:
            log_mt5_closure(None, 'CLEANUP_PROCESSED_ORDERS', 
                           comment=f'Would cancel orders matching {len(closed_trades)} closed trades')
        print(f"[SIMULATION] close_mt5_orders_already_processed - {len(closed_trades)} closed trades found")
        return
    
    # PRODUCTION MODE
    # establish connection to the MetaTrader 5 terminal
    if not mt5.initialize():
        print("initialize() failed, error code =",mt5.last_error())
        #quit()
    else:

        # Get the list of pending orders
        orders = mt5.orders_get()

        # Check if there are any pending orders
        if orders is None or len(orders) == 0:
            print("No pending orders found.")

        # Connect to the SQLite database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query the database for closed trades
        cursor.execute("SELECT * FROM trades WHERE status = 'CLOSED'")
        closed_trades = cursor.fetchall()

        # Print information about each pending order
        for order in orders:
            string = order.symbol
            symbol = string[:3] + "/" + string[3:]
            symbol_info = mt5.symbol_info(order.symbol)
            price_precision = symbol_info.digits

            # Iterate through the closed trades
            for closed_trade in closed_trades:

                adjusted_entry_price = round(closed_trade['entry_price'], price_precision)
                if (symbol == closed_trade['pair'] and
                    order.price_open == adjusted_entry_price ):
                        print('adjusted_entry_price: '+str(adjusted_entry_price))
                        request = {
                        "action": mt5.TRADE_ACTION_REMOVE,
                        "order": order.ticket
                        }
                        # send a trading request
                        result = mt5.order_send(request)

    # Disconnect from MetaTrader 5
    mt5.shutdown()

def close_mt5_partial_positions(pair):
    symbol = pair.replace("/", "")
    
    # SIMULATION MODE
    if SIMULATION_MODE:
        log_mt5_closure(pair, 'CLOSE_PARTIAL_POSITIONS', 
                       comment=f'Close all PARTIAL positions for {symbol}')
        print(f"[SIMULATION] PARTIAL positions for {symbol} would be closed")
        return
    
    # PRODUCTION MODE
    positions = mt5.positions_get(symbol=symbol)
    result = None  # Initialize result with a default value

    for position in positions:
        tick = mt5.symbol_info_tick(position.symbol)
        if position.comment == 'PARTIAL':
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol":position.symbol, 
                "position": position.ticket, 
                "volume":position.volume,
                "type": mt5.ORDER_TYPE_BUY if position.type == 1 else mt5.ORDER_TYPE_SELL,
                "price": tick.ask if position.type == 1 else tick.bid,
                "deviation":20,
                "magic":100,
                "comment": "python script close",
                "type_time": mt5.ORDER_TIME_GTC,
                #"type_filling": mt5.ORDER_FILLING_IOC
            }
            # send a trading request
            result = mt5.order_send(request)
        

        if result is not None:
            print("result: "+str(result))
        else:
            print("No PARTIAL positions to close or error in retrieving positions")

def mt5_close_positions(pair):
    symbol = pair.replace("/", "")
    
    # SIMULATION MODE
    if SIMULATION_MODE:
        log_mt5_closure(pair, 'CLOSE_ALL_POSITIONS', 
                       comment=f'Close all positions for {symbol}')
        print(f"[SIMULATION] All positions for {symbol} would be closed")
        return
    
    # PRODUCTION MODE
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
    else:

        positions = mt5.positions_get(symbol=symbol)

        for position in positions:
            tick = mt5.symbol_info_tick(position.symbol)
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol":position.symbol, 
                "position": position.ticket, 
                "volume":position.volume,
                "type": mt5.ORDER_TYPE_BUY if position.type == 1 else mt5.ORDER_TYPE_SELL,
                "price": tick.ask if position.type == 1 else tick.bid,
                "deviation":20,
                "magic":100,
                "comment": "python script close",
                "type_time": mt5.ORDER_TIME_GTC,
                #"type_filling": mt5.ORDER_FILLING_IOC
            }
            # send a trading request
            result = mt5.order_send(request)
        
    mt5.shutdown() 


def update_trade_target(pair, new_target, rr):
    conn = sqlite3.connect(DB_PATH)
    #print ('pair: '+str(pair)+' - new target: '+str(new_target)+' - rr: '+str(rr))
    table = 'trades'
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE {table} 
        SET target = ?, final_risk_reward = ?
        WHERE rowid = (
            SELECT rowid 
            FROM {table} 
            WHERE pair = ? AND trade_type = 'FULL' AND (status = 'IN RETEST' OR status = 'IN PROGRESS')
            LIMIT 1
            )
    """, (new_target, rr, pair))
    
    conn.commit()
    conn.close()

    # SIMULATION MODE
    if SIMULATION_MODE:
        log_mt5_modification(pair, 'UPDATE_TARGET', new_tp=new_target, 
                           comment=f'Update FULL position target, RR={rr}')
        return
    
    # PRODUCTION MODE
    # establish connection to the MetaTrader 5 terminal
    if not mt5.initialize():
        print("initialize() failed, error code =",mt5.last_error())
    else:

        # Get the list of pending orders
        symbol = pair.replace("/", "")
        positions = mt5.positions_get(symbol=symbol)

        # Check if there are any pending orders
        for position in positions:
            if position.comment == 'FULL':
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "sl": position.sl,
                    "tp": new_target,
                    "position": position.ticket
                }

            # send a trading request
            result = mt5.order_send(request)

def update_trade_target_ALL(pair, new_target, rr):
    symbol = pair.replace("/", "")
    
    # SIMULATION MODE
    if SIMULATION_MODE:
        log_mt5_modification(pair, 'UPDATE_TARGET_ALL', new_tp=new_target, new_sl=new_target,
                           comment=f'Update ALL positions SL/TP to {new_target}, RR={rr} (breakeven/exit)')
        print(f"[SIMULATION] All positions for {symbol} would be updated to target/SL: {new_target}")
        return
    
    # PRODUCTION MODE
    # establish connection to the MetaTrader 5 terminal
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        return
    
    # Get the list of pending orders
    positions = mt5.positions_get(symbol=symbol)

    # Check if there are any pending orders
    for position in positions:
        tick = mt5.symbol_info_tick(position.symbol)
        is_short = position.type == mt5.POSITION_TYPE_SELL
        is_long = position.type == mt5.POSITION_TYPE_BUY

        current_price = tick.ask if is_long else tick.bid

        # Determine whether to update TP or SL based on position type and current market price
        if (is_short and current_price < position.price_open) or (is_long and current_price > position.price_open):
            # Update SL for shorts below entry or longs above entry
            sl = new_target
            tp = position.tp
        else:
            # Update TP for shorts above entry or longs below entry
            tp = new_target
            sl = position.sl

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": position.ticket,
            "sl": sl,
            "tp": tp
        }

        # Send the trading request to update TP and SL
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Failed to update position {position.ticket}, error code = {result.retcode}")
        else:
            print(f"Successfully updated position {position.ticket} - SL: {sl}, TP: {tp}")
    
    mt5.shutdown()

def send_slack_message(channel, message):

    env_path = ".env"
    load_dotenv(env_path)

    ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
    sslcert = SSLContext()
    client = WebClient(token=os.environ['SLACK_BOT_TOKEN'], ssl=sslcert)

    try:
        response = client.chat_postMessage(
            channel=channel,
            text=message
        )
        print(f"Message sent: {response['ts']}")
    except SlackApiError as e:
        print(f"Error sending message: {e}")

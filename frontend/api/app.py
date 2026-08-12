"""
Trading Bot API Server
Provides REST endpoints for the React UI to interact with the bot configuration and data.
Includes Server-Sent Events (SSE) for real-time Activity Log streaming.
"""

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from dotenv import load_dotenv, set_key
import os
import re
import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path

# Paths: from frontend/api/ up to repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = _REPO_ROOT / '.env'
DB_PATH = _REPO_ROOT / 'my_database.db'

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

app = Flask(__name__)

# CORS: localhost (dev) + Render frontend URL from env (production)
_cors_origins = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:3001", "http://127.0.0.1:3001",
]
if os.getenv('FRONTEND_URL'):
    _cors_origins.append(os.getenv('FRONTEND_URL').rstrip('/'))
CORS(app, resources={
    r"/api/*": {
        "origins": _cors_origins,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# ============================================================================
# CONFIGURATION ENDPOINTS
# ============================================================================

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get all configuration from .env file"""
    return jsonify({
        'fxcm': {
            'loginId': os.getenv('FXCM_LOGIN_ID', ''),
            'password': os.getenv('FXCM_PASSWORD', ''),
            'url': os.getenv('FXCM_URL', ''),
            'connection': os.getenv('FXCM_CONNECTION', 'Demo'),
            'session': os.getenv('FXCM_SESSION', 'Trade'),
        },
        'risk': {
            'riskPerTrade': float(os.getenv('RISK_PER_TRADE', 1.0)),
            'minRewardRisk': float(os.getenv('MIN_REWARD_RISK', 2.0)),
            'referenceBalance': float(os.getenv('REFERENCE_BALANCE', 10000)),
        },
        'slack': {
            'botToken': os.getenv('SLACK_BOT_TOKEN', ''),
            'channel': os.getenv('SLACK_CHANNEL', ''),
        },
        'activePairs': os.getenv('ACTIVE_PAIRS', '').split(',') if os.getenv('ACTIVE_PAIRS') else [],
    })


@app.route('/api/config', methods=['PUT'])
def update_config():
    """Update configuration in .env file (no-op on Render if .env is not present)"""
    data = request.json
    if not ENV_PATH.exists():
        return jsonify({'success': False, 'error': 'No .env file; set variables in Render dashboard'}), 400

    try:
        # Update FXCM settings
        if 'fxcm' in data:
            if 'loginId' in data['fxcm']:
                set_key(ENV_PATH, 'FXCM_LOGIN_ID', data['fxcm']['loginId'])
            if 'password' in data['fxcm']:
                set_key(ENV_PATH, 'FXCM_PASSWORD', data['fxcm']['password'])
            if 'url' in data['fxcm']:
                set_key(ENV_PATH, 'FXCM_URL', data['fxcm']['url'])
            if 'connection' in data['fxcm']:
                set_key(ENV_PATH, 'FXCM_CONNECTION', data['fxcm']['connection'])
        
        # Update Risk settings
        if 'risk' in data:
            if 'riskPerTrade' in data['risk']:
                set_key(ENV_PATH, 'RISK_PER_TRADE', str(data['risk']['riskPerTrade']))
            if 'minRewardRisk' in data['risk']:
                set_key(ENV_PATH, 'MIN_REWARD_RISK', str(data['risk']['minRewardRisk']))
            if 'referenceBalance' in data['risk']:
                set_key(ENV_PATH, 'REFERENCE_BALANCE', str(data['risk']['referenceBalance']))
        
        # Update Slack settings
        if 'slack' in data:
            if 'botToken' in data['slack']:
                set_key(ENV_PATH, 'SLACK_BOT_TOKEN', data['slack']['botToken'])
            if 'channel' in data['slack']:
                set_key(ENV_PATH, 'SLACK_CHANNEL', data['slack']['channel'])
        
        # Update Active Pairs
        if 'activePairs' in data:
            set_key(ENV_PATH, 'ACTIVE_PAIRS', ','.join(data['activePairs']))
        
        # Reload env
        load_dotenv(ENV_PATH, override=True)
        
        return jsonify({'success': True, 'message': 'Configuration updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# DATABASE HELPERS
# ============================================================================

def get_db_connection():
    """Create a database connection"""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def iso_date_expr(column):
    """SQL expression converting the bot's 'MM.DD.YYYY HH:MM:SS' text dates to
    ISO 'YYYY-MM-DD HH:MM:SS', so they can be sorted and compared correctly."""
    return (f"SUBSTR({column}, 7, 4) || '-' || SUBSTR({column}, 1, 2) || '-' || "
            f"SUBSTR({column}, 4, 2) || SUBSTR({column}, 11)")


# ============================================================================
# TRADES ENDPOINTS
# ============================================================================

@app.route('/api/trades', methods=['GET'])
def get_trades():
    """Get all trades from database"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'trades': [], 'message': 'Database not found'})
    
    try:
        cursor = conn.cursor()
        
        # Get all trades from the 'trades' table
        cursor.execute(f'''
            SELECT rowid, pair, status, trade_type, entry_date, close_date,
                   entry_price, stop_loss, target, direction,
                   initial_risk_reward, final_risk_reward, profit, result
            FROM trades
            ORDER BY {iso_date_expr('entry_date')} DESC
        ''')
        all_trades = [dict(row) for row in cursor.fetchall()]
        
        # Separate active vs closed based on status
        active_trades = [t for t in all_trades if t.get('status') in ('active', 'retest', 'waiting', 'in_progress')]
        closed_trades = [t for t in all_trades if t.get('status') in ('closed', 'completed', 'stopped')]
        
        conn.close()
        
        return jsonify({
            'active': active_trades,
            'closed': closed_trades,
        })
    except sqlite3.OperationalError as e:
        return jsonify({'active': [], 'closed': [], 'message': f'Table error: {str(e)}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/trades/active', methods=['GET'])
def get_active_trades():
    """Get active trades formatted for the Forex Pairs Monitoring table"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'trades': []})
    
    try:
        cursor = conn.cursor()
        
        # Get trades that are not closed (case-insensitive)
        cursor.execute(f'''
            SELECT rowid, pair, status, direction, entry_price, initial_risk_reward
            FROM trades
            WHERE UPPER(status) NOT IN ('CLOSED', 'COMPLETED', 'STOPPED')
              AND close_date IS NULL
            ORDER BY {iso_date_expr('entry_date')} DESC
        ''')
        rows = cursor.fetchall()
        
        trades = []
        for row in rows:
            rr = row['initial_risk_reward']
            # Format risk/reward as "1:X.X"
            rr_formatted = f"1:{rr:.1f}" if rr else "1:0.0"
            
            # Map status to UI values (case-insensitive)
            status_raw = (row['status'] or 'active').upper()
            if status_raw in ('IN_PROGRESS', 'OPEN', 'ACTIVE'):
                status = 'active'
            elif status_raw in ('IN RETEST', 'IN_RETEST', 'WAITING_RETEST', 'RETEST_PENDING', 'RETEST'):
                status = 'retest'
            elif status_raw in ('WAITING', 'PENDING'):
                status = 'waiting'
            else:
                status = 'active'
            
            trades.append({
                'id': row['rowid'],
                'pair': row['pair'],
                'status': status,
                'direction': row['direction'] or 'LONG',
                'entryPrice': row['entry_price'] or 0,
                'riskReward': rr_formatted,
            })
        
        conn.close()
        
        return jsonify({'trades': trades})
    except sqlite3.OperationalError as e:
        return jsonify({'trades': [], 'message': f'Table error: {str(e)}'})
    except Exception as e:
        return jsonify({'trades': [], 'error': str(e)})


@app.route('/api/trades/stats', methods=['GET'])
def get_trade_stats():
    """Get trading statistics"""
    conn = get_db_connection()
    if not conn:
        return jsonify({
            'activeTrades': 0,
            'waitingRetest': 0,
            'todayProfit': 0,
            'totalTrades': 0,
            'winRate': 0,
        })
    
    try:
        cursor = conn.cursor()
        
        # Active trades count (not closed)
        cursor.execute('''
            SELECT COUNT(*) FROM trades 
            WHERE (status NOT IN ('closed', 'completed', 'stopped') OR status IS NULL)
              AND close_date IS NULL
        ''')
        active_count = cursor.fetchone()[0]
        
        # Waiting retest count (case-insensitive)
        cursor.execute('''
            SELECT COUNT(*) FROM trades 
            WHERE UPPER(status) IN ('IN RETEST', 'IN_RETEST', 'RETEST', 'WAITING_RETEST', 'RETEST_PENDING', 'WAITING')
        ''')
        retest_count = cursor.fetchone()[0]
        
        # Total closed trades
        cursor.execute('''
            SELECT COUNT(*) FROM trades 
            WHERE status IN ('closed', 'completed', 'stopped') OR close_date IS NOT NULL
        ''')
        total_closed = cursor.fetchone()[0]
        
        # Calculate win rate
        cursor.execute('''
            SELECT COUNT(*) FROM trades 
            WHERE result = 'win' OR profit > 0
        ''')
        wins = cursor.fetchone()[0]
        
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
        
        # Calculate today's profit (trades closed today)
        # close_date is stored as 'MM.DD.YYYY HH:MM:SS'
        cursor.execute('''
            SELECT SUM(CAST(profit AS REAL)) FROM trades
            WHERE close_date LIKE ?
        ''', (datetime.now().strftime('%m.%d.%Y') + '%',))
        today_profit_result = cursor.fetchone()[0]
        today_profit = today_profit_result if today_profit_result else 0
        
        conn.close()
        
        return jsonify({
            'activeTrades': active_count,
            'waitingRetest': retest_count,
            'todayProfit': today_profit,
            'totalTrades': total_closed,
            'winRate': round(win_rate, 1),
        })
    except sqlite3.OperationalError as e:
        return jsonify({
            'activeTrades': 0,
            'waitingRetest': 0,
            'todayProfit': 0,
            'totalTrades': 0,
            'winRate': 0,
            'message': f'Table error: {str(e)}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# PERFORMANCE ENDPOINTS
# ============================================================================

@app.route('/api/performance', methods=['GET'])
def get_performance():
    """Get performance data for the Performance page"""
    conn = get_db_connection()
    if not conn:
        return jsonify({
            'stats': {},
            'recentTrades': [],
            'pairPerformance': []
        })
    
    try:
        cursor = conn.cursor()
        
        # Get time filter from query params (default: all)
        time_filter = request.args.get('period', 'all')
        direction_filter = request.args.get('direction', 'all')
        
        # Build date filter (close_date is 'MM.DD.YYYY HH:MM:SS' → convert to ISO)
        iso_close = iso_date_expr('close_date')
        date_condition = ""
        if time_filter == '24h':
            date_condition = f"AND {iso_close} >= datetime('now', '-1 day')"
        elif time_filter == '7d':
            date_condition = f"AND {iso_close} >= datetime('now', '-7 days')"
        elif time_filter == 'month':
            date_condition = f"AND {iso_close} >= datetime('now', '-30 days')"
        elif time_filter == 'quarter':
            date_condition = f"AND {iso_close} >= datetime('now', '-90 days')"
        elif time_filter == 'ytd':
            date_condition = f"AND {iso_close} >= '{datetime.now().year}-01-01'"
        
        # Build direction filter
        direction_condition = ""
        if direction_filter == 'long':
            direction_condition = "AND UPPER(direction) = 'LONG'"
        elif direction_filter == 'short':
            direction_condition = "AND UPPER(direction) = 'SHORT'"
        
        # ========== STATS ==========
        # Total closed trades
        cursor.execute(f'''
            SELECT COUNT(*) FROM trades 
            WHERE UPPER(status) = 'CLOSED' {date_condition} {direction_condition}
        ''')
        total_trades = cursor.fetchone()[0]
        
        # Wins (TARGET hit)
        cursor.execute(f'''
            SELECT COUNT(*) FROM trades 
            WHERE UPPER(result) = 'TARGET' {date_condition} {direction_condition}
        ''')
        wins = cursor.fetchone()[0]
        
        # Losses (STOP LOSS hit)
        cursor.execute(f'''
            SELECT COUNT(*) FROM trades 
            WHERE UPPER(result) = 'STOP LOSS' {date_condition} {direction_condition}
        ''')
        losses = cursor.fetchone()[0]
        
        # Win rate
        total_with_result = wins + losses
        win_rate = (wins / total_with_result * 100) if total_with_result > 0 else 0
        
        # Average R:R
        cursor.execute(f'''
            SELECT AVG(initial_risk_reward) FROM trades 
            WHERE UPPER(status) = 'CLOSED' AND initial_risk_reward > 0 
            {date_condition} {direction_condition}
        ''')
        avg_rr_result = cursor.fetchone()[0]
        avg_rr = avg_rr_result if avg_rr_result else 0
        
        # Total profit in R (wins * avg_rr - losses)
        # Approximate: each win = avg R:R, each loss = -1R
        total_profit_r = (wins * avg_rr) - losses if avg_rr > 0 else wins - losses
        
        # ========== RECENT TRADES ==========
        cursor.execute(f'''
            SELECT rowid, pair, direction, trade_type, entry_price, result, 
                   initial_risk_reward, final_risk_reward, entry_date, close_date
            FROM trades
            WHERE UPPER(status) = 'CLOSED' AND result IS NOT NULL
            {date_condition} {direction_condition}
            ORDER BY {iso_close} DESC
            LIMIT 20
        ''')
        
        recent_trades = []
        for row in cursor.fetchall():
            result_type = 'win' if row['result'] == 'TARGET' else 'loss'
            rr = row['final_risk_reward'] or row['initial_risk_reward'] or 0
            profit_r = f"+{rr:.1f} R" if result_type == 'win' else "-1.0 R"
            
            recent_trades.append({
                'id': row['rowid'],
                'asset': row['pair'],
                'type': row['direction'] or 'LONG',
                'strategy': row['trade_type'] or 'Standard',
                'entry': row['entry_price'] or 0,
                'result': result_type,
                'profit': profit_r,
                'entryDate': row['entry_date'],
                'closeDate': row['close_date']
            })
        
        # ========== PAIR PERFORMANCE ==========
        cursor.execute(f'''
            SELECT pair, 
                   COUNT(*) as total,
                   SUM(CASE WHEN UPPER(result) = 'TARGET' THEN 1 ELSE 0 END) as wins
            FROM trades 
            WHERE UPPER(status) = 'CLOSED' AND result IS NOT NULL
            {date_condition} {direction_condition}
            GROUP BY pair
            ORDER BY total DESC
            LIMIT 10
        ''')
        
        pair_performance = []
        for row in cursor.fetchall():
            total = row['total']
            wins_pair = row['wins']
            win_rate_pair = (wins_pair / total * 100) if total > 0 else 0
            
            pair_performance.append({
                'pair': row['pair'],
                'total': total,
                'wins': wins_pair,
                'winRate': round(win_rate_pair, 1),
                'color': 'primary' if win_rate_pair >= 50 else 'rose'
            })
        
        # ========== EQUITY CURVE (all closed trades, cumulative P/L) ==========
        # Date format in DB is MM.DD.YYYY HH:MM:SS, so we extract and convert
        # Get the last 30 unique days in ascending order for proper cumulative calculation
        cursor.execute('''
            SELECT day, daily_pl FROM (
                SELECT 
                    SUBSTR(close_date, 7, 4) || '-' || SUBSTR(close_date, 1, 2) || '-' || SUBSTR(close_date, 4, 2) as day,
                    SUM(CASE WHEN UPPER(result) = 'TARGET' THEN initial_risk_reward ELSE -1 END) as daily_pl
                FROM trades 
                WHERE UPPER(status) = 'CLOSED' AND result IS NOT NULL
                  AND close_date IS NOT NULL AND close_date != ''
                GROUP BY day
                ORDER BY day DESC
                LIMIT 30
            ) ORDER BY day ASC
        ''')
        
        equity_curve = []
        cumulative = 0
        for row in cursor.fetchall():
            cumulative += row['daily_pl'] or 0
            equity_curve.append({
                'date': row['day'],
                'value': round(cumulative, 2)
            })
        
        conn.close()
        
        return jsonify({
            'stats': {
                'totalTrades': total_trades,
                'wins': wins,
                'losses': losses,
                'winRate': round(win_rate, 1),
                'avgRR': round(avg_rr, 2),
                'totalProfitR': round(total_profit_r, 1)
            },
            'recentTrades': recent_trades,
            'pairPerformance': pair_performance,
            'equityCurve': equity_curve
        })
        
    except sqlite3.OperationalError as e:
        return jsonify({
            'stats': {},
            'recentTrades': [],
            'pairPerformance': [],
            'equityCurve': [],
            'message': f'Table error: {str(e)}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# SIGNALS ENDPOINTS (Simulation Mode)
# ============================================================================

@app.route('/api/signals', methods=['GET'])
def get_signals():
    """Get MT5 simulation signals"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'signals': [], 'modifications': [], 'closures': []})
    
    try:
        cursor = conn.cursor()
        
        # Get pending signals
        cursor.execute('''
            SELECT * FROM mt5_signals 
            ORDER BY timestamp DESC
            LIMIT 100
        ''')
        signals = [dict(row) for row in cursor.fetchall()]
        
        # Get modifications
        cursor.execute('''
            SELECT * FROM mt5_modifications 
            ORDER BY timestamp DESC
            LIMIT 100
        ''')
        modifications = [dict(row) for row in cursor.fetchall()]
        
        # Get closures
        cursor.execute('''
            SELECT * FROM mt5_closures 
            ORDER BY timestamp DESC
            LIMIT 100
        ''')
        closures = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'signals': signals,
            'modifications': modifications,
            'closures': closures,
        })
    except sqlite3.OperationalError:
        # Tables don't exist yet
        return jsonify({'signals': [], 'modifications': [], 'closures': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/signals/clear', methods=['POST'])
def clear_signals():
    """Clear all MT5 simulation signals"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database not found'})
    
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM mt5_signals')
        cursor.execute('DELETE FROM mt5_modifications')
        cursor.execute('DELETE FROM mt5_closures')
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'All signals cleared'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# BOT CONTROL ENDPOINTS
# ============================================================================

import subprocess
import sys
import signal as os_signal

# systemd unit that runs bot_runner.py in production (override via .env if the
# unit has a different name on the server, e.g. BOT_SERVICE=mp-dh415-bot)
BOT_SERVICE = os.getenv('BOT_SERVICE', 'trading-bot')
BOT_SERVICE_UNIT = Path(f'/etc/systemd/system/{BOT_SERVICE}.service')

# Best-effort start time; the source of truth for "running" is the process list,
# because with multiple gunicorn workers each worker has its own globals.
bot_start_time = None


def _find_bot_pids():
    """Return PIDs of any running bot_runner.py, no matter who started it."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', r'bot_runner\.py'],
            capture_output=True, text=True, timeout=10
        )
        return [int(pid) for pid in result.stdout.split()]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []


def _systemctl_bot(action):
    """Start/stop the systemd bot service. Requires the passwordless sudo rule
    installed by deploy/gcp_setup.sh. Returns True on success."""
    try:
        result = subprocess.run(
            ['sudo', '-n', 'systemctl', action, BOT_SERVICE],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _add_system_log(log_type, message, pair=None):
    """Write an entry to activity_logs (creating the table if needed)."""
    conn = get_activity_logs_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute('''
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
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO activity_logs (timestamp, type, message, pair)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, log_type, message, pair))
        conn.commit()
    finally:
        conn.close()


@app.route('/api/bot/status', methods=['GET'])
def get_bot_status():
    """Get current bot status (based on the process list, works across workers)"""
    pids = _find_bot_pids()
    is_running = len(pids) > 0

    return jsonify({
        'status': 'running' if is_running else 'stopped',
        'pid': pids[0] if is_running else None,
        'simulationMode': os.getenv('SIMULATION_MODE', 'True') == 'True',
        'startTime': bot_start_time.isoformat() if bot_start_time and is_running else None,
    })


@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    """Start the trading bot (no-op on Render: use Background Worker instead)"""
    global bot_start_time

    if os.getenv('RENDER'):
        return jsonify({
            'success': False,
            'error': 'On Render the bot runs as a Background Worker; start/stop is not available from the UI.'
        }), 503

    if _find_bot_pids():
        return jsonify({
            'success': False,
            'error': 'Bot is already running',
            'pid': _find_bot_pids()[0]
        }), 400

    data = request.json or {}
    pair = data.get('pair', os.getenv('ACTIVE_PAIRS', 'EUR/USD').split(',')[0])

    login_id = os.getenv('FXCM_LOGIN_ID', '')
    password = os.getenv('FXCM_PASSWORD', '')

    if not login_id or not password:
        return jsonify({
            'success': False,
            'error': 'FXCM credentials not configured'
        }), 400

    try:
        _add_system_log('SYSTEM', f'Starting bot for {pair}...', pair)

        # Production (GCP VM): the bot is managed by systemd
        if BOT_SERVICE_UNIT.exists() and _systemctl_bot('start'):
            bot_start_time = datetime.now()
            time.sleep(1)
            pids = _find_bot_pids()
            return jsonify({
                'success': True,
                'message': f'Bot service started ({BOT_SERVICE})',
                'pid': pids[0] if pids else None
            })

        # Development / fallback: spawn bot_runner.py with the same interpreter
        # that runs this API (venv-aware, works on macOS and Linux)
        bot_script = _REPO_ROOT / 'backend' / 'bot_runner.py'
        interval = data.get('interval', 60)

        cmd = [sys.executable, str(bot_script), '--interval', str(interval)]
        if data.get('pairs'):
            cmd.extend(['--pairs', data.get('pairs')])

        # stdout goes to a log file: with PIPE nobody drains the buffer and the
        # bot would eventually block on a full pipe
        log_path = bot_script.parent / 'bot_runner.py.log'
        with open(log_path, 'ab') as log_file:
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=str(bot_script.parent),
                start_new_session=True
            )
        bot_start_time = datetime.now()

        return jsonify({
            'success': True,
            'message': f'Bot started for {pair}',
            'pid': process.pid
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    """Stop the trading bot (no-op on Render: use Background Worker instead)"""
    global bot_start_time

    if os.getenv('RENDER'):
        return jsonify({
            'success': False,
            'error': 'On Render the bot runs as a Background Worker; start/stop is not available from the UI.'
        }), 503

    pids = _find_bot_pids()
    if not pids:
        return jsonify({
            'success': False,
            'error': 'Bot is not running'
        }), 400

    try:
        _add_system_log('WARNING', 'Stop signal received...')

        # Production (GCP VM): stop via systemd so it does not get restarted
        stopped_via_service = BOT_SERVICE_UNIT.exists() and _systemctl_bot('stop')

        if not stopped_via_service:
            # SIGTERM triggers bot_runner's graceful shutdown; SIGKILL as last resort
            for pid in pids:
                try:
                    os.kill(pid, os_signal.SIGTERM)
                except ProcessLookupError:
                    pass

            deadline = time.time() + 10
            while _find_bot_pids() and time.time() < deadline:
                time.sleep(0.5)

            for pid in _find_bot_pids():
                try:
                    os.kill(pid, os_signal.SIGKILL)
                except ProcessLookupError:
                    pass

        _add_system_log('SYSTEM', 'Trading bot stopped')
        bot_start_time = None

        return jsonify({
            'success': True,
            'message': 'Bot stopped successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# CONNECTION TEST ENDPOINTS
# ============================================================================

@app.route('/api/test/fxcm', methods=['POST'])
def test_fxcm_connection():
    """Test FXCM connection with provided or stored credentials"""
    data = request.json or {}
    
    # Use provided credentials or fall back to env
    login_id = data.get('loginId') or os.getenv('FXCM_LOGIN_ID', '')
    password = data.get('password') or os.getenv('FXCM_PASSWORD', '')
    url = data.get('url') or os.getenv('FXCM_URL', 'http://www.fxcorporate.com/Hosts.jsp')
    connection = data.get('connection') or os.getenv('FXCM_CONNECTION', 'Demo')
    
    if not login_id or not password:
        return jsonify({
            'success': False,
            'error': 'Login ID and Password are required'
        }), 400
    
    try:
        # Try to import forexconnect
        from forexconnect import ForexConnect
        
        # Attempt connection
        fx = ForexConnect()
        fx.login(login_id, password, url, connection, None, None, None)
        
        # Get account info if connected
        accounts = fx.get_table(fx.ACCOUNTS)
        account_info = None
        if accounts and accounts.size > 0:
            account = accounts.get_row(0)
            account_info = {
                'accountId': account.account_id,
                'balance': account.balance,
                'equity': account.equity,
                'usedMargin': account.used_margin,
            }
        
        fx.logout()
        
        return jsonify({
            'success': True,
            'message': 'Connection successful!',
            'account': account_info,
            'server': connection,
        })
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'ForexConnect library not installed. Install it with: pip install forexconnect',
            'details': 'The forexconnect package is required to connect to FXCM.'
        }), 500
        
    except Exception as e:
        error_msg = str(e)
        # Parse common FXCM errors
        if 'incorrect login' in error_msg.lower() or 'authentication' in error_msg.lower():
            return jsonify({
                'success': False,
                'error': 'Invalid credentials. Please check your Login ID and Password.',
                'details': error_msg
            }), 401
        elif 'connection' in error_msg.lower() or 'network' in error_msg.lower():
            return jsonify({
                'success': False,
                'error': 'Connection failed. Please check your internet connection and server URL.',
                'details': error_msg
            }), 503
        else:
            return jsonify({
                'success': False,
                'error': f'Connection failed: {error_msg}',
                'details': error_msg
            }), 500


@app.route('/api/test/slack', methods=['POST'])
def test_slack_connection():
    """Test Slack connection with provided or stored credentials"""
    data = request.json or {}
    
    # Use provided credentials or fall back to env
    bot_token = data.get('botToken') or os.getenv('SLACK_BOT_TOKEN', '')
    channel = data.get('channel') or os.getenv('SLACK_CHANNEL', '')
    
    if not bot_token:
        return jsonify({
            'success': False,
            'error': 'Slack Bot Token is required'
        }), 400
    
    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
        import ssl
        import certifi
        
        # Create SSL context
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Create client and test auth
        client = WebClient(token=bot_token, ssl=ssl_context)
        
        # Test authentication
        auth_response = client.auth_test()
        
        result = {
            'success': True,
            'message': 'Slack connection successful!',
            'bot': {
                'name': auth_response.get('user'),
                'team': auth_response.get('team'),
                'botId': auth_response.get('bot_id'),
            }
        }
        
        # Test channel access if provided
        if channel:
            try:
                # Try to get channel info (remove # if present)
                channel_name = channel.lstrip('#')
                conversations = client.conversations_list(types="public_channel,private_channel")
                channel_found = any(
                    c['name'] == channel_name 
                    for c in conversations.get('channels', [])
                )
                result['channel'] = {
                    'name': channel,
                    'accessible': channel_found
                }
                if not channel_found:
                    result['warning'] = f'Channel {channel} not found or bot not invited'
            except SlackApiError:
                result['channel'] = {'name': channel, 'accessible': False}
                result['warning'] = 'Could not verify channel access'
        
        return jsonify(result)
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'slack_sdk library not installed. Install it with: pip install slack_sdk'
        }), 500
        
    except Exception as e:
        error_msg = str(e)
        if 'invalid_auth' in error_msg.lower():
            return jsonify({
                'success': False,
                'error': 'Invalid Slack token. Please check your Bot Token.',
                'details': error_msg
            }), 401
        else:
            return jsonify({
                'success': False,
                'error': f'Slack connection failed: {error_msg}',
                'details': error_msg
            }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """API health check"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'database': DB_PATH.exists(),
        'envFile': ENV_PATH.exists(),
    })


# ============================================================================
# ACTIVITY LOG ENDPOINTS - Real-time logging via SSE
# ============================================================================

def get_activity_logs_connection():
    """Get SQLite connection for activity logs"""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get recent activity logs (excludes TRADER debug logs by default)"""
    conn = get_activity_logs_connection()
    if not conn:
        return jsonify({'logs': []})
    
    try:
        cursor = conn.cursor()
        limit = int(request.args.get('limit', 100))
        include_debug = request.args.get('include_debug', 'false').lower() == 'true'
        
        if include_debug:
            cursor.execute('''
                SELECT id, timestamp, type, message, pair, details
                FROM activity_logs
                ORDER BY id DESC
                LIMIT ?
            ''', (limit,))
        else:
            # Exclude TRADER logs (debug logs) by default
            cursor.execute('''
                SELECT id, timestamp, type, message, pair, details
                FROM activity_logs
                WHERE type != 'TRADER'
                ORDER BY id DESC
                LIMIT ?
            ''', (limit,))
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                'id': row['id'],
                'timestamp': row['timestamp'],
                'type': row['type'],
                'message': row['message'],
                'pair': row['pair'],
                'details': row['details']
            })
        
        conn.close()
        return jsonify({'logs': logs})
        
    except sqlite3.OperationalError as e:
        return jsonify({'logs': [], 'error': f'Table not found: {str(e)}'})


@app.route('/api/logs/stream')
def stream_logs():
    """
    Server-Sent Events (SSE) endpoint for real-time log streaming.
    Client connects and receives new logs as they are added to the database.
    Use ?include_debug=true to include TRADER (debug) logs.
    """
    include_debug = request.args.get('include_debug', 'false').lower() == 'true'
    
    def generate(with_debug):
        conn = get_activity_logs_connection()
        if not conn:
            yield f"data: {json.dumps({'error': 'Database not found'})}\n\n"
            return
        
        cursor = conn.cursor()
        
        # Initialize with latest log ID
        try:
            cursor.execute('SELECT MAX(id) FROM activity_logs')
            result = cursor.fetchone()
            last_id = result[0] if result[0] else 0
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            last_id = 0
        
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'lastId': last_id, 'includeDebug': with_debug})}\n\n"
        
        # Keep connection open and poll for new logs
        while True:
            try:
                # Reconnect to get fresh data
                conn = get_activity_logs_connection()
                if not conn:
                    time.sleep(1)
                    continue
                    
                cursor = conn.cursor()
                
                if with_debug:
                    # Include all logs including TRADER (debug)
                    cursor.execute('''
                        SELECT id, timestamp, type, message, pair, details
                        FROM activity_logs
                        WHERE id > ?
                        ORDER BY id ASC
                    ''', (last_id,))
                else:
                    # Exclude TRADER logs (debug logs) to avoid flooding
                    cursor.execute('''
                        SELECT id, timestamp, type, message, pair, details
                        FROM activity_logs
                        WHERE id > ? AND type != 'TRADER'
                        ORDER BY id ASC
                    ''', (last_id,))
                
                new_logs = cursor.fetchall()
                
                for log in new_logs:
                    log_data = {
                        'id': log['id'],
                        'timestamp': log['timestamp'],
                        'type': log['type'],
                        'message': log['message'],
                        'pair': log['pair'],
                        'details': log['details']
                    }
                    yield f"data: {json.dumps(log_data)}\n\n"
                    last_id = log['id']
                
                # If not including debug, still update last_id to max to skip TRADER logs
                if not with_debug:
                    cursor.execute('SELECT MAX(id) FROM activity_logs')
                    result = cursor.fetchone()
                    if result[0]:
                        last_id = result[0]
                
                conn.close()
                
            except sqlite3.OperationalError:
                # Table might not exist yet, wait and retry
                pass
            except GeneratorExit:
                # Client disconnected
                break
            
            # Poll interval - check for new logs every 500ms
            time.sleep(0.5)
    
    return Response(
        generate(include_debug),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',  # Disable nginx buffering
            'Access-Control-Allow-Origin': '*'
        }
    )


@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    """Clear all activity logs"""
    conn = get_activity_logs_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database not found'})
    
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM activity_logs')
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Activity logs cleared'})
    except sqlite3.OperationalError as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/logs/add', methods=['POST'])
def add_log():
    """
    Add a new activity log (for testing or external integrations).
    Body: { type: string, message: string, pair?: string, details?: string }
    """
    data = request.json
    if not data or 'type' not in data or 'message' not in data:
        return jsonify({'success': False, 'error': 'type and message required'}), 400
    
    conn = get_activity_logs_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database not found'})
    
    try:
        cursor = conn.cursor()
        
        # Ensure table exists
        cursor.execute('''
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
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO activity_logs (timestamp, type, message, pair, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, data['type'], data['message'], data.get('pair'), data.get('details')))
        
        conn.commit()
        log_id = cursor.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'id': log_id})
        
    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': str(e)})


# ============================================================================
# BACKTEST ENDPOINTS
# ============================================================================
# Read-only access to the SQLite databases produced by the MP-DH415-BT
# backtesting engine (table `trades`). DB files are discovered in:
#   1. $BACKTEST_DB_DIR (if set)
#   2. <repo root>/backtest/          (drop .db files here on the server)
#   3. ../MP-DH415-BT/                (sibling project, local dev)
# On duplicate filenames the first directory wins.

_BACKTEST_DB_DIRS = []
if os.getenv('BACKTEST_DB_DIR'):
    _BACKTEST_DB_DIRS.append(Path(os.getenv('BACKTEST_DB_DIR')))
_BACKTEST_DB_DIRS.append(_REPO_ROOT / 'backtest')
_BACKTEST_DB_DIRS.append(_REPO_ROOT.parent / 'MP-DH415-BT')

# Columns as written by the backtester (martina_BT.py / db_utils.py).
# Older yearly archives may miss the last two: they are selected as NULL.
_BT_COLUMNS = [
    'pair', 'status', 'trade_type', 'entry_date', 'close_date',
    'entry_price', 'entry_price_index', 'stop_loss', 'target', 'direction',
    'initial_risk_reward', 'final_risk_reward', 'profit', 'result',
    'zones_rectX1_DLY', 'zones_rectY1_DLY', 'zones_rectY2_DLY',
    'zones_rectX1_H4', 'zones_rectY1_H4', 'zones_rectY2_H4',
    'pattern_x1', 'pattern_y1', 'pattern_y2',
    'breakup_date', 'fibonacci100',
]


def find_backtest_dbs():
    """Discover available backtest DB files. Returns {filename: Path}."""
    dbs = {}
    for directory in _BACKTEST_DB_DIRS:
        if not directory.is_dir():
            continue
        for f in sorted(directory.glob('*.db')):
            if f.name not in dbs:
                dbs[f.name] = f
    return dbs


def _backtest_label(filename):
    """my_database_2024.db -> '2024', my_database.db -> 'Latest'"""
    match = re.search(r'(\d{4})', filename)
    return match.group(1) if match else 'Latest'


@app.route('/api/backtest/databases', methods=['GET'])
def get_backtest_databases():
    """List available backtest databases with basic info"""
    databases = []
    for name, path in find_backtest_dbs().items():
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*), COUNT(DISTINCT pair) FROM trades')
            trades_count, pairs_count = cursor.fetchone()
            conn.close()
        except sqlite3.Error:
            continue  # not a backtest DB, skip
        databases.append({
            'name': name,
            'label': _backtest_label(name),
            'trades': trades_count,
            'pairs': pairs_count,
        })
    # 'Latest' first (letters sort after digits), then years descending
    databases.sort(key=lambda d: d['label'], reverse=True)
    return jsonify({'databases': databases})


@app.route('/api/backtest/trades', methods=['GET'])
def get_backtest_trades():
    """Get backtest trades from a selected DB, with filters and pagination.

    Query params: db (filename), pair, direction (LONG|SHORT),
    result (TARGET|STOP LOSS), type (FULL|PARTIAL), status,
    limit (default 50, max 20000), offset.
    """
    dbs = find_backtest_dbs()
    if not dbs:
        return jsonify({
            'trades': [], 'total': 0, 'pairs': [], 'stats': None,
            'message': 'No backtest database found. Put .db files in backtest/ or set BACKTEST_DB_DIR.',
        })

    db_name = request.args.get('db')
    if db_name and db_name not in dbs:
        return jsonify({'error': f'Unknown database: {db_name}'}), 404
    if not db_name:
        db_name = next(iter(dbs))

    try:
        limit = min(max(int(request.args.get('limit', 50)), 1), 20000)
        offset = max(int(request.args.get('offset', 0)), 0)
    except ValueError:
        return jsonify({'error': 'limit/offset must be integers'}), 400

    where, params = [], []
    if request.args.get('pair'):
        where.append('pair = ?')
        params.append(request.args.get('pair'))
    if request.args.get('direction'):
        where.append('UPPER(direction) = ?')
        params.append(request.args.get('direction').upper())
    if request.args.get('result'):
        where.append('UPPER(result) = ?')
        params.append(request.args.get('result').upper())
    if request.args.get('type'):
        where.append('UPPER(trade_type) = ?')
        params.append(request.args.get('type').upper())
    if request.args.get('status'):
        where.append('UPPER(status) = ?')
        params.append(request.args.get('status').upper())
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

    try:
        conn = sqlite3.connect(dbs[db_name])
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Older DBs miss some columns: select what exists, NULL the rest
        cursor.execute('PRAGMA table_info(trades)')
        existing = {row[1] for row in cursor.fetchall()}
        select_cols = ', '.join(
            f'"{c}"' if c in existing else f'NULL AS "{c}"' for c in _BT_COLUMNS
        )

        # Entry date can be empty for trades invalidated during retest:
        # fall back to breakup_date for a stable chronological order
        if 'breakup_date' in existing:
            date_col = "COALESCE(NULLIF(entry_date, ''), breakup_date)"
        else:
            date_col = 'entry_date'
        order_sql = f"ORDER BY {iso_date_expr(date_col)} DESC, rowid DESC"

        cursor.execute(f'SELECT COUNT(*) FROM trades {where_sql}', params)
        total = cursor.fetchone()[0]

        cursor.execute(f'''
            SELECT COUNT(*) AS n,
                   SUM(CASE WHEN UPPER(result) = 'TARGET' THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN UPPER(result) = 'STOP LOSS' THEN 1 ELSE 0 END) AS losses,
                   COALESCE(SUM(CAST(profit AS REAL)), 0) AS profit,
                   COALESCE(AVG(CASE WHEN initial_risk_reward != ''
                                     THEN CAST(initial_risk_reward AS REAL) END), 0) AS avg_rr
            FROM trades {where_sql}
        ''', params)
        s = cursor.fetchone()
        wins = s['wins'] or 0
        losses = s['losses'] or 0
        decided = wins + losses
        stats = {
            'totalTrades': total,
            'wins': wins,
            'losses': losses,
            'winRate': round(wins * 100 / decided, 1) if decided else 0,
            'totalProfitR': round(s['profit'], 2),
            'avgRR': round(s['avg_rr'], 2),
        }

        cursor.execute('SELECT DISTINCT pair FROM trades ORDER BY pair')
        pairs = [row['pair'] for row in cursor.fetchall()]

        cursor.execute(f'''
            SELECT rowid AS id, {select_cols}
            FROM trades {where_sql} {order_sql}
            LIMIT ? OFFSET ?
        ''', params + [limit, offset])
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({
            'db': db_name,
            'trades': trades,
            'total': total,
            'limit': limit,
            'offset': offset,
            'pairs': pairs,
            'stats': stats,
        })
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# BACKTEST RUNNER ENDPOINTS
# ============================================================================
# Launch/stop/monitor backend/backtest_runner.py, which drives the
# MP-DH415-BT engine (martina_BT.py) pair by pair. Progress is logged to the
# backtest_logs table (same shape as activity_logs) and streamed via SSE.

BACKTEST_ENGINE_DIR = Path(os.getenv('BACKTEST_ENGINE_DIR', str(_REPO_ROOT.parent / 'MP-DH415-BT')))
_PAIR_RE = re.compile(r'^[A-Z]{3}/[A-Z]{3}$')


def _find_backtest_runner_pids():
    """Return PIDs of any running backtest_runner.py."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', r'backtest_runner\.py'],
            capture_output=True, text=True, timeout=10
        )
        return [int(pid) for pid in result.stdout.split()]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []


def _ensure_backtest_logs_table(cursor):
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


def _add_backtest_log(log_type, message, pair=None):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        _ensure_backtest_logs_table(cursor)
        cursor.execute('''
            INSERT INTO backtest_logs (timestamp, type, message, pair)
            VALUES (?, ?, ?, ?)
        ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), log_type, message, pair))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass


@app.route('/api/backtest/run', methods=['POST'])
def start_backtest():
    """Start a backtest run: {year: 2024, pairs: [...], clean: bool}
    (or explicit datefrom/dateto in 'MM.DD.YYYY HH:MM:SS' format)."""
    data = request.json or {}

    pairs = data.get('pairs') or []
    if not isinstance(pairs, list) or not pairs:
        return jsonify({'success': False, 'error': 'Select at least one pair'}), 400
    invalid = [p for p in pairs if not isinstance(p, str) or not _PAIR_RE.match(p)]
    if invalid:
        return jsonify({'success': False, 'error': f'Invalid pairs: {invalid}'}), 400

    if data.get('datefrom') and data.get('dateto'):
        datefrom, dateto = data['datefrom'], data['dateto']
        try:
            datetime.strptime(datefrom, '%m.%d.%Y %H:%M:%S')
            datetime.strptime(dateto, '%m.%d.%Y %H:%M:%S')
        except ValueError:
            return jsonify({'success': False,
                            'error': 'Dates must be in MM.DD.YYYY HH:MM:SS format'}), 400
    else:
        try:
            year = int(data.get('year'))
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Provide a year or a date range'}), 400
        if not 2010 <= year <= datetime.now().year:
            return jsonify({'success': False, 'error': f'Year out of range: {year}'}), 400
        datefrom = f'01.01.{year} 00:00:00'
        dateto = f'12.31.{year} 23:00:00'

    if not (BACKTEST_ENGINE_DIR / 'martina_BT.py').exists():
        return jsonify({
            'success': False,
            'error': f'Backtest engine not found in {BACKTEST_ENGINE_DIR} '
                     '(set BACKTEST_ENGINE_DIR or install the MP-DH415-BT project there)'
        }), 400

    if not os.getenv('FXCM_LOGIN_ID') or not os.getenv('FXCM_PASSWORD'):
        return jsonify({'success': False,
                        'error': 'FXCM credentials not configured (Settings page)'}), 400

    if _find_backtest_runner_pids():
        return jsonify({'success': False, 'error': 'A backtest is already running'}), 400

    try:
        runner = _REPO_ROOT / 'backend' / 'backtest_runner.py'
        cmd = [sys.executable, str(runner),
               '--pairs', ','.join(pairs),
               '--datefrom', datefrom,
               '--dateto', dateto]
        if data.get('clean', False):
            cmd.append('--clean')

        log_path = runner.parent / 'backtest_runner.py.log'
        with open(log_path, 'ab') as log_file:
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=str(runner.parent),
                start_new_session=True
            )
        return jsonify({'success': True,
                        'message': f'Backtest started on {len(pairs)} pair(s)',
                        'pid': process.pid})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/backtest/run/status', methods=['GET'])
def get_backtest_run_status():
    pids = _find_backtest_runner_pids()
    return jsonify({
        'running': len(pids) > 0,
        'pid': pids[0] if pids else None,
    })


@app.route('/api/backtest/run/stop', methods=['POST'])
def stop_backtest():
    """Stop the running backtest (SIGTERM to the runner's process group,
    so the engine subprocess is terminated too)."""
    pids = _find_backtest_runner_pids()
    if not pids:
        return jsonify({'success': False, 'error': 'No backtest is running'}), 400

    try:
        _add_backtest_log('WARNING', 'Stop signal received...')
        for pid in pids:
            try:
                os.killpg(pid, os_signal.SIGTERM)
            except (ProcessLookupError, PermissionError, OSError):
                try:
                    os.kill(pid, os_signal.SIGTERM)
                except ProcessLookupError:
                    pass

        deadline = time.time() + 15
        while _find_backtest_runner_pids() and time.time() < deadline:
            time.sleep(0.5)

        for pid in _find_backtest_runner_pids():
            try:
                os.killpg(pid, os_signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                try:
                    os.kill(pid, os_signal.SIGKILL)
                except ProcessLookupError:
                    pass

        _add_backtest_log('SYSTEM', 'Backtest stopped')
        return jsonify({'success': True, 'message': 'Backtest stopped'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/backtest/logs', methods=['GET'])
def get_backtest_logs():
    """Recent backtest logs (newest first)."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        _ensure_backtest_logs_table(cursor)
        limit = int(request.args.get('limit', 100))
        cursor.execute('''
            SELECT id, timestamp, type, message, pair, details
            FROM backtest_logs
            ORDER BY id DESC
            LIMIT ?
        ''', (limit,))
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({'logs': logs})
    except sqlite3.Error as e:
        return jsonify({'logs': [], 'error': str(e)})


@app.route('/api/backtest/logs/stream')
def stream_backtest_logs():
    """SSE stream of new backtest logs (same protocol as /api/logs/stream)."""
    def generate():
        last_id = 0
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            _ensure_backtest_logs_table(cursor)
            conn.commit()
            cursor.execute('SELECT MAX(id) FROM backtest_logs')
            result = cursor.fetchone()
            last_id = result[0] if result[0] else 0
            conn.close()
        except sqlite3.Error:
            pass

        yield f"data: {json.dumps({'type': 'connected', 'lastId': last_id})}\n\n"

        while True:
            try:
                conn = sqlite3.connect(str(DB_PATH))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, timestamp, type, message, pair, details
                    FROM backtest_logs
                    WHERE id > ?
                    ORDER BY id ASC
                ''', (last_id,))
                for row in cursor.fetchall():
                    yield f"data: {json.dumps(dict(row))}\n\n"
                    last_id = row['id']
                conn.close()
            except sqlite3.OperationalError:
                pass
            except GeneratorExit:
                break
            time.sleep(0.5)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*'
        }
    )


@app.route('/api/backtest/logs/clear', methods=['POST'])
def clear_backtest_logs():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        _ensure_backtest_logs_table(cursor)
        cursor.execute('DELETE FROM backtest_logs')
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print(f"📁 ENV Path: {ENV_PATH}")
    print(f"📁 DB Path: {DB_PATH}")
    print(f"🚀 Starting API server on http://localhost:5001")
    app.run(debug=True, port=5001, host='0.0.0.0')

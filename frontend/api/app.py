"""
Trading Bot API Server
Provides REST endpoints for the React UI to interact with the bot configuration and data.
Includes Server-Sent Events (SSE) for real-time Activity Log streaming.
"""

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from dotenv import load_dotenv, set_key
import os
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
        cursor.execute('''
            SELECT rowid, pair, status, trade_type, entry_date, close_date, 
                   entry_price, stop_loss, target, direction, 
                   initial_risk_reward, final_risk_reward, profit, result
            FROM trades 
            ORDER BY entry_date DESC
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
        cursor.execute('''
            SELECT rowid, pair, status, direction, entry_price, initial_risk_reward
            FROM trades 
            WHERE UPPER(status) NOT IN ('CLOSED', 'COMPLETED', 'STOPPED')
              AND close_date IS NULL
            ORDER BY entry_date DESC
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
        cursor.execute('''
            SELECT SUM(CAST(profit AS REAL)) FROM trades 
            WHERE close_date LIKE ?
        ''', (datetime.now().strftime('%Y-%m-%d') + '%',))
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
        
        # Build date filter
        date_condition = ""
        if time_filter == '24h':
            date_condition = "AND close_date >= datetime('now', '-1 day')"
        elif time_filter == '7d':
            date_condition = "AND close_date >= datetime('now', '-7 days')"
        elif time_filter == 'month':
            date_condition = "AND close_date >= datetime('now', '-30 days')"
        elif time_filter == 'quarter':
            date_condition = "AND close_date >= datetime('now', '-90 days')"
        elif time_filter == 'ytd':
            date_condition = f"AND close_date >= '{datetime.now().year}-01-01'"
        
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
            ORDER BY close_date DESC
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
import signal

# Global variable to track bot process
bot_process = None
bot_start_time = None

@app.route('/api/bot/status', methods=['GET'])
def get_bot_status():
    """Get current bot status"""
    global bot_process, bot_start_time
    
    is_running = bot_process is not None and bot_process.poll() is None
    
    return jsonify({
        'status': 'running' if is_running else 'stopped',
        'pid': bot_process.pid if is_running else None,
        'simulationMode': os.getenv('SIMULATION_MODE', 'True') == 'True',
        'startTime': bot_start_time.isoformat() if bot_start_time and is_running else None,
    })


@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    """Start the trading bot (no-op on Render: use Background Worker instead)"""
    global bot_process, bot_start_time

    if os.getenv('RENDER'):
        return jsonify({
            'success': False,
            'error': 'On Render the bot runs as a Background Worker; start/stop is not available from the UI.'
        }), 503

    # Check if bot is already running
    if bot_process is not None and bot_process.poll() is None:
        return jsonify({
            'success': False,
            'error': 'Bot is already running',
            'pid': bot_process.pid
        }), 400
    
    # Get configuration from request or env
    data = request.json or {}
    pair = data.get('pair', os.getenv('ACTIVE_PAIRS', 'EUR/USD').split(',')[0])
    
    # Get FXCM credentials
    login_id = os.getenv('FXCM_LOGIN_ID', '')
    password = os.getenv('FXCM_PASSWORD', '')
    url = os.getenv('FXCM_URL', 'http://www.fxcorporate.com/Hosts.jsp')
    connection = os.getenv('FXCM_CONNECTION', 'Demo')
    
    if not login_id or not password:
        return jsonify({
            'success': False,
            'error': 'FXCM credentials not configured'
        }), 400
    
    # Build command - use bot_runner.py for continuous scanning
    bot_script = Path(__file__).resolve().parent.parent.parent / 'backend' / 'bot_runner.py'
    python_path = '/opt/homebrew/bin/python3.10'
    
    # Get scan interval from request or default to 60 seconds
    interval = data.get('interval', 60)
    
    cmd = [
        python_path,
        str(bot_script),
        '--interval', str(interval)
    ]
    
    # Add specific pairs if provided
    if data.get('pairs'):
        cmd.extend(['--pairs', data.get('pairs')])
    
    try:
        # Add activity log
        conn = get_activity_logs_connection()
        if conn:
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
            ''', (timestamp, 'SYSTEM', f'Starting bot for {pair}...', pair))
            conn.commit()
            conn.close()
        
        # Start bot process
        bot_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(bot_script.parent),
            text=True,
            bufsize=1
        )
        bot_start_time = datetime.now()
        
        return jsonify({
            'success': True,
            'message': f'Bot started for {pair}',
            'pid': bot_process.pid
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    """Stop the trading bot (no-op on Render: use Background Worker instead)"""
    global bot_process, bot_start_time

    if os.getenv('RENDER'):
        return jsonify({
            'success': False,
            'error': 'On Render the bot runs as a Background Worker; start/stop is not available from the UI.'
        }), 503

    if bot_process is None or bot_process.poll() is not None:
        return jsonify({
            'success': False,
            'error': 'Bot is not running'
        }), 400
    
    try:
        # Add activity log
        conn = get_activity_logs_connection()
        if conn:
            cursor = conn.cursor()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO activity_logs (timestamp, type, message)
                VALUES (?, ?, ?)
            ''', (timestamp, 'WARNING', 'Stop signal received...'))
            conn.commit()
            conn.close()
        
        # Terminate the process
        bot_process.terminate()
        
        # Wait a bit for graceful shutdown
        try:
            bot_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill if it doesn't stop
            bot_process.kill()
            bot_process.wait()
        
        # Add stopped log
        conn = get_activity_logs_connection()
        if conn:
            cursor = conn.cursor()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO activity_logs (timestamp, type, message)
                VALUES (?, ?, ?)
            ''', (timestamp, 'SYSTEM', 'Trading bot stopped'))
            conn.commit()
            conn.close()
        
        bot_process = None
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
# MAIN
# ============================================================================

if __name__ == '__main__':
    print(f"📁 ENV Path: {ENV_PATH}")
    print(f"📁 DB Path: {DB_PATH}")
    print(f"🚀 Starting API server on http://localhost:5001")
    app.run(debug=True, port=5001, host='0.0.0.0')

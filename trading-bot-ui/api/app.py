"""
Trading Bot API Server
Provides REST endpoints for the React UI to interact with the bot configuration and data.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv, set_key
import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Load .env from parent directory
ENV_PATH = Path(__file__).resolve().parent.parent.parent / '.env'
DB_PATH = Path(__file__).resolve().parent.parent.parent / 'my_database.db'

load_dotenv(ENV_PATH)

app = Flask(__name__)

# Enable CORS for React frontend - explicit configuration
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
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
    """Update configuration in .env file"""
    data = request.json
    
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
        
        # Get active trades
        cursor.execute('''
            SELECT * FROM trade 
            WHERE (in_progress = 1 OR in_retest = 1)
            ORDER BY timestamp DESC
        ''')
        active_trades = [dict(row) for row in cursor.fetchall()]
        
        # Get closed trades
        cursor.execute('''
            SELECT * FROM trade 
            WHERE closed = 1
            ORDER BY timestamp DESC
            LIMIT 50
        ''')
        closed_trades = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'active': active_trades,
            'closed': closed_trades,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
        
        # Active trades count
        cursor.execute('SELECT COUNT(*) FROM trade WHERE in_progress = 1')
        active_count = cursor.fetchone()[0]
        
        # Waiting retest count
        cursor.execute('SELECT COUNT(*) FROM trade WHERE in_retest = 1')
        retest_count = cursor.fetchone()[0]
        
        # Total closed trades
        cursor.execute('SELECT COUNT(*) FROM trade WHERE closed = 1')
        total_closed = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'activeTrades': active_count,
            'waitingRetest': retest_count,
            'todayProfit': 0,  # TODO: Calculate from actual P/L
            'totalTrades': total_closed,
            'winRate': 0,  # TODO: Calculate from results
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

@app.route('/api/bot/status', methods=['GET'])
def get_bot_status():
    """Get current bot status"""
    # TODO: Implement actual bot status check
    return jsonify({
        'status': 'stopped',
        'simulationMode': os.getenv('SIMULATION_MODE', 'True') == 'True',
        'lastRun': None,
    })


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
# MAIN
# ============================================================================

if __name__ == '__main__':
    print(f"📁 ENV Path: {ENV_PATH}")
    print(f"📁 DB Path: {DB_PATH}")
    print(f"🚀 Starting API server on http://localhost:5001")
    app.run(debug=True, port=5001, host='0.0.0.0')

#!/usr/bin/env python3
"""
Bot Runner - Continuous Trading Bot
Executes martina.py for each configured currency pair in a loop.
Designed to work with the React UI via Activity Log system.
"""

import os
import sys
import time
import signal
import subprocess
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import logging functions
from db_utils import (
    initialize_activity_logs_db, initialize_signals_db,
    add_activity_log, SIMULATION_MODE
)

# Global flag for graceful shutdown
running = True

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global running
    add_activity_log('WARNING', 'Shutdown signal received...')
    running = False

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def parse_args():
    parser = argparse.ArgumentParser(description='Continuous Trading Bot Runner')
    parser.add_argument('--interval', type=int, default=300, 
                        help='Scan interval in seconds (default: 300 = 5 minutes)')
    parser.add_argument('--pairs', type=str, default=None,
                        help='Comma-separated pairs to scan (default: from ACTIVE_PAIRS env)')
    parser.add_argument('--single-run', action='store_true',
                        help='Run once and exit (no loop)')
    return parser.parse_args()


def get_pairs():
    """Get currency pairs from environment"""
    pairs_str = os.getenv('ACTIVE_PAIRS', 'EUR/USD')
    return [p.strip() for p in pairs_str.split(',') if p.strip()]


def run_martina_for_pair(pair):
    """
    Execute martina.py for a single currency pair.
    Returns True if successful, False if error.
    """
    # Get FXCM credentials
    login_id = os.getenv('FXCM_LOGIN_ID', '')
    password = os.getenv('FXCM_PASSWORD', '')
    url = os.getenv('FXCM_URL', 'http://www.fxcorporate.com/Hosts.jsp')
    connection = os.getenv('FXCM_CONNECTION', 'Demo')
    
    # Build command
    script_dir = os.path.dirname(os.path.abspath(__file__))
    martina_script = os.path.join(script_dir, 'martina.py')
    python_path = '/opt/homebrew/bin/python3.10'
    
    cmd = [
        python_path,
        martina_script,
        '-l', login_id,
        '-p', password,
        '-u', url,
        '-c', connection,
        '-i', pair,
        '--from-runner'  # Skip redundant startup logs
    ]
    
    add_activity_log('INFO', f'Executing full analysis for {pair}...', pair=pair)
    
    try:
        # Run martina.py and capture output
        result = subprocess.run(
            cmd,
            cwd=script_dir,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout per pair
        )
        
        # Check for errors
        if result.returncode != 0:
            error_msg = result.stderr[:200] if result.stderr else 'Unknown error'
            add_activity_log('ERROR', f'{pair}: martina.py failed - {error_msg}', pair=pair)
            return False
        
        # Log completion
        add_activity_log('SUCCESS', f'{pair}: Analysis complete', pair=pair)
        return True
        
    except subprocess.TimeoutExpired:
        add_activity_log('ERROR', f'{pair}: Analysis timeout (>120s)', pair=pair)
        return False
    except Exception as e:
        add_activity_log('ERROR', f'{pair}: {str(e)}', pair=pair)
        return False


def main():
    global running
    
    args = parse_args()
    
    # Initialize databases
    initialize_activity_logs_db()
    if SIMULATION_MODE:
        initialize_signals_db()
    
    # Start logging
    mode = 'SIMULATION' if SIMULATION_MODE else 'LIVE'
    add_activity_log('SYSTEM', f'Trading bot starting in {mode} mode...')
    add_activity_log('INFO', 'Initializing FXCM API connection...')
    
    # Get pairs to scan
    pairs = args.pairs.split(',') if args.pairs else get_pairs()
    add_activity_log('INFO', f'Configured {len(pairs)} pairs: {", ".join(pairs[:5])}{"..." if len(pairs) > 5 else ""}')
    add_activity_log('INFO', f'Scan interval: {args.interval} seconds')
    
    # Verify credentials
    login_id = os.getenv('FXCM_LOGIN_ID', '')
    password = os.getenv('FXCM_PASSWORD', '')
    
    if not login_id or not password:
        add_activity_log('ERROR', 'FXCM credentials not configured!')
        return 1
    
    add_activity_log('SUCCESS', 'Connected to FXCM API successfully')
    
    scan_count = 0
    
    # Main loop
    while running:
        scan_count += 1
        add_activity_log('SYSTEM', f'===== Starting scan cycle #{scan_count} =====')
        
        successful = 0
        failed = 0
        
        for pair in pairs:
            if not running:
                break
            
            if run_martina_for_pair(pair):
                successful += 1
            else:
                failed += 1
            
            # Small delay between pairs
            if running:
                time.sleep(2)
        
        add_activity_log('SYSTEM', f'Scan cycle #{scan_count} complete: {successful} OK, {failed} errors')
        
        if args.single_run:
            add_activity_log('INFO', 'Single run mode - exiting')
            break
        
        # Wait for next scan
        if running:
            add_activity_log('INFO', f'Heartbeat: Bot active. Next scan in {args.interval}s...')
            
            # Sleep in small increments to respond to stop signal faster
            for i in range(args.interval):
                if not running:
                    break
                time.sleep(1)
                # Log progress every minute
                if (i + 1) % 60 == 0 and running:
                    remaining = args.interval - i - 1
                    add_activity_log('SYSTEM', f'Waiting... {remaining}s until next scan')
    
    # Graceful shutdown
    add_activity_log('WARNING', 'Stop signal received...')
    add_activity_log('INFO', 'Closing connections...')
    add_activity_log('SYSTEM', 'Trading bot stopped')
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

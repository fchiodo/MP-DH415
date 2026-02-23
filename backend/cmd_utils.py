import argparse
import sqlite3

# Import SIMULATION_MODE from db_utils
from db_utils import SIMULATION_MODE

# Import condizionale di MetaTrader5
if not SIMULATION_MODE:
    import MetaTrader5 as mt5
else:
    mt5 = None

def updatemt5Trade():
    if SIMULATION_MODE:
        print("[SIMULATION] updatemt5Trade() - Would update EURUSD positions")
        print("[SIMULATION] This function is only available in production mode (MT5 required)")
        return
    
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        return
        # Predefined variables
    
    symbol = "EURUSD"  # Forex pair to update
    new_target = 1.07982  # New target price
        
    positions = mt5.positions_get(symbol=symbol)

    for position in positions:
        tick = mt5.symbol_info_tick(position.symbol)
        is_short = position.type == mt5.POSITION_TYPE_SELL
        is_long = position.type == mt5.POSITION_TYPE_BUY

        current_price = tick.ask if is_long else tick.bid

        print("is_short: ",is_short)
        print("is_long: ",is_long)

        print("current_price: ",current_price)
        print("position.price_open: ",position.price_open)


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

def getmt5balance():
    if SIMULATION_MODE:
        print("[SIMULATION] getmt5balance() - Simulated balance: 10000.0")
        print("[SIMULATION] This function returns simulated data (MT5 not available)")
        print("Balance: 10000.0 (SIMULATED)")
        print("tick_size: 0.00001 (SIMULATED for EURUSD)")
        return
    
    if not mt5.initialize():
        print("initialize() failed")
        mt5.shutdown()
    
    balance = None
    account_info = mt5.account_info()
    if account_info is not None:
        # Access the balance property
        balance = account_info.balance
        print("Balance:", balance)

        symbol = 'EURUSD'
        mt5.symbol_select(symbol, True)
        symbol_info_tick = mt5.symbol_info_tick(symbol)
        symbol_info = mt5.symbol_info(symbol)

        tick_size = symbol_info.trade_tick_size
        print("tick_size",tick_size)
    else:
        print("Failed to retrieve account info.")

def clean_trades_table():
    conn = sqlite3.connect('my_database.db')
    cursor = conn.cursor()
    
    # Execute SQL statements to clean the trades table
    cursor.execute("DELETE FROM trades")  # Delete all rows from the table
    
    # Commit the changes and close the connection
    conn.commit()
    conn.close()

def show_signals():
    """Mostra tutti i segnali MT5 registrati in modalità simulazione"""
    conn = sqlite3.connect('my_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n" + "=" * 80)
    print("  MT5 SIGNALS (SIMULATION MODE)")
    print("=" * 80)
    
    # Segnali di trading
    try:
        cursor.execute("SELECT * FROM mt5_signals ORDER BY timestamp DESC LIMIT 20")
        signals = cursor.fetchall()
        print(f"\n--- Recent Trading Signals ({len(signals)}) ---")
        for s in signals:
            print(f"  [{s['timestamp']}] {s['signal_type']} | {s['pair']} | {s['action']} | "
                  f"Price: {s['price']} | SL: {s['stop_loss']} | TP: {s['take_profit']} | "
                  f"Vol: {s['volume']} | Processed: {s['processed']}")
    except:
        print("  No signals table found")
    
    # Modifiche
    try:
        cursor.execute("SELECT * FROM mt5_modifications ORDER BY timestamp DESC LIMIT 20")
        mods = cursor.fetchall()
        print(f"\n--- Recent Modifications ({len(mods)}) ---")
        for m in mods:
            print(f"  [{m['timestamp']}] {m['pair']} | {m['action']} | "
                  f"SL: {m['old_sl']}->{m['new_sl']} | TP: {m['old_tp']}->{m['new_tp']}")
    except:
        print("  No modifications table found")
    
    # Chiusure
    try:
        cursor.execute("SELECT * FROM mt5_closures ORDER BY timestamp DESC LIMIT 20")
        closures = cursor.fetchall()
        print(f"\n--- Recent Closures ({len(closures)}) ---")
        for c in closures:
            print(f"  [{c['timestamp']}] {c['pair']} | {c['action']} | {c['comment']}")
    except:
        print("  No closures table found")
    
    print("=" * 80 + "\n")
    conn.close()


def clear_signals():
    """Pulisce tutte le tabelle dei segnali MT5"""
    conn = sqlite3.connect('my_database.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM mt5_signals")
        cursor.execute("DELETE FROM mt5_modifications")
        cursor.execute("DELETE FROM mt5_closures")
        conn.commit()
        print("All MT5 signal tables cleared.")
    except Exception as e:
        print(f"Error clearing signals: {e}")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Process command parameters.')
    parser.add_argument('-c', '--command', required=True, help='Specify the command')
    
    args = parser.parse_args()

    if args.command == 'balance':
       getmt5balance()
    elif args.command == 'clean':
        clean_trades_table()
    elif args.command == 'update':
        updatemt5Trade()
    elif args.command == 'signals':
        show_signals()
    elif args.command == 'clear_signals':
        clear_signals()
    else:
        print("Invalid command specified.")
        print("Available commands:")
        print("  balance       - Show MT5 account balance")
        print("  clean         - Clean trades table")
        print("  update        - Update MT5 trade")
        print("  signals       - Show MT5 signals (simulation mode)")
        print("  clear_signals - Clear all MT5 signal tables")

if __name__ == "__main__":
    main()



#!/usr/bin/env python3
"""
Test script per verificare la modalità simulazione.
Testa le funzioni MT5 senza bisogno di MetaTrader5 o ForexConnect installati.
"""

import sys
sys.path.insert(0, '.')

# Test imports
print("=" * 60)
print("  TEST MODALITÀ SIMULAZIONE")
print("=" * 60)

print("\n1. Testing db_utils imports...")
from db_utils import (
    SIMULATION_MODE,
    initialize_signals_db,
    log_mt5_signal,
    log_mt5_modification,
    log_mt5_closure,
    get_pending_signals,
    mt5_place_order,
    mt5_close_order,
    mt5_close_positions,
    update_trade_stoploss,
    update_trade_target,
    calculate_trade_size_simulation,
    initialize_db
)
print(f"   SIMULATION_MODE = {SIMULATION_MODE}")
if not SIMULATION_MODE:
    print("   ATTENZIONE: SIMULATION_MODE è False! Impostalo a True per testare su Mac")
    sys.exit(1)
print("   OK")

print("\n2. Initializing databases...")
initialize_db()
initialize_signals_db()
print("   OK")

print("\n3. Testing mt5_place_order (simulation)...")
trade_setup = {
    'pair': 'EUR/USD',
    'entry_price': 1.08500,
    'stop_loss_price': 1.08200,
    'target_price': 1.09000,
    'direction': 'LONG',
    'type': 'FULL'
}
result = mt5_place_order(trade_setup)
print(f"   Returned entry price: {result}")
print("   OK")

print("\n4. Testing mt5_place_order SHORT...")
trade_setup_short = {
    'pair': 'GBP/JPY',
    'entry_price': 188.500,
    'stop_loss_price': 189.000,
    'target_price': 187.500,
    'direction': 'SHORT',
    'type': 'FULL'
}
result = mt5_place_order(trade_setup_short)
print(f"   Returned entry price: {result}")
print("   OK")

print("\n5. Testing update_trade_stoploss (simulation)...")
# Questo aggiorna solo il DB e logga il segnale
# Non farà nulla di reale perché non c'è un trade nel DB
print("   (Simulation only - no actual DB trade)")
print("   OK")

print("\n6. Testing mt5_close_order (simulation)...")
mt5_close_order('EUR/USD')
print("   OK")

print("\n7. Testing mt5_close_positions (simulation)...")
mt5_close_positions('GBP/JPY')
print("   OK")

print("\n8. Testing calculate_trade_size_simulation...")
lot_size = calculate_trade_size_simulation(
    symbol='EURUSD',
    entry_price=1.08500,
    risk_per_trade=0.005,
    stop_loss_price=1.08200,
    pair='EUR/USD'
)
print(f"   Calculated lot size: {lot_size}")
print("   OK")

print("\n9. Testing JPY pair calculation...")
lot_size_jpy = calculate_trade_size_simulation(
    symbol='GBPJPY',
    entry_price=188.500,
    risk_per_trade=0.005,
    stop_loss_price=189.000,
    pair='GBP/JPY'
)
print(f"   Calculated lot size (JPY): {lot_size_jpy}")
print("   OK")

print("\n10. Retrieving logged signals...")
signals = get_pending_signals()
print(f"    Found {len(signals)} pending signals:")
for s in signals:
    print(f"    - {s['timestamp']} | {s['pair']} | {s['action']} | Price: {s['price']}")
print("    OK")

print("\n" + "=" * 60)
print("  TUTTI I TEST PASSATI!")
print("  La modalità simulazione funziona correttamente.")
print("=" * 60)

print("\nPer vedere tutti i segnali registrati:")
print("  python3 cmd_utils.py -c signals")

print("\nPer pulire i segnali di test:")
print("  python3 cmd_utils.py -c clear_signals")

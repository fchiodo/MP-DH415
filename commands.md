# Terminale 1 — API Flask (porta 5001):
cd /Users/fabiochiodo/Documents/trading-bot/MP-DH415/frontend/api
python3.10 app.py

# Terminale 2 — Frontend React (porta 3000):
cd /Users/fabiochiodo/Documents/trading-bot/MP-DH415/frontend
npm run dev

# Backtest (dalla UI): pagina Backtest -> Run Backtest
# Il motore usa il progetto ../MP-DH415-BT (auto-rilevato) e le credenziali
# FXCM del .env; i risultati finiscono nel database "Latest".
# Log del motore: backtest/engine_output.log

# Backtest (da CLI, senza UI):
cd /Users/fabiochiodo/Documents/trading-bot/MP-DH415/backend
python3.10 backtest_runner.py --pairs "EUR/USD,GBP/USD" \
  --datefrom "01.01.2024 00:00:00" --dateto "12.31.2024 23:00:00" --clean

# Trading Bot Pro

An automated Forex trading bot using FXCM ForexConnect API with a modern React dashboard for monitoring and configuration.

## Features

- **Multi-Timeframe Analysis**: Analyzes D1, H4, and M15 timeframes
- **Ichimoku Kijun-sen**: Uses Kijun-sen for trend identification
- **Support/Resistance Zones**: Automatic zone detection and validation
- **Pattern Recognition**: Engulfing patterns, consecutive candles
- **Risk Management**: Dynamic position sizing based on account balance
- **Trailing Stop & Breakeven**: Automatic trade management
- **Simulation Mode**: Development mode that logs signals to SQLite instead of executing trades
- **React Dashboard**: Modern UI for monitoring trades and configuring the bot
- **Slack Notifications**: Real-time alerts for trade events

## Project Structure

```
MP-DH415/
├── martina.py              # Main trading bot script
├── combined_script.py      # Orchestrator for multiple pairs
├── db_utils.py             # Database and MT5 utilities
├── utils.py                # Trading utilities and calculations
├── cmd_utils.py            # Command-line tools
├── kijun.py                # Kijun-sen calculation
├── common_samples/         # FXCM ForexConnect helpers
│   ├── __init__.py
│   ├── common.py
│   ├── OrderMonitor.py
│   └── BatchOrderMonitor.py
├── trading-bot-ui/         # React Dashboard
│   ├── api/                # Flask API backend
│   │   ├── app.py
│   │   └── requirements.txt
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Dashboard pages
│   │   ├── context/        # Global state
│   │   └── hooks/          # Custom hooks
│   └── package.json
└── DOCUMENTAZIONE.md       # Detailed documentation (Italian)
```

## Requirements

### Python Bot
- Python 3.10+ (required for forexconnect)
- FXCM Trading Account (Demo or Real)
- MetaTrader 5 (for production, Windows only)

### React Dashboard
- Node.js 18+
- npm or yarn

## Installation

### 1. Clone the repository

```bash
git clone git@github.com:fchiodo/MP-DH415.git
cd MP-DH415
```

### 2. Create environment file

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Slack Notifications
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL=your-channel

# FXCM API Credentials
FXCM_LOGIN_ID=your-login-id
FXCM_PASSWORD=your-password
FXCM_URL=http://www.fxcorporate.com/Hosts.jsp
FXCM_CONNECTION=Demo
FXCM_SESSION=Trade

# Risk Management
RISK_PER_TRADE=1.0
MIN_REWARD_RISK=2.0
REFERENCE_BALANCE=10000

# Active Currency Pairs
ACTIVE_PAIRS=EUR/USD,GBP/USD,USD/JPY
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install pandas numpy python-dotenv slack_sdk certifi
```

For macOS with Apple Silicon, install forexconnect:

```bash
pip install forexconnect-1.6.43-cp310-cp310-macosx_11_0_arm64.whl
```

### 4. Install React Dashboard

```bash
cd trading-bot-ui
npm install
```

### 5. Install API dependencies

```bash
cd trading-bot-ui/api
pip install -r requirements.txt
```

## Running the Application

### Start the API Server

```bash
cd trading-bot-ui/api
python app.py
```

The API will run on `http://localhost:5001`

### Start the React Dashboard

```bash
cd trading-bot-ui
npm run dev
```

The dashboard will open at `http://localhost:3000`

### Run the Trading Bot

**Single pair:**
```bash
python martina.py -l YOUR_LOGIN -p YOUR_PASSWORD -u http://www.fxcorporate.com/Hosts.jsp -i EUR/USD -c Demo -datefrom "04.10.2022 00:00:00" -session Trade
```

**All pairs:**
```bash
python combined_script.py
```

## Simulation Mode

For development without MT5, set `SIMULATION_MODE = True` in `db_utils.py`. This will:

- Log all MT5 signals to SQLite database
- Skip actual trade execution
- Allow testing on macOS

View simulation signals:
```bash
python cmd_utils.py -c signals
```

Clear simulation data:
```bash
python cmd_utils.py -c clear_signals
```

## Dashboard Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Overview with active trades, stats, and activity log |
| **History** | Performance analytics and trade history |
| **Signals** | MT5 simulation signals log |
| **Settings** | Bot configuration (FXCM, risk, Slack) |

## Command Line Tools

```bash
# Show MT5 account balance
python cmd_utils.py -c balance

# Clean trades table
python cmd_utils.py -c clean

# Update MT5 trade
python cmd_utils.py -c update

# Show simulation signals
python cmd_utils.py -c signals

# Clear simulation signals
python cmd_utils.py -c clear_signals
```

## Configuration

### Simulation vs Production Mode

In `db_utils.py`:

```python
# Development (macOS, no MT5)
SIMULATION_MODE = True

# Production (Windows with MT5)
SIMULATION_MODE = False
```

### Risk Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `RISK_PER_TRADE` | 1.0% | Risk per trade as percentage of balance |
| `MIN_REWARD_RISK` | 2.0 | Minimum Risk:Reward ratio required |
| `REFERENCE_BALANCE` | 10000 | Reference balance for position sizing |

## Tech Stack

- **Backend**: Python, Flask, SQLite
- **Trading API**: FXCM ForexConnect, MetaTrader 5
- **Frontend**: React 18, Vite, Tailwind CSS
- **Notifications**: Slack SDK

## License

Private - All rights reserved

## Author

Fabio Chiodo

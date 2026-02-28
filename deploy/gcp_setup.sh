#!/bin/bash
# =============================================================================
# GCP e2-micro Setup Script — MP-DH415 Trading Bot
# Ubuntu 22.04 LTS
# Eseguire come utente con sudo (es. il tuo utente GCP)
# =============================================================================
set -e

REPO_DIR="/home/$USER/MP-DH415"
VENV_DIR="$REPO_DIR/venv"
PYTHON_VERSION="3.10"

echo "=== [1/7] Aggiornamento sistema ==="
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y git curl build-essential libssl-dev

echo "=== [2/7] Installazione Python $PYTHON_VERSION ==="
sudo apt-get install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update -y
sudo apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev python3-pip

echo "=== [3/7] Clone / aggiornamento repository ==="
if [ -d "$REPO_DIR" ]; then
    echo "Repository già presente, pull..."
    cd "$REPO_DIR"
    git pull origin main
else
    echo "Clone del repository..."
    cd "/home/$USER"
    git clone https://github.com/YOUR_GITHUB_USERNAME/MP-DH415.git
    cd "$REPO_DIR"
fi

echo "=== [4/7] Creazione virtualenv ==="
python${PYTHON_VERSION} -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "=== [5/7] Installazione dipendenze Python ==="
pip install --upgrade pip
pip install -r "$REPO_DIR/backend/requirements.txt"
pip install -r "$REPO_DIR/frontend/api/requirements.txt"

echo "=== [6/7] Configurazione file .env ==="
if [ ! -f "$REPO_DIR/.env" ]; then
    echo "ATTENZIONE: file .env non trovato in $REPO_DIR"
    echo "Crea il file .env con i tuoi valori prima di avviare i servizi."
    echo "Esempio:"
    cat << 'EOF'
SLACK_BOT_TOKEN='xoxb-...'
SLACK_CHANNEL='mt-bot'
FXCM_LOGIN_ID='...'
FXCM_PASSWORD='...'
FXCM_URL='http://www.fxcorporate.com/Hosts.jsp'
FXCM_CONNECTION='Demo'
FXCM_SESSION=Trade
RISK_PER_TRADE='1'
MIN_REWARD_RISK='2'
REFERENCE_BALANCE='10000'
ACTIVE_PAIRS='GBP/CHF'
EOF
else
    echo "File .env trovato."
fi

echo "=== [7/7] Installazione servizi systemd ==="
# Sostituisce il placeholder $USER nei service file e li copia in systemd
sed "s|__USER__|$USER|g; s|__REPO_DIR__|$REPO_DIR|g; s|__VENV_DIR__|$VENV_DIR|g" \
    "$REPO_DIR/deploy/trading-bot.service" \
    | sudo tee /etc/systemd/system/trading-bot.service > /dev/null

sed "s|__USER__|$USER|g; s|__REPO_DIR__|$REPO_DIR|g; s|__VENV_DIR__|$VENV_DIR|g" \
    "$REPO_DIR/deploy/flask-api.service" \
    | sudo tee /etc/systemd/system/flask-api.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl enable flask-api
sudo systemctl start flask-api
sudo systemctl start trading-bot

echo ""
echo "======================================================"
echo " Setup completato!"
echo " Controlla i log con:"
echo "   journalctl -u trading-bot -f"
echo "   journalctl -u flask-api -f"
echo " Stato:"
echo "   sudo systemctl status trading-bot"
echo "   sudo systemctl status flask-api"
echo "======================================================"

import time
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

from db_utils import send_slack_message

# .env nella root del progetto (parent di backend/)
SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR.parent / '.env')

DEFAULT_PAIRS = [
    "EUR/USD", "AUD/USD", "GBP/USD", "USD/JPY", "GBP/JPY", "USD/CAD",
    "EUR/JPY", "USD/CHF", "NZD/USD", "AUD/JPY", "EUR/GBP", "CAD/JPY",
    "GBP/AUD", "AUD/CAD", "EUR/AUD", "EUR/CAD", "GBP/CAD", "EUR/NZD",
    "AUD/NZD", "GBP/CHF", "GBP/NZD", "CHF/JPY", "EUR/CHF", "AUD/CHF",
    "CAD/CHF", "NZD/CAD", "NZD/CHF", "NZD/JPY",
]


def post_to_slack():
    channel = os.getenv('SLACK_CHANNEL', 'mt-bot')
    message = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    send_slack_message(channel, message)


def run_martina(arguments):
    subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "martina.py")] + arguments,
        cwd=str(SCRIPT_DIR),
    )


def get_pairs():
    pairs_str = os.getenv('ACTIVE_PAIRS', '')
    pairs = [p.strip() for p in pairs_str.split(',') if p.strip()]
    return pairs or DEFAULT_PAIRS


def main():
    login_id = os.getenv('FXCM_LOGIN_ID', '')
    password = os.getenv('FXCM_PASSWORD', '')
    url = os.getenv('FXCM_URL', 'http://www.fxcorporate.com/Hosts.jsp')
    connection = os.getenv('FXCM_CONNECTION', 'Demo')

    if not login_id or not password:
        print("FXCM_LOGIN_ID / FXCM_PASSWORD non configurati nel file .env")
        sys.exit(1)

    # Post initial message to Slack
    post_to_slack()

    for pair in get_pairs():
        print(f"processing: {pair}")
        run_martina([
            "-l", login_id,
            "-p", password,
            "-u", url,
            "-i", pair,
            "-c", connection,
            "-datefrom", "04.10.2022 00:00:00",
            "-session", "Trade",
        ])
        time.sleep(1)


if __name__ == "__main__":
    main()

# pyinstaller --onefile combined_script.py

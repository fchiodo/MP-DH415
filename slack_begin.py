from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

from datetime import datetime, timedelta, time

import os

os.chdir("C:\\Users\\Administrator\\Documents\\Eseguibile")

env_path = ".env"
load_dotenv(env_path)

client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])

channel = 'mt-bot'
current_timestamp = datetime.now()
message = current_timestamp.strftime("%Y-%m-%d %H:%M:%S")

try:
    response = client.chat_postMessage(
        channel=channel,
        text=message
    )
    print(f"Message sent: {response['ts']}")
except SlackApiError as e:
    print(f"Error sending message: {e}")
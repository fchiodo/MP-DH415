import time
import subprocess

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from datetime import datetime
import os
import certifi
import ssl
from ssl import SSLContext


def post_to_slack():
    # Change the directory to where your .env file is

    os.chdir("C:\\Users\\Administrator\\Documents\\Eseguibile")
    

    # Load environment variables
    env_path = ".env"
    load_dotenv(env_path)

    # Initialize Slack client
    ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
    sslcert = SSLContext()
    client = WebClient(token=os.environ['SLACK_BOT_TOKEN'], ssl=sslcert)
    channel = 'mt-bot'
    current_timestamp = datetime.now()
    message = current_timestamp.strftime("%Y-%m-%d %H:%M:%S")

    try:

        # Use this context in the request
        response = client.chat_postMessage(
            channel=channel,
            text=message
        )

        print(f"Message sent: {response['ts']}")
    except SlackApiError as e:
        print(f"Error sending message: {e}")

def run_martina(arguments):
    # This function runs martina.py with given arguments
    subprocess.run(["python", "martina.py"] + arguments)

def run_martina(arguments):
    # This function runs martina.py with given arguments
    subprocess.run(["python", "C:\\Users\\Administrator\\Documents\\Eseguibile\\martina.py"] + arguments)


def main():
    # Post initial message to Slack
    post_to_slack()

    # Define the parameters for each martina.py call
    params_list = [
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "EUR/USD", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "AUD/USD", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "GBP/USD", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "USD/JPY", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "GBP/JPY", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "USD/CAD", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "EUR/JPY", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "USD/CHF", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "NZD/USD", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "AUD/JPY", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "EUR/GBP", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "CAD/JPY", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "GBP/AUD", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "AUD/CAD", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "EUR/AUD", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "EUR/CAD", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "GBP/CAD", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "EUR/NZD", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "AUD/NZD", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "GBP/CHF", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "GBP/NZD", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "CHF/JPY", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "EUR/CHF", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "AUD/CHF", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "CAD/CHF", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "NZD/CAD", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "NZD/CHF", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
        ["-l", "D261369496", "-p", "6Ufxr", "-u", "http://www.fxcorporate.com/Hosts.jsp", "-i", "NZD/JPY", "-c", "Demo", "-datefrom", "04.10.2022 00:00:00", "-session", "Trade"],
    ]

    # Loop through each set of parameters, running the script and pausing
    for params in params_list:
        print(f"processing: {params[7]}")
        run_martina(params)
        time.sleep(1)  # 3-second delay

if __name__ == "__main__":
    main()

 # pyinstaller --onefile combined_script.py 


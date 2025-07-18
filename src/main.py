import requests
import time
import logging
import os
from dotenv import load_dotenv
from datetime import datetime
import pytz
import boto3

# --- IST Time Config for Logging ---
IST = pytz.timezone('Asia/Kolkata')
SLEEP = 30

def ist_time(*args):
    return datetime.now(IST).timetuple()

# Configure logging to work in both Lambda and local environments
logging.Formatter.converter = ist_time
log_format = '%(asctime)s - %(levelname)s - %(message)s'
date_format = '%Y-%m-%d %H:%M'

# Remove any existing handlers (important for Lambda)
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    datefmt=date_format
)

# --- Load Environment Variables ---
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

HEADERS = {
    "Accept": "application/vnd.github.v3+json"
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

GITHUB_EVENTS_URL = "https://api.github.com/events"

# --- Fetch GitHub Events ---
def fetch_events():
    try:
        response = requests.get(GITHUB_EVENTS_URL, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching events: {e}")
        return []

# --- Log Events Based on Type ---
def log_event(event):
    event_type = event.get("type")
    repo_name = event.get("repo", {}).get("name")
    actor = event.get("actor", {}).get("login")
    payload = event.get("payload", {})

    if event_type == "PushEvent":
        commits = payload.get("commits", [])
        messages = [c.get("message") for c in commits]
        branch = payload.get("ref", "").split("/")[-1]
        logging.info(f"🔹 PushEvent: {actor} pushed {len(commits)} commit(s) to {repo_name}/{branch}: {messages}")

    elif event_type == "IssuesEvent":
        action = payload.get("action")
        issue = payload.get("issue", {})
        title = issue.get("title")
        logging.info(f"🔹 IssuesEvent: Issue '{title}' was {action} in {repo_name} by {actor}")

    elif event_type == "WatchEvent":
        logging.info(f"🔹 WatchEvent: {actor} starred {repo_name}")

    elif event_type == "ForkEvent":
        logging.info(f"🔹 ForkEvent: {actor} forked {repo_name}")

    elif event_type == "PullRequestEvent":
        action = payload.get("action")
        pr = payload.get("pull_request", {})
        title = pr.get("title")
        base_branch = pr.get("base", {}).get("ref")
        logging.info(f"🔹 PullRequestEvent: PR '{title}' {action} on {repo_name} (→ {base_branch}) by {actor}")

    elif event_type == "CreateEvent":
        ref_type = payload.get("ref_type")
        ref_name = payload.get("ref")
        logging.info(f"🔹 CreateEvent: {actor} created a new {ref_type} '{ref_name}' in {repo_name}")

# --- Lambda entry point ---
def handle(event, context):
    """Lambda handler"""
    logging.info("GitHub Event Lambda triggered")
    events = fetch_events()
    if events:
        logging.info(f"Fetched {len(events)} events. Showing last 10.")
        for event in events[-10:]:
            log_event(event)
    
    # Trigger next execution if running in Lambda
    if context:
        lambda_client = boto3.client('lambda')
        lambda_client.invoke(
            FunctionName=context.function_name,
            InvocationType='Event',
            Payload='{}'
        )
        logging.info(f"Scheduled next invocation")
    
    return {"statusCode": 200, "body": "GitHub events logged."}

# For local testing
if __name__ == "__main__" and os.getenv('LOCAL_TEST'):
    logging.info("Starting GitHub Events monitoring...")
    while True:
        handle(None, None)
        logging.info(f"Sleeping for {SLEEP} seconds...")
        time.sleep(SLEEP)
#         logging.info(f"Sleeping for {SLEEP} seconds...")
#         time.sleep(SLEEP)

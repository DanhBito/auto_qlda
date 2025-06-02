import json
import os

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def reload_config():
    global config
    with open('config.json', 'r') as f:
        config.update(json.load(f))
    config = load_config()

config = load_config()

google_creds_env = os.getenv("GOOGLE_CREDENTIALS")
if google_creds_env:
    try:
        service_account_info = json.loads(google_creds_env)
        config["SERVICE_ACCOUNT_INFO"] = service_account_info
    except json.JSONDecodeError:
        print("Warning: GOOGLE_CREDENTIALS env var is not a valid JSON")
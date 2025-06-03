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
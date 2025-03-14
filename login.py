import requests
import time
import json
import os
import asyncio
from datetime import datetime, timedelta
from config import config, reload_config

# ✅ Đăng nhập để lấy token
def login():
    token = load_token()
    if token:
        return token

    url = f"{config.get('BASE_URL')}/Token"
    data = {
        "type": 0,
        "client_id": None,
        "grant_type": "password",
        "username": config.get('USERNAME'),
        "password": config.get('PASSWORD')
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0"
    }
    
    response = requests.post(url, data=data, headers=headers)
    
    if response.status_code == 200:
        response_data = response.json()
        expires_at = datetime.now() + timedelta(seconds=response_data.get("expires_in"))
        data = {
            "access_token": response_data.get("access_token"),
            "expires_at": expires_at.isoformat(),
            "account_id": response_data.get("AccountID")
        }    
        save_token(data)
        print("✅ Đăng nhập thành công!")
        return response_data.get("access_token")
    else:
        print("❌ Lỗi đăng nhập:", response.text)
        return None

# ✅ Kiểm tra token còn hạn không
def load_token():
    if not os.path.exists(config.get('TOKEN_FILE')):
        return None

    with open(config.get('TOKEN_FILE'), "r") as file:
        data = json.load(file)
    
    if "access_token" in data and "expires_at" in data:
        expires_at = datetime.fromisoformat(data["expires_at"])
        if datetime.now() < expires_at:
            return data["access_token"]  # Token còn hạn
    return None  

# ✅ Lưu token vào file
def save_token(data):
    with open(config.get('TOKEN_FILE'), "w") as file:
        json.dump(data, file)    

    with open("config.json", "r", encoding="utf-8") as file:
        config_data = json.load(file)

    config_data["ACCOUNT_ID"] = data.get("account_id")

    with open("config.json", "w", encoding="utf-8") as file:
        json.dump(config_data, file, indent=4, ensure_ascii=False)
  
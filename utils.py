import requests
import time
import json
import os
import asyncio
from datetime import datetime
from config import config
from login import login

# 🛠 Headers cơ bản
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json"
}

#✅ Gọi API với token
async def call_api(endpoint):
    token = login()
    if not token:
        await send_message("Không thể gọi API vì chưa đăng nhập")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Username": config.get('USERNAME'),
    }

    url = f"{config.get('BASE_URL')}{endpoint}"
    response = requests.get(url, headers=headers)

    if response.status_code == 401:
        print("🔄 Token bị từ chối, thử đăng nhập lại...")
        token = login()
        if not token:
            return None
        headers["Authorization"] = f"Bearer {token}"
        response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Lỗi khi gọi API {endpoint}: {response.status_code} - {response.text}")
        return None

async def post_api(endpoint, data):
    token = login()
    if not token:
        await send_message("Không thể gọi API vì chưa đăng nhập")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "username": config.get('USERNAME'),
    }

    url = f"{config.get('BASE_URL')}{endpoint}"

    response = requests.post(url, json=data, headers=headers)   
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Lỗi khi gọi API {endpoint}: {response.status_code} - {response.text}")
        return None

#Format date
def format_date(iso_date):
    return datetime.fromisoformat(iso_date).strftime("%d/%m/%Y")

#Convert keys to Vietnamese
def convert_keys_to_vietnamese(task):
    return {
        "Mã Task": task["TaskID"],
        "Tên Task": task["TaskName"],
        "Mã Code": task["TaskCode"],
        "Ngày Bắt Đầu": task["ScheduleStartDate"],
        "Ngày Kết Thúc": task["ScheduleEndDate"],
        "Tên Tài Khoản": task["AccountName"],
        "Trạng Thái": "Đang Làm" if task["DoingType"] == 1 else "Đang Dừng",
        "Số Giờ Đã Thực Hiện": task["HourNum"],
        "Thời Gian Được Giao": task["TimeDue"],
        "Ngoại Lệ": task["Exception"]
    }
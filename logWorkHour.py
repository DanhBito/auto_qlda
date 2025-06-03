import asyncio
from datetime import datetime, time, timedelta
import gspread
from google.oauth2.service_account import Credentials
from config import config
from utils import call_api

# Danh sách thời điểm cần chạy (dạng datetime.time)
RUN_TIMES = [
    time(7, 0), # 7h sáng
    time(13, 0), # 13h chiều
    time(19, 0) # 19h tối
]

async def search_detail_by_month(month, assignee_id):
    endpoint = f"/api/DashboardQLCV/SearchDetailByMonth?month={month}&assigneeIDs={assignee_id}"
    response = await call_api(endpoint)
    return response

async def run_task():
    print(f"🚀 Bắt đầu chạy tác vụ lúc {datetime.now().strftime('%H:%M:%S')}")

    month = datetime.now().strftime("%m/%Y")

    creds = Credentials.from_service_account_file(
        config["SERVICE_ACCOUNT_FILE"],
        scopes=[config.get("SERVICE_ACCOUNT_SCOPES")]
    )

    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.get("SPREADSHEET_ID")).worksheet(config.get("SHEET_NAME"))

    users = config.get("USERS", [])

    for user in users:
        user_id = user['id']
        user_name = user['name']

        result = await search_detail_by_month(month, user_id)
        print(f"📊 Kết quả cho {user_name}:", result)

        actual_hours = result["Data"][0]["ActualHourNums"] if result["Status"] == 1 and result["Data"] else 0
        user['actual_hour'] = actual_hours

    code_range = sheet.get("B4:B18")
    code_list = [row[0] if row else "" for row in code_range]

    user_map = {user["code"]: user.get("actual_hour", "") for user in config.get("USERS")}

    update_values = [[user_map.get(code, "")] for code in code_list]

    sheet.update("F4:F18", update_values)

    print("✅ Đã cập nhật thời gian thực hiện vào Google Sheet.")

async def scheduler():
    while True:
        now = datetime.now()

        today_run_times = [datetime.combine(now.date(), t) for t in RUN_TIMES]

        next_run = next((t for t in today_run_times if t > now), None)

        if not next_run:
            next_run = datetime.combine(now.date() + timedelta(days=1), RUN_TIMES[0])

        wait_seconds = (next_run - now).total_seconds()
        print(f"⏳ Chờ đến {next_run.strftime('%H:%M:%S')} để chạy task tiếp theo...")
        await asyncio.sleep(wait_seconds)
        await run_task()

if __name__ == "__main__":
    try:
        asyncio.run(scheduler())
    except KeyboardInterrupt:
        print("\n🛑 Đã dừng chương trình.")
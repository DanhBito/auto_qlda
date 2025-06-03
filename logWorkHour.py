import asyncio
from datetime import datetime, time, timedelta
import gspread
from google.oauth2.service_account import Credentials
from config import config
from utils import call_api
import json
import urllib.parse

# Danh sách thời điểm cần chạy (dạng datetime.time)
RUN_TIMES = [
    time(7, 0), # 7h sáng
    time(13, 0), # 13h chiều
    time(19, 0), # 19h tối
]

async def search_detail_by_month(month, assignee_id):
    endpoint = f"/api/DashboardQLCV/SearchDetailByMonth?month={month}&assigneeIDs={assignee_id}"
    response = await call_api(endpoint)
    return response

async def search_detail_log_work_team_by_current_month():
    now = datetime.now()
    fromDate = datetime(now.year, now.month, 1).strftime('%Y-%m-%dT00:00:00')
    toDate = datetime(now.year, now.month, now.day).strftime('%Y-%m-%dT00:00:00')
    endpoint = f"/api/DashboardQLCV/SearchPersonWorkByDate?searchText=&fromDate={fromDate}&toDate={toDate}&UnitID=&assigneeIDs=%5B%5D"
    response = await call_api(endpoint)
    return response

async def search_overdue_task_by_month(assignee_id):
    month = datetime.now().strftime("%m")
    year = datetime.now().strftime("%Y")
    encoded_uids = urllib.parse.quote(json.dumps([assignee_id]))
    endpoint = f"/api/DashboardDev/GetAverageQualityOfTreeMonth?month={month}&year={year}&uids={encoded_uids}"
    response = await call_api(endpoint)
    return response


async def run_task_search_detail_log_work_team_by_current_month():
    print(f"🚀 Bắt đầu chạy tác vụ lúc {datetime.now().strftime('%H:%M:%S')}")

    result = await search_detail_log_work_team_by_current_month()
    print("📊 Kết quả Thống kê công việc của nhóm là: ", result)

    creds = Credentials.from_service_account_file(
        config["SERVICE_ACCOUNT_FILE"],
        scopes=[config.get("SERVICE_ACCOUNT_SCOPES")]
    )

    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.get("SPREADSHEET_ID")).worksheet(config.get("SHEET_NAME"))

    username = sheet.get("D4:D16")
    username_list = [row[0] if row else "" for row in username]

    data_map = {user["AssigneeName"]: user for user in result["Data"]}

    values_total_task = [[data_map.get(name, {}).get("TotalTask", "")] for name in username_list]
    values_total_hour = [[data_map.get(name, {}).get("TotalHourNum", "")] for name in username_list]
    # values_wait_review = [[data_map.get(name, {}).get("TotalTaskWaitReview", "")] for name in username_list]
    values_done = [[data_map.get(name, {}).get("TotalTaskDone", "")] for name in username_list]
    values_not_done = [[data_map.get(name, {}).get("TotalTaskNotDone", "")] for name in username_list]

    sheet.update("K4:K16", values_total_task)
    sheet.update("L4:L16", values_total_hour)
    # sheet.update("O4:O16", values_wait_review)
    sheet.update("M4:M16", values_done)
    sheet.update("N4:N16", values_not_done)

    print("✅ Đã cập nhật đầy đủ các thống kê công việc của nhóm theo từng cột.")

       
async def run_task_search_detail_by_month():
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

        result_overdue_task = await search_overdue_task_by_month(user_id)
        print(f"📊 Kết quả task trễ hạn cho {user_name}:", result_overdue_task)

        actual_hours = result["Data"][0]["ActualHourNums"] if result["Status"] == 1 and result["Data"] else 0
        count_overdue = result_overdue_task["Data"]["CountOverDue"] if result_overdue_task["Status"] == 1 and "Data" in result_overdue_task else 0
        user['actual_hour'] = actual_hours
        user['count_overdue'] = count_overdue

    code_range = sheet.get("B4:B16")
    code_list = [row[0] if row else "" for row in code_range]

    user_map_actual = {user["code"]: user.get("actual_hour", "") for user in users}
    user_map_overdue = {user["code"]: user.get("count_overdue", "") for user in users}

    update_values_actual = [[user_map_actual.get(code, "")] for code in code_list]
    update_values_overdue = [[user_map_overdue.get(code, "")] for code in code_list]

    # Cập nhật thời gian thực hiện
    sheet.update("F4:F16", update_values_actual)

    # Cập nhật số lượng task trễ hạn
    sheet.update("J4:J16", update_values_overdue)

    print("✅ Đã cập nhật thời gian thực hiện và số task trễ hạn vào Google Sheet.")

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
        await run_task_search_detail_by_month()
        await run_task_search_detail_log_work_team_by_current_month()

if __name__ == "__main__":
    try:
        asyncio.run(scheduler())
    except KeyboardInterrupt:
        print("\n🛑 Đã dừng chương trình.")
import asyncio
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from config import config
from utils import call_api

async def search_detail_by_month(month, assignee_id):
    endpoint = f"/api/DashboardQLCV/SearchDetailByMonth?month={month}&assigneeIDs={assignee_id}"
    response = await call_api(endpoint)
    return response

async def main():

    month = datetime.now().strftime("%m/%Y")

    if config.get("SERVICE_ACCOUNT_INFO"):
        print("SERVICE_ACCOUNT_INFO is exist!!!")
        creds = Credentials.from_service_account_info(
            config["SERVICE_ACCOUNT_INFO"],
            scopes=[config.get("SERVICE_ACCOUNT_SCOPES")]
        )
    else:
        print("SERVICE_ACCOUNT_INFO is not exist!!!")
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
        print(f"📊 Result for {user_name}:", result)

        actual_hours = result["Data"][0]["ActualHourNums"] if result["Status"]  == 1 and result["Data"] else 0
        user['actual_hour'] = actual_hours

    code_range = sheet.get("B4:B18")
    code_list = [row[0] if row else "" for row in code_range]

    user_map = {user["code"]: user.get("actual_hour", "") for user in config.get("USERS")}

    update_values = [[user_map.get(code, "")] for code in code_list]

    sheet.update("F4:F18", update_values)

    print("✅ Đã cập nhật thời gian thực hiện vào Google Sheet.")

if __name__ == "__main__":
    asyncio.run(main())
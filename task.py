import requests
import time
import json
import os
import asyncio
from datetime import datetime, timedelta
from config import config
from utils import call_api, post_api, format_date
from telegram import Update, Bot

bot = Bot(token=config.get('TELEGRAM_BOT_TOKEN'))
async def send_message(text):
    await bot.send_message(chat_id=config.get('TELEGRAM_CHAT_ID'), text=text)

# ✅ Chạy hệ thống tự động
async def auto_checkin():    
    while True:
        current_time = datetime.now().strftime("%H:%M")
        if current_time >= config.get("START_TIME") and current_time <= config.get("STOP_TIME_2"):
            break
        print("⏹️ Not now")    
        time.sleep(30)  # Kiểm tra lại mỗi 30 giây

    await send_message("🚀 Bắt đầu tự động kiểm tra công việc...")

    delete_task_json()
    while True:
        try:
            current_time = datetime.now().strftime("%H:%M")

            if current_time >= config.get("STOP_TIME_2"):
                await send_message("⏹️ 16h30: Dừng công việc hoàn toàn.")
                print("⏹️ 16h30: Dừng công việc hoàn toàn.")
                await stop_task()
                break

            if current_time >= config.get("STOP_TIME_1") and current_time < config.get("RESUME_TIME"):
                await send_message("⏸️ 11h30: Tạm dừng công việc...")
                print("⏸️ 11h30: Tạm dừng công việc...")
                await stop_task()
                while datetime.now().strftime("%H:%M") < config.get("RESUME_TIME"):
                    time.sleep(30)  # Kiểm tra lại mỗi 30 giây
                await send_message("▶️ 13h00: Tiếp tục công việc...")
                print("▶️ 13h00: Tiếp tục công việc...")

        
            tasksArr = await get_tasks()
            print(f"📝 Có {len(tasksArr)} công việc cần thực hiện")
            if tasksArr:
                await update_tasks(tasksArr)
                await start_task()

            my_time_break = 5
            while True:
                my_time_break += 5
                if my_time_break >= 900:
                    break
                await asyncio.sleep(5)  

        except Exception as e:
            error_message = (f"❌ Error in auto_checkin:\n{traceback.format_exc()}")
            print(error_message)
            await send_message(error_message)

# ✅ Start task
async def start_task(task_start = None):
    tasks_arr = get_tasks_from_json()
    if task_start:
        await stop_task()
        task_doing = [task for task in tasks_arr if (task.get("TaskID") == task_start and task.get("DoingType") in (0,2) and task.get("StatusID") in (0,2))]
        task = task_doing[0]

        response_start = await stop_or_start_task(task.get("TaskID"))
        update_task_doing(response_start["Data"])
        await send_message(f"Đã start task {task.get('TaskName')}")
        print(f"Đã start task {task.get('TaskName')}")
    else:
        task_doing = [task for task in tasks_arr if (task.get("DoingType") == 1 and (task.get("StatusID") == 0 or task.get("StatusID") == 2))]

        if (task_doing and len(task_doing) > 1):
            print(f"🚀1 Có lỗi ở start_task {type(task_doing)}")
            print(f"🚀 Có lỗi ở start_task {task_doing}")
        elif (task_doing and len(task_doing) == 1):
            task = task_doing[0]
            time_remaining = task.get("TimeDue") - task.get("HourNum")
            print(f"Task {task.get('TaskName')}: còn {time_remaining} giờ")
            if time_remaining <= 0.1:
                response_stop = await stop_or_start_task(task.get("TaskID"))
                update_task_doing(response_stop["Data"])
                await send_message(f"Đã dừng task {task.get('TaskName')}")
                print(f"Đã dừng task {task.get('TaskName')}")
                await start_task()
        else:
            now = datetime.now()
            filtered_tasks = sorted(
                [
                    task for task in tasks_arr
                    if task.get("ScheduleEndDate")  # Kiểm tra task có `taskScheduleEndDate`
                    and (task["TimeDue"] - task["HourNum"]) >= 0.1  # Điều kiện taskTimeDue - taskHourNum > 0.25
                    and task["DoingType"] in (0, 2)  # taskDoing phải là 0 hoặc 2
                    and task["Exception"] == 0  # taskException phải là 0
                ],
                key=lambda task: abs(datetime.strptime(task["ScheduleEndDate"], "%d/%m/%Y") - now)
            )

            task_closest_to_now = filtered_tasks[0] if filtered_tasks else None

            if(task_closest_to_now):
                response_start = await stop_or_start_task(task_closest_to_now.get("TaskID"))
                update_task_doing(response_start["Data"])
                await send_message(f"Đã start task {task_closest_to_now.get('TaskName')}")
                print(f"Đã start task {task_closest_to_now.get('TaskName')}")
            else:
                print(f"Đã hết task để thực hiện")

# ✅ Stop task
async def stop_task(task_stop = None):
    tasks_arr = get_tasks_from_json()
    if task_stop:
        task_doing = [task for task in tasks_arr if (task.get("TaskID") == task_stop and task.get("DoingType") == 1 and task.get("StatusID") in (0,2))]
        task = task_doing[0]
        response_stop = await stop_or_start_task(task.get("TaskID"))
        await send_message(f"Đã dừng task {task.get('TaskName')}")
        update_task_doing(response_stop["Data"])
    else:
        task_doing = [task for task in tasks_arr if (task.get("DoingType") == 1 and task.get("StatusID") in (0,2))]

        if (task_doing and len(task_doing) > 1):
            print(f"🚀1 Có lỗi ở start_task {type(task_doing)}")
            print(f"🚀 Có lỗi ở start_task {task_doing}")
        elif (task_doing and len(task_doing) == 1):
            task = task_doing[0]
            response_stop = await stop_or_start_task(task.get("TaskID"))
            await send_message(f"Đã dừng task {task.get('TaskName')}")
            update_task_doing(response_stop["Data"])  

# ✅ Stop or start task
async def stop_or_start_task(task_id):
    url = "/api/Task/Done"
    data = {
        "ID": f"{task_id}",
        "DoingFlg": "true"
    }
    return await post_api(url, data)     

# ✅ Get Log task
async def get_first_task_log(task_id):
    url = f"/api/Step/GetTaskLogs?taskID={task_id}"
    log_task_detail = await call_api(url)
    if(log_task_detail and log_task_detail["Data"][0]):
        for log in log_task_detail["Data"]:
            if(log["Des1"] == "đã bắt đầu công việc"):
                first_log = log
                break
        if(first_log):
            return calculate_hours_difference(first_log["CreateAt"])
    return 0

# ✅ Tính thời gian còn lại
def calculate_hours_difference(create_at):
    given_date = datetime.strptime(create_at, "%d/%m/%Y %H:%M")
    return round((datetime.now() - given_date).total_seconds() / 3600, 2)

# ✅ Update tasks JSON
async def update_tasks(tasksArr):
    if(os.path.exists(config.get('TASK_FILE'))):
        with open(config.get('TASK_FILE'), "r", encoding="utf-8") as f:
            task_data = json.load(f)
    else:
        task_data = []
    
    for task in tasksArr:
        task_id = task["TaskID"]
        existing_task = next((t for t in task_data if t["TaskID"] == task_id), None)
        url_task_detail= f"/api/Task?iD={task_id}"
        task_detail = await call_api(url_task_detail)

        if(existing_task):
            existing_task["HourNum"] = float(task["HourNum"] or 0)
            if(task["DoingType"] == 1):
                time_log = await get_first_task_log(task_id)
                if(time_log):
                    existing_task["HourNum"] += time_log

            existing_task["TimeDue"] = task_detail["Data"]["ScheduleH"]
            task_data = [t if t["TaskID"] != task_id else existing_task for t in task_data]
        else:
            time_due = task_detail["Data"]["ScheduleH"] if task_detail else 0

            # Thêm task vào danh sách
            task_data.append({
                "TaskID": task_id,
                "TaskName": task["TaskName"],
                "TaskCode": task["Code"],
                "ScheduleStartDate": task["ScheduleStartDate"],
                "ScheduleEndDate": task["ScheduleEndDate"],
                "StatusID": task["StatusID"],
                "AccountName": task["AccountName"],
                "DoingType": task["DoingType"] or 0,
                "HourNum": float(task["HourNum"] or 0),
                "TimeDue": time_due,
                "Exception": 0
            })

    with open(config.get('TASK_FILE'), "w", encoding="utf-8") as f:
        json.dump(task_data, f, indent=4)


# ✅ Update task doing    
def update_task_doing(task_new):
    try:
        with open(config.get('TASK_FILE'), "r", encoding="utf-8") as file:
            tasks = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        tasks = []  # Nếu file không tồn tại hoặc lỗi đọc JSON, khởi tạo danh sách rỗng
  
    task_detail = {
                "TaskID": task_new.get("ID"),
                "TaskName": task_new.get("Name"),
                "TaskCode": task_new.get("Code"),
                "ScheduleStartDate": format_date(task_new.get("ScheduleStartDate")),
                "ScheduleEndDate": format_date(task_new.get("ScheduleEndDate")),
                "DoingType": task_new.get("DoingType"),
                "StatusID": task_new.get("StatusID"),
                "HourNum": task_new.get("HourNum"),
                "TimeDue": task_new.get("ScheduleH"),
                "Exception": 0
            }
    # Duyệt qua danh sách task và cập nhật thông tin task có `TaskID` tương ứng
    task_found = False
    for task in tasks:
        if task["TaskID"] == task_new.get("ID"):
            task_detail["AccountName"] = task["AccountName"]
            task.update(task_detail)
            task_found = True
            break
    
    # Nếu task không tồn tại, có thể thêm mới hoặc bỏ qua
    if not task_found:
        tasks.append({"TaskID": task_new.get("ID"), **task_detail})

    # Ghi lại file JSON với dữ liệu đã cập nhật
    with open(config.get('TASK_FILE'), "w", encoding="utf-8") as file:
        json.dump(tasks, file, indent=4, ensure_ascii=False)

    print(f"✅ Task {task_new.get('Name')} đã được cập nhật trong {config.get('TASK_FILE')}")

# ✅ Delete task JSON
def delete_task_json():
    if(os.path.exists(config.get('TASK_FILE'))):
        with open(config.get('TASK_FILE'), "w", encoding="utf-8") as f:
            json.dump([], f, indent=4)

# ✅ Lấy danh sách task của board
async def get_tasks():
    if config.get("ACCOUNT_ID") == "":
        return None
    urlGetTask = f"/api/DashboardQLCV/getDataRP?projectIDs=&uids={config.get('ACCOUNT_ID')}&searchText="
    response = await call_api(urlGetTask)
    tasks = [*response.get("Data", {}).get("DoingAssigneeTask", []), *response.get("Data", {}).get("DoingAssigneeTaskStart", [])]

    if tasks:
        return tasks
    return None

# ✅ Lấy danh sách task từ file JSON
def get_tasks_from_json():
    if(os.path.exists(config.get('TASK_FILE'))):
        with open(config.get('TASK_FILE'), "r", encoding="utf-8") as f:
            task_data = json.load(f)

            return task_data
    return []      
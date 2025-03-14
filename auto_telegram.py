import requests
import json
import asyncio
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import config, reload_config
from task import get_tasks, update_tasks, start_task, stop_task, get_tasks_from_json, auto_checkin
from utils import call_api, post_api, format_date, convert_keys_to_vietnamese
from login import login

auto_checkin_task = None

# Hàm main để chạy bot
def main():
    application = Application.builder().token(config.get("TELEGRAM_BOT_TOKEN")).build()

    login()
    reload_config()

    send_message_not_async(help())

   # Xử lý lệnh /help
    application.add_handler(CommandHandler("help", send_help_message))

    # Xử lý lệnh /start
    application.add_handler(CommandHandler("start", start))

    #Xử lý lệnh /stop
    application.add_handler(CommandHandler("stop", stop))

    # Xử lý lệnh /alltask
    application.add_handler(CommandHandler("listTask", list_task))

    # Xử lý lệnh /auto
    application.add_handler(CommandHandler("auto", auto_qlda))

    # Xử lý lệnh /stopauto
    application.add_handler(CommandHandler("stopauto", stop_auto_qlda))


    # Xử lý tin nhắn văn bản
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Chạy bot
    application.run_polling()

def send_message_not_async(text):
    url = f"https://api.telegram.org/bot{config.get('TELEGRAM_BOT_TOKEN')}/sendMessage?chat_id={config.get('TELEGRAM_CHAT_ID')}&text={text}"
    requests.get(url).json()

#Giới thiệu sản phẩm
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    introduction_message = """
    🌟 **Giới thiệu sản phẩm** 🌟

    Chào mừng bạn đến với HỆ THỐNG TỰ ĐỘNG QLDA của tôi! Dưới đây là các tính năng chính của bot:

    - **/start <code>**: Bắt đầu task với mã code.
    - **/stop <code>**: Dừng task với mã code.
    - **/listTask**: Lấy danh sách task.
    - **/auto**: Bắt đầu auto task.
    - **/stopauto**: Dừng auto task.
    - **/help**: Hiển thị hướng dẫn.

    Hãy thử các lệnh trên để khám phá các tính năng của bot. Nếu bạn có bất kỳ câu hỏi nào, hãy gửi tin nhắn cho chúng tôi!

    Cảm ơn bạn đã sử dụng bot của tôi! 😊
    """
    await update.message.reply_text(introduction_message, parse_mode='Markdown')

# Lệnh /start để bắt đầu task
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text  # Lấy nội dung tin nhắn
    if message_text.startswith("/start"):
        user_input = message_text[6:].strip()
        if not user_input:
            await update.message.reply_text(f"⚠️ Không hợp lệ")
            return

        tasksArr = await get_tasks()
        print(tasksArr)
        if tasksArr:
            task_from_code = [task for task in tasksArr if task.get("Code") == user_input]
            if not task_from_code:
                await update.message.reply_text(f"⚠️ Không tìm thấy task với mã là: {user_input}")
                return
            await update_tasks(tasksArr)
            task_doing = task_from_code[0]
            await start_task(task_doing.get("TaskID"))

#Lệnh /stop để dừng task
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text  # Lấy nội dung tin nhắn
    if message_text.startswith("/stop"):
        user_input = message_text[5:].strip()
        if not user_input:
            await update.message.reply_text(f"⚠️ Không hợp lệ")
            return

        tasksArr = await get_tasks()
        if tasksArr:
            task_from_code = [task for task in tasksArr if task.get("Code") == user_input]
            if not task_from_code:
                await update.message.reply_text(f"⚠️ Không tìm thấy task với mã là: {user_input}")
                return
            await update_tasks(tasksArr)
            task_doing = task_from_code[0]
            await stop_task(task_doing.get("TaskID"))     

# Lệnh /listTask lấy tất cả task
async def list_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text  # Lấy nội dung tin nhắn
    if message_text.startswith("/listTask"):
        tasksArr = await get_tasks()
        if tasksArr:
            await update_tasks(tasksArr)  
            list_tasks = get_tasks_from_json()
            list_task_convert = [convert_keys_to_vietnamese(task) for task in list_tasks]
            formatted_tasks = json.dumps(list_task_convert, indent=4, ensure_ascii=False)
            
            await update.message.reply_text(f"```\n{formatted_tasks}\n```", parse_mode='Markdown')
            return          

#Lệnh /help dùng để hiển thị hướng dẫn
async def send_help_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text  # Lấy nội dung tin nhắn
    if message_text.startswith("/help"):
        await update.message.reply_text(help())
        return

def help():
    return """/start <code> : Bắt đầu task với mã code
/stop <code> : Dừng task với mã code
/listTask : Lấy danh sách task
/auto : Bắt đầu auto task
/stopauto : Dừng auto task
/help : Hiển thị hướng dẫn
    """  

# Lệnh /auto để bắt đầu auto task
async def auto_qlda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_checkin_task

    message_text = update.message.text  # Lấy nội dung tin nhắn 
    if message_text.startswith("/auto"):
        if auto_checkin_task and not auto_checkin_task.done():
            await update.message.reply_text("⚠️ Hệ thống tự động kiểm tra công việc đã chạy!")
            return

        # await auto_checkin()
        auto_checkin_task = asyncio.create_task(auto_checkin())
    return

#Lệnh /stopauto để dừng auto task
async def stop_auto_qlda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_checkin_task

    message_text = update.message.text  # Lấy nội dung tin nhắn 
    if message_text.startswith("/stopauto"):
        if auto_checkin_task and not auto_checkin_task.done():
            auto_checkin_task.cancel()
            try:
                await auto_checkin_task
            except asyncio.CancelledError:
                print("🚫 Auto check-in đã bị hủy!")

            await stop_task()
            await update.message.reply_text("✅ Đã dừng tự động kiểm tra công việc!")    
        else:
            await update.message.reply_text("⚠️ Hệ thống tự động kiểm tra công việc chưa chạy!")
       
    return
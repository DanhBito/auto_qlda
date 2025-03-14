import asyncio
import logging
from auto_telegram import main

# Cấu hình logging
logging.basicConfig(
    filename="app.log",  # Tên file log
    level=logging.INFO,  # Mức độ log: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format="%(asctime)s - %(levelname)s - %(message)s",  # Định dạng log
    datefmt="%Y-%m-%d %H:%M:%S",  # Định dạng thời gian
)

# Ghi log khi chương trình khởi động
logging.info("🚀 Chương trình bắt đầu chạy...")

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if str(e) == "Event loop is closed":
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main())
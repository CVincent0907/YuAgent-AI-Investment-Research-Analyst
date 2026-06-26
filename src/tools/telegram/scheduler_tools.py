import threading
import schedule
import time

from langsmith import traceable


@traceable(
    name="Telegram Tool: Daily Scheduler",
    run_type="tool",
)
def start_daily_scheduler(callback, hour=8, minute=0):
    """
    Starts a background scheduler.

    callback:
        Function to execute every day.
    """

    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(callback)

    def scheduler_loop():
        while True:
            schedule.run_pending()
            time.sleep(30)

    thread = threading.Thread(
        target=scheduler_loop,
        daemon=True,
    )

    thread.start()

    print(f"[Scheduler] Daily report scheduled at {hour:02d}:{minute:02d}")
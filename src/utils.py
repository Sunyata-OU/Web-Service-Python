from datetime import datetime


def get_current_date_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

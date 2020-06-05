# utilities/time.py
import datetime


def format_seconds_to_minutes_and_seconds(seconds):
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def get_todays_date() -> str:
    date = datetime.datetime.now()
    return f"{date.month:02d}/{date.day:02d}/{date.year}"

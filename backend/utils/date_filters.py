from datetime import datetime


def filter_logs_by_date(logs, day, month, year):
    """Filter login logs by optional day, month, and year query values."""
    filtered_logs = []

    for log in logs:
        log_time = log.get("time", "")

        try:
            log_date = datetime.strptime(log_time, "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue

        if day and log_date.day != int(day):
            continue

        if month and log_date.month != int(month):
            continue

        if year and log_date.year != int(year):
            continue

        filtered_logs.append(log)

    return filtered_logs

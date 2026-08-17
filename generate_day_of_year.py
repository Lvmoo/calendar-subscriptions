"""
生成"全年第几天"订阅日历,每天一个事件,标题格式:Day 124 of 2026

年份范围由 day_of_year_config.json 里的 years_behind / years_ahead 自动计算,
以运行脚本当天的年份为基准,不需要每年手动编辑年份数字。
比如 years_ahead=2 表示始终自动生成"今年"以及"未来两年"的日历,
配合 GitHub Actions 的定时任务(cron),每年会自动往后滚动,长期免维护。
"""
import json
from datetime import datetime, timedelta

CONFIG = "day_of_year_config.json"
OUTPUT = "output/day-of-year.ics"


def fmt(date_str: str) -> str:
    return date_str.replace("-", "")


def daterange_of_year(year: int):
    d = datetime(year, 1, 1)
    end = datetime(year, 12, 31)
    while d <= end:
        yield d
        d += timedelta(days=1)


def main():
    with open(CONFIG, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    this_year = datetime.now().year
    start_year = this_year - cfg.get("years_behind", 0)
    end_year = this_year + cfg.get("years_ahead", 0)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Day of Year Counter//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{cfg.get('calendar_name', '全年第几天')}",
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]

    event_count = 0
    for year in range(start_year, end_year + 1):
        is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        total_days = 366 if is_leap else 365
        for d in daterange_of_year(year):
            day_num = d.timetuple().tm_yday
            date_str = d.strftime("%Y-%m-%d")
            uid = f"doy-{date_str}@day-of-year"
            summary = f"Day {day_num} of {year}"
            description = f"{year}年第{day_num}天(共{total_days}天),剩余{total_days - day_num}天"

            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTART;VALUE=DATE:{fmt(date_str)}",
                f"DTEND;VALUE=DATE:{fmt((d + timedelta(days=1)).strftime('%Y-%m-%d'))}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                "TRANSP:TRANSPARENT",
                "END:VEVENT",
            ])
            event_count += 1

    lines.append("END:VCALENDAR")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines) + "\r\n")

    print(f"已生成 {OUTPUT},覆盖 {start_year}-{end_year} 年,共 {event_count} 个事件")


if __name__ == "__main__":
    main()

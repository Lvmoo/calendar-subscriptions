"""
读取 holidays.json,生成标准 .ics 日历文件到 output/china-holidays.ics

设计说明:
- 每个假期条目只需填 start(开始日)/end(结束日)/workdays(调休上班日列表,没有就填 []),
  标题里的"第X/N天"、备注里的星期几、共计天数、上班日等信息全部由脚本自动计算生成。
- 每年只需要在 holidays.json 里新增一个年份的数据块,推送到 GitHub 后
  Action 会自动重新生成 ics 文件,订阅链接本身不会变化。
"""
import json
from datetime import datetime, timedelta

SOURCE = "holidays.json"
OUTPUT = "output/china-holidays.ics"

WEEKDAY_CN = ["一", "二", "三", "四", "五", "六", "日"]


def fmt(date_str: str) -> str:
    """'2026-01-01' -> '20260101'"""
    return date_str.replace("-", "")


def next_day(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return (d + timedelta(days=1)).strftime("%Y-%m-%d")


def weekday_cn(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"周{WEEKDAY_CN[d.weekday()]}"


def md_cn(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{d.month}月{d.day}日"


def date_range(start_str: str, end_str: str):
    """按天遍历 start_str 到 end_str(含首尾)"""
    d = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    while d <= end:
        yield d.strftime("%Y-%m-%d")
        d += timedelta(days=1)


def build_single_day_event(uid: str, day: str, summary: str, description: str) -> list:
    return [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTART;VALUE=DATE:{fmt(day)}",
        f"DTEND;VALUE=DATE:{fmt(next_day(day))}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ]


def build_holiday_description(start: str, end: str, total: int, workdays: list) -> str:
    desc = f"{md_cn(start)}({weekday_cn(start)})至{md_cn(end)}({weekday_cn(end)})放假,共{total}天"
    if workdays:
        wd_str = "、".join(f"{md_cn(w)}({weekday_cn(w)})" for w in workdays)
        desc += f";{wd_str}上班"
    else:
        desc += ";无调休"
    return desc


def build_event(year: str, ev: dict) -> list:
    lines: list = []
    name = ev["name"]
    start, end = ev["start"], ev["end"]
    workdays = ev.get("workdays", [])

    days = list(date_range(start, end))
    total = len(days)
    description = build_holiday_description(start, end, total, workdays)

    for idx, day in enumerate(days, start=1):
        uid_key = f"{year}-{name}-{day}".replace(" ", "")
        uid = f"{uid_key}@china-holidays"
        summary = f"{name} 放假(第{idx}/{total}天)"
        lines.extend(build_single_day_event(uid, day, summary, description))

    for w in workdays:
        uid_key = f"{year}-{name}-banban-{w}".replace(" ", "")
        uid = f"{uid_key}@china-holidays"
        summary = f"调休上班({name})"
        wd_desc = f"为{name}假期调休,{md_cn(w)}({weekday_cn(w)})上班"
        lines.extend(build_single_day_event(uid, w, summary, wd_desc))

    return lines


def main():
    with open(SOURCE, "r", encoding="utf-8") as f:
        data = json.load(f)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//China Public Holidays//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{data.get('calendar_name', '中国大陆法定节假日')}",
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]

    event_count = 0
    for year in sorted(data["years"].keys()):
        for ev in data["years"][year]:
            ev_lines = build_event(year, ev)
            lines.extend(ev_lines)
            event_count += ev_lines.count("BEGIN:VEVENT")

    lines.append("END:VCALENDAR")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines) + "\r\n")

    print(f"已生成 {OUTPUT},共 {event_count} 个事件")


if __name__ == "__main__":
    main()

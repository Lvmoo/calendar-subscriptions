"""
生成"中国农历"订阅日历,每天一个事件,显示对应的农历日期。
标题格式:农历 正月初一 / 农历 闰六月十五
备注里附带干支年、生肖、农历节日(如果当天是农历节日,如中秋、除夕)。

依赖 cnlunar 库做真实的农历换算(含闰月识别),不是简单数学能算出来的,
所以这个日历和"全年第几天"不同,必须依赖专门的历法库。

年份范围由 lunar_config.json 里的 years_behind / years_ahead 自动计算,
逻辑和 generate_day_of_year.py 一致,长期免维护。
"""
import json
from datetime import datetime, timedelta
import cnlunar

CONFIG = "lunar_config.json"
OUTPUT = "output/lunar-calendar.ics"


def fmt(date_str: str) -> str:
    return date_str.replace("-", "")


def clean_lunar_holiday(raw: str) -> str:
    """cnlunar的农历节日字段里混有冷门神佛诞辰(如'华严菩萨诞'),
    过滤掉这些,只保留元宵、七夕、重阳这类大家熟悉的传统节日。"""
    if not raw:
        return ""
    parts = [p for p in raw.split("-") if not p.endswith("诞")]
    return "、".join(parts)


def main():
    with open(CONFIG, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    this_year = datetime.now().year
    start_year = this_year - cfg.get("years_behind", 0)
    end_year = this_year + cfg.get("years_ahead", 0)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Chinese Lunar Calendar//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{cfg.get('calendar_name', '中国农历')}",
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]

    event_count = 0
    d = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)

    while d <= end_date:
        lunar = cnlunar.Lunar(d, godType="8char")
        date_str = d.strftime("%Y-%m-%d")

        leap_prefix = "闰" if lunar.isLunarLeapMonth else ""
        month_cn = lunar.lunarMonthCn.replace("闰", "").replace("大", "").replace("小", "")
        day_cn = lunar.lunarDayCn
        lunar_date_str = f"{leap_prefix}{month_cn}{day_cn}"

        summary = f"农历 {lunar_date_str}"

        desc_parts = [f"干支年:{lunar.year8Char}", f"生肖:{lunar.chineseYearZodiac}"]
        holidays = clean_lunar_holiday(lunar.get_otherLunarHolidays())
        legal = lunar.get_legalHolidays()
        if legal:
            desc_parts.insert(0, legal)
        elif holidays:
            desc_parts.insert(0, holidays)
        description = ";".join(desc_parts)

        uid = f"lunar-{date_str}@chinese-lunar"

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
        d += timedelta(days=1)

    lines.append("END:VCALENDAR")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines) + "\r\n")

    print(f"已生成 {OUTPUT},覆盖 {start_year}-{end_year} 年,共 {event_count} 个事件")


if __name__ == "__main__":
    main()

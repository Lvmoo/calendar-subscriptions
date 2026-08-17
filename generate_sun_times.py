"""
生成"日出日落"订阅日历,每天一个事件,标题显示日出/日落时间,
备注附带民用/航海/天文三种晨昏蒙影时间、正午时刻、白昼时长。

依赖 astral 库做真实天文计算(基于经纬度、太阳赤纬角推算),
城市坐标、时区都在 sun_config.json 里配置,换城市只需要改经纬度。

年份范围沿用其余脚本的自动滚动模式(years_behind/years_ahead)。

三种晨昏蒙影的定义(太阳在地平线下的角度):
- 民用晨昏蒙影(6°):室外活动基本仍可视物的临界点,最常用
- 航海晨昏蒙影(12°):海平面地平线仍可分辨的临界点,航海定位参考
- 天文晨昏蒙影(18°):天空完全变暗、可观测暗弱天体的临界点,天文观测参考
"""
import json
from datetime import date, timedelta
import zoneinfo

from astral import LocationInfo
from astral.sun import sun, dawn, dusk

CONFIG = "sun_config.json"
OUTPUT = "output/sun-times-shanghai.ics"

DEPRESSIONS = [("民用", 6.0), ("航海", 12.0), ("天文", 18.0)]


def fmt(d: date) -> str:
    return d.strftime("%Y%m%d")


def hm(dt) -> str:
    return dt.strftime("%H:%M")


def main():
    with open(CONFIG, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    tz = zoneinfo.ZoneInfo(cfg["timezone"])
    loc = LocationInfo(cfg["city_name"], cfg["country"], cfg["timezone"], cfg["latitude"], cfg["longitude"])

    this_year = date.today().year
    start_year = this_year - cfg.get("years_behind", 0)
    end_year = this_year + cfg.get("years_ahead", 0)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Shanghai Sun Times//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{cfg.get('calendar_name', '日出日落')}",
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]

    event_count = 0
    d = date(start_year, 1, 1)
    end_date = date(end_year, 12, 31)

    while d <= end_date:
        s = sun(loc.observer, date=d, tzinfo=tz)
        sunrise, sunset, noon = s["sunrise"], s["sunset"], s["noon"]

        daylen = sunset - sunrise
        h, rem = divmod(int(daylen.total_seconds()), 3600)
        m = rem // 60

        summary = f"日出 {hm(sunrise)} / 日落 {hm(sunset)}"

        civil_dawn = dawn(loc.observer, date=d, tzinfo=tz, depression=6.0)
        civil_dusk = dusk(loc.observer, date=d, tzinfo=tz, depression=6.0)

        desc_parts = [
            f"正午:{hm(noon)}",
            f"昼长:{h}小时{m}分钟",
            f"天亮:{hm(civil_dawn)}",
            f"天黑:{hm(civil_dusk)}",
        ]
        for name, dep in DEPRESSIONS[1:]:
            dw = dawn(loc.observer, date=d, tzinfo=tz, depression=dep)
            du = dusk(loc.observer, date=d, tzinfo=tz, depression=dep)
            desc_parts.append(f"{name}晨光:{hm(dw)} / {name}黄昏:{hm(du)}")
        description = ";".join(desc_parts)

        date_str = d.strftime("%Y-%m-%d")
        uid = f"sun-{date_str}@shanghai-sun"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTART;VALUE=DATE:{fmt(d)}",
            f"DTEND;VALUE=DATE:{fmt(d + timedelta(days=1))}",
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

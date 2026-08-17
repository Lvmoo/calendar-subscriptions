"""
生成"上海未来7天天气"订阅日历,数据来自中央气象台(www.nmc.cn)的公开接口。

⚠️ 重要说明:
这个接口是中央气象台网站前端自己在用的接口,官方没有正式发布文档,
字段结构是根据网上多方资料交叉验证整理出来的,不保证100%准确,
接口本身也可能被官方随时调整(不打招呼)。
所以这里做了大量防御性写法:任何一个字段拿不到,就显示"暂无数据",
不会导致整个脚本崩溃、也不会导致其他日历生成失败。

和前面几个"计算类"日历(农历/节气/日出日落)不同,天气预报是实时变化的
外部数据,不能只在数据变化时才触发生成——需要每天定时拉取一次最新预报,
所以 workflow 里给这个脚本单独配置了每天的 cron 定时任务。

输出的7天预报会完整覆盖旧文件(不是追加),这样过去的日期自然被替换掉,
永远只保留"从今天起未来7天"的最新预报。
"""
import json
from datetime import datetime, timedelta

import requests

CONFIG = "weather_config.json"
OUTPUT = "output/weather-shanghai.ics"

API_URL = "http://www.nmc.cn/rest/weather"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Referer": "http://www.nmc.cn/",
}

# 天气现象关键词 -> emoji,按出现顺序匹配(前面优先)
WEATHER_EMOJI = [
    ("雷阵雨伴有冰雹", "⛈️"), ("雷阵雨", "⛈️"), ("雷电", "⚡"),
    ("暴雪", "❄️"), ("大雪", "❄️"), ("中雪", "🌨️"), ("小雪", "🌨️"), ("雪", "🌨️"),
    ("暴雨", "🌧️"), ("大雨", "🌧️"), ("中雨", "🌧️"), ("小雨", "🌦️"), ("阵雨", "🌦️"), ("雨", "🌧️"),
    ("霾", "😷"), ("雾", "🌫️"), ("沙尘暴", "🌪️"), ("扬沙", "🌪️"), ("浮尘", "🌪️"),
    ("大风", "💨"), ("台风", "🌀"),
    ("晴", "☀️"), ("多云", "⛅"), ("阴", "☁️"),
]


def pick_emoji(weather_text: str) -> str:
    for keyword, emoji in WEATHER_EMOJI:
        if keyword in weather_text:
            return emoji
    return "🌡️"


def g(d: dict, *keys, default="暂无数据"):
    """安全地按路径取嵌套字典的值,取不到就返回默认值,不抛异常。"""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    if cur in (None, "", "9999.0", "9998.0"):
        return default
    return cur


def fmt(d: datetime) -> str:
    return d.strftime("%Y%m%d")


def fetch_forecast(stationid: str) -> dict:
    resp = requests.get(API_URL, params={"stationid": stationid}, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != 0 or not payload.get("data"):
        raise RuntimeError(f"接口返回异常: {payload.get('msg', '未知错误')}")
    return payload["data"]


def build_event_for_day(idx: int, day_data: dict, base_date: datetime, real: dict) -> list:
    date_str = day_data.get("date", "")
    d = base_date + timedelta(days=idx)

    day_weather = g(day_data, "day", "weather", "info")
    day_temp = g(day_data, "day", "weather", "temperature")
    day_wind_dir = g(day_data, "day", "wind", "direct")
    day_wind_power = g(day_data, "day", "wind", "power")

    night_weather = g(day_data, "night", "weather", "info")
    night_temp = g(day_data, "night", "weather", "temperature")
    night_wind_dir = g(day_data, "night", "wind", "direct")
    night_wind_power = g(day_data, "night", "wind", "power")

    emoji = pick_emoji(day_weather if day_weather != "暂无数据" else night_weather)

    high = day_temp if day_temp != "暂无数据" else "?"
    low = night_temp if night_temp != "暂无数据" else "?"
    summary = f"{emoji} {day_weather} {low}°~{high}°C"

    desc_parts = [
        f"白天:{day_weather} {day_wind_dir}{day_wind_power}",
        f"夜间:{night_weather} {night_wind_dir}{night_wind_power}",
        f"最高温:{high}°C",
        f"最低温:{low}°C",
    ]

    # 第一天(今天)额外附上实况数据,信息更丰富
    if idx == 0 and real:
        humidity = g(real, "weather", "humidity")
        pressure = g(real, "weather", "airpressure")
        feels_like = g(real, "weather", "feelst")
        rain = g(real, "weather", "rain")
        real_wind_dir = g(real, "wind", "direct")
        real_wind_power = g(real, "wind", "power")
        real_temp = g(real, "weather", "temperature")

        desc_parts.append(f"实况气温:{real_temp}°C")
        desc_parts.append(f"体感温度:{feels_like}°C")
        desc_parts.append(f"湿度:{humidity}%")
        desc_parts.append(f"气压:{pressure}hPa")
        desc_parts.append(f"实况风力:{real_wind_dir}{real_wind_power}")
        desc_parts.append(f"降水量:{rain}mm")

    desc_parts.append("数据来源:中央气象台(nmc.cn)")
    description = ";".join(desc_parts)

    uid = f"weather-{fmt(d)}@nmc-forecast"

    return [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTART;VALUE=DATE:{fmt(d)}",
        f"DTEND;VALUE=DATE:{fmt(d + timedelta(days=1))}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ]


def main():
    with open(CONFIG, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    data = fetch_forecast(cfg["stationid"])
    detail = g(data, "predict", "detail", default=[])
    real = data.get("real", {})

    if not detail:
        raise RuntimeError("未能从接口解析出7天预报数据(detail为空),接口结构可能已变化")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Shanghai Weather NMC//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{cfg.get('calendar_name', '天气预报')}",
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]

    base_date = datetime.now()
    event_count = 0
    for idx, day_data in enumerate(detail[:7]):
        lines.extend(build_event_for_day(idx, day_data, base_date, real))
        event_count += 1

    lines.append("END:VCALENDAR")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines) + "\r\n")

    print(f"已生成 {OUTPUT},共 {event_count} 天预报")


if __name__ == "__main__":
    main()

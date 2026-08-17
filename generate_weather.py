"""
生成"上海未来7天天气"订阅日历,数据来自中央气象台(www.nmc.cn)的公开接口。

⚠️ 重要说明:
这个接口是中央气象台网站前端自己在用的接口,官方没有正式发布文档,
字段结构是根据网上多方资料交叉验证整理出来的,不保证100%准确,
接口本身也可能被官方随时调整(不打招呼)。

所以这里做了大量防御性写法:任何一个字段拿不到,就显示"暂无数据",
不会导致整个脚本因为单个天气字段缺失而崩溃。

上海当前使用的 NMC stationid:
WwcJd

天气预报是实时变化的外部数据,
workflow 中建议单独配置定时任务,每小时拉取一次最新预报。

输出的7天预报会完整覆盖旧文件(不是追加),
这样过去的日期自然被替换掉,
永远只保留"从今天起未来7天"的最新预报。

每条日历备注会记录本次数据更新时间:
更新时间:YYYY-MM-DD HH:MM（北京时间）
"""

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests


CONFIG = "weather_config.json"
OUTPUT = "output/weather-shanghai.ics"

# 中央气象台天气接口
API_URL = "https://www.nmc.cn/rest/weather"

# 上海时区
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
UTC_TZ = ZoneInfo("UTC")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Referer": "https://www.nmc.cn/",
}


# 天气现象关键词 -> emoji
# 按出现顺序匹配,前面优先
WEATHER_EMOJI = [
    ("雷阵雨伴有冰雹", "⛈️"),
    ("雷阵雨", "⛈️"),
    ("雷电", "⚡"),
    ("暴雪", "❄️"),
    ("大雪", "❄️"),
    ("中雪", "🌨️"),
    ("小雪", "🌨️"),
    ("雪", "🌨️"),
    ("暴雨", "🌧️"),
    ("大雨", "🌧️"),
    ("中雨", "🌧️"),
    ("小雨", "🌦️"),
    ("阵雨", "🌦️"),
    ("雨", "🌧️"),
    ("霾", "😷"),
    ("雾", "🌫️"),
    ("沙尘暴", "🌪️"),
    ("扬沙", "🌪️"),
    ("浮尘", "🌪️"),
    ("大风", "💨"),
    ("台风", "🌀"),
    ("晴", "☀️"),
    ("多云", "⛅"),
    ("阴", "☁️"),
]


def pick_emoji(weather_text: str) -> str:
    """根据天气文字选择 emoji。"""

    if not weather_text or weather_text == "暂无数据":
        return "🌡️"

    for keyword, emoji in WEATHER_EMOJI:
        if keyword in str(weather_text):
            return emoji

    return "🌡️"


def g(d: dict, *keys, default="暂无数据"):
    """
    安全地按路径取嵌套字典的值。

    取不到、为空或者遇到 NMC 常见无效值时,
    返回 default。
    """

    cur = d

    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default

        cur = cur[k]

    if cur is None:
        return default

    if isinstance(cur, str):
        value = cur.strip()

        if value == "":
            return default

        if value in (
            "9998",
            "9999",
            "9998.0",
            "9999.0",
        ):
            return default

    if isinstance(cur, (int, float)):
        if cur in (9998, 9999, 9998.0, 9999.0):
            return default

    return cur


def ics_escape(value) -> str:
    """
    对 iCalendar SUMMARY / DESCRIPTION 中的特殊字符进行转义。
    """

    if value is None:
        return ""

    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def fmt(d) -> str:
    """日期 -> YYYYMMDD。"""
    return d.strftime("%Y%m%d")


def parse_api_date(value, fallback):
    """
    解析 NMC 返回的 date。

    正常情况下 NMC 返回:
    YYYY-MM-DD

    如果格式发生变化,则使用 fallback。
    """

    if not value:
        return fallback

    text = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]

    for date_format in formats:
        try:
            return datetime.strptime(
                text,
                date_format,
            ).date()
        except ValueError:
            continue

    return fallback


def fetch_forecast(stationid: str) -> dict:
    """
    获取 NMC 上海天气预报。

    当前上海 stationid:
    WwcJd
    """

    try:
        resp = requests.get(
            API_URL,
            params={"stationid": stationid},
            headers=HEADERS,
            timeout=15,
        )

        resp.raise_for_status()

    except requests.RequestException as e:
        raise RuntimeError(
            f"NMC天气接口请求失败:{e}"
        ) from e

    try:
        payload = resp.json()

    except ValueError as e:
        raise RuntimeError(
            "NMC天气接口返回的不是合法JSON"
        ) from e

    if not isinstance(payload, dict):
        raise RuntimeError(
            "NMC天气接口返回格式异常"
        )

    code = payload.get("code")
    msg = payload.get("msg")
    data = payload.get("data")

    if (
        code != 0
        or not isinstance(data, dict)
        or not data
    ):
        raise RuntimeError(
            "接口返回异常: "
            f"code={code!r}, "
            f"msg={msg!r}, "
            f"data={'存在' if data else '不存在'}"
        )

    return data


def build_event_for_day(
    idx: int,
    day_data: dict,
    forecast_date,
    real: dict,
    update_time: str,
) -> list:
    """
    生成一天的日历事件。
    """

    # API 返回的 date 优先
    d = parse_api_date(
        day_data.get("date"),
        forecast_date,
    )

    # -------------------------
    # 白天
    # -------------------------

    day_weather = g(
        day_data,
        "day",
        "weather",
        "info",
    )

    day_temp = g(
        day_data,
        "day",
        "weather",
        "temperature",
    )

    day_wind_dir = g(
        day_data,
        "day",
        "wind",
        "direct",
    )

    day_wind_power = g(
        day_data,
        "day",
        "wind",
        "power",
    )

    # -------------------------
    # 夜间
    # -------------------------

    night_weather = g(
        day_data,
        "night",
        "weather",
        "info",
    )

    night_temp = g(
        day_data,
        "night",
        "weather",
        "temperature",
    )

    night_wind_dir = g(
        day_data,
        "night",
        "wind",
        "direct",
    )

    night_wind_power = g(
        day_data,
        "night",
        "wind",
        "power",
    )

    # -------------------------
    # 温度
    # -------------------------

    high = (
        day_temp
        if day_temp != "暂无数据"
        else "?"
    )

    low = (
        night_temp
        if night_temp != "暂无数据"
        else "?"
    )

    # -------------------------
    # Emoji
    # -------------------------

    emoji = pick_emoji(
        day_weather
        if day_weather != "暂无数据"
        else night_weather
    )

    # -------------------------
    # 标题
    # -------------------------

    summary = (
        f"{emoji} "
        f"{day_weather} "
        f"{low}°~{high}°C"
    )

    # -------------------------
    # 描述
    # -------------------------

    desc_parts = [
        f"白天:{day_weather} {day_wind_dir}{day_wind_power}",
        f"夜间:{night_weather} {night_wind_dir}{night_wind_power}",
        f"最高温:{high}°C",
        f"最低温:{low}°C",
    ]

    # -------------------------
    # 第一天(今天)增加实况数据
    # -------------------------

    if idx == 0 and real:

        humidity = g(
            real,
            "weather",
            "humidity",
        )

        pressure = g(
            real,
            "weather",
            "airpressure",
        )

        feels_like = g(
            real,
            "weather",
            "feelst",
        )

        rain = g(
            real,
            "weather",
            "rain",
        )

        real_wind_dir = g(
            real,
            "wind",
            "direct",
        )

        real_wind_power = g(
            real,
            "wind",
            "power",
        )

        real_temp = g(
            real,
            "weather",
            "temperature",
        )

        desc_parts.append(
            f"实况气温:{real_temp}°C"
        )

        desc_parts.append(
            f"体感温度:{feels_like}°C"
        )

        desc_parts.append(
            f"湿度:{humidity}%"
        )

        desc_parts.append(
            f"气压:{pressure}hPa"
        )

        desc_parts.append(
            f"实况风力:{real_wind_dir}{real_wind_power}"
        )

        desc_parts.append(
            f"降水量:{rain}mm"
        )

    # -------------------------
    # 更新时间
    # -------------------------

    desc_parts.append(
        f"更新时间:{update_time}（北京时间）"
    )

    # -------------------------
    # 数据来源
    # -------------------------

    desc_parts.append(
        "数据来源:中央气象台(nmc.cn)"
    )

    description = ";".join(desc_parts)

    # -------------------------
    # UID
    # -------------------------

    uid = (
        f"weather-{fmt(d)}"
        "@nmc-forecast"
    )

    # -------------------------
    # DTSTAMP
    # -------------------------

    now_utc = datetime.now(UTC_TZ)

    dtstamp = now_utc.strftime(
        "%Y%m%dT%H%M%SZ"
    )

    return [
        "BEGIN:VEVENT",
        f"UID:{ics_escape(uid)}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;VALUE=DATE:{fmt(d)}",
        (
            f"DTEND;VALUE=DATE:"
            f"{fmt(d + timedelta(days=1))}"
        ),
        f"SUMMARY:{ics_escape(summary)}",
        f"DESCRIPTION:{ics_escape(description)}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ]


def main():

    print(
        "开始生成上海未来7天天气日历..."
    )

    # -------------------------
    # 读取配置
    # -------------------------

    try:
        with open(
            CONFIG,
            "r",
            encoding="utf-8",
        ) as f:
            cfg = json.load(f)

    except FileNotFoundError as e:
        raise RuntimeError(
            f"找不到配置文件:{CONFIG}"
        ) from e

    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"{CONFIG} JSON格式错误:{e}"
        ) from e

    if not isinstance(cfg, dict):
        raise RuntimeError(
            f"{CONFIG}必须是JSON对象"
        )

    # -------------------------
    # stationid
    # -------------------------

    stationid = cfg.get(
        "stationid",
        "WwcJd",
    )

    if not stationid:
        raise RuntimeError(
            "weather_config.json缺少stationid"
        )

    stationid = str(stationid)

    print(
        f"stationid:{stationid}"
    )

    # -------------------------
    # 上海当前时间
    # -------------------------

    now_shanghai = datetime.now(
        SHANGHAI_TZ
    )

    today = now_shanghai.date()

    update_time = now_shanghai.strftime(
        "%Y-%m-%d %H:%M"
    )

    print(
        f"更新时间:{update_time}"
        "（北京时间）"
    )

    # -------------------------
    # 获取天气
    # -------------------------

    data = fetch_forecast(
        stationid
    )

    # -------------------------
    # 获取7天预报
    # -------------------------

    detail = g(
        data,
        "predict",
        "detail",
        default=[],
    )

    real = data.get(
        "real",
        {},
    )

    if not isinstance(real, dict):
        real = {}

    if not isinstance(detail, list):
        raise RuntimeError(
            "未能从接口解析出7天预报数据"
            "(predict.detail不是数组),"
            "接口结构可能已变化"
        )

    if not detail:
        raise RuntimeError(
            "未能从接口解析出7天预报数据"
            "(detail为空),"
            "接口结构可能已变化"
        )

    print(
        f"NMC返回{len(detail)}条预报数据"
    )

    # -------------------------
    # 解析未来7天
    # -------------------------

    forecast_days = []

    for idx, day_data in enumerate(
        detail
    ):

        if not isinstance(
            day_data,
            dict,
        ):
            print(
                f"警告:第{idx + 1}条"
                "预报数据不是字典,跳过"
            )
            continue

        fallback_date = (
            today
            + timedelta(days=idx)
        )

        forecast_date = parse_api_date(
            day_data.get("date"),
            fallback_date,
        )

        # 过去日期不生成
        if forecast_date < today:
            continue

        forecast_days.append(
            (
                forecast_date,
                day_data,
            )
        )

    # 按日期排序
    forecast_days.sort(
        key=lambda item: item[0]
    )

    # 只保留未来7天
    forecast_days = forecast_days[:7]

    if not forecast_days:
        raise RuntimeError(
            "没有解析出未来7天预报"
        )

    # -------------------------
    # 创建ICS
    # -------------------------

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Shanghai Weather NMC//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        (
            "X-WR-CALNAME:"
            f"{ics_escape(cfg.get('calendar_name', '天气预报'))}"
        ),
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]

    event_count = 0

    # -------------------------
    # 生成事件
    # -------------------------

    for idx, (
        forecast_date,
        day_data,
    ) in enumerate(
        forecast_days
    ):

        lines.extend(
            build_event_for_day(
                idx,
                day_data,
                forecast_date,
                real,
                update_time,
            )
        )

        event_count += 1

        weather = g(
            day_data,
            "day",
            "weather",
            "info",
        )

        high = g(
            day_data,
            "day",
            "weather",
            "temperature",
        )

        low = g(
            day_data,
            "night",
            "weather",
            "temperature",
        )

        print(
            f"{forecast_date}:"
            f"{weather} "
            f"{low}~{high}°C"
        )

    # -------------------------
    # 结束ICS
    # -------------------------

    lines.append(
        "END:VCALENDAR"
    )

    # -------------------------
    # 确保输出目录存在
    # -------------------------

    output_dir = OUTPUT.rsplit(
        "/",
        1,
    )[0]

    if output_dir:
        import os

        os.makedirs(
            output_dir,
            exist_ok=True,
        )

    # -------------------------
    # 完整覆盖旧文件
    # -------------------------

    with open(
        OUTPUT,
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        f.write(
            "\r\n".join(lines)
            + "\r\n"
        )

    print(
        f"已生成{OUTPUT},"
        f"共{event_count}天预报"
    )


if __name__ == "__main__":
    main()
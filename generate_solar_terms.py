"""
生成"二十四节气"订阅日历,每个节气一个事件(全年24个,比逐日农历轻量很多)。
标题格式:立春 / 清明 / 冬至 等。

依赖 cnlunar 库计算节气的公历日期(基于太阳黄经的真实天文计算,
不是固定日期,每年会有1天左右浮动)。

年份范围由 solar_terms_config.json 自动计算,逻辑与其余脚本一致。
"""
import json
from datetime import datetime, timedelta
import cnlunar

CONFIG = "solar_terms_config.json"
OUTPUT = "output/solar-terms.ics"

# 二十四节气对应的季节/物候简介,写进备注方便订阅者查看
SOLAR_TERM_NOTES = {
    "立春": "春季开始,万物复苏",
    "雨水": "降雨渐增,气温回升",
    "惊蛰": "春雷始鸣,蛰虫苏醒",
    "春分": "昼夜平分,春意正浓",
    "清明": "气清景明,传统扫墓踏青时节",
    "谷雨": "雨生百谷,春季最后一个节气",
    "立夏": "夏季开始,万物繁茂",
    "小满": "夏熟作物籽粒渐满",
    "芒种": "麦类等有芒作物成熟,农事繁忙",
    "夏至": "北半球白昼最长的一天",
    "小暑": "天气开始炎热",
    "大暑": "一年中最热的时节",
    "立秋": "秋季开始,暑去凉来",
    "处暑": "暑气结束,气温下降",
    "白露": "昼夜温差加大,清晨出现白色露水",
    "秋分": "昼夜平分,秋意渐浓",
    "寒露": "露水已寒,气温更低",
    "霜降": "开始降霜,秋季最后一个节气",
    "立冬": "冬季开始,万物收藏",
    "小雪": "开始降雪但雪量小",
    "大雪": "降雪量增多,天气更冷",
    "冬至": "北半球白昼最短的一天,传统重要节气",
    "小寒": "天气寒冷但未至极点",
    "大寒": "一年中最冷的时节,冬季最后一个节气",
}


def fmt(date_str: str) -> str:
    return date_str.replace("-", "")


def main():
    with open(CONFIG, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    this_year = datetime.now().year
    start_year = this_year - cfg.get("years_behind", 0)
    end_year = this_year + cfg.get("years_ahead", 0)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//24 Solar Terms//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{cfg.get('calendar_name', '二十四节气')}",
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]

    event_count = 0
    for year in range(start_year, end_year + 1):
        lunar = cnlunar.Lunar(datetime(year, 6, 1), godType="8char")
        terms_dic = lunar.thisYearSolarTermsDic  # {"立春": (2, 4), ...}

        for term_name, (month, day) in terms_dic.items():
            d = datetime(year, month, day)
            date_str = d.strftime("%Y-%m-%d")
            uid = f"term-{date_str}-{term_name}@solar-terms"
            note = SOLAR_TERM_NOTES.get(term_name, "")

            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTART;VALUE=DATE:{fmt(date_str)}",
                f"DTEND;VALUE=DATE:{fmt((d + timedelta(days=1)).strftime('%Y-%m-%d'))}",
                f"SUMMARY:{term_name}",
                f"DESCRIPTION:{note}",
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

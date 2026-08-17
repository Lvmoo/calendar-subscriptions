# 中国日历订阅合集

免费、可自动更新的中国相关订阅日历合集,基于 GitHub 免费托管。共4个独立日历:

| 日历 | 文件 | 更新频率 |
|---|---|---|
| 法定节假日 | `output/china-holidays.ics` | 每年手动编辑一次(官方公布后) |
| 全年第几天 | `output/day-of-year.ics` | 完全自动,免维护 |
| 中国农历 | `output/lunar-calendar.ics` | 完全自动,免维护 |
| 二十四节气 | `output/solar-terms.ics` | 完全自动,免维护 |
| 上海日出日落 | `output/sun-times-shanghai.ics` | 完全自动,免维护 |
| 上海未来7天天气 | `output/weather-shanghai.ics` | 完全自动,**每小时**刷新 |

## 工作原理

- 每个日历有各自的生成脚本(`generate_*.py`)和配置文件
- `.github/workflows/build.yml`:代码或配置变化后自动运行全部脚本,重新生成所有ics文件;
  另外设置了**每月1号定时任务**,让"全年第几天/农历/节气"这三个纯计算类日历的年份范围自动往后滚动
- 每个日历的订阅链接**永远不变**,内容随更新自动刷新

## 一次性部署步骤(约10分钟)

### 1. 创建 GitHub 仓库
1. 注册/登录 [github.com](https://github.com)
2. 右上角 `+` → `New repository`
3. 仓库名随意,比如 `calendar-subscriptions`
4. 选择 **Public**(公开仓库,Actions对个人账户免费不限时长)
5. 点击 `Create repository`

### 2. 上传本项目文件
把这个文件夹里的所有文件(包括隐藏的 `.github` 文件夹)上传到仓库:
- 网页端:`Add file → Upload files`,把所有文件拖进去
  - 注意确保 `.github/workflows/build.yml` 路径结构保持不变
  - 网页拖拽有时会漏掉隐藏文件夹,建议改用 GitHub Desktop 或 `git` 命令行上传更可靠
- 提交(Commit)到 `main` 分支

### 3. 开启 Actions 权限
1. 仓库 `Settings → Actions → General`
2. `Workflow permissions` 选择 `Read and write permissions`
3. 保存

### 4. 手动触发一次生成
1. 仓库的 `Actions` 标签页
2. 选择 `生成订阅日历`
3. 点击 `Run workflow`
4. 等待跑完(cnlunar需要额外安装依赖,大约1分钟),`output/` 目录下会出现4个ics文件

### 5. 获取订阅链接
链接格式统一为:

```
https://raw.githubusercontent.com/lvmoo/calendar-subscriptions/main/output/文件名.ics
```

比如:
```
https://raw.githubusercontent.com/lvmoo/calendar-subscriptions/main/output/china-holidays.ics
https://raw.githubusercontent.com/lvmoo/calendar-subscriptions/main/output/day-of-year.ics
https://raw.githubusercontent.com/lvmoo/calendar-subscriptions/main/output/lunar-calendar.ics
https://raw.githubusercontent.com/lvmoo/calendar-subscriptions/main/output/solar-terms.ics
https://raw.githubusercontent.com/lvmoo/calendar-subscriptions/main/output/sun-times-shanghai.ics
https://raw.githubusercontent.com/lvmoo/calendar-subscriptions/main/output/weather-shanghai.ics
```

四个链接互相独立,可以分别发给不同的人订阅。

## 别人怎么订阅

**iPhone / iPad**
设置 → 日历 → 账户 → 添加账户 → 其他 → 添加已订阅的日历 → 粘贴链接

**Google 日历**
网页版左侧「其他日历」旁边的 `+` → 通过网址 → 粘贴链接

**Outlook**
日历 → 添加日历 → 从 Internet 订阅 → 粘贴链接

---

# 日历一:法定节假日

## 显示效果

**放假日,标题:** `劳动节 放假(第1/5天)`
**放假日,备注:** `5月1日(周五)至5月5日(周二)放假,共5天;5月9日(周六)上班`
**调休日,标题:** `调休上班(劳动节)`
**调休日,备注:** `为劳动节假期调休,5月9日(周六)上班`

没有调休的假期(清明节、端午节),备注显示"无调休"。

## 每年更新方法(这是4个日历里唯一需要手动更新的)

国务院每年11月前后公布次年节假日安排,那之后:
1. 打开仓库里的 `holidays.json`,右上角铅笔图标编辑
2. 在 `"years"` 里新增一个年份数据块,格式参考已有的 `"2026"`
3. 提交(Commit changes)
4. Actions自动检测到变化,几十秒内重新生成,链接不变,订阅者自动收到更新

## holidays.json 数据格式

```json
{
  "name": "劳动节",
  "start": "2026-05-01",
  "end": "2026-05-05",
  "workdays": ["2026-05-09"]
}
```

只需要填名称、开始日、结束日、调休日期(没有调休填 `[]`)。标题里的"第X/N天"、
备注里的星期几、共计天数,全部由脚本自动算出来。

---

# 日历二:全年第几天(Day of Year)

标题格式:`Day 124 of 2026`,备注显示当年共多少天、剩余多少天(自动识别闰年)。

纯数学计算,不需要每年手动维护。`day_of_year_config.json`:

```json
{"years_behind": 0, "years_ahead": 2}
```

`years_ahead: 2` 表示始终自动生成"今年 + 未来2年",配合每月自动定时任务,
年份范围随时间自动往后滚动,不需要手动改任何数字。

---

# 日历三:中国农历

## 显示效果

标题:`农历 正月初一`、`农历 闰六月初一`(自动识别闰月)
备注:`干支年:丙午;生肖:马`,如果当天是元宵、七夕、中秋、重阳等传统节日,
会额外标注在备注最前面,比如 `中秋节;干支年:丙午;生肖:马`

冷门的神佛诞辰(如"华严菩萨诞")已经在脚本里过滤掉,不会出现在备注里。

## 技术说明

依赖 `cnlunar` 这个开源库做真实的农历换算(农历有闰月、大小月,不是靠数学公式
能推算的,必须用历法库)。`lunar_config.json` 的年份范围配置方式和"全年第几天"
完全一样,同样是全自动免维护。

---

# 日历四:二十四节气

## 显示效果

标题:`立春`、`清明`、`冬至` 等
备注:简短的节气介绍,比如清明的备注是"气清景明,传统扫墓踏青时节"

节气的公历日期基于太阳黄经,每年会有1天左右浮动(不是固定日期),
同样依赖 `cnlunar` 库做真实天文计算。`solar_terms_config.json` 配置方式不变,全自动免维护。

---

# 日历五:上海日出日落

## 显示效果

标题:`日出 04:50 / 日落 19:01`

备注:`正午:11:55;昼长:14小时10分钟;天亮:04:22;天黑:19:29;航海晨光:03:48 / 航海黄昏:20:03;天文晨光:03:11 / 天文黄昏:20:40`

"天亮"、"天黑"用的是民用晨昏蒙影(地平线下6°)的时间点——也就是天文学上"室外基本能看清东西"的临界点,和日常生活里"天亮了/天黑了"的感觉最接近。

## 三种晨昏蒙影时间是什么

太阳落到地平线以下后天不会立刻全黑,根据太阳在地平线下的角度分成三档,
角度越大天越黑:

- **民用晨昏蒙影(地平线下6°)**:室外活动基本还能看清东西的临界点,日常生活最常用,备注里标注为"天亮"/"天黑"
- **航海晨昏蒙影(地平线下12°)**:海平面地平线仍能分辨的临界点,传统航海定位的参考标准
- **天文晨昏蒙影(地平线下18°)**:天空完全变黑、能观测暗弱天体的临界点,天文观测(比如看银河、拍星空)通常要等过了这个时间点

## 技术说明

依赖 `astral` 这个开源天文库,根据经纬度和太阳赤纬角做真实天文计算,和农历、
节气一样不是简单数学公式能算出来的。

`sun_config.json` 里存放城市坐标,目前是上海:

```json
{
  "city_name": "Shanghai",
  "latitude": 31.2304,
  "longitude": 121.4737,
  "timezone": "Asia/Shanghai",
  "years_behind": 0,
  "years_ahead": 1
}
```

**如果你以后想换城市或者加另一个城市**,改经纬度和时区即可(时区必须是IANA
时区名,比如北京/上海统一用 `Asia/Shanghai`)。如果想同时订阅多个城市,
可以复制一份 `sun_config.json` 和 `generate_sun_times.py`,改个输出文件名
(比如 `sun-times-beijing.ics`),互不冲突。

年份范围配置方式和其余自动化日历一致,免维护。

---

# 日历六:上海未来7天天气(中央气象台)

## 显示效果

标题:`☀️ 晴 22°~31°C`(emoji随天气现象自动匹配,晴天☀️、下雨🌧️、雷阵雨⛈️、雾🌫️等)

备注(今天,信息最丰富,附带实况数据):
```
白天:晴 东南风3-4级;夜间:多云 东风2-3级;最高温:31°C;最低温:22°C;
实况气温:26°C;体感温度:28°C;湿度:65%;气压:1012hPa;实况风力:东南风3级;
降水量:0mm;数据来源:中央气象台(nmc.cn)
```

未来2-7天(没有实况数据,只有预报):
```
白天:多云 西南风3-4级;夜间:阴 无持续风向<3级;最高温:29°C;最低温:23°C;
数据来源:中央气象台(nmc.cn)
```

## ⚠️ 重要说明:这个日历和其他5个不一样

前面5个日历(节假日/全年第几天/农历/节气/日出日落)的数据要么是官方一次性
公布的固定安排,要么是纯数学天文计算,**结果是确定的、可提前算好的**。

**天气预报不是**——它是每天变化的实时外部数据,依赖的是中央气象台网站
(nmc.cn)提供给自己前端用的一个**非官方公开文档**的接口。这意味着:

- 数据本身来自中央气象台,权威可靠
- 但接口本身没有官方文档,字段结构是社区逆向摸索出来的,细节可能有出入
- 接口有反爬保护(需要伪装浏览器请求头才能访问),理论上随时可能被调整,
  届时脚本可能需要跟着微调

**因此代码里做了防御性处理**:任何一个字段解析失败,只会显示"暂无数据"
而不会导致整个日历生成失败;这个日历单独抓取失败时(workflow里配置了
`continue-on-error: true`),也不会影响其余5个日历正常更新和提交。

## 更新频率

天气预报每天都会变,workflow里为这个日历单独配置了**每小时自动运行一次**
的定时任务(其余计算类日历是每月一次)。也就是说这个日历始终保持"从今天
起未来7天"的最新预报,过时的日期会在每次刷新时自动被替换掉,不需要
手动维护。

## 换成别的城市

`weather_config.json`:

```json
{
  "calendar_name": "上海未来7天天气(中央气象台)",
  "city_name": "上海",
  "stationid": "WwcJd"
}
```

`stationid` 是中央气象台内部的气象站编号,换城市需要先查到对应编号:
1. 访问 `http://www.nmc.cn/rest/province` 找到省份代码
2. 访问 `http://www.nmc.cn/rest/province/省份代码` 找到城市对应的站号
3. 把 `stationid` 换成查到的编号即可

## 如果部署后发现字段显示"暂无数据"

说明接口返回的实际字段名和脚本里假设的不完全一致,把生成出来的
`output/weather-shanghai.ics` 内容发给我,我可以照着实际返回的结构调整
`generate_weather.py` 里的字段解析部分。

---

## 常见问题

**Q: 链接会不会过期?**
不会。只要仓库不删除,`raw.githubusercontent.com` 的链接永久有效。

**Q: 节假日官方安排有调整怎么办(历史上出现过)?**
直接编辑 `holidays.json` 对应条目并提交,链接不变,订阅者自动收到更新。

**Q: 其他三个日历(全年第几天/农历/节气)需要我做什么吗?**
部署完之后完全不需要管,每月自动定时任务会让年份范围一直往后滚动。

**Q: Actions 会不会收费?**
公开(Public)仓库的 GitHub Actions 对个人账户完全免费,没有时长限制。

**Q: cnlunar 这个库靠谱吗?**
它是一个成熟的开源农历计算库,基于天文算法而非查表拼凑,闰月、节气日期
都是真实计算得出,不是估算值。

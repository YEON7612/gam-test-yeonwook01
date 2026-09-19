# -*- coding: utf-8 -*-
"""공개 데이터 → 10주제 × 5문항.

**모든 숫자는 raw/ 의 원본에서 계산합니다.** 지어낸 값이 하나도 없어야 합니다.
결과는 앱이 읽는 topics/*.json 과, 사람이 읽는 tools/정답지.md 로 나갑니다.

정답지와 이 스크립트는 .vercelignore 에 들어 있어 **배포되지 않습니다.**
공개 URL 에 정답지가 올라가면 게임이 성립하지 않습니다.

실행 (저장소 최상위에서):
    python tools/build_topics.py
"""
from __future__ import annotations

import csv
import io
import json
import datetime as dt
from collections import Counter
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent          # tools/
APP = HERE.parent                                # 저장소 최상위 = 배포되는 곳
RAW = APP / "data" / "raw"
OUT = APP / "topics"

TOPICS: list[dict] = []


def load_json(name):
    return json.load(io.open(RAW / name, encoding="utf-8"))


def load_csv(name):
    return list(csv.DictReader(io.open(RAW / name, encoding="utf-8")))


# World Bank·OWID 응답에는 '유럽연합' '고소득국' 같은 **집계치**가 섞여 있다.
# 그대로 순위를 매기면 나라와 대륙을 한 줄에 놓고 세는 셈이 된다.
REAL = {x["id"] for x in load_json("wb_countries.json")[1]
        if x["region"]["id"] != "NA"}


def wb_countries(rows, year):
    """그 해의 실제 국가 값만 남긴다 (집계치 제외)."""
    return {r["country"]["value"]: r["value"] for r in rows
            if int(r["date"]) == year and r["countryiso3code"] in REAL}


def owid_countries(rows, year, col):
    """OWID 도 마찬가지. code 가 비었거나 OWID_ 로 시작하면 집계치다."""
    return {r["entity"]: float(r[col]) for r in rows
            if int(r["year"]) == year and r["code"]
            and not r["code"].startswith("OWID")}


def topic(tid, emoji, title, blurb, source, source_url, questions, caveat=""):
    """caveat = 이 데이터를 믿을 때의 한계. 앱 화면에도 그대로 나간다.

    출처가 다르면 같은 '서울 기온'도 값이 다르다. 그 사실을 감추지 않는다.
    """
    TOPICS.append({"id": tid, "emoji": emoji, "title": title, "blurb": blurb,
                   "source": source, "source_url": source_url,
                   "caveat": caveat, "questions": questions})


def slider(qid, text, answer, unit, lo, hi, step, basis, why):
    return {"id": qid, "type": "slider", "text": text, "unit": unit,
            "min": lo, "max": hi, "step": step,
            "answer": round(float(answer), 1), "basis": basis, "why": why}


def choice(qid, text, options, answer, basis, why):
    assert answer in options, f"{qid}: 정답이 선택지에 없습니다"
    return {"id": qid, "type": "choice", "text": text, "options": options,
            "answer": answer, "basis": basis, "why": why}


# ════════════════════════════════════════════════════════════════
# 기상 공통
# ════════════════════════════════════════════════════════════════
w = load_json("seoul_weather.json")["daily"]
W = [{"d": dt.date.fromisoformat(t), "hi": hi, "lo": lo, "rain": r}
     for t, hi, lo, r in zip(w["time"], w["temperature_2m_max"],
                             w["temperature_2m_min"], w["precipitation_sum"])]
W24 = [x for x in W if x["d"].year == 2024]


def years(a, b):
    return [x for x in W if a <= x["d"].year <= b]


# ── 1. 서울 기온 ─────────────────────────────────────────────────
# ERA5 는 1950~70년대 구간의 품질이 낮고(초기 확장), 격자 평균이라 도심
# 관측값보다 낮게 나온다. 그래서 '역대 최고기온'이나 '폭염일 추세'처럼
# 그 구간에 기대는 문항은 쓰지 않는다. 열대야·연평균처럼 신호가 뚜렷한 것만 쓴다.
tropical_24 = sum(1 for x in W24 if x["lo"] >= 25)
trop_50s = sum(1 for x in years(1950, 1959) if x["lo"] >= 25) / 10
trop_10s = sum(1 for x in years(2015, 2024) if x["lo"] >= 25) / 10
t_ratio = trop_10s / trop_50s if trop_50s else 0
mean_50s = mean((x["hi"] + x["lo"]) / 2 for x in years(1950, 1959))
mean_10s = mean((x["hi"] + x["lo"]) / 2 for x in years(2015, 2024))
warming = mean_10s - mean_50s
below0_24 = sum(1 for x in W24 if x["lo"] < 0)
hot_days = Counter((x["d"].month, x["d"].day)
                   for x in years(1995, 2024) if x["hi"] >= 33)
peak_day = hot_days.most_common(1)[0]

topic(
    "seoul-heat", "🌡️", "서울은 얼마나 더워졌나",
    "1950년부터 2024년까지, 서울의 매일 기온",
    "Open-Meteo Archive (ERA5 재분석)", "https://open-meteo.com/",
    [
        slider("h1", "2024년 서울에서 열대야(밤 최저기온 25도 이상)는 며칠이었을까요?",
               tropical_24, "일", 0, 60, 1,
               f"2024년 일최저기온 25도 이상인 날 {tropical_24}일",
               "유난히 더웠던 밤 몇 번이 기억을 지배합니다. 실제 일수는 세어 봐야 "
               "압니다."),
        choice("h2", "1950년대와 2015~2024년, 열대야는 몇 배 차이일까요?",
               ["거의 같다", "약 2배", "약 5배", "약 20배"],
               ["거의 같다", "약 2배", "약 5배", "약 20배"][
                   0 if t_ratio < 1.5 else 1 if t_ratio < 3.5
                   else 2 if t_ratio < 10 else 3],
               f"연평균 열대야 1950년대 {trop_50s:.1f}일 → 2015~2024년 "
               f"{trop_10s:.1f}일 ({t_ratio:.1f}배)",
               "'옛날에도 더웠다'는 느낌과 기록은 다릅니다. 낮 기온보다 밤 기온이 "
               "훨씬 크게 변했습니다."),
        slider("h3", "1950년대와 비교해 서울의 연평균 기온은 몇 도 올랐을까요?",
               warming, "도", 0, 4, 0.1,
               f"1950년대 {mean_50s:.2f}도 → 2015~2024년 {mean_10s:.2f}도 "
               f"(+{warming:.2f}도)",
               "1~2도는 작아 보이지만, 그 변화가 열대야 일수를 몇 배로 바꿉니다. "
               "평균의 변화와 극단의 변화는 크기가 다릅니다."),
        choice("h4", "최근 30년간 33도 이상인 날이 가장 잦았던 날짜는?",
               ["7월 초", "7월 말", "8월 초", "8월 말"],
               "7월 말" if peak_day[0][0] == 7 and peak_day[0][1] >= 20
               else "8월 초" if peak_day[0][0] == 8 and peak_day[0][1] <= 10
               else "7월 초" if peak_day[0][0] == 7 else "8월 말",
               f"1995~2024년 중 가장 잦았던 날짜는 {peak_day[0][0]}월 "
               f"{peak_day[0][1]}일 ({peak_day[1]}회)",
               "장마가 끝나는 시점과 가장 더운 시점은 다릅니다."),
        slider("h5", "2024년 서울에서 밤 기온이 영하로 내려간 날은 며칠이었을까요?",
               below0_24, "일", 30, 150, 5,
               f"2024년 일최저기온 0도 미만인 날 {below0_24}일",
               "겨울이 짧아졌다고 느끼지만, 영하로 내려가는 날은 여전히 석 달 "
               "치가 넘습니다."),
    ],
    caveat="ERA5는 넓은 격자의 재분석 값이라 도심 관측소보다 낮게 나옵니다. "
           "예컨대 여기서는 역대 최고기온이 37.6도지만 기상청 서울 관측 기록은 "
           "2018년 39.6도입니다. 같은 '서울 기온'도 출처에 따라 다릅니다.")

# ── 2. 비 ────────────────────────────────────────────────────────
rain_days = [sum(1 for x in W if x["d"].year == y and x["rain"] >= 1.0)
             for y in range(1995, 2025)]
rain_avg = mean(rain_days)
by_month = {m: mean([sum(x["rain"] for x in W
                         if x["d"].year == y and x["d"].month == m)
                     for y in range(1995, 2025)]) for m in range(1, 13)}
wettest_m = max(by_month, key=by_month.get)
max_day = max(W, key=lambda x: x["rain"])
ann = {y: sum(x["rain"] for x in W if x["d"].year == y) for y in range(1995, 2025)}
norm = mean(ann.values())
r2024 = ann[2024]


def days_to_half(y):
    v = sorted((x["rain"] for x in W if x["d"].year == y), reverse=True)
    half, s = sum(v) / 2, 0
    for i, r in enumerate(v, 1):
        s += r
        if s >= half:
            return i
    return len(v)


half_days = round(mean(days_to_half(y) for y in range(1995, 2025)))

topic(
    "seoul-rain", "☔", "비는 언제, 얼마나",
    "서울의 하루치 강수량 30년",
    "Open-Meteo Archive (ERA5 재분석)", "https://open-meteo.com/",
    [
        slider("r1", "서울에서 1년 중 비가 온 날(1mm 이상)은 며칠쯤일까요?",
               rain_avg, "일", 40, 160, 5,
               f"1995~2024년 평균 {rain_avg:.1f}일 "
               f"(최소 {min(rain_days)}일 · 최대 {max(rain_days)}일)",
               "비 오는 날은 기억에 오래 남아서 실제보다 많게 느껴집니다."),
        choice("r2", "1년 강수량이 가장 많은 달은?",
               ["6월", "7월", "8월", "9월"], f"{wettest_m}월",
               " · ".join(f"{m}월 {by_month[m]:.0f}mm" for m in (6, 7, 8, 9)),
               "장마가 낀 달과 비가 가장 많이 오는 달이 같지 않을 수 있습니다."),
        slider("r3", "하루에 내린 비의 최대 기록은?",
               max_day["rain"], "mm", 100, 500, 10,
               f"{max_day['d']:%Y년 %m월 %d일} {max_day['rain']:.1f}mm",
               "하루 300mm는 한 달 평균치가 하루에 쏟아진다는 뜻입니다."),
        slider("r4", "1년 강수량의 절반은 '비 온 날' 며칠 만에 채워질까요?",
               half_days, "일", 3, 40, 1,
               f"많이 온 날부터 더해서 연 강수량의 절반에 도달하는 데 "
               f"평균 {half_days}일 (1995~2024년)",
               "비는 고르게 오지 않습니다. 열흘 남짓이 1년의 절반을 만듭니다."),
        slider("r5", "2024년 서울 강수량은 30년 평균의 몇 %였을까요?",
               r2024 / norm * 100, "%", 50, 180, 5,
               f"2024년 {r2024:.0f}mm · 1995~2024년 평균 {norm:.0f}mm",
               "'올해 비가 많았다'는 체감과 실제 총량은 자주 어긋납니다."),
    ],
    caveat="ERA5 재분석 값입니다. 기상청 관측 강수량과 조금씩 다릅니다.")

# ── 3. 미세먼지 ──────────────────────────────────────────────────
a = load_json("seoul_air.json")["hourly"]
A = [{"t": dt.datetime.fromisoformat(t), "pm25": p25, "pm10": p10}
     for t, p25, p10 in zip(a["time"], a["pm2_5"], a["pm10"])]
A24 = [x for x in A if x["t"].year == 2024]
pm_month = {m: mean([x["pm25"] for x in A if x["t"].month == m])
            for m in range(1, 13)}
worst_m = max(pm_month, key=pm_month.get)
pm_hour = {h: mean([x["pm25"] for x in A if x["t"].hour == h])
           for h in range(24)}
worst_h = max(pm_hour, key=pm_hour.get)
pm24_avg = mean(x["pm25"] for x in A24)


def daily_avg(year):
    d = {}
    for x in A:
        if x["t"].year == year:
            d.setdefault(x["t"].date(), []).append(x["pm25"])
    return {k: mean(v) for k, v in d.items()}


d24 = daily_avg(2024)
d23 = daily_avg(2023)
bad_ratio = sum(1 for v in d24.values() if v > 35) / len(d24) * 100
worse_year = "2023년" if mean(d23.values()) > mean(d24.values()) else "2024년"

topic(
    "seoul-air", "😷", "미세먼지, 언제 나쁜가",
    "서울의 시간별 초미세먼지 2년치",
    "Open-Meteo Air Quality (CAMS)", "https://open-meteo.com/",
    [
        choice("a1", "초미세먼지(PM2.5)가 가장 나쁜 달은?",
               ["1월", "3월", "5월", "11월"],
               f"{worst_m}월" if f"{worst_m}월" in ["1월", "3월", "5월", "11월"]
               else "3월",
               " · ".join(f"{m}월 {pm_month[m]:.1f}" for m in (1, 3, 5, 11))
               + f" (최악은 {worst_m}월 {pm_month[worst_m]:.1f})",
               "황사 뉴스가 많은 달과 실제 수치가 높은 달은 다를 수 있습니다."),
        slider("a2", "2024년 서울의 초미세먼지 연평균 농도는?",
               pm24_avg, "㎍/㎥", 5, 60, 1,
               f"2024년 시간값 {len(A24):,}개의 평균 {pm24_avg:.1f}㎍/㎥ "
               f"(WHO 권고 연평균 5, 국내 기준 15)",
               "'나쁨'인 날이 인상에 남아서 연평균을 높게 잡게 됩니다."),
        choice("a3", "하루 중 초미세먼지가 가장 높은 시간대는?",
               ["새벽 4시", "오전 10시", "오후 3시", "밤 9시"],
               {4: "새벽 4시", 10: "오전 10시", 15: "오후 3시",
                21: "밤 9시"}.get(worst_h, "오전 10시"),
               " · ".join(f"{h}시 {pm_hour[h]:.1f}" for h in (4, 10, 15, 21))
               + f" (최고는 {worst_h}시)",
               "출퇴근 시간이 가장 나쁠 것 같지만 대기가 정체되는 시간은 따로 "
               "있습니다."),
        slider("a4", "2024년 하루 평균이 '나쁨'(35㎍/㎥ 초과)이었던 날의 비율은?",
               bad_ratio, "%", 0, 60, 1,
               f"2024년 {len(d24)}일 중 "
               f"{sum(1 for v in d24.values() if v > 35)}일",
               "마스크를 챙긴 날은 강하게 기억되지만, 1년 전체로 보면 비율이 "
               "다릅니다."),
        choice("a5", "2023년과 2024년 중 초미세먼지가 더 나빴던 해는?",
               ["2023년", "2024년"], worse_year,
               f"연평균 2023년 {mean(d23.values()):.1f} · "
               f"2024년 {mean(d24.values()):.1f}㎍/㎥",
               "체감은 최근 쪽으로 쏠립니다. 두 해 차이는 생각보다 작습니다."),
    ],
    caveat="CAMS 대기질 모델의 추정값입니다. 에어코리아 측정소 실측값과 "
           "다를 수 있습니다.")

# ── 4. 노동시간 ──────────────────────────────────────────────────
wh = [r for r in load_csv("working_hours.csv") if r["working_hours_omm"]]
latest_year = max(int(r["year"]) for r in wh if r["code"] == "KOR")
cur = owid_countries(wh, latest_year, "working_hours_omm")
kor = cur["South Korea"]
rank = sorted(cur.items(), key=lambda kv: -kv[1])
kor_rank = [k for k, _ in rank].index("South Korea") + 1
longer = kor_rank - 1
past = {int(r["year"]): float(r["working_hours_omm"])
        for r in wh if r["code"] == "KOR"}
y30 = latest_year - 30
drop = past[y30] - kor
trio = {c: cur[c] for c in ("South Korea", "Japan", "Germany") if c in cur}
shortest = min(trio, key=trio.get)
name_ko = {"South Korea": "한국", "Japan": "일본", "Germany": "독일"}

topic(
    "working-hours", "⏰", "우리는 얼마나 일하나",
    "나라별 1인당 연간 노동시간",
    "Our World in Data", "https://ourworldindata.org/grapher/annual-working-hours-per-worker",
    [
        slider("w1", f"{latest_year}년 한국의 1인당 연간 노동시간은?",
               kor, "시간", 1200, 2600, 50,
               f"{latest_year}년 한국 {kor:,.0f}시간 "
               f"(주 5일 기준 하루 약 {kor / 250:.1f}시간)",
               "연 단위로 물으면 감이 잘 안 옵니다. 하루로 나눠 보면 체감과 "
               "맞는지 확인할 수 있습니다."),
        slider("w2", f"한국보다 더 오래 일하는 나라는 {len(cur)}개국 중 몇 개일까요?",
               longer, "개국", 0, 60, 1,
               f"{latest_year}년 기준 {len(cur)}개국 중 한국은 {kor_rank}위",
               "'한국이 제일 많이 일한다'는 인상이 강하지만, 비교 대상에 따라 "
               "순위가 달라집니다."),
        slider("w3", f"한국의 노동시간은 30년 전({y30}년)보다 몇 시간 줄었을까요?",
               drop, "시간", 0, 900, 50,
               f"{y30}년 {past[y30]:,.0f}시간 → {latest_year}년 {kor:,.0f}시간",
               "줄어든 폭은 대개 과소평가됩니다. 하루로 치면 크게 달라진 값입니다."),
        choice("w4", "한국·일본·독일 중 가장 적게 일하는 나라는?",
               ["한국", "일본", "독일"], name_ko[shortest],
               " · ".join(f"{name_ko[c]} {trio[c]:,.0f}시간" for c in trio),
               "나라마다 통계 기준이 다릅니다. 순위보다 격차의 크기를 봅니다."),
        slider("w5", "한국과 독일의 연간 노동시간 차이는?",
               abs(cur["South Korea"] - cur["Germany"]), "시간", 0, 900, 50,
               f"한국 {cur['South Korea']:,.0f} · 독일 "
               f"{cur['Germany']:,.0f}시간",
               "두 나라 차이를 주 단위로 나눠 보면 체감이 확 달라집니다."),
    ],
    caveat="이 자료에는 개발도상국이 많이 포함돼 있어, OECD 안에서의 순위와 "
           "전체 순위가 다릅니다. '어느 집단과 비교하느냐'가 순위를 만듭니다.")

# ── 5. 인구와 출산 ───────────────────────────────────────────────
fert = [r for r in load_json("wb_fertility.json")[1] if r["value"] is not None]
f_latest = max(int(r["date"]) for r in fert if r["countryiso3code"] == "KOR")
f_cur = wb_countries(fert, f_latest)
kor_f = f_cur["Korea, Rep."]
f_rank = sorted(f_cur.items(), key=lambda kv: kv[1])
kor_f_rank = [k for k, _ in f_rank].index("Korea, Rep.") + 1
kor_1970 = next(r["value"] for r in fert
                if r["countryiso3code"] == "KOR" and r["date"] == "1970")

pop = load_json("wb_pop_kor.json")[1]
tot = {int(r["date"]): r["value"] for r in pop
       if r["indicator"]["id"] == "SP.POP.TOTL" and r["value"]}
old = {int(r["date"]): r["value"] for r in pop
       if r["indicator"]["id"] == "SP.POP.65UP.TO.ZS" and r["value"]}
urb = {int(r["date"]): r["value"] for r in pop
       if r["indicator"]["id"] == "SP.URB.TOTL.IN.ZS" and r["value"]}
peak_year = max(tot, key=tot.get)
old_latest = max(old)
urb_latest = max(urb)

topic(
    "population", "👶", "인구와 출산",
    "전 세계 출산율과 한국의 인구 구조",
    "World Bank Open Data", "https://data.worldbank.org/",
    [
        slider("p1", f"{f_latest}년 한국의 합계출산율(여성 1명당 출생아 수)은?",
               kor_f, "명", 0.5, 3.0, 0.05,
               f"{f_latest}년 한국 {kor_f:.2f}명",
               "숫자는 자주 들었어도 '여성 1명당'이라는 단위는 잘 안 와닿습니다."),
        slider("p2", f"출산율이 낮은 순으로 세면 한국은 {len(f_cur)}개 나라·지역 중 몇 위일까요?",
               kor_f_rank, "위", 1, 30, 1,
               f"{f_latest}년 기준 {len(f_cur)}곳 중 {kor_f_rank}위 "
               f"(1위 {f_rank[0][0]} {f_rank[0][1]:.2f})",
               "'꼴찌'라고 알고 있지만, 비교 목록에 어떤 나라·지역이 들어가느냐에 "
               "따라 순위가 달라집니다."),
        slider("p3", "1970년 한국의 출산율은 몇 명이었을까요?",
               kor_1970, "명", 1.0, 7.0, 0.1,
               f"1970년 {kor_1970:.2f}명 → {f_latest}년 {kor_f:.2f}명",
               "한 세대 만에 일어난 변화의 크기는 대개 과소평가됩니다."),
        slider("p4", f"{old_latest}년 한국에서 65세 이상 인구의 비율은?",
               old[old_latest], "%", 5, 35, 1,
               f"{old_latest}년 {old[old_latest]:.1f}% "
               f"(World Bank 최신 공표치. 최근 연도는 추계값입니다)",
               "고령화는 '다가올 일'로 느껴지지만 이미 지나온 숫자입니다."),
        slider("p5", f"{urb_latest}년 한국에서 도시에 사는 사람의 비율은?",
               urb[urb_latest], "%", 50, 100, 1,
               f"{urb_latest}년 {urb[urb_latest]:.1f}% "
               f"(World Bank 최신 공표치. 최근 연도는 추계값입니다)",
               "'절반쯤'이라고 답하기 쉽지만 한국은 세계에서도 손꼽히는 도시 국가입니다."),
    ])

# ── 6. 인터넷 ────────────────────────────────────────────────────
net = [r for r in load_json("wb_internet.json")[1] if r["value"] is not None]
n_latest = max(int(r["date"]) for r in net if r["countryiso3code"] == "KOR")
n_cur = wb_countries(net, n_latest)
kor_n = n_cur["Korea, Rep."]
n_rank = sorted(n_cur.items(), key=lambda kv: -kv[1])
kor_n_rank = [k for k, _ in n_rank].index("Korea, Rep.") + 1
kor_2000 = next(r["value"] for r in net
                if r["countryiso3code"] == "KOR" and r["date"] == "2000")
world = next((r["value"] for r in net
              if r["countryiso3code"] == "WLD" and int(r["date"]) == n_latest), None)
if world is None:
    world = mean(n_cur.values())
offline = 100 - world

topic(
    "internet", "🌐", "인터넷과 연결",
    "나라별 인터넷 사용 인구 비율",
    "World Bank Open Data", "https://data.worldbank.org/",
    [
        slider("i1", f"{n_latest}년 한국에서 인터넷을 쓰는 사람의 비율은?",
               kor_n, "%", 60, 100, 1,
               f"{n_latest}년 한국 {kor_n:.1f}%",
               "'거의 다'라고 생각하지만 100%는 아닙니다. 남은 몇 %가 누구인지가 "
               "정책의 대상입니다."),
        slider("i2", f"한국보다 인터넷 사용률이 높은 나라는 {len(n_cur)}곳 중 몇 곳일까요?",
               kor_n_rank - 1, "곳", 0, 60, 1,
               f"{n_latest}년 {len(n_cur)}곳 중 한국 {kor_n_rank}위",
               "'IT 강국'이라는 말과 실제 보급률 순위는 다른 이야기입니다."),
        slider("i3", "2000년 한국의 인터넷 사용률은?",
               kor_2000, "%", 0, 100, 5,
               f"2000년 {kor_2000:.1f}% → {n_latest}년 {kor_n:.1f}%",
               "20여 년 전을 떠올릴 때는 지금의 기준으로 과대평가하기 쉽습니다."),
        slider("i4", f"{n_latest}년 전 세계 평균 인터넷 사용률은?",
               world, "%", 20, 100, 5,
               f"{n_latest}년 세계 {world:.1f}%",
               "내 주변이 전부 연결돼 있으면 세계도 그럴 거라고 생각하게 됩니다."),
        slider("i5", "전 세계에서 인터넷을 쓰지 않는 사람은 몇 %일까요?",
               offline, "%", 0, 70, 5,
               f"100 - {world:.1f} = {offline:.1f}%",
               "같은 사실을 뒤집어 물으면 전혀 다른 크기로 느껴집니다."),
    ])

# ── 7. 환율 ──────────────────────────────────────────────────────
fx = load_json("usdkrw.json")["rates"]
FX = sorted((d, v["KRW"]) for d, v in fx.items() if "KRW" in v)
hi_d, hi_v = max(FX, key=lambda x: x[1])
lo_d, lo_v = min(FX, key=lambda x: x[1])
avg_fx = mean(v for _, v in FX)
under1200 = sum(1 for _, v in FX if v < 1200) / len(FX) * 100
last_d, last_v = FX[-1]
era = ("1997~1999년 외환위기" if hi_d < "2005" else
       "2008~2009년 금융위기" if hi_d < "2012" else
       "2020년 코로나" if hi_d < "2022" else "2022년 이후")

topic(
    "usdkrw", "💵", "원달러 환율 26년",
    "1999년부터 오늘까지의 원달러 환율",
    "Frankfurter (유럽중앙은행 고시)", "https://frankfurter.dev/",
    [
        slider("x1", "1999년 이후 원달러 환율의 최고 기록은?",
               hi_v, "원", 1100, 1800, 25,
               f"{hi_d} {hi_v:,.2f}원",
               "최고치는 위기의 기억과 함께 남지만, 정확한 시점은 자주 헷갈립니다."),
        choice("x2", "그 최고치를 찍은 시기는?",
               ["1997~1999년 외환위기", "2008~2009년 금융위기",
                "2020년 코로나", "2022년 이후"], era,
               f"최고 {hi_v:,.2f}원 ({hi_d}). 이 데이터는 1999년부터라 "
               f"1997~98년 외환위기 구간은 포함되어 있지 않습니다",
               "데이터가 시작하는 시점을 확인하지 않으면 '역대 최고'를 잘못 "
               "말하게 됩니다."),
        slider("x3", "26년간의 평균 환율은?",
               avg_fx, "원", 900, 1500, 25,
               f"{FX[0][0]} ~ {FX[-1][0]} 거래일 {len(FX):,}일 평균 "
               f"{avg_fx:,.0f}원 (최저 {lo_v:,.0f}원 · {lo_d})",
               "최근 값이 기준점이 되어 과거 평균을 높게 잡게 됩니다."),
        slider("x4", "환율이 1,200원 아래였던 날은 전체의 몇 %일까요?",
               under1200, "%", 0, 100, 5,
               f"거래일 {len(FX):,}일 중 1,200원 미만은 "
               f"{sum(1 for _, v in FX if v < 1200):,}일",
               "'원래 1,100원대였는데'라는 감각이 맞는지 비율로 확인해 봅니다."),
        slider("x5", f"{last_d} 기준 환율은?",
               last_v, "원", 1100, 1800, 25,
               f"{last_d} {last_v:,.2f}원",
               "가장 최근 값조차 기억은 며칠 전 뉴스에 묶여 있습니다."),
    ])

# ── 8. 도시 비교 ─────────────────────────────────────────────────
CITY = {}
for cid in ("seoul", "tokyo", "london", "singapore"):
    _d = load_json(f"city_{cid}.json")["daily"]
    CITY[cid] = [{"d": dt.date.fromisoformat(t), "hi": a, "lo": b, "r": c}
                 for t, a, b, c in zip(_d["time"], _d["temperature_2m_max"],
                                       _d["temperature_2m_min"],
                                       _d["precipitation_sum"])]
CN = {"seoul": "서울", "tokyo": "도쿄", "london": "런던", "singapore": "싱가포르"}
YRS = 30
c_rain = {k: sum(x["r"] for x in v) / YRS for k, v in CITY.items()}
c_days = {k: sum(1 for x in v if x["r"] >= 1) / YRS for k, v in CITY.items()}


def monthly_avg(v):
    """월별 평균기온((최고+최저)/2) — 1~12월 딕셔너리."""
    buckets = {m: [] for m in range(1, 13)}
    for x in v:
        buckets[x["d"].month].append((x["hi"] + x["lo"]) / 2)
    return {m: mean(vals) for m, vals in buckets.items()}


c_month = {k: monthly_avg(v) for k, v in CITY.items()}
c_range = {k: max(m.values()) - min(m.values()) for k, m in c_month.items()}
c_summer = {k: mean(x["hi"] for x in v if x["d"].month in (6, 7, 8))
            for k, v in CITY.items()}

rainier_days = "런던" if c_days["london"] > c_days["seoul"] else "서울"
more_rain = "서울" if c_rain["seoul"] > c_rain["london"] else "런던"
london_pct = c_rain["london"] / c_rain["seoul"] * 100
range_ratio = c_range["seoul"] / c_range["singapore"]
summer_warmer = "서울" if c_summer["seoul"] > c_summer["tokyo"] else "도쿄"

topic(
    "cities", "🏙️", "서울·도쿄·런던·싱가포르",
    "네 도시의 30년 평년값 (1991~2020)",
    "Open-Meteo Archive (ERA5 재분석)", "https://open-meteo.com/",
    [
        choice("c1", "서울과 런던 중, 1년에 비 오는 날(1mm 이상)이 더 많은 "
               "도시는?",
               ["서울", "런던"], rainier_days,
               f"런던 {c_days['london']:.0f}일 · 서울 {c_days['seoul']:.0f}일",
               "런던은 '비의 도시'라는 인상 때문에 자주 온다고 생각하기 쉽고, "
               "실제로도 서울보다 비 오는 날 자체는 더 많습니다."),
        choice("c2", "그런데 1년 강수량(mm) 총량이 더 많은 도시는?",
               ["서울", "런던"], more_rain,
               f"서울 {c_rain['seoul']:,.0f}mm · 런던 {c_rain['london']:,.0f}mm",
               "비 오는 '날'이 많다고 '양'도 많은 건 아닙니다. 런던은 조금씩 "
               "자주 오고, 서울은 장마·태풍 때 몰아서 옵니다."),
        slider("c3", "런던의 연강수량은 서울의 몇 %일까요?",
               london_pct, "%", 0, 150, 5,
               f"런던 {c_rain['london']:,.0f}mm ÷ 서울 {c_rain['seoul']:,.0f}mm "
               f"× 100",
               "'비가 많이 오는 도시'라는 인상과 달리 런던의 연강수량은 서울의 "
               "절반 수준입니다."),
        slider("c4", "서울의 연교차(가장 더운 달 − 가장 추운 달의 평균기온 "
               "차이)는 싱가포르의 몇 배일까요?",
               range_ratio, "배", 0, 30, 1,
               f"서울 연교차 {c_range['seoul']:.1f}도 · 싱가포르 연교차 "
               f"{c_range['singapore']:.1f}도",
               "싱가포르는 적도 부근이라 계절 변화가 거의 없고, 서울은 사계절이 "
               "뚜렷해 그 차이가 20배가 넘습니다."),
        choice("c5", "여름철(6~8월) 평균 최고기온이 더 높은 도시는 서울일까 "
               "도쿄일까?",
               ["서울", "도쿄"], summer_warmer,
               f"서울 {c_summer['seoul']:.1f}도 · 도쿄 {c_summer['tokyo']:.1f}도",
               "도쿄가 더 습해서 체감은 더 덥지만, 평균 최고기온 자체는 두 "
               "도시가 거의 같습니다."),
    ],
    caveat="ERA5는 실제 관측소가 아니라 격자(약 30km) 평균값이라, 도시 중심부의 "
           "열섬 효과 같은 국지적 차이는 반영되지 않습니다. 또한 서울은 계절풍의 "
           "영향을, 싱가포르는 적도 기후를 크게 받아 '평균기온'이라는 같은 지표라도 "
           "도시마다 의미하는 바가 다릅니다.")

# ── 9. 지진 ──────────────────────────────────────────────────────
Q = [f["properties"] for f in load_json("quakes.geojson")["features"]]
QK = [f["properties"] for f in load_json("quakes_korea.geojson")["features"]]
n_years = 25
per_year = len(Q) / n_years
m7 = sum(1 for p in Q if p["mag"] >= 7.0) / n_years
biggest = max(Q, key=lambda p: p["mag"])


def region(place):
    return (place or "").split(",")[-1].strip()


top_region = Counter(region(p["place"]) for p in Q).most_common(1)[0]
region_ko = {"Japan": "일본", "Indonesia": "인도네시아", "Chile": "칠레",
             "Philippines": "필리핀"}
kr_band = ("50건 미만" if len(QK) < 50 else "50~150건" if len(QK) <= 150
           else "150~400건" if len(QK) <= 400 else "400건 이상")

topic(
    "quakes", "🌎", "지진은 얼마나 자주",
    "2000~2024년 전 세계 지진 기록",
    "USGS 지진 카탈로그", "https://earthquake.usgs.gov/",
    [
        slider("q1", "규모 5.5 이상 지진은 전 세계에서 1년에 몇 번쯤 일어날까요?",
               per_year, "회", 50, 1200, 50,
               f"2000~2024년 {len(Q):,}건 ÷ {n_years}년 = "
               f"연평균 {per_year:.0f}회",
               "뉴스에 나오는 지진만 세면 실제보다 훨씬 적게 잡게 됩니다."),
        slider("q2", "규모 7.0 이상은 1년에 몇 번쯤일까요?",
               m7, "회", 0, 40, 1,
               f"2000~2024년 규모 7.0 이상 "
               f"{sum(1 for p in Q if p['mag'] >= 7.0)}건, 연평균 {m7:.1f}회",
               "규모는 로그 척도입니다. 0.5만 올라가도 횟수가 크게 줄어듭니다."),
        choice("q3", "규모 5.5 이상 지진이 가장 자주 기록된 나라는?",
               ["일본", "인도네시아", "칠레", "필리핀"],
               region_ko.get(top_region[0], "인도네시아"),
               f"1위 {top_region[0]} {top_region[1]:,}건",
               "지진 하면 떠오르는 나라와 실제로 가장 많이 기록되는 곳은 "
               "다를 수 있습니다."),
        slider("q4", "2000년 이후 기록된 가장 큰 지진의 규모는?",
               biggest["mag"], "", 7.0, 9.9, 0.1,
               f"규모 {biggest['mag']} · "
               f"{dt.datetime.fromtimestamp(biggest['time'] / 1000, dt.UTC):%Y-%m-%d} "
               f"{biggest['place']}",
               "규모 9는 8보다 약 32배 큰 에너지입니다."),
        choice("q5", "한반도 주변(위도 33~39.5도)에서 25년간 기록된 규모 3.0 이상 지진은?",
               ["50건 미만", "50~150건", "150~400건", "400건 이상"], kr_band,
               f"USGS 기준 {len(QK)}건. 이 관측망은 작은 지진을 모두 잡지는 "
               f"못하므로 기상청 집계와 다릅니다",
               "'어느 기관이 센 숫자인가'를 확인하지 않으면 같은 현상도 다른 "
               "값이 됩니다."),
    ],
    caveat="USGS 카탈로그는 작은 지진을 모두 담지 못합니다. 한반도 지진은 "
           "기상청 집계가 더 많습니다.")

# ── 10. 수명 ─────────────────────────────────────────────────────
le = [r for r in load_csv("life_expectancy.csv") if r["life_expectancy_0"]]
l_latest = max(int(r["year"]) for r in le if r["code"] == "KOR")
l_cur = owid_countries(le, l_latest, "life_expectancy_0")
kor_l = l_cur["South Korea"]
l_rank = sorted(l_cur.items(), key=lambda kv: -kv[1])
kor_l_rank = [k for k, _ in l_rank].index("South Korea") + 1
_kle = {r["year"]: float(r["life_expectancy_0"]) for r in le if r["code"] == "KOR"}
kor_1950, kor_1953, kor_1955 = _kle["1950"], _kle["1953"], _kle["1955"]
wld = next(float(r["life_expectancy_0"]) for r in le
           if r["code"] == "OWID_WRL" and int(r["year"]) == l_latest)
trio_l = {c: l_cur[c] for c in ("South Korea", "Japan", "United States")
          if c in l_cur}
top_l = max(trio_l, key=trio_l.get)
name_l = {"South Korea": "한국", "Japan": "일본", "United States": "미국"}

topic(
    "life", "🩺", "얼마나 오래 사나",
    "나라별 기대수명 1950~현재",
    "Our World in Data", "https://ourworldindata.org/grapher/life-expectancy",
    [
        slider("l1", f"{l_latest}년 한국의 기대수명은?",
               kor_l, "세", 60, 95, 1,
               f"{l_latest}년 한국 {kor_l:.1f}세",
               "기대수명은 '지금 태어난 아이가 평균적으로 살 햇수'입니다. "
               "지금 살아 있는 사람의 예상 수명과는 다릅니다."),
        slider("l2", f"기대수명이 긴 순으로 세면 한국은 {len(l_cur)}곳 중 몇 위일까요?",
               kor_l_rank, "위", 1, 60, 1,
               f"{l_latest}년 {len(l_cur)}곳 중 {kor_l_rank}위 "
               f"(1위 {l_rank[0][0]} {l_rank[0][1]:.1f}세)",
               "상위권인 것은 맞지만 몇 위인지는 대개 크게 빗나갑니다."),
        slider("l3", "1950년 한국의 기대수명은?",
               kor_1950, "세", 20, 70, 1,
               f"1950년 {kor_1950:.1f}세. 한국전쟁 기간의 사망이 반영된 값이라 "
               f"1953년 {kor_1953:.1f}세, 1955년 {kor_1955:.1f}세로 빠르게 "
               f"회복합니다. {l_latest}년은 {kor_l:.1f}세",
               "숫자가 튀면 사건을 의심해야 합니다. 이 값은 오류가 아니라 "
               "전쟁의 기록입니다."),
        choice("l4", "한국·일본·미국 중 기대수명이 가장 긴 나라는?",
               ["한국", "일본", "미국"], name_l[top_l],
               " · ".join(f"{name_l[c]} {trio_l[c]:.1f}세" for c in trio_l),
               "가장 잘사는 나라가 가장 오래 사는 나라는 아닙니다."),
        slider("l5", f"{l_latest}년 세계 평균 기대수명은?",
               wld, "세", 50, 90, 1,
               f"{l_latest}년 세계 평균 {wld:.1f}세 · 한국 {kor_l:.1f}세",
               "내가 사는 곳의 수준을 세계 평균으로 착각하기 쉽습니다."),
    ])

# ── 11. 세계 음식 소비량 (보너스) ────────────────────────────────
# FAO 식량수급표(Food Balance Sheet) 기반 OWID 자료. '실제로 먹은 양'이 아니라
# 생산+수입-수출-사료-폐기물 등을 인구로 나눈 '공급 기준' 값이라는 점에
# 유의한다 (아래 caveat 참고).
MEAT_COL = ("meat__total__00002943__food_available_for_consumption"
            "__0645pe__grams_per_day_per_capita")
FISH_COL = ("fish_and_seafood__00002960__food_available_for_consumption"
            "__0645pc__kilograms_per_year_per_capita")
meat_rows = [r for r in load_csv("meat_consumption.csv") if r[MEAT_COL]]
fish_rows = [r for r in load_csv("fish_consumption.csv") if r[FISH_COL]]

food_year = max(int(r["year"]) for r in meat_rows if r["code"] == "KOR")
meat_cur = owid_countries(meat_rows, food_year, MEAT_COL)
fish_cur = owid_countries(fish_rows, food_year, FISH_COL)

kor_meat = meat_cur["South Korea"]                     # g/일
kor_meat_kg = kor_meat * 365 / 1000                    # 연간 kg 환산
kor_fish = fish_cur["South Korea"]                     # kg/년 (원 단위)

kor_meat_1961 = next(float(r[MEAT_COL]) for r in meat_rows
                     if r["code"] == "KOR" and r["year"] == "1961")
meat_growth = kor_meat / kor_meat_1961

fish_rank = sorted(fish_cur.items(), key=lambda kv: -kv[1])
kor_fish_rank = [k for k, _ in fish_rank].index("South Korea") + 1

trio_meat = {c: meat_cur[c] for c in
             ("United States", "Argentina", "Australia", "South Korea")}
top_meat_c = max(trio_meat, key=trio_meat.get)
name_meat = {"United States": "미국", "Argentina": "아르헨티나",
             "Australia": "호주", "South Korea": "한국"}

topic(
    "food-consumption", "🍖", "세계 음식 소비량",
    "나라별 1인당 육류·해산물 소비량 (1961~현재)",
    "Our World in Data (FAO)",
    "https://ourworldindata.org/grapher/daily-meat-consumption-per-person",
    [
        slider("f1", f"{food_year}년 한국인 1인당 하루 육류 소비량은 몇 g쯤일까요?",
               kor_meat, "g", 0, 400, 10,
               f"{food_year}년 한국 {kor_meat:.1f}g/일 "
               f"(연간 {kor_meat_kg:.1f}kg에 해당)",
               "매일 먹는다는 느낌은 있어도 하루 그램 수로 세어 본 적은 드뭅니다."),
        choice("f2", "다음 네 나라 중 1인당 하루 육류 소비량이 가장 많은 나라는?",
               ["미국", "아르헨티나", "호주", "한국"], name_meat[top_meat_c],
               " · ".join(f"{name_meat[c]} {trio_meat[c]:.1f}g" for c in trio_meat),
               "'고기 하면 아르헨티나'라는 인상이 강하지만, 하루 섭취량 자체는 "
               "미국이 근소하게 앞섭니다."),
        choice("f3", "한국인이 무게로 더 많이 먹는 것은 육류일까, 해산물일까?",
               ["육류", "해산물"], "육류",
               f"{food_year}년 육류 {kor_meat_kg:.1f}kg/년 · "
               f"해산물 {kor_fish:.1f}kg/년",
               "'물 좋은 나라, 생선 많이 먹는 나라'라는 인상과 달리, 무게로 "
               "따지면 이미 육류가 해산물을 앞질렀습니다."),
        slider("f4", f"해산물 소비량 기준, 한국은 전 세계 {len(fish_cur)}개국 중 "
                     "몇 위일까요?",
               kor_fish_rank, "위", 1, 50, 1,
               f"{food_year}년 {len(fish_cur)}개국 중 {kor_fish_rank}위 "
               f"(1위 아이슬란드 {fish_rank[0][1]:.1f}kg/년 · "
               f"한국 {kor_fish:.1f}kg/년)",
               "정확한 순위를 맞히긴 어려워도, 상위권이라는 인상 자체는 사실과 "
               "맞아떨어집니다."),
        slider("f5", "1961년과 비교해 한국인의 하루 육류 소비량은 몇 배 늘었을까요?",
               meat_growth, "배", 0, 30, 1,
               f"1961년 {kor_meat_1961:.1f}g/일 → {food_year}년 "
               f"{kor_meat:.1f}g/일 ({meat_growth:.1f}배)",
               "한국이 훨씬 잘살게 됐다는 감각은 있어도, 식탁 위 변화가 20배 "
               "규모라는 건 체감하기 어렵습니다."),
    ],
    caveat="이 값은 실제 섭취량이 아니라 FAO 식량수급표가 생산·수입·수출·사료·"
           "폐기물 등을 계산해 인구로 나눈 '공급 기준' 수치입니다. 유통·가정에서 "
           "버려지는 양까지 포함되어 있어 실제로 몸에 들어가는 양보다 많게 "
           "잡히고, 국가 평균이라 소득·지역별 차이는 드러나지 않습니다.")

# ── 12. 1인당 탄소 배출량 (보너스) ───────────────────────────────
CO2_COL = "emissions_total_per_capita"
co2_rows = [r for r in load_csv("co2_per_capita.csv") if r[CO2_COL]]

co2_year = max(int(r["year"]) for r in co2_rows if r["code"] == "KOR")
co2_cur = owid_countries(co2_rows, co2_year, CO2_COL)

kor_co2 = co2_cur["South Korea"]
co2_rank = sorted(co2_cur.items(), key=lambda kv: -kv[1])
kor_co2_rank = [k for k, _ in co2_rank].index("South Korea") + 1

world_co2 = next(float(r[CO2_COL]) for r in co2_rows
                  if r["code"] == "OWID_WRL" and int(r["year"]) == co2_year)

trio_co2 = {c: co2_cur[c] for c in
            ("Qatar", "United States", "China", "South Korea")}
top_co2_c = max(trio_co2, key=trio_co2.get)
name_co2 = {"Qatar": "카타르", "United States": "미국", "China": "중국",
            "South Korea": "한국"}

kor_co2_1990 = next(float(r[CO2_COL]) for r in co2_rows
                    if r["code"] == "KOR" and r["year"] == "1990")


def co2_at(code, year):
    return next(float(r[CO2_COL]) for r in co2_rows
                if r["code"] == code and r["year"] == str(year))


usa_1990, usa_now = co2_at("USA", 1990), co2_cur["United States"]
deu_1990, deu_now = co2_at("DEU", 1990), co2_cur["Germany"]
up_since_1990 = max(
    (("미국", usa_now / usa_1990), ("독일", deu_now / deu_1990),
     ("한국", kor_co2 / kor_co2_1990)),
    key=lambda kv: kv[1])[0]

topic(
    "carbon", "🏭", "1인당 탄소 배출량",
    "나라별 1인당 CO2 배출량 (1750~현재)",
    "Our World in Data (Global Carbon Project)",
    "https://ourworldindata.org/grapher/co-emissions-per-capita",
    [
        slider("e1", f"{co2_year}년 한국인 1인당 CO2 배출량은 몇 톤쯤일까요?",
               kor_co2, "톤", 0, 20, 0.5,
               f"{co2_year}년 한국 {kor_co2:.1f}톤/인",
               "탄소 배출은 눈에 보이지 않아서 감으로 맞히기 어렵습니다."),
        choice("e2", "카타르·미국·중국·한국 중 1인당 CO2 배출량이 가장 많은 "
                     "나라는?",
               ["카타르", "미국", "중국", "한국"], name_co2[top_co2_c],
               " · ".join(f"{name_co2[c]} {trio_co2[c]:.1f}톤" for c in trio_co2),
               "'배출 하면 미국·중국'이라는 인상이 강하지만, 1인당으로 보면 "
               "산유국이 압도적으로 높습니다."),
        choice("e3", "총배출량 세계 1위는 중국인데, 1인당으로는 중국과 한국 중 "
                     "어느 쪽이 더 많을까요?",
               ["중국", "한국"], "한국",
               f"{co2_year}년 중국 {trio_co2['China']:.1f}톤/인 · "
               f"한국 {kor_co2:.1f}톤/인 (중국은 인구가 훨씬 많아 총량이 "
               f"앞섭니다)",
               "'중국이 제일 심하다'는 인상은 총량 기준이고, 1인당으로 보면 "
               "한국이 더 높습니다."),
        choice("e4", "1990년과 비교해 1인당 CO2 배출량이 늘어난 나라는 "
                     "미국·독일·한국 중 어디일까요?",
               ["미국", "독일", "한국"], up_since_1990,
               f"1990→{co2_year}년 미국 {usa_1990:.1f}→{usa_now:.1f}톤 · "
               f"독일 {deu_1990:.1f}→{deu_now:.1f}톤 · "
               f"한국 {kor_co2_1990:.1f}→{kor_co2:.1f}톤",
               "'선진국은 계속 줄이고 있다'는 인상과 달리, 한국은 오히려 거의 "
               "두 배로 늘었습니다."),
        slider("e5", f"1인당 CO2 배출량 기준, 한국은 전 세계 {len(co2_cur)}개국 "
                     "중 몇 위일까요?",
               kor_co2_rank, "위", 1, 60, 1,
               f"{co2_year}년 {len(co2_cur)}개국 중 {kor_co2_rank}위 "
               f"(1위 카타르 {co2_rank[0][1]:.1f}톤 · 세계 평균 "
               f"{world_co2:.1f}톤)",
               "환경에 신경 쓴다는 인식과 달리, 순위로 보면 상위권에 속합니다."),
    ],
    caveat="이 값은 그 나라 안에서 배출된 화석연료·시멘트 CO2만 센 '생산 "
           "기준' 수치입니다. 소비재를 수입해 쓰는 나라는 실제 소비로 인한 "
           "배출보다 낮게, 원유·가스를 수출용으로 많이 생산하는 나라는 국민의 "
           "생활 수준보다 훨씬 높게 나옵니다. 산림 벌채 같은 토지이용 변화로 "
           "인한 배출은 포함되지 않습니다.")

# ── 13. 포켓몬 스펙 감각 (보너스) ────────────────────────────────
# 실제로 측정한 값이 아니라 게임이 정해 둔 설정값이라는 점에 유의 (caveat 참고).
_POKE_NAMES = ("pikachu", "jigglypuff", "arcanine", "mamoswine", "snorlax",
               "magnemite", "dragonite", "machamp", "ditto", "gyarados")
POKE = {name: load_json(f"pokemon_{name}.json") for name in _POKE_NAMES}


def poke_weight(name):
    return POKE[name]["weight"] / 10          # kg


def poke_height(name):
    return POKE[name]["height"] / 10          # m


def poke_speed(name):
    return next(s["base_stat"] for s in POKE[name]["stats"]
                if s["stat"]["name"] == "speed")


pika_w = poke_weight("pikachu")
puri_w = poke_weight("jigglypuff")
koil_w = poke_weight("magnemite")
jamb_w, jamb_h = poke_weight("snorlax"), poke_height("snorlax")
gyar_w, gyar_h = poke_weight("gyarados"), poke_height("gyarados")
gwe_spd = poke_speed("machamp")
mangna_spd = poke_speed("dragonite")

topic(
    "pokemon", "👾", "포켓몬 스펙 감각",
    "겉모습만 보고 몸무게·스피드 비교하기 (PokeAPI)",
    "PokeAPI", "https://pokeapi.co/",
    [
        slider("m1", "국민 마스코트 피카츄의 실제 몸무게는 몇 kg일까요?",
               pika_w, "kg", 0, 20, 0.5,
               f"피카츄 {pika_w:.1f}kg (키 {poke_height('pikachu'):.1f}m)",
               "작고 가벼워 보이지만, 막상 숫자로 보면 꽤 묵직합니다."),
        choice("m2", "푸린과 피카츄 중, 실제 몸무게가 더 무거운 쪽은?",
               ["푸린", "피카츄"], "피카츄",
               f"피카츄 {pika_w:.1f}kg · 푸린 {puri_w:.1f}kg",
               "동글동글한 푸린이 더 커 보이지만, 몸무게는 피카츄가 근소하게 "
               "앞섭니다."),
        choice("m3", "작은 쇳덩이 코일과 피카츄, 몸무게가 더 무거운 쪽은?",
               ["코일", "피카츄", "둘 다 같다"], "둘 다 같다",
               f"코일 {koil_w:.1f}kg · 피카츄 {pika_w:.1f}kg — 정확히 같습니다",
               "생김새는 완전히 다르지만, 설정값상 몸무게는 똑같습니다."),
        choice("m4", "잠만보와 갸라도스 중, 실제 몸무게가 더 무거운 쪽은?",
               ["잠만보", "갸라도스"], "잠만보",
               f"잠만보 {jamb_w:.1f}kg(키 {jamb_h:.1f}m) · "
               f"갸라도스 {gyar_w:.1f}kg(키 {gyar_h:.1f}m)",
               "몸길이는 갸라도스가 3배 가까이 길지만, 몸무게는 잠만보가 두 배 "
               "가까이 더 나갑니다."),
        choice("m5", "근육질 괴력몬과 덩치 큰 망나뇽 중, 기본 스피드가 더 빠른 "
                     "쪽은?",
               ["괴력몬", "망나뇽"], "망나뇽",
               f"망나뇽 스피드 {mangna_spd} · 괴력몬 스피드 {gwe_spd}",
               "근육이 많으면 빠를 것 같지만, 도감 수치로는 몸집이 큰 망나뇽이 "
               "더 빠릅니다."),
    ],
    caveat="여기 나온 몸무게·스피드는 실제로 측정한 값이 아니라 게임 개발사가 "
           "밸런스를 위해 정해 둔 설정값입니다. 스피드는 실제 이동 속도가 아니라 "
           "전투에서 누가 먼저 행동할지를 정하는 수치이고, 몸무게도 게임 "
           "세대가 바뀌며 조정되기도 합니다.")

# ── 화면에 보여줄 카드 순서 ──────────────────────────────────────
# 계산 순서(위 코드 순서)와 화면에 보이는 카드 순서는 다를 수 있다.
# cities(내 주제) → 보너스 2개 → 나머지는 원래 만든 순서.
_CARD_ORDER = ["cities", "food-consumption", "carbon"]
_original_order = list(TOPICS)


def _card_rank(t):
    if t["id"] in _CARD_ORDER:
        return _CARD_ORDER.index(t["id"])
    return len(_CARD_ORDER) + _original_order.index(t)


TOPICS.sort(key=_card_rank)


# ════════════════════════════════════════════════════════════════
def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for t in TOPICS:
        assert len(t["questions"]) == 5, f"{t['id']}: 문항이 5개가 아닙니다"
        pack = {k: t[k] for k in ("id", "emoji", "title", "blurb",
                                  "source", "source_url", "caveat")}
        pack["questions"] = t["questions"]
        io.open(OUT / f"{t['id']}.json", "w", encoding="utf-8").write(
            json.dumps(pack, ensure_ascii=False, indent=2))
        index.append({k: t[k] for k in ("id", "emoji", "title", "blurb",
                                        "source")})

    io.open(APP / "topics.json", "w", encoding="utf-8").write(json.dumps({
        "title": "감 테스트",
        "subtitle": "숫자에 대한 당신의 감은 몇 점입니까",
        "crowd_label": "우리 반",
        # 등급·문구는 여기서 고칩니다. 코드를 건드릴 일이 아닙니다
        "grades": [
            {"min": 90, "name": "촉이 데이터급", "emoji": "🎯"},
            {"min": 70, "name": "감이 좋은 편", "emoji": "📊"},
            {"min": 50, "name": "보통의 감각", "emoji": "🙂"},
            {"min": 30, "name": "느낌대로 삽니다", "emoji": "🎲"},
            {"min": 0, "name": "감은 접어두시죠", "emoji": "🙈"},
        ],
        "reactions_choice": {"hit": "맞히셨습니다", "miss": "다들 그렇게 찍습니다"},
        "reactions": [
            {"max": 5, "text": "촉이 좋으시네요"},
            {"max": 20, "text": "비슷하게 보셨습니다"},
            {"max": 60, "text": "음…"},
            {"max": 999, "text": "꽤 멀리 가셨습니다"},
        ],
        "topics": index,
    }, ensure_ascii=False, indent=2))

    # 사람이 읽는 정답지
    md = ["# 문항 정답지 — 10주제 50문항", "",
          "> 모든 값은 `데이터/raw/` 의 원본에서 `문항/build_topics.py` 가 계산합니다.", ""]
    for t in TOPICS:
        md += [f"## {t['emoji']} {t['title']}", "",
               f"- 출처: {t['source']} · {t['source_url']}"]
        if t["caveat"]:
            md += [f"- **한계** {t['caveat']}"]
        md += [""]
        for q in t["questions"]:
            a = f"{q['answer']}{q.get('unit', '')}" if q["type"] == "slider" \
                else q["answer"]
            md += [f"**{q['text']}**", "",
                   f"- 정답 **{a}**", f"- 근거 {q['basis']}",
                   f"- 왜 틀리나 {q['why']}", ""]
    io.open(HERE / "정답지.md", "w", encoding="utf-8").write("\n".join(md))

    print(f"주제 {len(TOPICS)}개 · 문항 {sum(len(t['questions']) for t in TOPICS)}개")
    for t in TOPICS:
        print(f"\n{t['emoji']} {t['title']}  ({t['source']})")
        for q in t["questions"]:
            a = f"{q['answer']}{q.get('unit', '')}" if q["type"] == "slider" \
                else q["answer"]
            print(f"    [{q['type'][:6]:<6}] {q['text'][:44]:<44} → {a}")


if __name__ == "__main__":
    main()

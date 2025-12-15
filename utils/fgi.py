import math
import requests
import pandas as pd
from datetime import datetime, timezone

# ❌ CNN_FGI_URL 는 더 이상 쓰지 않음
# from utils.config import CNN_FGI_URL
from utils.config import RAPIDAPI_KEY


def get_fgi_category(score):
    """점수에 따른 FGI 구간/한글 라벨."""
    s = float(score) if score is not None else math.nan
    if math.isnan(s):
        return "Unknown", "정보 없음"
    if s < 25:
        return "Extreme Fear", "극단적 공포"
    elif s < 45:
        return "Fear", "공포"
    elif s <= 55:
        return "Neutral", "중립"
    elif s <= 75:
        return "Greed", "탐욕"
    else:
        return "Extreme Greed", "극단적 탐욕"


def fetch_fear_greed():
    """
    API Key(RapidAPI) 기반으로 공포·탐욕 지수와 히스토리를 가져온다.

    main_app.py가 기대하는 리턴 형식:
      current_score: float
      current_rating: str
      last_update: datetime (UTC 또는 None)
      hist_df: pd.DataFrame(columns=['date', 'score', 'rating'])
    """

    if not RAPIDAPI_KEY:
        # main에서 ValueError를 받아서 경고 띄우도록 되어 있음
        raise ValueError("RAPIDAPI_KEY 환경변수가 설정되어 있지 않습니다.")

    # 👉 실제 사용 중인 RapidAPI FGI 엔드포인트에 맞춰 URL/host 수정
    url = "https://fear-and-greed-index.p.rapidapi.com/v1/fgi"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "fear-and-greed-index.p.rapidapi.com",
        "Accept": "application/json",
    }

    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # ─────────────────────
    # 1) 현재 지수 파싱
    # ─────────────────────

    current_score = math.nan
    current_rating = ""
    last_update = None

    # 여러 API 포맷을 방어적으로 처리
    # ① CNN 원본 형태를 프록시한 경우
    #    { "fear_and_greed": [{ "score": 56, "rating": "Greed", "timestamp": 1710... }], ... }
    if "fear_and_greed" in data:
        current = data.get("fear_and_greed")
        if isinstance(current, list):
            current = current[0] if current else {}
        elif not isinstance(current, dict):
            current = {}

        score_raw = current.get("score")
        rating_raw = current.get("rating")
        ts = current.get("timestamp")

        try:
            current_score = float(score_raw)
        except Exception:
            current_score = math.nan

        current_rating = str(rating_raw) if rating_raw is not None else ""

        if isinstance(ts, (int, float)):
            # CNN JSON은 ms 기준이라 /1000 필요할 수도 있음 → 둘 다 대응
            if ts > 10_000_000_000:  # 대략 ms 범위면
                last_update = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
            else:
                last_update = datetime.fromtimestamp(ts, tz=timezone.utc)

    # ② RapidAPI에서 "fgi" 루트로 주는 형태 (예시)
    #    { "fgi": { "now": { "value": 78, "valueText": "Greed", "timestamp": 1710... }, ... }, "historical": [...] }
    elif "fgi" in data:
        fgi_root = data["fgi"]
        now = fgi_root.get("now", {})
        score_raw = now.get("value") or now.get("score")
        rating_raw = now.get("valueText") or now.get("rating")
        ts = now.get("timestamp") or data.get("lastUpdated")

        try:
            current_score = float(score_raw)
        except Exception:
            current_score = math.nan

        current_rating = str(rating_raw) if rating_raw is not None else ""

        if isinstance(ts, (int, float)):
            last_update = datetime.fromtimestamp(float(ts), tz=timezone.utc)
        elif isinstance(ts, str):
            try:
                last_update = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                last_update = None

    # ─────────────────────
    # 2) 히스토리 파싱
    # ─────────────────────

    hist_raw = []

    # CNN 원본 스타일
    if "fear_and_greed_historical" in data:
        block = data.get("fear_and_greed_historical") or {}
        hist_raw = block.get("data") or []

        hist = []
        for d in hist_raw:
            ts_h = d.get("x")
            if ts_h is None:
                continue

            if isinstance(ts_h, (int, float)):
                # CNN의 x 도 ms 기준
                if ts_h > 10_000_000_000:
                    dt = datetime.fromtimestamp(ts_h / 1000.0, tz=timezone.utc)
                else:
                    dt = datetime.fromtimestamp(ts_h, tz=timezone.utc)
            else:
                try:
                    dt = datetime.fromisoformat(str(ts_h).replace("Z", "+00:00"))
                except Exception:
                    continue

            score = d.get("y")
            rating = d.get("rating") or ""
            try:
                score_f = float(score)
            except Exception:
                continue

            hist.append({"date": dt, "score": score_f, "rating": rating})

        df = pd.DataFrame(hist)

    # RapidAPI가 별도 "historical" 배열로 주는 경우
    elif "historical" in data:
        hist_raw = data.get("historical") or []
        hist = []
        for d in hist_raw:
            ts_h = d.get("timestamp") or d.get("time")
            if ts_h is None:
                continue

            if isinstance(ts_h, (int, float)):
                dt = datetime.fromtimestamp(float(ts_h), tz=timezone.utc)
            else:
                try:
                    dt = datetime.fromisoformat(str(ts_h).replace("Z", "+00:00"))
                except Exception:
                    continue

            score = d.get("score") or d.get("value")
            rating = d.get("rating") or d.get("valueText") or ""
            try:
                score_f = float(score)
            except Exception:
                continue

            hist.append({"date": dt, "score": score_f, "rating": rating})

        df = pd.DataFrame(hist)

    else:
        # 히스토리 자체를 제공하지 않는 API인 경우
        df = pd.DataFrame(columns=["date", "score", "rating"])

    return current_score, current_rating, last_update, df

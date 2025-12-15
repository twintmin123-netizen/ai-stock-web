#시장/기업/전망 점수 계산

# utils/scoring.py

import math
from typing import Any

from .common import to_number


# utils/scoring.py

import math
from typing import Any
from .common import to_number

# ─────────────────────────────
# 1) 미국 시장 점수 (기존 로직)
# ─────────────────────────────
def compute_us_market_score(spy_ret_1m: Any, qqq_ret_1m: Any, fgi_score: Any) -> int:
    """
    미국 고정 지표 기반 시장 점수 (0~10).
    - SPY / QQQ 1개월 수익률
    - CNN Fear & Greed Index
    """
    spy = to_number(spy_ret_1m)
    qqq = to_number(qqq_ret_1m)
    fgi = to_number(fgi_score)

    # 수익률 평균
    rets = [x for x in (spy, qqq) if not math.isnan(x)]
    avg_ret = sum(rets) / len(rets) if rets else 0.0

    # 1) 수익률 기준 기본 점수
    if avg_ret >= 8:
        base = 8
    elif avg_ret >= 3:
        base = 7
    elif avg_ret >= 0:
        base = 6
    elif avg_ret >= -3:
        base = 5
    elif avg_ret >= -8:
        base = 4
    else:
        base = 3

    # 2) FGI 보정
    if not math.isnan(fgi):
        if fgi >= 80:      # 극단적 탐욕
            base += 1
        elif fgi <= 20:    # 극단적 공포
            base -= 1

    return max(0, min(10, int(round(base))))


# 뒤에서 기존 이름으로도 쓸 수 있게 alias 유지
def compute_market_score(spy_ret_1m: Any, qqq_ret_1m: Any, fgi_score: Any) -> int:
    return compute_us_market_score(spy_ret_1m, qqq_ret_1m, fgi_score)


# ─────────────────────────────
# 2) 한국 시장 점수 (KOSPI/KOSDAQ/환율)
# ─────────────────────────────
def compute_korea_market_score(
    kospi_ret_3m: Any,
    kosdaq_ret_3m: Any,
    usdkrw: Any | None = None,
) -> int:
    """
    국내 고정 지표 기반 시장 점수 (0~10).
    - KOSPI / KOSDAQ 3개월 수익률
    - 환율(USDKRW) 수준으로 소폭 보정
    """

    k1 = to_number(kospi_ret_3m)
    k2 = to_number(kosdaq_ret_3m)

    vals = [x for x in (k1, k2) if not math.isnan(x)]
    if vals:
        avg_3m = sum(vals) / len(vals)
    else:
        # 데이터 없으면 중립
        return 5

    # 1) 3개월 수익률 기준 기본 점수 매핑
    #    (실제 코스피/코스닥 체감 구간에 맞춰서 대략적인 계단 함수)
    if avg_3m >= 20:
        base = 9
    elif avg_3m >= 10:
        base = 8
    elif avg_3m >= 5:
        base = 7
    elif avg_3m >= 0:
        base = 6
    elif avg_3m >= -5:
        base = 5
    elif avg_3m >= -15:
        base = 4
    elif avg_3m >= -25:
        base = 3
    else:
        base = 2

    # 2) 환율 보정 (원화 약세 심하면 -1, 강세면 +1)
    u = to_number(usdkrw)
    if not math.isnan(u):
        if u >= 1350:
            base -= 1
        elif u <= 1200:
            base += 1

    return max(0, min(10, int(round(base))))



def compute_us_company_score(
    ticker_ret_1m: float,
    benchmark_ret_1m: float,
    news_list: list,
    pe: float = None,
    roe: float = None,
) -> int:
    """
    미국 종목 점수 (0~10) - "좋은 기업인가?"
    구성: 펀더멘털(4) + 상대수익률(3) + 뉴스(3)
    제거: RSI, 절대수익률 (전망 점수로 이관)
    """
    score = 5 # 기본 점수
    
    # 1. 펀더멘털 (Fundamental) - 최대 ±4점
    # 퀄리티(ROE)와 밸류에이션(PE)
    f_score = 0
    pe = to_number(pe)
    roe = to_number(roe)
    
    if not math.isnan(roe):
        if roe > 20: f_score += 2
        elif roe > 10: f_score += 1
        elif roe < 0: f_score -= 1
        elif roe < -10: f_score -= 2
        
    if not math.isnan(pe):
        if 0 < pe < 15: f_score += 1  # 저평가
        elif pe > 60: f_score -= 1    # 고평가 부담
        
    score += f_score
    
    # 2. 상대 수익률 (Alpha) - 최대 ±3점
    # 시장(지수) 대비 얼마나 강한가?
    if not math.isnan(ticker_ret_1m) and not math.isnan(benchmark_ret_1m):
        alpha = ticker_ret_1m - benchmark_ret_1m
        if alpha > 5: score += 2
        elif alpha > 1: score += 1
        elif alpha < -5: score -= 2
        elif alpha < -1: score -= 1
        
    # 3. 뉴스 감정 (Sentiment) - 최대 ±2점
    # 기존 키워드 방식 유지
    positive_keywords = ["beat", "record", "outperform", "growth", "strong", "upgrade", "buy"]
    negative_keywords = ["miss", "downgrade", "lawsuit", "antitrust", "weak", "slump", "sell"]
    
    news_list = news_list or []
    pos = 0
    neg = 0
    for n in news_list:
        txt = ((n.get("title") or "") + " " + (n.get("description") or "")).lower()
        if any(k in txt for k in positive_keywords): pos += 1
        if any(k in txt for k in negative_keywords): neg += 1
        
    if pos > neg: score += 1
    elif neg > pos: score -= 1
    
    return max(1, min(score, 10))


def compute_korea_company_score(
    ticker_ret_1m: float,
    benchmark_ret_1m: float,
    news_list: list,
    pe: float = None,
    roe: float = None,
) -> int:
    """
    한국 종목 점수 (0~10) - "좋은 기업인가?"
    구성: 펀더멘털(4) + 상대수익률(3) + 뉴스(3)
    """
    score = 5 # 기본 점수
    
    # 1. 펀더멘털 (Fundamental)
    f_score = 0
    pe = to_number(pe)
    roe = to_number(roe)
    
    if not math.isnan(roe):
        if roe > 15: f_score += 2     # 한국 기준 15%면 매우 우수
        elif roe > 8: f_score += 1
        elif roe < 0: f_score -= 1
        elif roe < -5: f_score -= 2
        
    if not math.isnan(pe):
        if 0 < pe < 10: f_score += 1  # 한국 디스카운트 고려
        elif pe > 40: f_score -= 1
        
    score += f_score
    
    # 2. 상대 수익률 (Alpha)
    if not math.isnan(ticker_ret_1m) and not math.isnan(benchmark_ret_1m):
        alpha = ticker_ret_1m - benchmark_ret_1m
        if alpha > 7: score += 2       # 한국은 변동성이 커서 기준 상향
        elif alpha > 2: score += 1
        elif alpha < -7: score -= 2
        elif alpha < -2: score -= 1
        
    # 3. 뉴스 감정
    positive_keywords = ["실적", "성장", "상승", "호재", "긍정", "수주", "계약", "개발"]
    negative_keywords = ["하락", "악재", "부진", "감소", "소송", "유상증자", "적자"]
    
    news_list = news_list or []
    pos = 0
    neg = 0
    for n in news_list:
        txt = ((n.get("title") or "") + " " + (n.get("description") or "")).lower()
        if any(k in txt for k in positive_keywords): pos += 1
        if any(k in txt for k in negative_keywords): neg += 1
        
    if pos > neg: score += 1
    elif neg > pos: score -= 1

    return max(1, min(score, 10))


# 기존 함수명 유지 (하위 호환성)
def compute_company_score(
    ticker_ret_1m: Any,
    ticker_ret_1w: Any,
    qqq_ret_1m: Any,
    rsi: Any,
    news_list: list,
    is_korean: bool = False,
    pe: Any = None,
    roe: Any = None,
) -> int:
    """
    종목 개별 점수 계산 (시장 자동 감지).
    is_korean=True면 한국 기준, False면 미국 기준 사용
    """
    if is_korean:
        return compute_korea_company_score(ticker_ret_1m, qqq_ret_1m, news_list, pe, roe)
    else:
        return compute_us_company_score(ticker_ret_1m, qqq_ret_1m, news_list, pe, roe)


def compute_outlook_score(
    ret_1w: float,
    ret_1m: float,
    ret_3m: float,
    volatility: float,
    rsi: float = 50
) -> int:
    """
    전망 점수 (0~10) - "지금 매수 타이밍인가?"
    구성: 추세(40%) + 모멘텀(20%) + 타이밍/RSI(20%) + 안정성(20%)
    """
    ret_1w = to_number(ret_1w)
    ret_1m = to_number(ret_1m)
    ret_3m = to_number(ret_3m)
    volatility = to_number(volatility)
    rsi = to_number(rsi)
    
    score = 5  # 기본 중립
    
    # 1. 중기 추세 (Trend 3m) - 방향성
    if ret_3m > 15: score += 2
    elif ret_3m > 5: score += 1
    elif ret_3m < -10: score -= 2
    elif ret_3m < -5: score -= 1
        
    # 2. 단기 모멘텀 (Momentum 1w/1m) - 가속도
    if ret_1m > 10: score += 1    # 1개월 강세
    if ret_1w > 5: score += 1     # 1주 급등 (단기 탄력)
    elif ret_1w < -5: score -= 1  # 1주 급락
    
    # 3. RSI 타이밍 (Timing)
    # 과열권 진입 시 오히려 감점 (조정 리스크)
    # 과매도권 진입 시 가점 (반등 기회)
    if rsi > 75: score -= 2       # 너무 과열
    elif rsi > 65: score -= 1     # 과열 주의
    elif 45 <= rsi <= 60: score += 1 # 가장 건강한 상승 구간
    elif rsi < 25: score += 2     # 과매도 (Strong Buy Signal)
    elif rsi < 35: score += 1     # 과매도 보너스
        
    # 4. 안정성 (Stability)
    if volatility < 20: score += 1
    elif volatility > 50: score -= 2
    elif volatility > 35: score -= 1
        
    return max(0, min(score, 10))


def decide_action(market_score: int, company_score: int, outlook_score: int) -> str:
    """
    최종 액션 결정:
    - '추가 매수'
    - '현상 유지'
    - '매도'
    """
    # 추가 매수: 시장·종목 점수 양호 + 3개월 전망도 우호적
    if market_score >= 6 and company_score >= 6 and outlook_score >= 7:
        return "추가 매수"

    # 매도: 시장/종목 모두 좋지 않거나, 3개월 전망 점수가 낮을 때
    if (market_score <= 3 and company_score <= 4) or outlook_score <= 3:
        return "매도"

    # 그 외는 유지
    return "현상 유지"



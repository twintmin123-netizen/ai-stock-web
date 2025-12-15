"""
utils.market_indicators
=======================

한국 시장 고정 지표 모듈 (KOSPI / KOSDAQ / VKOSPI / 국채10Y / KOSPI PBR / USDKRW).

- 미국 지표는 main 쪽에서 처리 → 여기서는 비워둠.
- 이 모듈은 "korea" 섹션만 실제 값으로 채운다.

데이터 소스 설계
----------------
1) KOSPI / KOSDAQ 3개월 수익률
   - 우선 pykrx의 공식 지수 데이터 사용
     * KOSPI  : 지수코드 "1001"
     * KOSDAQ: 지수코드 "2001"
   - pykrx 미설치/오류 시 yfinance (^KS11, ^KQ11)로 fallback (정확도는 다소 떨어질 수 있음).

2) VKOSPI
   - 우선 pykrx get_index_ohlcv(지수코드 "1028") 시도
   - 실패 시 (None, None) 반환.

3) 한국 10년물 국채 금리 (KR10Y)
   - FRED API 사용 (series_id=IRLTLT01KRM156N, 한국 10년물 수익률)
   - 환경변수 FRED_API_KEY 필요.
   - 실패 시 None.

4) KOSPI PBR
   - pykrx.get_index_fundamental(지수코드 "1001")에서 PBR 컬럼 사용.
   - 실패 시 None.

5) USD/KRW 환율
   - FRED API 사용 (series_id=DEXKOUS, 원/달러 환율)
   - FRED 실패 시 yfinance("KRW=X") fallback.

반환 형식
---------
get_market_indicators() → dict
{
    "equity": {},
    "volatility": {},
    "macro": {},
    "sentiment": {},
    "korea": {
        "equity": {
            "KOSPI": { "ret_3m": { "value": float|None, "label": "3개월 수익률" } },
            "KOSDAQ": { ... },
        },
        "volatility": {
            "VKOSPI": { "value": float|None, "change_pct": float|None },
        },
        "macro": {
            "KR10Y": { "value": float|None },
        },
        "valuation": {
            "KOSPI_PBR": { "value": float|None },
        },
        "fx": {
            "USDKRW": { "value": float|None },
        },
    }
}
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any

import pandas as pd
import requests
import yfinance as yf

# ─────────────────────────────────────
# pykrx (있으면 사용, 없으면 None)
# ─────────────────────────────────────
try:
    from pykrx import stock as krx_stock
except ImportError:  # 선택 라이브러리
    krx_stock = None


# ─────────────────────────────────────
# 공통 헬퍼
# ─────────────────────────────────────
def _safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _ret_3m(df: pd.DataFrame, col: str = "Close") -> Optional[float]:
    """
    3개월 히스토리 DataFrame에서 단순 구간 수익률(%) 계산.
    """
    if df is None or df.empty:
        return None
    try:
        first = float(df[col].iloc[0])
        last = float(df[col].iloc[-1])
        if first == 0:
            return None
        return (last / first - 1.0) * 100.0
    except Exception:
        return None


def _fetch_3m_history_yf(ticker: str, interval: str = "1d") -> pd.DataFrame:
    """
    yfinance에서 3개월치 데이터를 받아오는 헬퍼 함수.
    실패하면 빈 DataFrame 리턴.
    """
    try:
        df = yf.Ticker(ticker).history(period="3mo", interval=interval)
        if not df.empty:
            df = df.copy()
            df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()


def _fetch_last_price_yf(ticker: str) -> Optional[float]:
    """
    가장 최근 종가(또는 환율·금리 등)를 하나만 가져오는 간단 함수.
    실패 시 None.
    """
    try:
        df = yf.Ticker(ticker).history(period="5d", interval="1d")
        if df is None or df.empty:
            return None
        val = df["Close"].iloc[-1]
        return float(val)
    except Exception:
        return None


# ─────────────────────────────────────
# FRED 공통 함수 (한국 10Y, USDKRW 등)
# ─────────────────────────────────────
FRED_API_KEY = os.getenv("FRED_API_KEY")


def _fetch_latest_from_fred(series_id: str, limit: int = 10) -> Optional[float]:
    """
    FRED에서 최근 관측치를 가져오는 헬퍼.
    - series_id: FRED 시리즈 ID (예: IRLTLT01KRM156N, DEXKOUS 등)
    - 실패 시 None.
    """
    if not FRED_API_KEY:
        return None

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        obs = data.get("observations", []) or []
        # value 가 "." 인 항목 제외
        for o in obs:
            v = o.get("value")
            if v is None or v == ".":
                continue
            fv = _safe_float(v)
            if fv is not None:
                return fv
    except Exception:
        return None

    return None


# ─────────────────────────────────────
# KOSPI / KOSDAQ 3개월 수익률
# ─────────────────────────────────────
def _fetch_index_3m_pykrx(index_code: str) -> Tuple[Optional[pd.DataFrame], Optional[float]]:
    """
    pykrx로 지수코드(index_code)의 3개월 일자별 데이터를 가져와 수익률 계산.
    - index_code 예: KOSPI "1001", KOSDAQ "2001"
    """
    if krx_stock is None:
        return None, None

    try:
        end = datetime.today()
        start = end - timedelta(days=90)
        s = start.strftime("%Y%m%d")
        e = end.strftime("%Y%m%d")

        df = krx_stock.get_index_ohlcv_by_date(s, e, index_code)
        if df is None or df.empty:
            return None, None

        # 인덱스: 날짜, 컬럼: 시가/고가/저가/종가/거래량 ...
        df = df.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # 종가 컬럼 검색
        close_col = None
        for col in ["종가", "Close", "close"]:
            if col in df.columns:
                close_col = col
                break
        if close_col is None:
            return df, None

        ret_3m = _ret_3m(df, col=close_col)
        return df, ret_3m
    except Exception:
        return None, None


def fetch_kospi_kosdaq_3m() -> Tuple[Optional[float], Optional[float]]:
    """
    KOSPI / KOSDAQ 3개월 수익률 (%)
    - yfinance (^KS11, ^KQ11) 사용
    
    주의: pykrx 코드 1001/2001은 KOSPI200/KOSDAQ150 등 다른 지수를 반환하므로 사용하지 않음
    """
    # yfinance로 직접 가져오기 (가장 정확함)
    kospi_df = _fetch_3m_history_yf("^KS11")
    kosdaq_df = _fetch_3m_history_yf("^KQ11")

    kospi_ret_3m = _ret_3m(kospi_df)
    kosdaq_ret_3m = _ret_3m(kosdaq_df)

    return kospi_ret_3m, kosdaq_ret_3m


# ─────────────────────────────────────
# VKOSPI (pykrx)
# ─────────────────────────────────────
def fetch_vkospi() -> Tuple[Optional[float], Optional[float]]:
    """
    VKOSPI 현재값 + 3개월 변동률(%)
    - yfinance 사용 (티커: ^VKOSPI 또는 investing.com 크롤링)
    
    주의: VKOSPI는 보통 10-40 범위의 값
    pykrx 코드 1028은 잘못된 값을 반환하므로 사용하지 않음 (540 instead of 41)
    """
    # 방법 1: investing.com에서 VKOSPI 크롤링
    try:
        url = "https://kr.investing.com/indices/kospi-volatility"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        html = res.text
        
        import re
        
        # data-test="instrument-price-last" 패턴 찾기
        match = re.search(r'data-test="instrument-price-last"[^>]*>([0-9.]+)', html)
        if match:
            current_val = _safe_float(match.group(1))
            if current_val and 5 < current_val < 100:  # 합리적인 VKOSPI 범위
                # 3개월 변동률은 계산 불가 (과거 데이터 없음)
                return current_val, None
        
        # 대체 패턴: 숫자 범위 기반 검색
        matches = re.findall(r'\b([1-9][0-9]\.[0-9]{2})\b', html)
        for m in matches:
            val = _safe_float(m)
            if val and 10 < val < 60:  # VKOSPI 일반적 범위
                return val, None
                
    except Exception:
        pass
    
    return None, None


# ─────────────────────────────────────
# 한국 10년물 금리 (FRED → investing.com)
# ─────────────────────────────────────
def _fetch_kr_10y_from_investing() -> Optional[float]:
    """
    investing.com에서 한국 10년물 국채 수익률 크롤링.
    - https://kr.investing.com/rates-bonds/south-korea-10-year-bond-yield
    """
    try:
        url = "https://kr.investing.com/rates-bonds/south-korea-10-year-bond-yield"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        html = res.text
        
        import re
        
        # 방법 1: data-test="instrument-price-last" 속성 찾기 (investing.com 공통 패턴)
        match = re.search(r'data-test="instrument-price-last"[^>]*>([0-9.]+)', html)
        if match:
            val = _safe_float(match.group(1))
            if val is not None and 0 < val < 20:
                return val
        
        # 방법 2: class="text-2xl" 같은 큰 숫자 표시 영역 찾기
        match = re.search(r'class="[^"]*text-[^"]*"[^>]*>([0-9]{1,2}\.[0-9]{2,3})', html)
        if match:
            val = _safe_float(match.group(1))
            if val is not None and 0 < val < 20:
                return val
        
        # 방법 3: 일반적인 숫자 패턴 (페이지 전체에서 합리적인 수익률 값 찾기)
        # 한국 10년물은 보통 2-5% 범위
        matches = re.findall(r'\b([2-5]\.[0-9]{2,3})\b', html)
        if matches:
            # 가장 먼저 나오는 값 사용
            val = _safe_float(matches[0])
            if val is not None:
                return val
        
        return None
    except Exception as e:
        return None



def fetch_kr_10y_yield() -> Optional[float]:
    """
    한국 10년물 국채 금리 (%)

    1차: FRED 시리즈 IRLTLT01KRM156N 사용
    - Long-Term Government Bond Yields: 10-Year for Korea
    - 이미 % 단위로 제공됨.

    2차: investing.com 웹 크롤링
    - https://kr.investing.com/rates-bonds/south-korea-10-year-bond-yield

    실패 시 None.
    """
    # 1) FRED 시도
    series_id = os.getenv("FRED_KR10Y_SERIES", "IRLTLT01KRM156N")
    val = _fetch_latest_from_fred(series_id)
    if val is not None:
        return val

    # 2) investing.com 크롤링
    val = _fetch_kr_10y_from_investing()
    if val is not None:
        return val
    
    return None


# ─────────────────────────────────────
# KOSPI PBR (pykrx)
# ─────────────────────────────────────
def fetch_kospi_pbr() -> Optional[float]:
    """
    KOSPI 전체 PBR 지수.
    - pykrx.get_index_fundamental(지수코드 "1001") 사용.
    - 최근 영업일 기준으로 가장 가까운 날짜에서 PBR 가져옴.
    """
    if krx_stock is None:
        return None

    try:
        today = datetime.today()
        # 최근 영업일을 찾기 위해 최대 15일 이전까지 탐색 (주말/공휴일)
        for i in range(0, 15):
            date_str = (today - timedelta(days=i)).strftime("%Y%m%d")
            try:
                df = krx_stock.get_index_fundamental(date_str, date_str, "1001")
            except Exception:
                continue

            if df is None or df.empty:
                continue

            # 컬럼명 후보
            pbr_col = None
            for col in ["PBR", "pbr", "BPS/PBR", "PER/PBR"]:
                if col in df.columns:
                    pbr_col = col
                    break

            if pbr_col is None:
                # pykrx 버전에 따라 PBR 이 별도 컬럼이 아니라 BPS 와 PB 계수를 나눠야 할 수도 있음
                continue

            val = df[pbr_col].iloc[-1]
            return _safe_float(val)
    except Exception:
        return None

    return None


# ─────────────────────────────────────
# USD/KRW 환율
# ─────────────────────────────────────
def fetch_usdkrw() -> Optional[float]:
    """
    원/달러 환율 (USDKRW).

    1차: FRED DEXKOUS 시리즈 사용 (일간 고시 환율, 원/달러)
    2차: yfinance("KRW=X") 종가 fallback
    """
    # 1) FRED
    fx = _fetch_latest_from_fred("DEXKOUS")
    if fx is not None:
        return fx

    # 2) yfinance fallback
    return _fetch_last_price_yf("KRW=X")


# ─────────────────────────────────────
# 한국 지표 블록 조립
# ─────────────────────────────────────
def build_korea_block() -> Dict[str, Any]:
    kospi_ret_3m, kosdaq_ret_3m = fetch_kospi_kosdaq_3m()
    vkospi_val, vkospi_ret_3m = fetch_vkospi()
    kr10y_val = fetch_kr_10y_yield()
    kospi_pbr = fetch_kospi_pbr()
    usdkrw = fetch_usdkrw()

    korea_block: Dict[str, Any] = {
        "equity": {
            "KOSPI": {
                "ret_3m": {
                    "value": kospi_ret_3m,
                    "label": "3개월 수익률",
                }
            },
            "KOSDAQ": {
                "ret_3m": {
                    "value": kosdaq_ret_3m,
                    "label": "3개월 수익률",
                }
            },
        },
        "volatility": {
            "VKOSPI": {
                "value": vkospi_val,
                "change_pct": vkospi_ret_3m,
            }
        },
        "macro": {
            "KR10Y": {
                "value": kr10y_val,
            }
        },
        "valuation": {
            "KOSPI_PBR": {
                "value": kospi_pbr,
            }
        },
        "fx": {
            "USDKRW": {
                "value": usdkrw,
            }
        },
    }

    return korea_block


# ─────────────────────────────────────
# 미국 시장 지표 조회
# ─────────────────────────────────────
def build_us_block() -> Dict[str, Any]:
    """
    미국 시장 지표 수집:
    - SPY, QQQ (3개월 수익률 및 현재가)
    - VIX (현재값)
    - Fear & Greed Index
    """
    # SPY, QQQ 데이터
    spy_df = _fetch_3m_history_yf("SPY")
    qqq_df = _fetch_3m_history_yf("QQQ")
    vix_df = _fetch_3m_history_yf("^VIX")
    
    spy_current = _fetch_last_price_yf("SPY")
    qqq_current = _fetch_last_price_yf("QQQ")
    vix_current = _fetch_last_price_yf("^VIX")
    
    spy_ret_3m = _ret_3m(spy_df)
    qqq_ret_3m = _ret_3m(qqq_df)
    
    # Calculate change_pct (recent change)
    spy_change_pct = None
    qqq_change_pct = None
    
    if not spy_df.empty and len(spy_df) >= 2:
        try:
            spy_prev = float(spy_df["Close"].iloc[-2])
            spy_curr = float(spy_df["Close"].iloc[-1])
            spy_change_pct = ((spy_curr / spy_prev) - 1) * 100
        except:
            pass
    
    if not qqq_df.empty and len(qqq_df) >= 2:
        try:
            qqq_prev = float(qqq_df["Close"].iloc[-2])
            qqq_curr = float(qqq_df["Close"].iloc[-1])
            qqq_change_pct = ((qqq_curr / qqq_prev) - 1) * 100
        except:
            pass
    
    # Fear & Greed Index
    fgi_value = None
    fgi_rating = None
    try:
        from utils.fgi import fetch_fear_greed
        fgi_score, _, _, _ = fetch_fear_greed()
        if fgi_score is not None:
            fgi_value = fgi_score
            # Determine rating
            if fgi_score <= 25:
                fgi_rating = "Extreme Fear"
            elif fgi_score <= 45:
                fgi_rating = "Fear"
            elif fgi_score <= 55:
                fgi_rating = "Neutral"
            elif fgi_score <= 75:
                fgi_rating = "Greed"
            else:
                fgi_rating = "Extreme Greed"
    except Exception:
        pass

    # Additional US Indicators (TNX, DXY)
    tnx_df = _fetch_3m_history_yf("^TNX")
    dxy_df = _fetch_3m_history_yf("DX-Y.NYB")
    
    tnx_current = _fetch_last_price_yf("^TNX")
    dxy_current = _fetch_last_price_yf("DX-Y.NYB")
    
    return {
        "spy": {
            "value": spy_current,
            "change_pct": spy_change_pct,
            "ret_3m": spy_ret_3m
        },
        "qqq": {
            "value": qqq_current,
            "change_pct": qqq_change_pct,
            "ret_3m": qqq_ret_3m
        },
        "vix": {
            "value": vix_current
        },
        "tnx": {
            "value": tnx_current
        },
        "dxy": {
            "value": dxy_current
        },
        "fgi": {
            "value": fgi_value,
            "rating": fgi_rating
        }
    }


# ─────────────────────────────────────
# 외부에서 사용하는 진입 함수
# ─────────────────────────────────────
def get_market_indicators() -> Dict[str, Any]:
    """
    시장 지표 통합 조회 함수.
    
    - 미국 지표: SPY, QQQ, VIX, Fear & Greed Index
    - 한국 지표: KOSPI, KOSDAQ, VKOSPI, 국채10Y, KOSPI PBR, USD/KRW
    """
    us_data = build_us_block()
    korea = build_korea_block()

    return {
        "us": us_data,       # 미국 시장 데이터
        "korea": korea,      # 한국 시장 데이터
    }

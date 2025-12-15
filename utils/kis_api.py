# kis_api.py (마지막 부분 근처)

from typing import List, Dict, Any
from datetime import datetime
from pykrx import stock as krx_stock


def search_korean_stocks(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    한국(코스피/코스닥) 종목 검색.

    반환 형식 예시:
    {
        "symbol": "005930.KS",      # yfinance 에 바로 쓸 수 있는 심볼
        "code": "005930",           # 6자리 종목코드 (표시용/참고용)
        "name": "삼성전자",
        "exchange": "KOSPI",
        "region": "KR",
    }
    """
    if krx_stock is None:
        return []

    keyword = (keyword or "").strip()
    if not keyword:
        return []

    # KRX 전체(코스피+코스닥) 코드 목록
    try:
        tickers = krx_stock.get_market_ticker_list(market="ALL")
    except Exception:
        return []

    results: List[Dict[str, Any]] = []

    for code in tickers:
        try:
            name = krx_stock.get_market_ticker_name(code)
        except Exception:
            continue

        # 이름이나 코드에 키워드가 포함된 것만 필터링
        if keyword not in name and keyword not in code:
            continue

        # ── 여기서 '시장' 정보 계산 ──
        # 0/1/2/3/4 로 시작하면 KOSPI, 그 외는 KOSDAQ 으로 단순 분류
        first = code[0]
        exchange = "KOSPI" if first in ("0", "1", "2", "3", "4") else "KOSDAQ"

        # yfinance 용 심볼 만들기
        if exchange == "KOSPI":
            yf_symbol = f"{code}.KS"
        else:
            yf_symbol = f"{code}.KQ"

        results.append(
            {
                "symbol": yf_symbol,         # ★ Streamlit 전체에서 이 값을 티커로 사용
                "code": code,               #   (가격 조회시도 이 값이 넘어감)
                "name": name,
                "exchange": exchange,
                "region": "KR",
            }
        )

        if len(results) >= limit:
            break

    return results


# ───────────────────────
# KIS API: 주가/투자지표 (PER, PBR, ROE)
# ───────────────────────

import os
import requests
from dotenv import load_dotenv

load_dotenv()

KIS_APP_KEY = os.getenv('KIS_APP_KEY')
KIS_APP_SECRET = os.getenv('KIS_APP_SECRET')
KIS_BASE_URL = os.getenv('KIS_BASE_URL')

_KIS_ACCESS_TOKEN = None

def _get_kis_token():
    """KIS 접근 토큰 발급 (메모리 캐싱)"""
    global _KIS_ACCESS_TOKEN
    if _KIS_ACCESS_TOKEN:
        return _KIS_ACCESS_TOKEN
    
    if not KIS_APP_KEY or not KIS_APP_SECRET:
        return None
        
    url = f"{KIS_BASE_URL}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET
    }
    try:
        res = requests.post(url, headers=headers, json=body, timeout=5)
        if res.status_code == 200:
            _KIS_ACCESS_TOKEN = res.json().get('access_token')
            return _KIS_ACCESS_TOKEN
    except Exception as e:
        print(f"[_get_kis_token] 토큰 발급 실패: {e}")
    return None

def get_market_metrics(ticker: str) -> Dict[str, Any]:
    """
    KIS API를 통해 주가 지표(PER, PBR, ROE) 조회
    
    Returns:
        {
            "per": 19.79,
            "pbr": 5.15,
            "roe": 0.26,  # 26% (비율로 반환)
            "eps": 27182,
            "bps": 104567
        }
    """
    # 티커 정리 (000660.KS -> 000660)
    code = ticker.split('.')[0]
    
    token = _get_kis_token()
    if not token:
        return {}
    
    url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": "FHKST01010100"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": code
    }
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        data = res.json().get('output', {})
        
        per = float(data.get('per', 0))
        pbr = float(data.get('pbr', 0))
        eps = float(data.get('eps', 0))
        bps = float(data.get('bps', 0))
        
        # ROE 계산 (EPS / BPS)
        roe = None
        if bps > 0:
            roe = eps / bps  # 비율 (0.26 = 26%)
            
        return {
            "per": per if per > 0 else None,
            "pbr": pbr if pbr > 0 else None,
            "roe": roe,
            "eps": eps,
            "bps": bps
        }
    except Exception as e:
        print(f"[get_market_metrics] KIS API 조회 실패 ({ticker}): {e}")
        return {}


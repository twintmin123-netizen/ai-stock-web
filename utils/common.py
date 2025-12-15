# utils/common.py

import math
from typing import Any

import pandas as pd
import requests
import yfinance as yf

from .config import NEWS_API_KEY


def to_number(x: Any) -> float:
    """
    Series / None / float / int 상관없이 float 하나로 통일.
    - Series면 마지막 값 사용
    - 변환 실패 시 NaN
    """
    if isinstance(x, pd.Series):
        if len(x) == 0:
            return math.nan
        x = x.iloc[-1]
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def _get_kr_company_name_from_krx(code: str) -> str:
    """
    KRX API를 사용하여 한국 종목 이름 가져오기.
    네이버 크롤링보다 안정적.
    
    Args:
        code: 6자리 종목코드 (예: "005930")
    
    Returns:
        회사명 (한글)
    """
    try:
        from pykrx import stock
        # pykrx에서 종목명 가져오기
        name = stock.get_market_ticker_name(code)
        if name:
            return name
    except Exception as e:
        print(f"[get_kr_company_name_from_krx] KRX 조회 실패: {e}")
    
    return ""


def get_company_name(ticker: str) -> str:
    """
    종목 이름(회사명) 가져오기.
    한국 종목은 KRX API, 그 외는 yfinance 사용.
    """
    # 한국 종목인지 확인
    if _is_korean_symbol(ticker):
        # .KS, .KQ 제거하고 6자리 코드만 추출
        code = ticker.split('.')[0]
        if code.isdigit() and len(code) == 6:
            return _get_kr_company_name_from_krx(code)
    
    # 미국 종목은 yfinance 사용
    try:
        info = yf.Ticker(ticker).info
        return info.get("shortName") or info.get("longName") or ""
    except Exception:
        return ""


def _is_korean_symbol(ticker: str) -> bool:
    """
    국내 종목 여부 판별:
    - 6자리 숫자 (005930)
    - .KS, .KQ 로 끝나는 티커
    """
    s = (ticker or "").strip().upper()
    if s.endswith(".KS") or s.endswith(".KQ"):
        return True
    return s.isdigit() and len(s) == 6


def _fetch_naver_news(keyword: str, display: int = 20) -> list:
    """
    네이버 뉴스 API로 한국어 뉴스 검색.
    
    Args:
        keyword: 검색 키워드
        display: 결과 개수 (최대 100)
    
    Returns:
        뉴스 리스트 (title, description, source, url, published_at)
    """
    from .config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
    
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return []
    
    try:
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        }
        params = {
            "query": keyword,
            "display": min(display, 100),  # 최대 100개
            "start": 1,
            "sort": "date",  # 날짜순 정렬
        }
        
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        data = res.json()
        
        items = data.get("items", [])
        clean = []
        for item in items:
            # HTML 태그 제거 (<b>, </b> 등)
            import re
            title = re.sub(r'<[^>]+>', '', item.get("title", ""))
            description = re.sub(r'<[^>]+>', '', item.get("description", ""))
            
            # 한국 뉴스는 이미 한글이므로 번역 불필요
            clean.append({
                "title": title,
                "description": description,
                "source": "네이버 뉴스",
                "url": item.get("link", ""),
                "published_at": item.get("pubDate", ""),
            })
        
        return clean
    except Exception as e:
        print(f"[fetch_naver_news] 네이버 뉴스 API 호출 실패: {e}")
        return []



def _translate_with_deepl(text: str) -> str:
    """
    텍스트를 한국어로 번역 (OpenAI GPT 사용).
    
    이미 한국어인 경우에도 번역 시도 (혼합 텍스트 처리).
    """
    if not text:
        return text
    
    # OpenAI GPT로 번역
    try:
        from .config import client
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use cheaper model for translation
            messages=[
                {"role": "system", "content": "You are a professional translator. Translate the following text to Korean. Preserve formatting, numbers, and technical terms. Only output the translation, nothing else."},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        
        translated = response.choices[0].message.content.strip()
        print(f"[OpenAI] ✅ Translation success")
        return translated
    except Exception as e:
        print(f"[OpenAI] ❌ Translation failed: {e}")
        return text


def _fetch_newsapi_news(keyword: str, page_size: int = 20) -> list:
    """
    NewsAPI로 영문 뉴스 검색 (기존 로직).
    """
    from .config import NEWS_API_KEY
    
    if not NEWS_API_KEY:
        return []

    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": keyword,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "apiKey": NEWS_API_KEY,
        }
        res = requests.get(url, params=params)
        res.raise_for_status()
        articles = res.json().get("articles", [])
        clean = []
        for a in articles:
            title = a.get("title", "")
            description = a.get("description", "")
            
            # DeepL 번역 시도
            title = _translate_with_deepl(title)
            description = _translate_with_deepl(description)

            clean.append({
                "title": title,
                "description": description,
                "source": a.get("source", {}).get("name", ""),
                "url": a.get("url", ""),
                "published_at": a.get("publishedAt", ""),
            })
        return clean
    except Exception as e:
        print(f"[fetch_newsapi_news] NewsAPI 호출 실패: {e}")
        return []


def fetch_news(keyword: str, page_size: int = 20, ticker: str = "") -> list:
    """
    뉴스 검색 통합 함수.
    
    - 한국 종목: 네이버 뉴스 API 사용
    - 미국 종목: NewsAPI 사용
    
    Args:
        keyword: 검색 키워드
        page_size: 결과 개수
        ticker: 종목 심볼 (한국/미국 구분용, 선택사항)
    
    Returns:
        뉴스 리스트
    """
    # ticker가 주어진 경우 한국 종목인지 확인
    if ticker and _is_korean_symbol(ticker):
        return _fetch_naver_news(keyword, display=page_size)
    else:
        return _fetch_newsapi_news(keyword, page_size=page_size)

# utils/search.py
# 번역 + 심볼 검색 모듈

import re
import requests
from utils.config import client, OPENAI_API_KEY, OPENAI_CHAT_MODEL
from utils.finance_data import fetch_price_history  # 앞으로 국내/미국 공통으로 쓸 수 있음
from utils.kis_api import search_korean_stocks


def translate_to_english(text: str) -> str:
    """
    한국어로 입력된 미국/해외 종목 검색어를
    영어 회사명 / 티커 형태로 번역.
    
    Fallback 순서:
    1. OpenAI API
    2. Papago API (Naver)
    3. 원본 텍스트 반환
    """
    if not text.strip():
        return text
    
    # 1차: OpenAI API 시도
    if OPENAI_API_KEY:
        try:
            res = client.chat.completions.create(
                model=OPENAI_CHAT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Translate the user's stock search keyword into English "
                            "company or ticker format. Return only the keyword."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0.0,
            )
            translated = res.choices[0].message.content.strip()
            print(f"[OpenAI] Translated '{text}' -> '{translated}'")
            return translated
        except Exception as e:
            print(f"[OpenAI] Translation failed: {e}, trying Papago fallback...")
    
    # 2차: Papago API 시도
    try:
        from utils.papago import translate_with_papago
        translated = translate_with_papago(text, source="ko", target="en")
        if translated:
            return translated
    except Exception as e:
        print(f"[Papago] Fallback failed: {e}")
    
    # 3차: 원본 반환
    print(f"[Translation] All methods failed, returning original: '{text}'")
    return text



def _contains_korean(text: str) -> bool:
    """한글 포함 여부 간단 체크."""
    return bool(re.search("[가-힣]", text))


def search_symbols(query: str, quotes_count: int = 10):
    """
    통합 종목 검색:
    - 국내: KIS + pykrx 기반 search_korean_stocks()
    - 해외: Yahoo Finance 검색 API
    반환: (results, translated_query)
      results: [{symbol, name, exchange, region}, ...]
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    translated = translate_to_english(query)
    results = []

    # 1) 국내 종목 검색 (한글/숫자 코드 위주)
    try:
        kr_results = search_korean_stocks(query, limit=quotes_count)
        results.extend(kr_results)
    except Exception:
        # KIS/pykrx 쪽에서 에러가 나더라도 미국 검색은 계속 진행
        pass

    # 2) 미국/해외 종목 – Yahoo Finance
    for q in [query, translated]:
        if not q:
            continue
        url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {
            "q": q,
            "quotesCount": quotes_count,
            "newsCount": 0,
            "lang": "en-US",
            "region": "US",
        }
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            r.raise_for_status()
            quotes = r.json().get("quotes", [])
            for item in quotes:
                results.append(
                    {
                        "symbol": item.get("symbol"),
                        "name": item.get("shortname") or item.get("longname"),
                        "exchange": item.get("exchDisp"),
                        "region": item.get("region"),
                    }
                )
        except Exception:
            continue

    # 3) 심볼 + region 기준으로 중복 제거
    seen = set()
    deduped = []
    for r in results:
        key = (r.get("symbol"), r.get("region"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    return deduped, translated

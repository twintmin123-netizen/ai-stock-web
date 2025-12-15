"""
News ranking and filtering utility.
Implements 'Job 2: News Directness Filtering + Summary Connection'.
"""
from typing import List, Dict, Any

# Constants for scoring
SCORE_TICKER_MATCH = 60
SCORE_COMPANY_MATCH = 50
SCORE_TRUSTED_DOMAIN = 10
SCORE_KEYWORD_MATCH = 15
SCORE_EXCLUSION = -40
SCORE_MACRO = -30

DIRECT_NEWS_THRESHOLD = 60
INDIRECT_NEWS_THRESHOLD = 30

TRUSTED_DOMAINS = [
    "finance.yahoo.com", "reuters.com", "bloomberg.com", "wsj.com", "cnbc.com", 
    "marketwatch.com", "barrons.com", "investing.com", "hankyung.com", "mk.co.kr", 
    "sedaily.com", "mt.co.kr"
]

DIRECT_KEYWORDS = [
    "rating", "target price", "upgrade", "downgrade", "earnings", "revenue", 
    "profit", "sales", "launch", "product", "lawsuit", "regulation", "approval", 
    "fda", "split", "dividend", "buyback", "merger", "acquisition",
    "실적", "영업이익", "매출", "목표가", "투자의견", "상향", "하향", "출시", 
    "공급", "계약", "수주", "합병", "인수", "소송", "규제", "승인"
]

MACRO_KEYWORDS = [
    "fed", "federal reserve", "cpi", "inflation", "rate hike", "interest rate", 
    "nasdaq", "s&p 500", "dow jones", "market outlook", 
    "연준", "금리", "물가", "인플레이션", "지수", "증시", "코스피", "코스닥"
]

def calculate_news_directness_score(item: Dict[str, Any], ticker: str, company_name: str) -> int:
    """
    Calculate directness score (0-100) for a news item.
    
    Rules:
    (1) Ticker exact match: +60
    (2) Company name match: +50
    (3) Trusted domain: +10
    (4) Event keywords: +15
    (5) Other stock focus (without target stock): -40
    (6) Macro focus (without target stock): -30
    """
    score = 0
    title = (item.get("title") or "").lower()
    description = (item.get("description") or "").lower()
    full_text = f"{title} {description}"
    url = (item.get("link") or "").lower()
    
    ticker_clean = ticker.split('.')[0].lower() # Remove .KS/.KQ for matching
    company_clean = company_name.lower().replace("inc.", "").replace("corp.", "").strip()
    
    # 1. Ticker match
    if ticker_clean in full_text.split(): # Exact word match preferred
        score += SCORE_TICKER_MATCH
    elif ticker_clean in full_text:
        score += SCORE_TICKER_MATCH
        
    # 2. Company Name match
    if company_clean in full_text:
        score += SCORE_COMPANY_MATCH
        
    # 3. Trusted Domain
    if any(domain in url for domain in TRUSTED_DOMAINS):
        score += SCORE_TRUSTED_DOMAIN
        
    # 4. Keyword Match
    if any(kw in full_text for kw in DIRECT_KEYWORDS):
        score += SCORE_KEYWORD_MATCH
        
    # 5. Penalties (Exclusion / Macro) - IF target is missing
    has_target = (ticker_clean in full_text) or (company_clean in full_text)
    
    if not has_target:
        # Check for macro keywords
        if any(mk in full_text for mk in MACRO_KEYWORDS):
            score += SCORE_MACRO
        
        # Check for potential competitor/other mentions (Naive check)
        # In a real system, we'd check NER. Here, simple heuristic.
        score += SCORE_EXCLUSION
        
    return max(0, min(100, score))


def get_news_sentiment(item: Dict[str, Any]) -> str:
    """
    Determine sentiment based on keywords.
    Returns: 'POSITIVE', 'NEGATIVE', 'NEUTRAL'
    """
    title = (item.get("title") or "").lower()
    description = (item.get("description") or "").lower()
    text = f"{title} {description}"
    
    neg_kw = ["downgrade", "sell", "miss", "weak", "concern", "lawsuit", "investigation", "fall", "drop",
              "하향", "매도", "부진", "하락", "감소", "우려", "소송", "조사"]
    pos_kw = ["upgrade", "buy", "beat", "strong", "record", "growth", "jump", "surge", "approval",
              "상향", "매수", "호조", "성장", "급등", "승인", "최고"]
              
    if any(k in text for k in neg_kw):
        return "NEGATIVE"
    if any(k in text for k in pos_kw):
        return "POSITIVE"
    return "NEUTRAL"


def rank_and_filter_news(news_list: List[Dict[str, Any]], ticker: str, company_name: str):
    """
    Rank news and categorize into Direct, Indirect, Irrelevant.
    """
    scored_news = []
    for item in news_list:
        score = calculate_news_directness_score(item, ticker, company_name)
        item["directness_score"] = score
        item["sentiment_label"] = get_news_sentiment(item)
        scored_news.append(item)
        
    # Sort by score descending
    scored_news.sort(key=lambda x: x["directness_score"], reverse=True)
    
    direct = [n for n in scored_news if n["directness_score"] >= DIRECT_NEWS_THRESHOLD]
    indirect = [n for n in scored_news if INDIRECT_NEWS_THRESHOLD <= n["directness_score"] < DIRECT_NEWS_THRESHOLD]
    irrelevant = [n for n in scored_news if n["directness_score"] < INDIRECT_NEWS_THRESHOLD]
    
    return {
        "direct": direct,
        "indirect": indirect,
        "irrelevant": irrelevant,
        "all_scored": scored_news
    }

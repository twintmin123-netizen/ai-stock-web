"""
Enhanced profile classifier with news relevance scoring and detailed action profiles.
"""

from typing import Dict, List, Tuple
import math
from datetime import datetime


def calculate_news_relevance_score(news_item: dict, ticker: str, company_name: str = "") -> float:
    """
    Calculate relevance score for a news article (0-1 scale).
    
    Scoring factors:
    - direct_match: Company name/ticker/brand in title/description
    - event_strength: Price-impacting events (earnings, product launch, lawsuit, etc.)
    - source_quality: Penalty for low-quality "theme stock listing" articles
    - recency: Boost for recent articles
    
    Args:
        news_item: News article dict with 'title', 'description', 'published_at'
        ticker: Stock ticker
        company_name: Company name for matching
    
    Returns:
        Relevance score (0-1)
    """
    score = 0.0
    title = news_item.get('title', '').lower()
    desc = news_item.get('description', '').lower()
    combined_text = title + " " + desc
    
    # 1. Direct Match (0.4 points)
    direct_keywords = [ticker.lower(), company_name.lower()]
    # Add brand keywords based on company (extensible)
    if '삼성' in company_name or 'samsung' in company_name.lower():
        direct_keywords.extend(['갤럭시', 'galaxy', '삼성전자'])
    
    if any(kw in combined_text for kw in direct_keywords if kw):
        score += 0.4
    
    # 2. Event Strength (0.3 points)
    strong_events = ['실적', '수주', '출시', '신제품', 'earnings', 'launch', 'contract',
                     '합병', 'merger', '인수', 'acquisition', '소송', 'lawsuit',
                     '규제', 'regulation', '승인', 'approval']
    if any(event in combined_text for event in strong_events):
        score += 0.3
    
    # 3. Source Quality (-0.3 penalty for low quality)
    low_quality_patterns = ['관련주', '껑충껑충', '봄날의', '신바람', '테마주']
    if any(pattern in title for pattern in low_quality_patterns):
        # Check if it's just a stock listing article
        stock_count = combined_text.count('·') + combined_text.count(',')
        if stock_count > 5:  # Lists many stocks
            score -= 0.3
    
    # 4. Recency (0.2 points for very recent, 0.1 for recent)
    try:
        pub_date_str = news_item.get('published_at', '')
        if pub_date_str:
            # Parse date (assumes format like "Sat, 13 Dec 2025 22:00:00 +0900")
            from dateutil import parser
            pub_date = parser.parse(pub_date_str)
            now = datetime.now(pub_date.tzinfo)
            hours_ago = (now - pub_date).total_seconds() / 3600
            
            if hours_ago < 24:
                score += 0.2
            elif hours_ago < 72:
                score += 0.1
    except:
        pass  # Parsing failed, skip recency bonus
    
    # Normalize to 0-1
    return max(0.0, min(1.0, score))


def generate_semantic_flags(
    ticker: str,
    ret_1w: float,
    ret_1m: float,
    ret_3m: float,
    rsi: float,
    volatility: float,
    pe: float = None,
    roe: float = None,
    news_list: list = None,
    vix_or_vkospi: float = None,
    is_korean: bool = False,
    company_name: str = ""
) -> Tuple[List[str], Dict]:
    """
    Generate semantic flags and news analysis from stock features.
    
    Returns:
        (flags_list, news_analysis_dict)
    """
    flags = []
    
    # --- 1. TREND FLAGS ---
    if ret_3m > 20:
        flags.append("TREND_UP_STRONG")
    elif ret_3m < -15:
        flags.append("TREND_DOWN")
    elif -5 < ret_3m < 5:
        flags.append("RANGE_BOUND")
    
    # --- 2. MOMENTUM FLAGS ---
    if ret_1m > 15:
        flags.append("MOMENTUM_SPIKE")
        flags.append("SPIKE_UP")
    elif ret_1m > 5:
        flags.append("MOMENTUM_UP")
    elif ret_1m < -15:
        flags.append("MOMENTUM_DOWN")
        flags.append("SPIKE_DOWN")
    elif ret_1m < -5:
        flags.append("MOMENTUM_DOWN")
    
    # --- 3. TECHNICAL FLAGS (RSI) ---
    if rsi >= 80:
        flags.append("TECH_EXTREME_OVERBOUGHT")
    elif rsi >= 70:
        flags.append("TECH_OVERBOUGHT")
    elif rsi <= 20:
        flags.append("TECH_EXTREME_OVERSOLD")
    elif rsi <= 30:
        flags.append("TECH_OVERSOLD")
    
    # --- 4. VOLATILITY FLAGS ---
    if volatility > 50:
        flags.append("VOLATILITY_HIGH")
    elif volatility < 20:
        flags.append("VOLATILITY_LOW")
    
    # --- 5. VALUATION FLAGS ---
    if pe is not None and not math.isnan(pe):
        if is_korean:
            if pe > 25:
                flags.append("VALUATION_EXPENSIVE")
            elif pe < 8:
                flags.append("VALUATION_CHEAP")
        else:  # US
            if pe > 35:
                flags.append("VALUATION_EXPENSIVE")
            elif pe < 12:
                flags.append("VALUATION_CHEAP")
    
    # --- 6. QUALITY FLAGS ---
    if roe is not None and not math.isnan(roe):
        roe_pct = roe * 100 if roe < 1.0 else roe
        if roe_pct > 20:
            flags.append("QUALITY_STRONG")
        elif roe_pct < 5:
            flags.append("QUALITY_WEAK")
    
    # --- 7. MARKET RISK FLAGS ---
    if vix_or_vkospi is not None and not math.isnan(vix_or_vkospi):
        if vix_or_vkospi > 25:
            flags.append("MARKET_RISK_OFF")
        elif vix_or_vkospi < 15:
            flags.append("MARKET_RISK_ON")
    
    # --- 8. NEWS ANALYSIS with RELEVANCE SCORING ---
    news_analysis = {
        "top_news": None,
        "relevance_score": 0.0,
        "is_relevant": False,
        "sentiment": "NEUTRAL"
    }
    
    if news_list and len(news_list) > 0:
        # Score all news
        scored_news = []
        for news in news_list:
            relevance = calculate_news_relevance_score(news, ticker, company_name)
            scored_news.append((news, relevance))
        
        # Sort by relevance
        scored_news.sort(key=lambda x: x[1], reverse=True)
        top_news, top_score = scored_news[0]
        
        news_analysis["top_news"] = top_news
        news_analysis["relevance_score"] = top_score
        news_analysis["is_relevant"] = top_score >= 0.3  # Threshold
        
        # Sentiment analysis (simple keyword-based)
        pos_keywords = ["surge", "jump", "record", "beat", "buy", "upgrade", "growth", "launch",
                       "상승", "급등", "호재", "성장", "최고", "돌파"]
        neg_keywords = ["drop", "fall", "miss", "sell", "downgrade", "risk", "concern", "loss",
                       "하락", "급락", "악재", "손실", "우려"]
        
        if top_score >= 0.3:  # Only for relevant news
            title_text = top_news.get('title', '').lower()
            pos_count = sum(1 for k in pos_keywords if k in title_text)
            neg_count = sum(1 for k in neg_keywords if k in title_text)
            
            if pos_count > neg_count and pos_count >= 1:
                flags.append("NEWS_POSITIVE_EVENT")
                news_analysis["sentiment"] = "POSITIVE"
            elif neg_count > pos_count and neg_count >= 1:
                flags.append("NEWS_NEGATIVE_EVENT")
                news_analysis["sentiment"] = "NEGATIVE"
            else:
                flags.append("NEWS_MIXED_OR_THIN")
                news_analysis["sentiment"] = "NEUTRAL"
        else:
            # Low relevance
            flags.append("NEWS_LOW_RELEVANCE")
            news_analysis["sentiment"] = "LOW_RELEVANCE"
    else:
        flags.append("NEWS_MIXED_OR_THIN")
    
    # Ensure minimum 3 flags
    if len(flags) < 3:
        flags.append("NEUTRAL_SIGNAL")
    
    return flags, news_analysis


def get_action_profile(flags: List[str], rsi: float = None) -> Dict[str, any]:
    """
    Determine comprehensive action profile from flags.
    
    Returns detailed execution guidance including:
    - decision_action: The investment decision (buy/sell/hold)
    - execution_style: How to execute (gradual, wait-for-pullback, etc.)
    - position_sizing: Suggested position size
    - invalidators: Conditions that would invalidate the strategy
    - take_profit_rule: When to take profits
    - stop_rule: When to stop out
    """
    flag_set = set(flags)
    
    # EXTREME OVERBOUGHT: Pause new entries
    if "TECH_EXTREME_OVERBOUGHT" in flag_set:
        return {
            "id": "EXTREME_OVERBOUGHT_PAUSE",
            "decision_action": "현상 유지",
            "execution_style": "신규 진입 보류, 기존 보유분 일부 차익실현 검토",
            "position_sizing": "축소 권장",
            "invalidators": ["RSI가 70 아래로 복귀"],
            "take_profit_rule": "현 수준(RSI 80+)에서 일부 차익실현",
            "stop_rule": "단기 지지선(MA5) 이탈 시 추가 축소",
            "summary": "극심한 과열 구간으로 신규 진입을 보류하고 차익실현을 검토해야 합니다.",
            "risk_note": "RSI 80 이상은 단기 조정 확률이 매우 높습니다.",
            "market_condition": "과열"
        }
    
    # 1. MOMENTUM_CHASER
    if ("TREND_UP_STRONG" in flag_set and 
        ("MOMENTUM_SPIKE" in flag_set or "MOMENTUM_UP" in flag_set) and
        "VALUATION_EXPENSIVE" not in flag_set and
        "TECH_EXTREME_OVERBOUGHT" not in flag_set):
        return {
            "id": "MOMENTUM_CHASER",
            "decision_action": "매수",
            "execution_style": "추세 추종, 분할 매수",
            "position_sizing": "보통",
            "invalidators": ["단기 이평선(MA20) 이탈", "RSI 80 돌파"],
            "take_profit_rule": "RSI 75+ 도달 시 일부 차익",
            "stop_rule": "MA20 하향 이탈 시 50% 축소",
            "summary": "강력한 상승 추세와 모멘텀이 확인되어 추세 추종 전략이 유효합니다.",
            "risk_note": "급등 이후 조정 리스크가 있으니 분할 매수를 권장합니다.",
            "market_condition": "상승"
        }
    
    # 2. VALUE_RECOVERY
    if (("TECH_OVERSOLD" in flag_set or "VALUATION_CHEAP" in flag_set) and
        "QUALITY_WEAK" not in flag_set and
        "TREND_DOWN" not in flag_set):
        return {
            "id": "VALUE_RECOVERY",
            "decision_action": "매수",
            "execution_style": "분할 매수, 평단가 낮추기",
            "position_sizing": "보통",
            "invalidators": ["추가 하락 -10% 이상", "재무 악화 뉴스"],
            "take_profit_rule": "RSI 60+ 도달 시 일부 차익",
            "stop_rule": "최근 저점 -5% 이탈 시 손절",
            "summary": "저평가 또는 과매도 국면에서 반등 가능성이 포착됩니다.",
            "risk_note": "바닥 확인이 필요하며, 낙폭 과대 리스크가 존재합니다.",
            "market_condition": "저평가"
        }
    
    # 3. QUALITY_COMPOUNDER
    if ("QUALITY_STRONG" in flag_set and
        "VOLATILITY_LOW" in flag_set and
        "TREND_DOWN" not in flag_set):
        return {
            "id": "QUALITY_COMPOUNDER",
            "decision_action": "매수",
            "execution_style": "장기 보유, 조정 시 추가 매수",
            "position_sizing": "크게",
            "invalidators": ["ROE 15% 미만 하락", "산업 구조 악화"],
            "take_profit_rule": "목표 수익률 도달 또는 밸류에이션 과열 시",
            "stop_rule": "펀더멘털 훼손 시에만 고려",
            "summary": "우수한 펀더멘털과 낮은 변동성으로 장기 성장이 기대됩니다.",
            "risk_note": "시장 급락 시에도 기업 본질은 건전하나, 단기 주가 조정은 발생 가능합니다.",
            "market_condition": "안정"
        }
    
    # 4. RISK_OFF_DEFENSIVE
    if ("MARKET_RISK_OFF" in flag_set and
        ("VOLATILITY_LOW" in flag_set or "QUALITY_STRONG" in flag_set)):
        return {
            "id": "RISK_OFF_DEFENSIVE",
            "decision_action": "현상 유지",
            "execution_style": "보수적 대기, 소량 보유",
            "position_sizing": "작게",
            "invalidators": ["시장 변동성 완화 (VIX < 20)"],
            "take_profit_rule": "단기 반등 시 일부 차익",
            "stop_rule": "시장 추가 악화 시 추가 축소",
            "summary": "시장 불확실성이 높은 상황에서 방어적 움직임을 보이고 있습니다.",
            "risk_note": "전반적 하락장에서는 개별 종목 강세도 제한적일 수 있습니다.",
            "market_condition": "불확실"
        }
    
    # 5. EVENT_DRIVEN
    if (("NEWS_POSITIVE_EVENT" in flag_set or "NEWS_NEGATIVE_EVENT" in flag_set) and
        ("VOLATILITY_HIGH" in flag_set or "SPIKE_UP" in flag_set or "SPIKE_DOWN" in flag_set)):
        return {
            "id": "EVENT_DRIVEN",
            "decision_action": "기민한 대응 필요",
            "execution_style": "뉴스 추세 확인 후 단기 대응",
            "position_sizing": "작게 (높은 변동성)",
            "invalidators": ["뉴스 영향 소멸", "변동성 정상화"],
            "take_profit_rule": "뉴스 효과 피크 시 빠른 차익",
            "stop_rule": "뉴스 반전 시 즉시 청산",
            "summary": "뉴스/이벤트로 인한 단기 변동성이 확대되고 있어 기민한 대응이 요구됩니다.",
            "risk_note": "뉴스 기반 급등/급락은 되돌림이 빠를 수 있습니다.",
            "market_condition": "이벤트"
        }
    
    # Legacy: Overbought (not extreme)
    if "TECH_OVERBOUGHT" in flag_set and "TECH_EXTREME_OVERBOUGHT" not in flag_set:
        return {
            "id": "OVERBOUGHT_CAUTIOUS",
            "decision_action": "매수",
            "execution_style": "눌림목 대기 또는 소량 분할",
            "position_sizing": "작게",
            "invalidators": ["RSI 80 돌파"],
            "take_profit_rule": "RSI 75+ 시 일부 차익",
            "stop_rule": "단기 지지선 이탈 시 축소",
            "summary": "단기 과열 신호가 나타나므로 신중한 접근이 필요합니다.",
            "risk_note": "RSI 70+ 구간은 조정 가능성이 높습니다.",
            "market_condition": "과열"
        }
    
    # 6. NEUTRAL_WAIT (Default)
    return {
        "id": "NEUTRAL_WAIT",
        "decision_action": "관망",
        "execution_style": "추가 신호 확인 후 판단",
        "position_sizing": "보통",
        "invalidators": ["명확한 추세 형성"],
        "take_profit_rule": "N/A",
        "stop_rule": "N/A",
        "summary": "뚜렷한 방향성이 보이지 않아 혼조세 양상입니다.",
        "risk_note": "추세 불명확 구간에서는 성급한 진입이 위험할 수 있습니다.",
        "market_condition": "중립"
    }


def format_news_connection(news_analysis: Dict, flags: List[str]) -> str:
    """
    Format news connection text for summary field (MANDATORY).
    
    Args:
        news_analysis: News analysis dict from generate_semantic_flags
        flags: List of flags
    
    Returns:
        Formatted news connection string
    """
    if not news_analysis.get("is_relevant") or "NEWS_LOW_RELEVANCE" in flags:
        return "특별한 뉴스 이슈가 부재하여 수급과 차트 중심 대응이 필요합니다."
    
    top_news = news_analysis.get("top_news")
    if not top_news:
        return "뉴스 근거가 부족하여 기술적 분석 위주로 판단합니다."
    
    title = top_news.get('title', '')
    # Trim title if too long
    if len(title) > 60:
        title = title[:57] + "..."
    
    sentiment = news_analysis.get("sentiment", "NEUTRAL")
    
    if sentiment == "POSITIVE":
        return f"'{title}' 등 긍정적 뉴스가 주가에 호재로 작용하고 있습니다."
    elif sentiment == "NEGATIVE":
        return f"'{title}' 등 부정적 이슈가 단기 부담 요인으로 작용하고 있습니다."
    else:
        return f"최근 '{title}' 등의 뉴스를 주시할 필요가 있습니다."

"""
Intent Classification System for Financial Chatbot

Defines intent types and action schemas for the 4-role chatbot:
1. Information Retrieval (정보제공형)
2. Navigational (탐색형)
3. Transactional (업무처리형)
4. Analytical (분석형)
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel


class IntentType(str, Enum):
    """Intent categories for chatbot interactions"""
    # Information Retrieval
    INFO_GENERAL = "info_general"  # General Q&A about finance
    INFO_TERM = "info_term"  # Financial term explanation
    
    # Navigational
    NAV_TAB = "nav_tab"  # Switch tabs (Dashboard, Analytics)
    NAV_MARKET = "nav_market"  # Navigate to market section
    NAV_PORTFOLIO = "nav_portfolio"  # Navigate to portfolio
    
    # Transactional
    TRANS_ANALYZE = "trans_analyze"  # Run stock analysis
    TRANS_PORTFOLIO_ADD = "trans_portfolio_add"  # Add to portfolio
    TRANS_PORTFOLIO_REMOVE = "trans_portfolio_remove"  # Remove from portfolio
    TRANS_REPORT = "trans_report"  # Generate PDF report
    
    # Analytical
    ANAL_WHY = "anal_why"  # Explain reasoning (Why is it a buy?)
    ANAL_COMPARE = "anal_compare"  # Compare two stocks
    ANAL_RISK = "anal_risk"  # Explain risks
    ANAL_OUTLOOK = "anal_outlook"  # Explain outlook
    
    # Unknown
    UNKNOWN = "unknown"


class ActionType(str, Enum):
    """Action types that the frontend can execute"""
    NAVIGATE = "navigate"  # Navigate to a specific tab/section
    SEARCH_STOCK = "search_stock"  # Search for a stock
    RUN_ANALYSIS = "run_analysis"  # Trigger stock analysis
    ADD_TO_PORTFOLIO = "add_to_portfolio"  # Add stock to portfolio
    REMOVE_FROM_PORTFOLIO = "remove_from_portfolio"  # Remove stock from portfolio
    GENERATE_REPORT = "generate_report"  # Generate PDF report
    SCROLL_TO = "scroll_to"  # Scroll to specific element
    NONE = "none"  # No action needed


class ChatAction(BaseModel):
    """Action payload for frontend execution"""
    type: ActionType
    target: Optional[str] = None  # Tab name, ticker, element ID, etc.
    params: Optional[Dict[str, Any]] = None  # Additional parameters


class IntentClassification(BaseModel):
    """Result of intent classification"""
    intent: IntentType
    confidence: float  # 0.0 to 1.0
    entities: Dict[str, Any] = {}  # Extracted entities (ticker, company name, etc.)
    action: Optional[ChatAction] = None


# Intent Keywords Mapping
INTENT_KEYWORDS = {
    # Information
    IntentType.INFO_TERM: [
        "뭐야", "무엇", "설명", "알려줘", "의미", "이란", "란", "어때",
        "RSI", "PER", "PBR", "ROE", "부채비율", "영업이익률", "매출", "성장률",
        "what is", "explain", "meaning", "how about"
    ],
    IntentType.INFO_GENERAL: [
        "어떻게", "방법", "추천", "좋은", "나쁜",
        "how to", "recommend", "good", "bad"
    ],
    
    # Navigational
    IntentType.NAV_TAB: [
        "대시보드", "분석", "포트폴리오", "보여줘", "가자", "이동", "가줘", "가줄래",
        "탭", "로그", "뉴스", "차트", "주가",
        "dashboard", "analytics", "portfolio", "show", "go to", "tab", "log", "news", "chart"
    ],
    IntentType.NAV_MARKET: [
        "시장", "지표", "미국", "한국", "코스피", "코스닥",
        "market", "indicator", "us", "korea", "kospi", "kosdaq"
    ],
    
    # Transactional
    IntentType.TRANS_ANALYZE: [
        "분석", "조회", "검색", "찾아", "확인", "해줘", "해봐",
        "analyze", "check", "search", "find", "look up"
    ],
    IntentType.TRANS_PORTFOLIO_ADD: [
        "추가", "담기", "넣어", "넣어줘", "넣어줄래", "포트폴리오",
        "add", "include", "put in", "put"
    ],
    IntentType.TRANS_PORTFOLIO_REMOVE: [
        "제거", "삭제", "빼", "지워", "빼줘",
        "remove", "delete", "take out"
    ],
    IntentType.TRANS_REPORT: [
        "리포트", "보고서", "PDF", "다운로드", "저장",
        "report", "download", "save"
    ],
    
    # Analytical
    IntentType.ANAL_WHY: [
        "왜", "이유", "근거", "설명해줘",
        "why", "reason", "explain"
    ],
    IntentType.ANAL_COMPARE: [
        "비교", "vs", "차이", "어느게",
        "compare", "versus", "difference", "which"
    ],
    IntentType.ANAL_RISK: [
        "위험", "리스크", "위험요소", "주의",
        "risk", "danger", "caution"
    ],
    IntentType.ANAL_OUTLOOK: [
        "전망", "미래", "앞으로", "예상",
        "outlook", "future", "forecast", "prediction"
    ]
}


# Stock name/ticker patterns
STOCK_NAME_MAPPING = {
    # Korean companies
    "삼성전자": "005930",
    "삼성": "005930",
    "SK하이닉스": "000660",
    "하이닉스": "000660",
    "네이버": "035420",
    "카카오": "035720",
    "현대차": "005380",
    "기아": "000270",
    "LG에너지솔루션": "373220",
    "LG화학": "051910",
    "포스코": "005490",
    "KB금융": "105560",
    "신한지주": "055550",
    
    # US companies (Korean names)
    "애플": "AAPL",
    "테슬라": "TSLA",
    "마이크로소프트": "MSFT",
    "엔비디아": "NVDA",
    "아마존": "AMZN",
    "구글": "GOOGL",
    "메타": "META",
    "넷플릭스": "NFLX",
    
    # US companies (English names - lowercase for matching)
    "apple": "AAPL",
    "tesla": "TSLA",
    "microsoft": "MSFT",
    "nvidia": "NVDA",
    "amazon": "AMZN",
    "google": "GOOGL",
    "meta": "META",
    "netflix": "NFLX",
}


def extract_ticker(text: str) -> Optional[str]:
    """
    Extract stock ticker from user message
    
    Args:
        text: User message
        
    Returns:
        Ticker symbol or None
    """
    text_lower = text.lower().strip()
    
    # Check for company names (both Korean and English)
    for name, ticker in STOCK_NAME_MAPPING.items():
        if name.lower() in text_lower:
            return ticker
    
    # Check for US tickers (uppercase letters, 1-5 chars)
    import re
    us_ticker_match = re.search(r'\b([A-Z]{1,5})\b', text)
    if us_ticker_match:
        return us_ticker_match.group(1)
    
    # Check for Korean tickers (6-digit numbers)
    kr_ticker_match = re.search(r'\b(\d{6})\b', text)
    if kr_ticker_match:
        return kr_ticker_match.group(1)
    
    return None


def classify_intent(user_message: str, context: Optional[str] = None) -> IntentClassification:
    """
    Classify user intent based on message content
    
    Args:
        user_message: User's message
        context: Current context (e.g., current stock being analyzed)
        
    Returns:
        IntentClassification with intent type, confidence, and action
    """
    msg_lower = user_message.lower().strip()
    
    # Extract ticker if present
    ticker = extract_ticker(user_message)
    entities = {}
    if ticker:
        entities["ticker"] = ticker
    
    # Score each intent based on keyword matches
    intent_scores: Dict[IntentType, float] = {intent: 0.0 for intent in IntentType}
    
    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in msg_lower:
                intent_scores[intent] += 1.0
    
    # Boost TRANS_ANALYZE score if ticker is present
    # This ensures "애플 분석해줘" is classified as TRANS_ANALYZE
    if ticker and intent_scores[IntentType.TRANS_ANALYZE] > 0:
        intent_scores[IntentType.TRANS_ANALYZE] *= 2.0  # Double the score
    
    # Normalize scores
    max_score = max(intent_scores.values()) if intent_scores else 0
    if max_score > 0:
        for intent in intent_scores:
            intent_scores[intent] /= max_score
    
    # Get top intent
    top_intent = max(intent_scores.items(), key=lambda x: x[1])
    intent_type, confidence = top_intent
    
    # Debug logging
    print(f"🔍 Intent Classification Debug:")
    print(f"   User message: {user_message}")
    print(f"   Extracted ticker: {ticker}")
    print(f"   Top 3 intents: {sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)[:3]}")
    print(f"   Selected intent: {intent_type} (confidence: {confidence:.2f})")
    
    # If confidence is too low, mark as unknown
    if confidence < 0.3:
        intent_type = IntentType.UNKNOWN
        confidence = 1.0
    
    # Generate action based on intent
    action = _generate_action(intent_type, entities, msg_lower, context)
    
    print(f"   Generated action: {action}")
    
    return IntentClassification(
        intent=intent_type,
        confidence=confidence,
        entities=entities,
        action=action
    )


def _generate_action(
    intent: IntentType,
    entities: Dict[str, Any],
    message: str,
    context: Optional[str]
) -> Optional[ChatAction]:
    """
    Generate frontend action based on intent
    
    Args:
        intent: Classified intent type
        entities: Extracted entities
        message: User message (lowercase)
        context: Current context
        
    Returns:
        ChatAction or None
    """
    ticker = entities.get("ticker")
    
    # Navigational intents
    if intent == IntentType.NAV_TAB:
        if "대시보드" in message or "dashboard" in message:
            return ChatAction(type=ActionType.NAVIGATE, target="dashboard")
        elif "포트폴리오" in message or "portfolio" in message:
            return ChatAction(type=ActionType.NAVIGATE, target="dashboard", params={"scroll_to": "portfolio"})
        elif "로그" in message or "log" in message:
            return ChatAction(type=ActionType.NAVIGATE, target="analytics", params={"sub_tab": "logs"})
        elif "뉴스" in message or "news" in message:
            return ChatAction(type=ActionType.NAVIGATE, target="analytics", params={"sub_tab": "news"})
        elif "차트" in message or "주가" in message or "chart" in message:
            return ChatAction(type=ActionType.NAVIGATE, target="analytics", params={"sub_tab": "chart"})
        elif "분석" in message or "analytics" in message:
            return ChatAction(type=ActionType.NAVIGATE, target="analytics")
    
    elif intent == IntentType.NAV_MARKET:
        if "미국" in message or "us" in message:
            return ChatAction(type=ActionType.NAVIGATE, target="dashboard", params={"market": "us"})
        elif "한국" in message or "korea" in message or "국내" in message:
            return ChatAction(type=ActionType.NAVIGATE, target="dashboard", params={"market": "korea"})
    
    # Transactional intents
    elif intent == IntentType.TRANS_ANALYZE:
        if ticker:
            return ChatAction(type=ActionType.RUN_ANALYSIS, target=ticker)
    
    elif intent == IntentType.TRANS_PORTFOLIO_ADD:
        if ticker:
            return ChatAction(type=ActionType.ADD_TO_PORTFOLIO, target=ticker)
    
    elif intent == IntentType.TRANS_PORTFOLIO_REMOVE:
        if ticker:
            return ChatAction(type=ActionType.REMOVE_FROM_PORTFOLIO, target=ticker)
    
    elif intent == IntentType.TRANS_REPORT:
        # Generate report for current stock in context
        return ChatAction(type=ActionType.GENERATE_REPORT)
    
    # No action needed for info/analytical intents (handled by LLM response)
    return None

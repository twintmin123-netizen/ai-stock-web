"""
Flags generation engine.
Implements 'Job 1: Flags Generation & Injection'.
Calculates semantic flags based on technicals, fundamentals, and news.
"""
from typing import List, Dict, Any, Optional
import math
from utils.common import to_number

# Threshold Constants
RSI_OVERBOUGHT = 70.0
RSI_EXTREME_OVERBOUGHT = 80.0
RSI_OVERSOLD = 30.0
RSI_EXTREME_OVERSOLD = 20.0

PE_HIGH = 35.0  # Common
PB_HIGH = 5.0   # Common
RET_3M_SPIKE = 30.0 # 30% jump in 3m

def calculate_flags(
    ticker: str, 
    rsi: Optional[float], 
    ret_3m: Optional[float], 
    volatility: Optional[float],
    pe: Optional[float],
    pbr: Optional[float],
    news_analysis_result: Dict[str, Any]
) -> List[str]:
    """
    Generate normalized semantic flags.
    Defensive: Handles missing data gracefully.
    """
    flags = []
    
    # Clean inputs
    rsi = to_number(rsi) if rsi is not None else math.nan
    ret_3m = to_number(ret_3m) if ret_3m is not None else math.nan
    volatility = to_number(volatility) if volatility is not None else math.nan
    pe = to_number(pe) if pe is not None else math.nan
    pbr = to_number(pbr) if pbr is not None else math.nan
    
    # 1. Technical Flags (RSI)
    if not math.isnan(rsi):
        if rsi >= RSI_EXTREME_OVERBOUGHT:
            flags.append("TECH_EXTREME_OVERBOUGHT")
        elif rsi >= RSI_OVERBOUGHT:
            flags.append("TECH_OVERBOUGHT")
        elif rsi <= RSI_EXTREME_OVERSOLD:
            flags.append("TECH_EXTREME_OVERSOLD")
        elif rsi <= RSI_OVERSOLD:
            flags.append("TECH_OVERSOLD")
            
    # 2. Momentum Flags
    if not math.isnan(ret_3m):
        if ret_3m >= RET_3M_SPIKE:
            # Check RSI to differentiate Overbought vs Strong Momentum
            if math.isnan(rsi) or rsi < RSI_OVERBOUGHT:
                flags.append("MOMENTUM_STRONG")
            else:
                pass # Already flagged as Overbought
    
    # 3. Valuation Flags
    if not math.isnan(pe):
        if pe >= PE_HIGH:
            flags.append("VALUATION_HIGH")
            
    if not math.isnan(pbr):
        if pbr >= PB_HIGH:
            flags.append("VALUATION_STRETCHED")
            
    # 4. Volatility Flags
    if not math.isnan(volatility):
        if volatility >= 60.0:
            flags.append("VOLATILITY_HIGH")
        elif volatility <= 15.0:
            flags.append("VOLATILITY_LOW")

    # 5. News Flags (Based on Ranker Result)
    direct_news = news_analysis_result.get("direct", [])
    
    if len(direct_news) > 0:
        # Check sentiment
        sentiments = [n.get("sentiment_label", "NEUTRAL") for n in direct_news[:3]] # Top 3
        if "NEGATIVE" in sentiments and "POSITIVE" in sentiments:
            flags.append("NEWS_MIXED_SENTIMENT")
        elif "NEGATIVE" in sentiments:
            flags.append("NEWS_NEGATIVE_OVERHANG")
        elif "POSITIVE" in sentiments:
            flags.append("NEWS_POSITIVE")
    else:
        # 0 direct news
        flags.append("NEWS_LOW_DIRECT_IMPACT")
        
    return list(set(flags)) # Dedup

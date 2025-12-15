"""
Sector Data Fetcher
Retrieves sector ETF performance data
"""
import yfinance as yf
import pandas as pd
from typing import Dict, Any


def fetch_sector_etf_data(sector_etf: str, spy_benchmark: bool = True) -> Dict[str, Any]:
    """
    Fetch sector ETF performance metrics.
    
    Args:
        sector_etf: Sector ETF ticker (e.g., 'XLK')
        spy_benchmark: Whether to calculate relative performance vs SPY
        
    Returns:
        dict with returns, volatility, and relative performance
    """
    try:
        # Fetch sector ETF data
        etf = yf.Ticker(sector_etf)
        hist = etf.history(period="3mo")
        
        if hist.empty:
            return None
        
        # Calculate returns
        ret_1w = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-5]) - 1) * 100 if len(hist) >= 5 else 0
        ret_1m = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-21]) - 1) * 100 if len(hist) >= 21 else 0
        ret_3m = ((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100 if len(hist) >= 63 else 0
        
        # Calculate volatility (annualized)
        returns = hist['Close'].pct_change().dropna()
        volatility = returns.std() * (252 ** 0.5) * 100  # Annualized %
        
        result = {
            "ticker": sector_etf,
            "ret_1w": ret_1w,
            "ret_1m": ret_1m,
            "ret_3m": ret_3m,
            "volatility": volatility
        }
        
        # Calculate relative performance vs SPY
        if spy_benchmark:
            spy = yf.Ticker("SPY")
            spy_hist = spy.history(period="3mo")
            
            if not spy_hist.empty:
                spy_ret_1w = ((spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[-5]) - 1) * 100 if len(spy_hist) >= 5 else 0
                spy_ret_1m = ((spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[-21]) - 1) * 100 if len(spy_hist) >= 21 else 0
                spy_ret_3m = ((spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[0]) - 1) * 100 if len(spy_hist) >= 63 else 0
                
                result["relative_1w"] = ret_1w - spy_ret_1w
                result["relative_1m"] = ret_1m - spy_ret_1m
                result["relative_3m"] = ret_3m - spy_ret_3m
        
        return result
        
    except Exception as e:
        print(f"⚠️ Error fetching sector ETF data for {sector_etf}: {e}")
        return None


def calculate_sector_score(sector_data: Dict[str, Any]) -> float:
    """
    Calculate sector score (0-100) based on performance and volatility.
    
    Logic:
    - Base score from relative returns (weighted: 1M=50%, 3M=30%, 1W=20%)
    - Volatility penalty (higher vol = lower score)
    
    Args:
        sector_data: Dict from fetch_sector_etf_data
        
    Returns:
        Score 0-100
    """
    if not sector_data:
        return 50.0  # Neutral if no data
    
    # Extract relative returns (default to 0 if not available)
    rel_1w = sector_data.get("relative_1w", 0)
    rel_1m = sector_data.get("relative_1m", 0)
    rel_3m = sector_data.get("relative_3m", 0)
    vol = sector_data.get("volatility", 20)  # Default to market avg ~20%
    
    # Weighted relative performance (-10% to +10% typical range)
    # Map to ~40-60 score range
    perf_score = 50 + (0.2 * rel_1w + 0.5 * rel_1m + 0.3 * rel_3m) * 2  # Scale by 2
    
    # Volatility adjustment (lower vol = better)
    # Typical range: 15-30% annualized
    # Penalty: -5 points if vol > 30%, +5 if vol < 15%
    vol_adjustment = 0
    if vol > 30:
        vol_adjustment = -5
    elif vol < 15:
        vol_adjustment = 5
    
    final_score = perf_score + vol_adjustment
    
    # Clamp to 0-100
    return max(0, min(100, final_score))

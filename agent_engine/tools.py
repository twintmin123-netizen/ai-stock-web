"""
CrewAI Tools - Wrapping existing utility functions
"""

from crewai.tools import BaseTool
from typing import Dict, Any, List, Type
from pydantic import BaseModel, Field
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.finance_data import (
    fetch_price_history, 
    fetch_fundamentals,
    compute_returns,
    compute_rsi,
    estimate_3m_outlook
)
from utils.market_indicators import get_market_indicators
from utils.common import fetch_news, get_company_name
from utils.scoring import (
    compute_market_score,
    compute_korea_market_score,
    compute_company_score,
    compute_outlook_score,
    decide_action
)


# Helper function
def period_ret(df) -> float:
    """Calculate period return from DataFrame."""
    import math
    if df is None or df.empty:
        return math.nan
    try:
        first = float(df["close"].iloc[0])
        last = float(df["close"].iloc[-1])
        if first == 0:
            return math.nan
        return (last / first - 1.0) * 100.0
    except Exception:
        return math.nan


# Input schemas for tools
class StockPriceInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol (e.g., 'AAPL', '005930.KS')")

class MarketIndicatorsInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker to determine market context")

class NewsSearchInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")

class FundamentalsInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")



class StockPriceTool(BaseTool):
    name: str = "Stock Price Tool"
    description: str = "Fetch price history for long-term (3Y) and short-term (3M) analysis. Returns comprehensive analysis including trends, volatility, and momentum indicators."
    args_schema: Type[BaseModel] = StockPriceInput
    
    def _run(self, ticker: str) -> str:
        try:
            import numpy as np
            import math
            
            # Fetch BOTH long-term (3Y) and short-term (3M) data
            df_long = fetch_price_history(ticker, period="3y")
            df_short = fetch_price_history(ticker, period="3mo")
            
            if df_short.empty:
                return f"No data found for {ticker}"
            
            current_price = float(df_short["close"].iloc[-1])
            
            # ============================================
            # SHORT-TERM ANALYSIS (3 Months)
            # ============================================
            ret_1w = compute_returns(df_short, 5)
            ret_1m = compute_returns(df_short, 21)
            ret_3m = period_ret(df_short)
            rsi_short = compute_rsi(df_short["close"])
            
            # Calculate short-term volatility (with error handling)
            try:
                short_vol = df_short["close"].pct_change().std() * np.sqrt(252) * 100
                short_volatility = short_vol if not math.isnan(short_vol) else 0.0
            except:
                short_volatility = 0.0
            
            # Detect recent spike/drop
            recent_spike = "없음"
            try:
                if len(df_short) >= 25:
                    last_5_avg = df_short["close"].iloc[-5:].mean()
                    prev_20_avg = df_short["close"].iloc[-25:-5].mean()
                    if not math.isnan(last_5_avg) and not math.isnan(prev_20_avg) and prev_20_avg > 0:
                        change_pct = (last_5_avg / prev_20_avg - 1) * 100
                        if change_pct > 5:
                            recent_spike = f"급등 (+{change_pct:.1f}%)"
                        elif change_pct < -5:
                            recent_spike = f"급락 ({change_pct:.1f}%)"
            except:
                pass
            
            # Format values safely
            def safe_format(value, suffix="%", default="N/A"):
                if math.isnan(value):
                    return default
                return f"{value:.2f}{suffix}"
            
            ret_1w_str = safe_format(ret_1w)
            ret_1m_str = safe_format(ret_1m)
            ret_3m_str = safe_format(ret_3m)
            rsi_short_val = rsi_short if not math.isnan(rsi_short) else 50
            
            rsi_status = ""
            if not math.isnan(rsi_short):
                if rsi_short > 70:
                    rsi_status = " (과매수)"
                elif rsi_short < 30:
                    rsi_status = " (과매도)"
                else:
                    rsi_status = " (중립)"
            
            short_analysis = f"""[단기 분석 (3개월)]
- 1주 수익률: {ret_1w_str}
- 1개월 수익률: {ret_1m_str}
- 3개월 수익률: {ret_3m_str}
- 단기 RSI(14): {safe_format(rsi_short_val, "", "N/A")}{rsi_status}
- 단기 변동성: {short_volatility:.2f}% (연환산)
- 최근 급등/급락: {recent_spike}"""
            
            # ============================================
            # LONG-TERM ANALYSIS (3 Years)
            # ============================================
            if not df_long.empty and len(df_long) >= 200:
                ret_3y = period_ret(df_long)
                
                # 200-day MA
                try:
                    ma_200 = df_long["close"].rolling(window=200).mean().iloc[-1]
                    if not math.isnan(ma_200) and ma_200 > 0:
                        current_vs_ma200 = (current_price / ma_200 - 1) * 100
                        ma_status = "상향" if current_vs_ma200 > 0 else "하향"
                    else:
                        current_vs_ma200 = 0.0
                        ma_status = "불가"
                except:
                    current_vs_ma200 = 0.0
                    ma_status = "불가"
                
                # Long-term trend (try scipy, fallback to simple method)
                annual_trend = 0.0
                trend_direction = "분석 불가"
                try:
                    from scipy import stats
                    if len(df_long) >= 252:
                        x = np.arange(len(df_long))
                        y = df_long["close"].values
                        mask = ~np.isnan(y)
                        if mask.sum() >= 252:
                            slope, _, _, _, _ = stats.linregress(x[mask], y[mask])
                            first_price = y[mask][0]
                            if first_price > 0:
                                annual_trend = (slope * 252 / first_price) * 100
                                if annual_trend > 5:
                                    trend_direction = "상승 추세"
                                elif annual_trend < -5:
                                    trend_direction = "하락 추세"
                                else:
                                    trend_direction = "횡보 추세"
                except ImportError:
                    # Fallback: compare first year avg to last year avg
                    try:
                        if len(df_long) >= 252:
                            first_year = df_long["close"].iloc[:252].mean()
                            last_year = df_long["close"].iloc[-252:].mean()
                            if not math.isnan(first_year) and not math.isnan(last_year) and first_year > 0:
                                annual_trend = (last_year / first_year - 1) * 100
                                if annual_trend > 5:
                                    trend_direction = "상승 추세"
                                elif annual_trend < -5:
                                    trend_direction = "하락 추세"
                                else:
                                    trend_direction = "횡보 추세"
                    except:
                        pass
                except:
                    pass
                
                # Long-term volatility
                try:
                    long_vol = df_long["close"].pct_change().std() * np.sqrt(252) * 100
                    long_volatility = long_vol if not math.isnan(long_vol) else 0.0
                except:
                    long_volatility = 0.0
                
                # Long-term RSI
                try:
                    rsi_long = compute_rsi(df_long["close"])
                    rsi_long_str = safe_format(rsi_long, "", "N/A")
                except:
                    rsi_long_str = "N/A"
                
                long_analysis = f"""
[장기 분석 (3년)]
- 3년 수익률: {safe_format(ret_3y)}
- 장기 추세: {trend_direction} (연간 {annual_trend:.2f}%)
- 200일 이동평균 대비: {current_vs_ma200:+.2f}% ({ma_status})
- 장기 변동성: {long_volatility:.2f}% (연환산)
- 장기 RSI(14): {rsi_long_str}
- 데이터 포인트: {len(df_long)} days"""
            else:
                long_analysis = f"""
[장기 분석 (3년)]
- 데이터 부족: 장기 추세 분석 불가 (확보된 데이터: {len(df_long)} days)
- 최소 200일 이상의 데이터가 필요합니다."""
            
            # Combined result
            result = f"""Stock: {ticker}
현재가: ${current_price:.2f}

{long_analysis}

{short_analysis}

데이터 요약: 장기 {len(df_long)}일 / 단기 {len(df_short)}일"""
            
            return result
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return f"""Error analyzing {ticker}: {str(e)}

Technical Details (for debugging):
{error_details}

Note: Please check if numpy and scipy are installed, and if data can be fetched for this ticker."""


class MarketIndicatorsTool(BaseTool):
    name: str = "Market Indicators Tool"
    description: str = "Fetch current market indicators (SPY, QQQ, VIX, FGI, KOSPI, KOSDAQ). Automatically determines if stock is Korean or US based on ticker."
    args_schema: Type[BaseModel] = MarketIndicatorsInput
    
    def _run(self, ticker: str) -> str:
        try:
            is_korean = ticker.endswith('.KS') or ticker.endswith('.KQ')
            indicators = get_market_indicators()
            
            if is_korean:
                korea_data = indicators.get("korea", {})
                equity_data = korea_data.get("equity", {})
                kospi_data = equity_data.get("KOSPI", {}).get("ret_3m", {})
                kosdaq_data = equity_data.get("KOSDAQ", {}).get("ret_3m", {})
                vkospi_data = korea_data.get("volatility", {}).get("VKOSPI", {})
                usdkrw_data = korea_data.get("fx", {}).get("USDKRW", {})
                kr10y_data = korea_data.get("macro", {}).get("KR10Y", {})
                kospi_pbr_data = korea_data.get("valuation", {}).get("KOSPI_PBR", {})
                
                # Format values with proper null handling
                kospi_ret = kospi_data.get('value')
                kosdaq_ret = kosdaq_data.get('value')
                vkospi_val = vkospi_data.get('value')
                usdkrw_val = usdkrw_data.get('value')
                kr10y_val = kr10y_data.get('value')
                kospi_pbr_val = kospi_pbr_data.get('value')
                
                result = f"""Market Context: KOREAN MARKET
KOSPI 3개월 수익률: {f'{kospi_ret:.2f}%' if kospi_ret is not None else 'N/A'}
KOSDAQ 3개월 수익률: {f'{kosdaq_ret:.2f}%' if kosdaq_ret is not None else 'N/A'}
VKOSPI (변동성 지수): {f'{vkospi_val:.2f}' if vkospi_val is not None else 'N/A'}
한국 10년물 국채 금리: {f'{kr10y_val:.2f}%' if kr10y_val is not None else 'N/A'}
KOSPI PBR: {f'{kospi_pbr_val:.2f}' if kospi_pbr_val is not None else 'N/A'}
USD/KRW 환율: {f'{usdkrw_val:.2f}' if usdkrw_val is not None else 'N/A'}"""
            else:
                us_data = indicators.get("us", {})
                spy = us_data.get("spy", {})
                qqq = us_data.get("qqq", {})
                vix = us_data.get("vix", {})
                fgi = us_data.get("fgi", {})
                
                result = f"""Market Context: US MARKET
S&P 500 (SPY): ${spy.get('value', 'N/A')} ({spy.get('change_pct', 'N/A')}%)
NASDAQ (QQQ): ${qqq.get('value', 'N/A')} ({qqq.get('change_pct', 'N/A')}%)
VIX: {vix.get('value', 'N/A')}
Fear & Greed Index: {fgi.get('value', 'N/A')} ({fgi.get('rating', 'N/A')})"""
            
            return result
        except Exception as e:
            return f"Error fetching market indicators: {str(e)}"


class NewsSearchTool(BaseTool):
    name: str = "News Search Tool"
    description: str = "Fetch recent news articles for a given stock ticker."
    args_schema: Type[BaseModel] = NewsSearchInput
    
    def _run(self, ticker: str) -> str:
        try:
            # Get company name using the improved function
            company_name = get_company_name(ticker)
            
            # Determine search keyword
            if company_name:
                if ticker.endswith('.KS') or ticker.endswith('.KQ'):
                    search_keyword = company_name
                else:
                    search_keyword = f"{company_name} stock"
            else:
                # Fallback if name fetch fails completely
                if ticker.endswith('.KS') or ticker.endswith('.KQ'):
                    search_keyword = ticker.split('.')[0] # Use code only for Korean stocks
                else:
                    search_keyword = f"{ticker} stock"
            
            # Log search attempt
            result = f"""News Search Process for {ticker}:

STEP 1: Company Name Resolution
- Ticker: {ticker}
- Resolved Name: {company_name if company_name else 'N/A (using ticker)'}
- Search Keyword: "{search_keyword}"

STEP 2: News API Call
"""
            
            # Fetch news
            news_list = fetch_news(search_keyword, page_size=10, ticker=ticker)
            
            if not news_list:
                result += f"""- Status: ❌ FAILED
- Reason: No articles returned from API
- Possible causes:
  1. NewsAPI/Naver API key not configured
  2. API rate limit exceeded
  3. No recent news for this keyword
  4. Network/connection issue

RECOMMENDATION: Check .env file for API keys:
- NEWS_API_KEY (for US stocks)
- NAVER_CLIENT_ID, NAVER_CLIENT_SECRET (for Korean stocks)
"""
                return result
            
            # Success - show detailed news data
            result += f"""- Status: ✅ SUCCESS
- Articles Retrieved: {len(news_list)}

STEP 3: News Data Quality Check
"""
            
            # Analyze news quality
            has_description = sum(1 for n in news_list if n.get('description'))
            has_source = sum(1 for n in news_list if n.get('source'))
            
            result += f"""- Articles with description: {has_description}/{len(news_list)}
- Articles with source: {has_source}/{len(news_list)}
- Data Quality: {"✅ Good" if has_description > len(news_list) * 0.7 else "⚠️ Medium"}

STEP 4: News Articles (Top 5 for Analysis)

"""
            
            for i, news in enumerate(news_list[:5], 1):
                title = news.get('title', 'No title')
                description = news.get('description', 'No description')
                
                # Handle source being either a string or dict
                source_data = news.get('source', 'Unknown')
                if isinstance(source_data, dict):
                    source = source_data.get('name', 'Unknown')
                else:
                    source = source_data
                
                published = news.get('published_at', 'N/A')
                
                result += f"""{i}. [{source}] {title}
   Published: {published}
   Description: {description[:200]}{"..." if len(description) > 200 else ""}
   
"""
            
            # Add remaining count
            if len(news_list) > 5:
                result += f"\n... and {len(news_list) - 5} more articles available for analysis.\n"
            
            result += f"""
STEP 5: Ready for Sentiment Analysis
Total articles available: {len(news_list)}
You can now proceed with:
1. Sentiment scoring (0-10)
2. High-impact event identification
3. Key narrative extraction
"""
            
            return result
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return f"""❌ ERROR in News Search Tool for {ticker}

Error Message: {str(e)}

Technical Details:
{error_details}

Troubleshooting Steps:
1. Check if .env file exists with valid API keys
2. Verify internet connection
3. Check API service status (newsapi.org or Naver Developer)
4. Review error details above for specific issues
"""


class FundamentalsTool(BaseTool):
    name: str = "Fundamentals Tool"
    description: str = "Fetch fundamental data (PER, PBR, ROE, etc.) for a stock."
    args_schema: Type[BaseModel] = FundamentalsInput
    
    def _run(self, ticker: str) -> str:
        try:
            fundamentals = fetch_fundamentals(ticker)
            
            if not fundamentals:
                return f"No fundamental data available for {ticker}"
            
            # Get additional data from yfinance info
            import yfinance as yf
            try:
                info = yf.Ticker(ticker).info
                market_cap = info.get('marketCap', 'N/A')
                if market_cap != 'N/A' and market_cap:
                    # Format market cap in billions
                    market_cap = f"${market_cap / 1e9:.2f}B"
                
                dividend_yield = info.get('dividendYield')
                
                # Strict Validation (User Request)
                if dividend_yield is not None:
                    try:
                        div_val = float(dividend_yield)
                        if div_val < 0 or div_val > 0.20:
                            # Out of range (0% ~ 20%)
                            # e.g. 1.36 (136%) or 5.0 (500%) -> Invalid
                            dividend_yield = None 
                            # Note: flagging "invalid_dividend_yield" is tricky here as we return a dict.
                            # The caller (api.py) needs to detect None/Anomaly.
                            # Or I can log it?
                            print(f"[fetch_fundamentals] Invalid Dividend Yield detected: {div_val}")
                    except:
                        dividend_yield = None
                
                week_52_high = info.get('fiftyTwoWeekHigh', 'N/A')
                week_52_low = info.get('fiftyTwoWeekLow', 'N/A')
            except:
                market_cap = 'N/A'
                dividend_yield = 'N/A'
                week_52_high = 'N/A'
                week_52_low = 'N/A'
            
            # Format fundamentals data (using correct keys: pe, pb, roe)
            pe = fundamentals.get('pe', 'N/A')
            pb = fundamentals.get('pb', 'N/A')
            roe = fundamentals.get('roe', 'N/A')
            
            # Format ROE as percentage if it's a decimal
            if roe != 'N/A' and isinstance(roe, (int, float)) and roe < 1:
                roe = f"{roe * 100:.2f}%"
            elif roe != 'N/A' and isinstance(roe, (int, float)):
                roe = f"{roe:.2f}%"
            
            result = f"""Fundamental Data for {ticker}:
Market Cap: {market_cap}
P/E Ratio: {pe if pe else 'N/A'}
P/B Ratio: {pb if pb else 'N/A'}
ROE: {roe}
Dividend Yield: {dividend_yield}
52-Week High: {week_52_high}
52-Week Low: {week_52_low}"""
            
            return result
        except Exception as e:
            return f"Error fetching fundamentals for {ticker}: {str(e)}"


class DecisionFusionInput(BaseModel):
    market_score: float = Field(..., description="Market score (0-10)")
    company_score: float = Field(..., description="Company/Stock score (0-10)")
    outlook_score: float = Field(..., description="3-month outlook/timing score (0-10)")
    industry_score: float = Field(None, description="Industry/Sector score (0-10), optional")


class DecisionFusionTool(BaseTool):
    name: str = "Decision Fusion Calculator"
    description: str = """
    Calculate the final investment action using probabilistic fusion logic.
    This tool applies conditional gating and calibrated thresholds to determine:
    - Final Action (적극적 매수/소극적 매수/현상 유지/소극적 매도/적극적 매도)
    - Rise Probability (p_up)
    - Confidence level
    
    CRITICAL: You MUST use this tool to determine the final action. Do not decide manually.
    
    Input: Your calculated scores (0-10 scale)
    Output: Scientifically calibrated investment decision
    """
    args_schema: Type[BaseModel] = DecisionFusionInput
    
    def _run(self, market_score: float, company_score: float, outlook_score: float, industry_score: float = None) -> str:
        try:
            from utils.score_fusion import compute_probabilities
            
            # Convert 0-10 scores to 0-100 scale
            M = float(market_score) * 10.0
            S = float(company_score) * 10.0
            T = float(outlook_score) * 10.0
            
            # User Rule 1: Industry Score Fallback
            # If industry_score is None, use company_score (S) as proxy
            if industry_score is not None:
                I = float(industry_score) * 10.0
            else:
                I = S  # Fallback: Use Company Score
            
            # Run probabilistic fusion
            result = compute_probabilities(M=M, I=I, S=S, T=T)
            
            # Format detailed output
            output = f"""
╔══════════════════════════════════════════════════════════════╗
║           DECISION FUSION CALCULATOR RESULT                  ║
╚══════════════════════════════════════════════════════════════╝

📊 INPUT SCORES (0-10 scale):
   Market Score:    {market_score:.1f}/10 → {M:.0f}/100
   Industry Score:  {f'{industry_score:.1f}/10 → {I:.0f}/100' if industry_score else 'None (using Company as proxy)'}
   Company Score:   {company_score:.1f}/10 → {S:.0f}/100
   Outlook Score:   {outlook_score:.1f}/10 → {T:.0f}/100

🔬 PROBABILISTIC CALIBRATION:
   pM (Market Probability):    {result['breakdown']['pM']:.4f}
   pI (Industry Probability):  {result['breakdown']['pI']:.4f}
   pS (Stock Probability):     {result['breakdown']['pS']:.4f}
   pT (Timing Probability):    {result['breakdown']['pT']:.4f}

🚪 CONDITIONAL GATING (Top-down):
   gM (Market Gate):           {result['breakdown']['gM']:.4f}
   gI (Industry Gate):         {result['breakdown']['gI']:.4f}
   gT (Timing Gate):           {result['breakdown']['gT']:.4f}
   
   pI_given_M (Industry|Market):  {result['breakdown']['pI_given_M']:.4f}
   pS_given_I (Stock|Industry):   {result['breakdown']['pS_given_I']:.4f}
   pT_adj (Timing adjusted):      {result['breakdown']['pT_adj']:.4f}

🎯 FINAL CALCULATION:
   p_product = {result['breakdown']['p_product']:.6f}
   p_up (Rise Probability) = {result['p_up']:.4f}

📈 DECISION OUTPUT:
   ✅ Final Action: {result['action']}
   📊 Confidence: {result['confidence']:.4f} ({result['confidence_level']})

📋 THRESHOLDS REFERENCE:
   p_up ≥ 0.62 : 적극적 매수 (Aggressive Buy)
   p_up ≥ 0.57 : 소극적 매수 (Passive Buy)
   p_up ≥ 0.47 : 현상 유지 (Hold)
   p_up ≥ 0.42 : 소극적 매도 (Passive Sell)
   p_up <  0.42 : 적극적 매도 (Aggressive Sell)

⚠️  SPECIAL FLAGS:
   {chr(10).join(f'   - {flag}' for flag in result['breakdown']['flags']) if result['breakdown']['flags'] else '   None'}

═══════════════════════════════════════════════════════════════

INSTRUCTION FOR YOUR REPORT:
Copy the "Final Action" value above as your "Initial Action Recommendation".
Do NOT override or modify this decision based on text rules.
"""
            
            return output
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            # User Rule 3: Fail safe with 'analysis_failed' action
            # Do NOT allow manual fallback. Return a structured error that Agent must use.
            return f"""
╔══════════════════════════════════════════════════════════════╗
║           DECISION FUSION CALCULATOR RESULT                  ║
╚══════════════════════════════════════════════════════════════╝

❌ ERROR: CALCULATION FAILED
Error: {str(e)}

📈 DECISION OUTPUT:
   ✅ Final Action: analysis_failed
   📊 Confidence: 0.0

⚠️  SPECIAL FLAGS:
   - fusion_error
   - {str(e)[:50]}

═══════════════════════════════════════════════════════════════

INSTRUCTION FOR YOUR REPORT:
The calculation has FAILED. 
You MUST set your Action to "analysis_failed".
Do NOT attempt to guess or manually calculate.
"""


class SectorAnalysisTool(BaseTool):
    name: str = "Sector Analysis Tool"
    description: str = "Analyze sector/industry performance for US stocks using SPDR sector ETFs. Returns sector score (0-100) based on relative performance vs SPY."
    args_schema: Type[BaseModel] = StockPriceInput
    
    def _run(self, ticker: str) -> str:
        try:
            from utils.sector_mapping import get_sector_etf, is_korean_stock
            from utils.sector_data import fetch_sector_etf_data, calculate_sector_score
            
            # Check if Korean stock
            if is_korean_stock(ticker):
                return f"Korean stocks (Phase 1): Industry score not yet implemented. Fallback to None will be used."
            
            # Get sector ETF for the ticker
            sector_etf = get_sector_etf(ticker)
            
            if not sector_etf:
                return f"Unable to determine sector for {ticker}. Industry score will fallback to None."
            
            # Fetch sector ETF performance data
            sector_data = fetch_sector_etf_data(sector_etf, spy_benchmark=True)
            
            if not sector_data:
                return f"Unable to fetch data for sector ETF {sector_etf}. Industry score will fallback to None."
            
            # Calculate sector score
            sector_score = calculate_sector_score(sector_data)
            
            # Format response
            result = f"""Sector Analysis for {ticker}:
Sector ETF: {sector_etf}
Sector Score: {sector_score:.2f}/100

Performance vs SPY:
- 1W Relative: {sector_data.get('relative_1w', 0):+.2f}%
- 1M Relative: {sector_data.get('relative_1m', 0):+.2f}%
- 3M Relative: {sector_data.get('relative_3m', 0):+.2f}%

Sector Absolute Returns:
- 1W: {sector_data.get('ret_1w', 0):.2f}%
- 1M: {sector_data.get('ret_1m', 0):.2f}%
- 3M: {sector_data.get('ret_3m', 0):.2f}%

Volatility: {sector_data.get('volatility', 0):.2f}% (annualized)

Interpretation:
- Score > 60: Sector tailwind (favorable environment)
- Score 40-60: Sector neutral
- Score < 40: Sector headwind (challenging environment)
"""
            
            return result
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return f"""Error analyzing sector for {ticker}: {str(e)}

Technical Details:
{error_details}

Note: Industry score will fallback to None."""



class QuantitativeAnalysisInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")

class QuantitativeAnalysisTool(BaseTool):
    name: str = "Quantitative Analysis Tool"
    description: str = """
    Perform strict quantitative analysis using deterministic algorithms (same as API logic).
    Calculates Market Score, Company Score, and Outlook Score based on mathematical models.
    Input: Ticker
    Output: Calculated scores (0-10) with detailed breakdown.
    """
    args_schema: Type[BaseModel] = QuantitativeAnalysisInput
    
    def _run(self, ticker: str) -> str:
        try:
            # Import scoring functions
            from utils.scoring import (
                compute_market_score,
                compute_korea_market_score,
                compute_company_score,
                compute_outlook_score
            )
            from utils.market_indicators import get_market_indicators
            from utils.fgi import fetch_fear_greed
            from utils.finance_data import (
                fetch_price_history, 
                compute_returns, 
                compute_rsi,
                estimate_3m_outlook
            )
            from utils.common import fetch_news
            import pandas as pd
            import numpy as np
            import math
            
            # 1. Fetch Data
            is_korean = ticker.endswith('.KS') or ticker.endswith('.KQ')
            
            # Price Data
            df_short = fetch_price_history(ticker, period="3mo")
            if df_short.empty:
                return f"Error: No price data found for {ticker}"
            
            ret_1w = compute_returns(df_short, 5)
            ret_1m = compute_returns(df_short, 21)
            rsi = compute_rsi(df_short["close"])
            
            # Market Data
            indicators = get_market_indicators()
            fgi_data = fetch_fear_greed()
            
            # User Rule 2: Handle FGI Tuple
            # fetch_fear_greed returns (score, rating, date, df) tuple
            if isinstance(fgi_data, tuple):
                fgi_score = fgi_data[0]
            elif isinstance(fgi_data, dict):
                fgi_score = fgi_data.get('value')
            else:
                fgi_score = 50 # Fallback
            
            # News Data (for sentiment in company score)
            from utils.common import get_company_name
            c_name = get_company_name(ticker)
            kw = c_name if is_korean else f"{ticker} stock"
            news_list = fetch_news(kw, page_size=5, ticker=ticker)
            
            # 2. Calculate Market Score
            if is_korean:
                k_data = indicators.get("korea", {}).get("equity", {})
                kospi_ret = k_data.get("KOSPI", {}).get("ret_3m", 0)
                kosdaq_ret = k_data.get("KOSDAQ", {}).get("ret_3m", 0)
                usdkrw = indicators.get("korea", {}).get("fx", {}).get("USDKRW", {}).get("value")
                
                market_score = compute_korea_market_score(kospi_ret, kosdaq_ret, usdkrw)
                market_analysis = f"Korea Market (KOSPI 3m: {kospi_ret}%, KOSDAQ 3m: {kosdaq_ret}%, USD/KRW: {usdkrw})"
            else:
                us_data = indicators.get("us", {})
                spy_ret = us_data.get("spy", {}).get("ret_3m", 0) # Using 3m for consistency
                qqq_ret = us_data.get("qqq", {}).get("ret_3m", 0)
                
                market_score = compute_market_score(spy_ret, qqq_ret, fgi_score)
                market_analysis = f"US Market (SPY 3m: {spy_ret}%, QQQ 3m: {qqq_ret}%, FGI: {fgi_score})"
                
                
            # Fetch Fundamentals EARLY (Needed for Company Score)
            from utils.finance_data import fetch_fundamentals
            fund = fetch_fundamentals(ticker)
            pe = fund.get('pe') if fund else None
            roe = fund.get('roe') if fund else None

            # 3. Calculate Company Score (with market-specific logic & Fundamentals)
            # Need benchmark return (QQQ or similar)
            qqq_ret_1m = indicators.get("us", {}).get("qqq", {}).get("ret_3m", 0) # Fallback to 3m/US
            
            company_score = compute_company_score(
                ticker_ret_1m=ret_1m, 
                ticker_ret_1w=ret_1w, 
                qqq_ret_1m=qqq_ret_1m, 
                rsi=rsi, 
                news_list=news_list, 
                is_korean=is_korean,
                pe=pe,
                roe=roe
            )
            
            
            # Calculate 3M return properly
            try:
                ret_3m = (df_short["close"].iloc[-1] / df_short["close"].iloc[0] - 1) * 100
            except:
                ret_3m = 0.0
            
            # Calculate Volatility
            try:
                vol = df_short["close"].pct_change().std() * np.sqrt(252) * 100
            except:
                vol = 30.0  # Default mid-range
                
            # *** exp_3m is DEPRECATED - Always return None ***
            # No longer calculate or use 3-month expected return
            exp_3m = None
            alpha_3m = None
                
            
            # Get market risk indicator (VIX or VKOSPI)
            if is_korean:
                vix_or_vkospi = indicators.get("korea", {}).get("volatility", {}).get("VKOSPI", {}).get("value")
            else:
                vix_or_vkospi = indicators.get("us", {}).get("vix", {}).get("value")
            
            # Get company name for news relevance scoring
            from utils.common import get_company_name
            company_name = get_company_name(ticker)
            
            # ==================================================================
            # GENERATE SEMANTIC FLAGS with NEWS RELEVANCE using profile_classifier
            # ==================================================================
            from utils.profile_classifier import generate_semantic_flags
            
            data_flags, news_analysis = generate_semantic_flags(
                ticker=ticker,
                ret_1w=ret_1w,
                ret_1m=ret_1m,
                ret_3m=ret_3m,
                rsi=rsi,
                volatility=vol,
                pe=pe,
                roe=roe,
                news_list=news_list,
                vix_or_vkospi=vix_or_vkospi,
                is_korean=is_korean,
                company_name=company_name
            )


            # Calculate Outlook Score (Use new Technical Heavy Logic)
            outlook_score = compute_outlook_score(
                ret_1w=ret_1w,
                ret_1m=ret_1m,
                ret_3m=ret_3m,
                volatility=vol,
                rsi=rsi
            )
            
            # Get Action Profile from flags (with RSI for granular control)
            from utils.profile_classifier import get_action_profile
            profile_info = get_action_profile(data_flags, rsi=rsi)
            
            # Format Output
            news_rel_text = f"Top News Relevance: {news_analysis['relevance_score']:.2f}"
            if news_analysis.get('is_relevant'):
                news_rel_text += f" (RELEVANT - {news_analysis.get('sentiment', 'NEUTRAL')})"
            else:
                news_rel_text += " (LOW RELEVANCE)"
            
            result = f"""
QUANTITATIVE ANALYSIS RESULT (Deterministic Model):
--------------------------------------------------
1. Market Score: {market_score}/10
   Context: {market_analysis}

2. Company Score: {company_score}/10
   Factors:
   - 1M Return: {ret_1m:.2f}%
   - 1W Return: {ret_1w:.2f}%
   - RSI: {rsi:.2f}
   - News: {len(news_list)} articles
   - {news_rel_text}

3. Outlook Score: {outlook_score}/10 (Based on ret_3m: {ret_3m:.1f}%, volatility: {vol:.1f}%)
   *** exp_3m is DEPRECATED and always null ***
   
4. SEMANTIC FLAGS ({len(data_flags)}):
   {', '.join(data_flags) if data_flags else 'None'}

5. ACTION PROFILE: {profile_info['id']}
   Decision: {profile_info['decision_action']}
   Execution Style: {profile_info['execution_style']}
   Position Sizing: {profile_info['position_sizing']}
   
   Summary: {profile_info['summary']}
   Risk Note: {profile_info['risk_note']}
   
   Invalidators: {', '.join(profile_info.get('invalidators', ['N/A']))}
   Take Profit: {profile_info.get('take_profit_rule', 'N/A')}
   Stop Rule: {profile_info.get('stop_rule', 'N/A')}

--------------------------------------------------
USAGE INSTRUCTION:
1. Use the EXACT scores above (Market/Company/Outlook) for Decision Fusion Calculator.
2. MUST incorporate ACTION PROFILE details in your final report.
3. MUST include news connection in summary using top relevant news.
4. exp_3m will always be null in final JSON output.
1. Use the EXACT scores above (Market/Company/Outlook) as inputs for the Decision Fusion Calculator.
2. Copy the "SEMANTIC FLAGS" list and "ACTION PROFILE" information to your final report.
3. When writing overall_comment.summary or suggestion, incorporate the Action Profile guidance.
"""
            return result
            
        except Exception as e:
            import traceback
            return f"Error in Quantitative Analysis: {str(e)}\n{traceback.format_exc()}"

# Create tool instances
stock_price_tool = StockPriceTool()
market_indicators_tool = MarketIndicatorsTool()
news_search_tool = NewsSearchTool()
fundamentals_tool = FundamentalsTool()
decision_fusion_tool = DecisionFusionTool()
sector_analysis_tool = SectorAnalysisTool()
quantitative_analysis_tool = QuantitativeAnalysisTool()


# Export all tools
__all__ = [
    'stock_price_tool',
    'market_indicators_tool',
    'news_search_tool',
    'fundamentals_tool',
    'decision_fusion_tool',
    'sector_analysis_tool',
    'quantitative_analysis_tool'
]


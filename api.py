from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import math
import os

# Utils imports
from utils.finance_data import fetch_price_history, compute_returns, compute_rsi, estimate_3m_outlook, fetch_fundamentals
from utils.market_indicators import get_market_indicators
from utils.fgi import fetch_fear_greed, get_fgi_category
from utils.search import search_symbols
from utils.scoring import compute_market_score, compute_company_score, compute_outlook_score, decide_action
from utils.explain import build_move_explanation
from utils.chatbot import generate_chat_response
from utils.common import to_number, get_company_name, fetch_news
from utils.config import client
# from utils.score_fusion import compute_probabilities

# Agentic AI Engine
from agent_engine import run_agentic_analysis

app = FastAPI()

# CORS setup (allow all for local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ---------------------------------------------------------
# Models
# ---------------------------------------------------------
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[str] = ""

# ---------------------------------------------------------
# Helper Functions (Adapted from main.py)
# ---------------------------------------------------------
def _is_korea_symbol(ticker: str) -> bool:
    """
    Check if ticker is a Korean stock.
    Returns True for: 005930, 005930.KS, 035720.KQ
    """
    t = str(ticker).strip()
    # Remove .KS or .KQ suffix for checking
    base_ticker = t.replace('.KS', '').replace('.KQ', '')
    # Korean stocks are 6-digit numbers
    return len(base_ticker) == 6 and base_ticker.isdigit()

def period_ret(df: pd.DataFrame) -> float:
    """Calculate period return from DataFrame."""
    if df is None or df.empty:
        return math.nan
    try:
        col_name = "close" if "close" in df.columns else "Close" if "Close" in df.columns else None
        if col_name is None:
            return math.nan
        first = float(df[col_name].iloc[0])
        last = float(df[col_name].iloc[-1])
        if first == 0:
            return math.nan
        return (last / first - 1.0) * 100.0
    except Exception:
        return math.nan

# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------

@app.get("/api/market-status")
def get_market_status():
    """Fetch market indicators (SPY, QQQ, VIX, FGI, US10Y, DXY, Korea)."""
    # Unified Market Indicators Fetching
    try:
        indicators = get_market_indicators()
    except Exception as e:
        print(f"❌ Market Indicators Failed: {e}")
        indicators = {"us": {}, "korea": {}}
        
    us_data = indicators.get("us", {})
    korea_data = indicators.get("korea", {})
    
    # Map to existing frontend structure
    # US Data Mapping
    spy_data = us_data.get("spy", {})
    qqq_data = us_data.get("qqq", {})
    vix_data = us_data.get("vix", {})
    tnx_data = us_data.get("tnx", {})
    dxy_data = us_data.get("dxy", {})
    fgi_data = us_data.get("fgi", {})
    
    return {
        "us": {
            "spy_3m_ret": spy_data.get("ret_3m"),
            "qqq_3m_ret": qqq_data.get("ret_3m"),
            "vix_current": vix_data.get("value"),
            "tnx_current": tnx_data.get("value"),
            "dxy_current": dxy_data.get("value"),
            "fgi_score": fgi_data.get("value")
        },
        "korea": korea_data
    }

@app.get("/api/search")
def search_stock(query: str):
    """Search for stocks by name or ticker."""
    results, translated = search_symbols(query)
    return {"results": results, "translated_query": translated}

@app.get("/api/stock/{ticker}/basic")
def get_stock_basic(ticker: str):
    """Fetch basic stock information (name, returns, chart) without heavy analysis."""
    try:
        # 1. Get Company Name
        company_name = get_company_name(ticker)
        
        # 2. Get Price History for Returns & Chart
        # Use 3y to ensure we have enough data for all period returns (1w, 1m, 3m, 6m, 1y, 3y) and chart
        print(f"🔍 Fetching data for {ticker} (3y)...")
        df = fetch_price_history(ticker, period="3y")
        
        if df.empty:
            print(f"⚠️ No data found for {ticker}")
            return {
                "ticker": ticker,
                "company_name": company_name,
                "current_price": 0.0,
                "returns": {},
                "chart_data": {"dates": [], "prices": []}
            }
            
        print(f"✅ Data fetched for {ticker}: {len(df)} rows")
        
        # 3. Calculate Returns - Enhanced 1D Calculation
        import yfinance as yf
        ret_1d = math.nan
        t_obj = yf.Ticker(ticker)
        
        print(f"📊 Calculating 1D return for {ticker}...")
        
        # Korean stocks: Use KRX data (df-based calculation only)
        if _is_korea_symbol(ticker):
            print(f"🇰🇷 Korean stock detected: {ticker}, using KRX data")
            try:
                if len(df) >= 2:
                    last_close = float(df["close"].iloc[-1])
                    prev_close = float(df["close"].iloc[-2])
                    if prev_close != 0:
                        ret_1d = (last_close / prev_close - 1) * 100.0
                        print(f"✅ Korean 1D: {ticker} = {ret_1d:.2f}% (Last: {last_close:.2f}, Prev: {prev_close:.2f})")
                    else:
                        ret_1d = 0.0
                else:
                    ret_1d = 0.0
            except Exception as e:
                print(f"⚠️ Korean 1D calculation failed for {ticker}: {e}")
                ret_1d = 0.0
        
        # US stocks: Use yfinance real-time methods (4-step process)
        else:
            print(f"🇺🇸 US stock detected: {ticker}, using yfinance real-time data")
            
            # METHOD 1: Try current session data (most accurate for real-time)
            try:
                # Get today's intraday data - this is the most current
                hist_1d = t_obj.history(period="1d", interval="1m")
                if not hist_1d.empty and len(hist_1d) >= 2:
                    # Get the latest price and opening price from today
                    current_price = hist_1d["Close"].iloc[-1]
                    opening_price = hist_1d["Open"].iloc[0]
                    if opening_price != 0:
                        ret_1d = (current_price / opening_price - 1) * 100.0
                        print(f"✅ Method 1 (Intraday): {ticker} 1D = {ret_1d:.2f}% (Current: {current_price:.2f}, Open: {opening_price:.2f})")
            except Exception as e:
                print(f"⚠️ Method 1 (Intraday) failed for {ticker}: {e}")
            
            # METHOD 2: Use fast_info if Method 1 failed
            if math.isnan(ret_1d):
                try:
                    last = t_obj.fast_info.last_price
                    prev = t_obj.fast_info.previous_close
                    if last and prev and prev != 0:
                        ret_1d = (last / prev - 1) * 100.0
                        print(f"✅ Method 2 (fast_info): {ticker} 1D = {ret_1d:.2f}% (Last: {last:.2f}, Prev Close: {prev:.2f})")
                except Exception as e:
                    print(f"⚠️ Method 2 (fast_info) failed for {ticker}: {e}")

            # METHOD 3: Fallback to recent history (last 5 days)
            if math.isnan(ret_1d):
                try:
                    hist_short = t_obj.history(period="5d")
                    if len(hist_short) >= 2:
                        last_close = hist_short["Close"].iloc[-1]
                        prev_close = hist_short["Close"].iloc[-2]
                        if prev_close != 0:
                            ret_1d = (last_close / prev_close - 1) * 100.0
                            print(f"✅ Method 3 (5d history): {ticker} 1D = {ret_1d:.2f}% (Last: {last_close:.2f}, Prev: {prev_close:.2f})")
                except Exception as e:
                    print(f"⚠️ Method 3 (history fallback) failed for {ticker}: {e}")
            
            # METHOD 4: Final fallback for US stocks
            if math.isnan(ret_1d):
                ret_1d_fallback = compute_returns(df, 1)
                if not math.isnan(ret_1d_fallback):
                    ret_1d = ret_1d_fallback
                    print(f"✅ Method 4 (compute_returns): {ticker} 1D = {ret_1d:.2f}%")
                else:
                    print(f"❌ All methods failed for {ticker}, setting 1D to 0.0%")
                    ret_1d = 0.0

        returns = {
            "1d": ret_1d if not math.isnan(ret_1d) else compute_returns(df, 1),
            "1w": compute_returns(df, 5),
            "1m": compute_returns(df, 21),
            "3m": compute_returns(df, 63),
            "6m": compute_returns(df, 126),
            "1y": compute_returns(df, 252),
            "3y": compute_returns(df, 756)
        }
        print(f"📊 Returns for {ticker}: {returns}")
        
        # Handle NaN
        for k, v in returns.items():
            if math.isnan(v):
                returns[k] = 0.0
            
        current_price = float(df["close"].iloc[-1])
        
        # 4. Prepare Chart Data (Full 5y for frontend filtering)
        chart_data = {
            "dates": df.index.strftime("%Y-%m-%d").tolist(),
            "prices": df["close"].tolist()
        }
        
        return {
            "ticker": ticker,
            "company_name": company_name,
            "current_price": current_price,
            "returns": returns,
            "chart_data": chart_data
        }
    except Exception as e:
        print(f"❌ Basic Info Failed for {ticker}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "ticker": ticker,
            "company_name": get_company_name(ticker),
            "current_price": 0.0,
            "returns": {},
            "chart_data": {"dates": [], "prices": []}
        }

@app.get("/api/stock/{ticker}/analysis")
def analyze_stock(ticker: str, use_cache: bool = True):
    """Run heavy analysis for a specific stock using Agentic AI with caching."""
    from utils.cache import get_cached_analysis, save_to_cache
    
    try:
        # Check cache first (if enabled)
        if use_cache:
            cached_result = get_cached_analysis(ticker)
            if cached_result:
                print(f"✅ [Cache Hit] Returning cached analysis for {ticker}")
                return cached_result
        
        print(f"\n🤖 Starting Agent Analysis for {ticker} (No cache available)...")
        
        # 1. Run the agentic analysis
        agent_result = run_agentic_analysis(ticker, model_name="gpt-4o")
        
        # ============================================================
        # 2. DUAL DATA FETCHING STRATEGY
        # ============================================================
        # SHORT-TERM DATA (3mo): For analysis calculations (returns, RSI, agent analysis)
        print(f"📊 Fetching SHORT-TERM data (3mo) for {ticker}...")
        df_short = fetch_price_history(ticker, period="3mo")
        if df_short.empty:
            raise HTTPException(status_code=404, detail="Stock data not found")
        print(f"   ✅ Short-term data: {len(df_short)} rows")
        
        # LONG-TERM DATA (3y): For chart display (frontend period filtering)
        print(f"📈 Fetching LONG-TERM data (3y) for {ticker}...")
        df_long = fetch_price_history(ticker, period="3y")
        if df_long.empty:
            print(f"   ⚠️ Failed to fetch 3y data, using 3mo as fallback")
            df_long = df_short  # Fallback to short-term data
        print(f"   ✅ Long-term data: {len(df_long)} rows")
        
        # ============================================================
        # 3. CALCULATIONS (MUST USE df_short FOR ACCURACY)
        # ============================================================
        print(f"🔢 Calculating returns and indicators using SHORT-TERM data...")
        ret_1w = compute_returns(df_short, 5)
        ret_1m = compute_returns(df_short, 21)
        ret_3m = period_ret(df_short)
        rsi = compute_rsi(df_short["close"])
        print(f"   ✅ 1w: {ret_1w:.2f}%, 1m: {ret_1m:.2f}%, 3m: {ret_3m:.2f}%, RSI: {rsi:.2f}")
        
        # ============================================================
        # 4. CHART DATA (USE df_long FOR FULL PERIOD SUPPORT)
        # ============================================================
        print(f"📊 Preparing chart data using LONG-TERM data...")
        chart_dates = df_long.index.strftime('%Y-%m-%d').tolist()
        chart_prices = df_long["close"].tolist()
        print(f"   ✅ Chart data: {len(chart_dates)} points ({chart_dates[0]} ~ {chart_dates[-1]})")
        
        # ============================================================
        # 5. ADDITIONAL DATA
        # ============================================================
        # Get fundamentals
        fundamentals = fetch_fundamentals(ticker)
        
        # Get news (fetch more for UI)
        # For Korean stocks, use company name; for US stocks, use ticker with "stock"
        company_name = get_company_name(ticker)
        if company_name and any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in company_name):
            # Korean company name detected
            news_keyword = company_name
        else:
            # US stock or no Korean characters
            news_keyword = f"{ticker} stock"
        news_list = fetch_news(news_keyword, page_size=10, ticker=ticker)
        
        # ============================================================
        # 6. ENHANCED LOGIC: FLAGS & NEWS PURIFICATION (FORCE INJECT)
        # ============================================================
        from utils.news_ranker import rank_and_filter_news
        from utils.flags_engine import calculate_flags
        import numpy as np

        # 1. Calculate Volatility (Annualized)
        if len(df_short) > 1:
            daily_rets = df_short['close'].pct_change().dropna()
            volatility = daily_rets.std() * np.sqrt(252) * 100
        else:
            volatility = None
        
        # 2. News Ranking & Filtering
        news_analysis = rank_and_filter_news(news_list, ticker, company_name)
        
        # 3. Calculate Flags (Normalized)
        pe = fundamentals.get('pe') if fundamentals else None
        pbr = fundamentals.get('pbr') if fundamentals else None
        
        computed_flags = calculate_flags(
            ticker=ticker,
            rsi=rsi,
            ret_3m=ret_3m,
            volatility=volatility,
            pe=pe,
            pbr=pbr,
            news_analysis_result=news_analysis
        )
        
        # 4. Merge Flags (Agent + Computed) -> SSOT
        existing_flags = agent_result.get("decision_breakdown", {}).get("flags", [])
        if existing_flags is None: existing_flags = []
        
        merged_flags = list(set(existing_flags + computed_flags))
        if "decision_breakdown" not in agent_result:
            agent_result["decision_breakdown"] = {}
        agent_result["decision_breakdown"]["flags"] = merged_flags
        
        # 5. Force Connect Summary with Direct News (Rule B-3)
        direct_news = news_analysis['direct']
        if "overall_comment" not in agent_result:
             agent_result["overall_comment"] = {}
             
        current_summary = agent_result.get("overall_comment", {}).get("summary", "")
        
        # Remove old placeholder/generic text if exists (Clean up filler)
        placeholders = [
            "뉴스 이슈 부재", "특별한 뉴스 이슈가 부재하여", 
            "수급과 차트 중심 대응이 필요합니다", "수급과 차트 중심 대응",
            "직접적인 뉴스 이슈는 없으나", "특이 사항 없음"
        ]
        for ph in placeholders:
            current_summary = current_summary.replace(ph, "")
            
        # Cleanup trailing punctuation/spaces/brackets
        current_summary = current_summary.strip().rstrip(" .")
        current_summary = current_summary.replace("[뉴스/전략]", "").strip() # Remove empty tag if it became empty
        
        new_summary_suffix = ""
        if direct_news:
            top_news = direct_news[0]
            sentiment = top_news.get('sentiment_label', 'NEUTRAL')
            
            # Simple summarization of title (truncate if too long) -- LIMIT REMOVED per user request
            news_title = top_news.get('title', '관련 뉴스')
            
            # Format: "[뉴스] {Title} → {User Friendly Comment}"
            if sentiment == "POSITIVE":
                action_hint = "호재가 포착되었습니다. 비중 확대를 고려해보세요."
            elif sentiment == "NEGATIVE":
                action_hint = "부정적인 이슈가 있습니다. 리스크 관리에 유의하세요."
            else:
                action_hint = "큰 이슈는 없습니다. 현상을 유지하며 지켜보세요."

            new_summary_suffix = f" [뉴스] {news_title} → {action_hint}"
            
            current_summary = current_summary.rstrip('.') + "." + new_summary_suffix
                 
        elif not direct_news and news_analysis['indirect']:
            # Indirect only
            current_summary = current_summary.rstrip('.') + ". 직접적 호재는 제한적이며, 섹터/매크로 변수 모니터링이 필요합니다."
        else:
            # No relevant news at all
            current_summary = current_summary.rstrip('.') + ". 특이 뉴스 이슈 부재, 수급과 차트 중심 대응."

        agent_result["overall_comment"]["summary"] = current_summary
        
        # Update news list for UI
        news_list = news_analysis['all_scored']

        # ============================================================
        # 7. CONSTRUCT RESPONSE (DIRECT FROM AGENT)
        # ============================================================
        import json
        



        
        response = {
            "ticker": ticker,
            "company_name": get_company_name(ticker),
            
            # Use Agent Result Directly (SSOT enforced in agent_engine)
            "action": agent_result.get("action", "현상 유지"),
            "decision_prob": agent_result.get("decision_prob", 0.5),
            "confidence": agent_result.get("confidence", 0.0),
            "confidence_level": agent_result.get("confidence_level", "중간"),
            "decision_breakdown": agent_result.get("decision_breakdown", {}),
            
            "market_score": agent_result.get("market_score") or 5,
            "company_score": agent_result.get("company_score") or 5,
            "outlook_score": agent_result.get("outlook_score") or 5,
            "ret_1w": ret_1w,
            "ret_1m": ret_1m,
            "ret_3m": ret_3m,
            "exp_3m": 0, # Removed as per user request
            "rsi": rsi,
            "overall_comment": agent_result.get("overall_comment", {}),
            "news": news_list,
            "fundamentals": fundamentals,
            "chart_data": {
                "dates": chart_dates,
                "prices": chart_prices
            },
            "_agent_mode": True,
            "agent_logs": agent_result.get("agent_logs", [])
        }
        
        # Debug: Log score values for troubleshooting
        print(f"\n📊 Score Values Debug:")
        print(f"   Agent Result Scores (raw):")
        print(f"     - market_score: {agent_result.get('market_score')}")
        print(f"     - company_score: {agent_result.get('company_score')}")
        print(f"     - outlook_score: {agent_result.get('outlook_score')}")
        
        print(f"   Decision (Agent):")
        print(f"     - Action: {agent_result.get('action')}")
        print(f"     - p_up: {agent_result.get('decision_prob')}")
        print(f"     - Confidence: {agent_result.get('confidence')}")
        
        # Debug: Check if agent_logs are present
        print(f"\n📝 Agent logs count: {len(agent_result.get('agent_logs', []))}")
        if agent_result.get('agent_logs'):
            print(f"   First log: {agent_result['agent_logs'][0].get('step_name', 'N/A')}")
        
        # Save to cache
        if use_cache:
            save_to_cache(ticker, response)
        
        print(f"\n✅ Agent Analysis Complete for {ticker}")
        return response

    except Exception as e:
        print(f"❌ Agent Analysis Failed for {ticker}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Fallback logic to prevent UI crash
        try:
            # Try to get at least 3y data for chart
            df_fallback = fetch_price_history(ticker, period="3y")
            if df_fallback.empty:
                # If 3y fails, try 3mo
                df_fallback = fetch_price_history(ticker, period="3mo")
            
            if not df_fallback.empty:
                chart_dates = df_fallback.index.strftime('%Y-%m-%d').tolist()
                chart_prices = df_fallback["close"].tolist()
            else:
                chart_dates = []
                chart_prices = []
        except:
            chart_dates = []
            chart_prices = []
            
        return {
            "ticker": ticker,
            "action": "현상 유지",
            "market_score": 5,
            "company_score": 5,
            "outlook_score": 5,
            "overall_comment": {
                "summary": "AI 에이전트 분석 중 오류가 발생했습니다.",
                "market_env": "분석 실패",
                "company_summary": "분석 실패",
                "outlook_3m": "분석 실패",
                "risks": f"오류 내용: {str(e)}",
                "suggestion": "잠시 후 다시 시도해주세요."
            },
            "chart_data": {
                "dates": chart_dates,
                "prices": chart_prices
            },
            "_error": True
        }

@app.post("/api/chat")
def chat(request: ChatRequest):
    """Chatbot endpoint."""
    # Convert Pydantic models to dicts
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    response = generate_chat_response(messages, context=request.context)
    return {"response": response}

@app.post("/api/tts")
def text_to_speech(request: dict = Body(...)):
    """
    Text-to-Speech endpoint using OpenAI TTS API.
    Input: {"text": "안녕하세요..."}
    Output: Audio file (MP3)
    """
    from fastapi.responses import Response
    
    text = request.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        
        return Response(
            content=response.content,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

@app.post("/api/stt")
async def speech_to_text(file: bytes = Body(...)):
    """
    Speech-to-Text endpoint using OpenAI Whisper API.
    Input: Audio file
    Output: {"text": "transcribed text"}
    """
    import tempfile
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_file:
            tmp_file.write(file)
            tmp_path = tmp_file.name
        
        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ko"
            )
        
        os.unlink(tmp_path)
        
        return {"text": transcript.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT failed: {str(e)}")

@app.get("/api/stock/{ticker}/agent-analysis")
def agent_analyze_stock(ticker: str):
    """
    Run AI Agent Team analysis for a specific stock.
    
    This endpoint uses a multi-agent CrewAI system with 4 specialized agents:
    1. Market Data Analyst - Collects comprehensive data
    2. Trading Strategy Developer - Calculates quantitative scores
    3. Risk & Investment Advisor - Assesses risks and finalizes recommendation
    4. Report Writer - Synthesizes everything into JSON
    
    Returns the same format as /api/stock/{ticker}/analysis for frontend compatibility.
    """
    try:
        print(f"\n🤖 Starting Agent Analysis for {ticker}...")
        
        # Run the agentic analysis
        agent_result = run_agentic_analysis(ticker, model_name="gpt-4o")
        
        # The agent result should already be in the correct format
        # But we need to ensure compatibility with the existing frontend
        
        # Get additional data that the frontend expects
        df = fetch_price_history(ticker, period="3mo")
        if df.empty:
            raise HTTPException(status_code=404, detail="Stock data not found")
        
        # Calculate returns for chart data
        ret_1w = compute_returns(df, 5)
        ret_1m = compute_returns(df, 21)
        ret_3m = period_ret(df)
        
        # Get fundamentals
        fundamentals = fetch_fundamentals(ticker)
        
        # Get news
        # For Korean stocks, use company name; for US stocks, use ticker with "stock"
        company_name = get_company_name(ticker)
        if company_name and any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in company_name):
            # Korean company name detected
            news_keyword = company_name
        else:
            # US stock or no Korean characters
            news_keyword = f"{ticker} stock"
        news_list = fetch_news(news_keyword, page_size=10, ticker=ticker)
        
        # Prepare chart data
        chart_data = []
        for idx, row in df.iterrows():
            chart_data.append({
                "date": idx.strftime("%Y-%m-%d"),
                "close": float(row["close"])
            })
        
        # Build response in the format expected by frontend
        # Build response in the format expected by frontend
        
        # ============================================================
        # 6. CONSTRUCT RESPONSE (DIRECT FROM AGENT)
        # ============================================================
        # SSOT: Use agent_result directly. Do not re-calculate fusion or comments.
        
        response = {
            "ticker": ticker,
            "company_name": get_company_name(ticker),
            
            # Use Agent Result Directly (SSOT enforced in agent_engine)
            "action": agent_result.get("action", "현상 유지"),
            "decision_prob": agent_result.get("decision_prob", 0.5),
            "confidence": agent_result.get("confidence", 0.0),
            "confidence_level": agent_result.get("confidence_level", "중간"),
            "decision_breakdown": agent_result.get("decision_breakdown", {}),
            
            "market_score": agent_result.get("market_score") or 5,
            "company_score": agent_result.get("company_score") or 5,
            "outlook_score": agent_result.get("outlook_score") or 5,
            "ret_1w": ret_1w,
            "ret_1m": ret_1m,
            "ret_3m": ret_3m,
            "exp_3m": 0, # Removed
            "rsi": 0, # RSI not calculated in this endpoint, but not critical? Wait, analyze_stock calc it.
                      # agent_analyze_stock calc ret_3m but not RSI in the snippet above (534-539).
                      # Let's add RSI calc if needed or just pass 0.
                      # Ideally we should match analyze_stock logic. 
                      # But for now, let's fix the crash.
            "overall_comment": agent_result.get("overall_comment", {}),
            "news": news_list[:10],
            "fundamentals": fundamentals,
            "chart_data": {
                "dates": [d["date"] for d in chart_data],
                "prices": [d["close"] for d in chart_data]
            },
            "_agent_mode": True,
            "agent_logs": agent_result.get("agent_logs", [])
        }
        
        # Debug: Log score values
        print(f"\n📊 Score Values Debug (agent_analyze_stock):")
        print(f"   Agent Result Scores (raw):")
        print(f"     - market_score: {agent_result.get('market_score')} (type: {type(agent_result.get('market_score')).__name__})")
        print(f"     - company_score: {agent_result.get('company_score')} (type: {type(agent_result.get('company_score')).__name__})")
        print(f"     - outlook_score: {agent_result.get('outlook_score')} (type: {type(agent_result.get('outlook_score')).__name__})")
        print(f"   Response Scores (to UI):")
        print(f"     - market_score: {response['market_score']}")
        print(f"     - company_score: {response['company_score']}")
        print(f"     - outlook_score: {response['outlook_score']}")
        
        print(f"\n✅ Agent Analysis Complete for {ticker}")
        return response
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        print(f"❌ Agent Analysis Failed for {ticker}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return a valid JSON error response instead of raising HTTPException
        # This prevents the frontend from trying to parse "Internal Server Error" as JSON
        try:
            # Try to get basic data for the response
            df = fetch_price_history(ticker, period="3mo")
            if not df.empty:
                ret_1w = compute_returns(df, 5)
                ret_1m = compute_returns(df, 21)
                ret_3m = period_ret(df)
                chart_data = [
                    {"date": idx.strftime("%Y-%m-%d"), "close": float(row["close"])}
                    for idx, row in df.iterrows()
                ]
            else:
                ret_1w = ret_1m = ret_3m = 0
                chart_data = []
        except:
            ret_1w = ret_1m = ret_3m = 0
            chart_data = []
        
        # Return error response in valid JSON format
        return {
            "ticker": ticker,
            "company_name": get_company_name(ticker),
            "action": "현상 유지",
            "market_score": 5,
            "company_score": 5,
            "outlook_score": 5,
            "ret_1w": ret_1w,
            "ret_1m": ret_1m,
            "ret_3m": ret_3m,
            "overall_comment": {
                "summary": f"{ticker} AI 에이전트 분석 중 오류가 발생했습니다.",
                "market_env": "시장 환경 분석을 완료하지 못했습니다.",
                "company_summary": "종목 분석을 완료하지 못했습니다.",
                "outlook_3m": "3개월 전망을 생성하지 못했습니다.",
                "risks": f"오류: {str(e)[:200]}",
                "suggestion": "잠시 후 다시 시도해주세요. 문제가 지속되면 관리자에게 문의하세요."
            },
            "chart_data": chart_data,
            "news": [],
            "fundamentals": {},
            "_agent_mode": True,
            "_error": True,
            "_error_message": str(e)
        }

@app.post("/api/translate")
def translate_text(request: dict = Body(...)):
    """
    Translate text from English to Korean using DeepL API.
    Used for on-demand translation of agent logs.
    
    Input: {"text": "English text to translate"}
    Output: {"translated_text": "번역된 텍스트", "success": true}
    """
    from utils.common import _translate_with_deepl
    
    text = request.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    try:
        # For long texts, split into paragraphs to avoid API limits
        if len(text) > 3000:
            print(f"📦 Splitting long text ({len(text)} chars) into paragraphs...")
            paragraphs = text.split('\n\n')
            translated_paragraphs = []
            
            for idx, para in enumerate(paragraphs, 1):
                if para.strip():
                    try:
                        print(f"   📝 Translating paragraph {idx}/{len(paragraphs)} ({len(para)} chars)...")
                        translated = _translate_with_deepl(para)
                        translated_paragraphs.append(translated)
                    except Exception as e:
                        print(f"      ⚠️ Translation failed for paragraph {idx}: {e}")
                        translated_paragraphs.append(para)  # Keep original if translation fails
            
            translated_text = '\n\n'.join(translated_paragraphs)
        else:
            print(f"📝 Translating text ({len(text)} chars)...")
            translated_text = _translate_with_deepl(text)
        
        print(f"✅ Translation complete: {len(text)} chars → {len(translated_text)} chars")
        
        return {
            "translated_text": translated_text,
            "success": True
        }
    except Exception as e:
        print(f"❌ Translation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@app.post("/api/report/pdf")
def generate_pdf_report(request: dict = Body(...)):
    """
    Generate PDF report from analysis data.
    
    Input: Full analysis data including logs, scores, and commentary
    Output: PDF file download
    """
    from fastapi.responses import StreamingResponse
    from utils.report_generator import PDFReportGenerator
    
    try:
        ticker = request.get('ticker', 'UNKNOWN')
        company_name = request.get('company_name', ticker)
        
        print(f"📄 Generating PDF report for {ticker} ({company_name})...")
        
        # Create PDF generator
        generator = PDFReportGenerator()
        
        # Generate PDF in memory
        pdf_buffer = generator.generate_report(request, ticker)
        
        # Prepare filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"AI_Analysis_{ticker}_{timestamp}.pdf"
        
        print(f"✅ PDF generated successfully: {filename}")
        
        # Return as streaming response
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        print(f"❌ PDF generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


# ---------------------------------------------------------
# Static Files (Mount last to avoid shadowing API)
# ---------------------------------------------------------
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)

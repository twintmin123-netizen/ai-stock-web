# agent_engine/parallel_tools.py
"""
Parallel data fetching wrapper for CrewAI tools
Speeds up agent analysis by fetching data concurrently
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any
import time


def fetch_all_data_parallel(ticker: str) -> Dict[str, Any]:
    """
    Fetch all stock data in parallel using ThreadPoolExecutor.
    
    This function runs 4 separate data fetches concurrently:
    1. Price history (3 months)
    2. Market indicators
    3. News articles
    4. Fundamental data
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dictionary with all fetched data
    """
    from .tools import (
        stock_price_tool,
        market_indicators_tool,
        news_search_tool,
        fundamentals_tool
    )
    
    start_time = time.time()
    results = {}
    
    # Define fetch tasks
    tasks = {
        "price_data": lambda: stock_price_tool._run(ticker),
        "market_data": lambda: market_indicators_tool._run(ticker),
        "news_data": lambda: news_search_tool._run(ticker),
        "fundamental_data": lambda: fundamentals_tool._run(ticker)
    }
    
    # Execute all tasks in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all tasks
        future_to_key = {
            executor.submit(task_func): key 
            for key, task_func in tasks.items()
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                results[key] = future.result()
                print(f"✅ [{key}] fetched successfully")
            except Exception as e:
                results[key] = f"Error: {str(e)}"
                print(f"❌ [{key}] failed: {e}")
    
    elapsed = time.time() - start_time
    print(f"⚡ Parallel fetch completed in {elapsed:.2f}s")
    
    # Format results as a combined summary
    combined_result = f"""
=== PARALLEL DATA FETCH RESULTS ===
Completed in {elapsed:.2f} seconds

--- PRICE DATA ---
{results.get('price_data', 'No data')}

--- MARKET INDICATORS ---
{results.get('market_data', 'No data')}

--- NEWS ---
{results.get('news_data', 'No data')}

--- FUNDAMENTALS ---
{results.get('fundamental_data', 'No data')}
"""
    
    return {
        "combined_summary": combined_result,
        "individual_results": results,
        "fetch_time_seconds": elapsed
    }


# Optional: Create a tool wrapper for CrewAI
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class ParallelDataInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")


class ParallelDataTool(BaseTool):
    name: str = "Parallel Data Fetcher"
    description: str = "Fetch all stock data (price, market, news, fundamentals) in parallel for maximum speed"
    args_schema: Type[BaseModel] = ParallelDataInput
    
    def _run(self, ticker: str) -> str:
        result = fetch_all_data_parallel(ticker)
        return result["combined_summary"]


# Create tool instance
parallel_data_tool = ParallelDataTool()

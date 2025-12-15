# utils/cache.py
"""
Simple file-based caching for analysis results
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path


# Cache directory
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# Cache duration (1 hour)
CACHE_DURATION = timedelta(hours=1)


def _get_cache_key(ticker: str) -> str:
    """Generate cache key for a ticker."""
    today = datetime.now().strftime("%Y-%m-%d")
    key_str = f"{ticker}_{today}"
    # Use hash to create safe filename
    return hashlib.md5(key_str.encode()).hexdigest()


def _get_cache_path(ticker: str) -> Path:
    """Get cache file path for a ticker."""
    cache_key = _get_cache_key(ticker)
    return CACHE_DIR / f"{cache_key}.json"


def get_cached_analysis(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached analysis result if available and not expired.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Cached analysis dictionary or None if not found/expired
    """
    cache_path = _get_cache_path(ticker)
    
    if not cache_path.exists():
        print(f"[Cache] No cache found for {ticker}")
        return None
    
    try:
        # Read cache file
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Check expiration
        cached_time = datetime.fromisoformat(cache_data.get("cached_at", ""))
        age = datetime.now() - cached_time
        
        if age > CACHE_DURATION:
            print(f"[Cache] Cache expired for {ticker} (age: {age})")
            # Delete expired cache
            cache_path.unlink()
            return None
        
        print(f"[Cache] ✅ Cache hit for {ticker} (age: {age})")
        return cache_data.get("result")
        
    except Exception as e:
        print(f"[Cache] Error reading cache for {ticker}: {e}")
        return None


def save_to_cache(ticker: str, result: Dict[str, Any]) -> bool:
    """
    Save analysis result to cache.
    
    Args:
        ticker: Stock ticker symbol
        result: Analysis result dictionary
        
    Returns:
        True if successfully cached, False otherwise
    """
    cache_path = _get_cache_path(ticker)
    
    try:
        cache_data = {
            "ticker": ticker,
            "cached_at": datetime.now().isoformat(),
            "result": result
        }
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        print(f"[Cache] ✅ Saved cache for {ticker}")
        return True
        
    except Exception as e:
        print(f"[Cache] Error saving cache for {ticker}: {e}")
        return False


def clear_cache(ticker: Optional[str] = None) -> int:
    """
    Clear cache for a specific ticker or all caches.
    
    Args:
        ticker: Stock ticker symbol, or None to clear all
        
    Returns:
        Number of cache files deleted
    """
    if ticker:
        # Clear specific ticker
        cache_path = _get_cache_path(ticker)
        if cache_path.exists():
            cache_path.unlink()
            print(f"[Cache] Cleared cache for {ticker}")
            return 1
        return 0
    else:
        # Clear all caches
        count = 0
        for cache_file in CACHE_DIR.glob("*.json"):
            cache_file.unlink()
            count += 1
        print(f"[Cache] Cleared {count} cache files")
        return count


def get_cache_info() -> Dict[str, Any]:
    """
    Get information about current cache status.
    
    Returns:
        Dictionary with cache statistics
    """
    cache_files = list(CACHE_DIR.glob("*.json"))
    total_size = sum(f.stat().st_size for f in cache_files)
    
    return {
        "total_files": len(cache_files),
        "total_size_bytes": total_size,
        "cache_dir": str(CACHE_DIR.absolute()),
        "cache_duration_hours": CACHE_DURATION.total_seconds() / 3600
    }

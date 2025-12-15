"""
Sector Mapping Utility
Maps stock tickers to SPDR Select Sector ETFs
"""

# SPDR Select Sector ETF mapping
SECTOR_ETFS = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Health Care": "XLV",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Consumer Staples": "XLP",
    "Consumer Discretionary": "XLY",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
    "Materials": "XLB"
}

# Reverse mapping for quick lookup
ETF_TO_SECTOR = {v: k for k, v in SECTOR_ETFS.items()}


def get_sector_etf(ticker: str) -> str:
    """
    Get the SPDR sector ETF for a given stock ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Sector ETF ticker (e.g., 'XLK') or None if not found
    """
    try:
        import yfinance as yf
        
        # Fetch stock info
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Try to get sector from yfinance
        sector = info.get('sector')
        
        if sector and sector in SECTOR_ETFS:
            return SECTOR_ETFS[sector]
        
        # Fallback: manual mapping for common tickers
        manual_mapping = {
            'AAPL': 'XLK',  # Technology
            'MSFT': 'XLK',
            'GOOGL': 'XLC',  # Communication
            'AMZN': 'XLY',  # Consumer Discretionary
            'TSLA': 'XLY',
            'NVDA': 'XLK',
            'META': 'XLC',
            'JPM': 'XLF',   # Financials
            'BAC': 'XLF',
            'WMT': 'XLP',   # Consumer Staples
            'PG': 'XLP',
            'JNJ': 'XLV',   # Health Care
            'UNH': 'XLV',
            'XOM': 'XLE',   # Energy
            'CVX': 'XLE'
        }
        
        if ticker.upper() in manual_mapping:
            return manual_mapping[ticker.upper()]
            
        return None
        
    except Exception as e:
        print(f"⚠️ Error getting sector for {ticker}: {e}")
        return None


def is_korean_stock(ticker: str) -> bool:
    """Check if ticker is a Korean stock."""
    return ticker.endswith('.KS') or ticker.endswith('.KQ') or ticker.isdigit()

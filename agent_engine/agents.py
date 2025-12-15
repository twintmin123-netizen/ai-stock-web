"""
CrewAI Agents Definition
"""

from crewai import Agent
from langchain_openai import ChatOpenAI
from .tools import (
    stock_price_tool,
    market_indicators_tool,
    news_search_tool,
    fundamentals_tool,
    decision_fusion_tool,
    sector_analysis_tool,
    quantitative_analysis_tool
)


def create_data_analyst_agent(llm) -> Agent:
    """
    Market Data Analyst - 객관적인 관찰자
    시장 데이터와 재무 정보를 수집하고 통계적 특성을 파악 (뉴스 분석 제외)
    """
    return Agent(
        role="Market Data Analyst",
        goal="Collect comprehensive market data and fundamental information for the given stock ticker",
        backstory="""You are an expert financial data analyst with deep knowledge of both 
        US and Korean stock markets. You specialize in gathering accurate, real-time market data 
        and identifying statistical patterns. You understand the importance of context - comparing 
        individual stock performance against broader market indices (SPY/QQQ for US stocks, 
        KOSPI/KOSDAQ for Korean stocks). Your analysis is always objective and data-driven.
        You focus purely on quantitative data: price movements, technical indicators, and fundamentals.
        
        CRITICAL: Output your analysis in ENGLISH with clear section headers and bullet points.""",
        tools=[
            stock_price_tool,
            market_indicators_tool,
            fundamentals_tool
        ],
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_news_analyst_agent(llm) -> Agent:
    """
    Market News Analyst - 뉴스 데이터 분석가
    뉴스를 수집하고 감정 분석 및 주요 이벤트를 식별
    """
    return Agent(
        role="Market News Analyst",
        goal="Analyze news sentiment and identify key market events affecting the stock",
        backstory="""You are an expert in financial news analysis and sentiment detection. 
        You specialize in distinguishing between noise and signal in financial media. You can 
        identify high-impact events (earnings surprises, regulatory changes, major partnerships, 
        legal issues) and assess overall market sentiment from news articles. You provide a 
        quantitative sentiment score (0-10 scale) where 0 is extremely negative, 5 is neutral, 
        and 10 is extremely positive. You also flag critical events that could significantly 
        impact the stock price. Your analysis helps other team members understand the narrative 
        and sentiment surrounding the stock.
        
        CRITICAL: You MUST output your analysis in ENGLISH using this exact format:
        
        News Sentiment Score: X/10
        
        High-Impact Events:
        - [List events or write "None identified"]
        
        Key Narratives:
        - [Theme 1]: [Description]
        - [Theme 2]: [Description]
        
        News Summary:
        1. [Topic]: [Description]. [Sentiment: Positive/Neutral/Negative]
        2. [Topic]: [Description]. [Sentiment: Positive/Neutral/Negative]
        ...
        
        DO NOT translate to Korean. Use English for all analysis output.""",
        tools=[
            news_search_tool
        ],
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_strategy_agent(llm) -> Agent:
    """
    Trading Strategy Agent - 냉철한 전략가
    기술적 지표와 스코어링 모델을 통해 매매 전략 수립
    """
    return Agent(
        role="Trading Strategy Developer",
        goal="Develop quantitative trading strategies based on technical indicators and scoring models",
        backstory="""You are a quantitative analyst with expertise in technical analysis 
        and systematic trading strategies. You excel at calculating precise metrics like RSI, 
        returns, and volatility. You use a proprietary scoring system (0-10 scale) to evaluate 
        market conditions, company strength, and future outlook. Your recommendations are based 
        on mathematical models, not emotions. You understand that different markets (US vs Korean) 
        require different benchmarks and scoring approaches.
        
        CRITICAL: Output your analysis in ENGLISH.""",
        tools=[
            decision_fusion_tool,
            sector_analysis_tool,
            quantitative_analysis_tool
        ],
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_risk_advisor_agent(llm) -> Agent:
    """
    Risk & Investment Advisor - 신중한 관리자
    전략의 리스크를 검증하고 최종 투자의견 결정
    """
    return Agent(
        role="Risk & Investment Advisor",
        goal="Assess risks associated with proposed strategies and make final investment recommendations",
        backstory="""You are a seasoned investment advisor with a strong focus on risk management. 
        You critically evaluate trading strategies proposed by the quantitative team, looking for 
        potential pitfalls such as: market volatility, negative news sentiment, legal issues, 
        macroeconomic shocks, and valuation concerns. You balance potential returns against risks 
        to provide prudent investment advice. Your final recommendations (Buy/Hold/Sell) consider 
        both quantitative scores and qualitative risk factors. You always explain your reasoning 
        clearly, citing specific risks and opportunities.
        
        CRITICAL: Output your analysis in ENGLISH.""",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_report_writer_agent(llm) -> Agent:
    """
    Report Writer - 완벽주의 편집자
    모든 분석 내용을 JSON 포맷으로 변환
    """
    return Agent(
        role="Investment Report Writer",
        goal="Synthesize all analysis into a structured JSON report for the frontend system",
        backstory="""You are a meticulous financial report writer who specializes in creating 
        clear, structured investment reports. You take complex analysis from multiple analysts 
        and distill it into a precise JSON format that frontend systems can consume. You ensure 
        all required fields are present, numbers are accurate, and the narrative is coherent and 
        professional. You write in Korean (한국어) using polite language (존댓말) suitable for 
        individual investors. Your reports always include: market environment summary, company 
        analysis, 3-month outlook, risk factors, and actionable suggestions.""",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_all_agents(model_name: str = "gpt-4o"):
    """
    Create all agents with specified LLM model
    
    Args:
        model_name: OpenAI model name (default: gpt-4o)
    
    Returns:
        Dictionary of agents
    """
    llm = ChatOpenAI(model=model_name, temperature=0)
    
    return {
        "data_analyst": create_data_analyst_agent(llm),
        "news_analyst": create_news_analyst_agent(llm),
        "strategy_agent": create_strategy_agent(llm),
        "risk_advisor": create_risk_advisor_agent(llm),
        "report_writer": create_report_writer_agent(llm)
    }

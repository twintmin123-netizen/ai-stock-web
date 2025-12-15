"""
CrewAI Tasks Definition
"""

from crewai import Task


def create_data_collection_task(agent, ticker: str) -> Task:
    """
    Task 1: Market Research (Quantitative Data Only)
    Analyst가 가격, 시장 지표, 재무 데이터를 수집 (뉴스 제외)
    """
    return Task(
        description=f"""Collect comprehensive market data for stock ticker: {ticker}

**CRITICAL: You must analyze BOTH long-term (3 years) and short-term (3 months) perspectives.**

Your responsibilities:
1. **장기 분석 (3Y)**: Use the Stock Price Tool to fetch 3-year data
   - Calculate 3-year return
   - Identify long-term trend (상승/하락/횡보)
   - Analyze 200-day moving average relationship
   - Calculate long-term volatility
   
2. **단기 분석 (3M)**: Use the Stock Price Tool to fetch 3-month data
   - Calculate 1-week, 1-month, 3-month returns
   - Calculate RSI (Relative Strength Index)
   - Identify short-term volatility
   - Detect recent spikes/drops
   
3. **Market Indicators**: Use the Market Indicators Tool
   - For US stocks: SPY, QQQ, VIX, Fear & Greed Index
   - For Korean stocks (.KS, .KQ): KOSPI, KOSDAQ, VKOSPI, USD/KRW
   
4. **Fundamentals**: Use the Fundamentals Tool to fetch financial data
   - P/E Ratio (Price-to-Earnings)
   - P/B Ratio (Price-to-Book)
   - ROE (Return on Equity)
   - Market Capitalization
   - Dividend Yield
   - 52-week High/Low

Provide TWO SEPARATE summaries:
- [장기 분석 요약 (3Y)]: Long-term price trends, structural movements
- [단기 분석 요약 (3M)]: Short-term momentum, recent volatility

Be objective and data-driven. Include specific numbers and percentages.

**NOTE: Do NOT collect news. The News Analyst will handle that separately.**""",
        expected_output=f"""A detailed market research report for {ticker} with TWO SECTIONS:

[장기 분석 요약 (3Y)]:
- 3-year return and long-term trend direction
- 200-day MA analysis
- Long-term volatility assessment

[단기 분석 요약 (3M)]:
- 1w/1m/3m returns and RSI
- Short-term volatility and recent momentum shifts
- Market environment (benchmark indices)

- Fundamental metrics (P/E, P/B, ROE, etc.)""",
        agent=agent
    )


def create_news_analysis_task(agent, ticker: str) -> Task:
    """
    Task 2: News Analysis
    News Analyst가 뉴스를 수집하고 감정 분석 및 주요 이벤트 식별
    """
    return Task(
        description=f"""Analyze news and market sentiment for stock ticker: {ticker}

Your responsibilities:
1. **News Collection**: Use the News Search Tool to collect recent news articles (at least 10)

2. **Sentiment Analysis**: 
   - Analyze the overall sentiment of news articles
   - Provide a quantitative **News Sentiment Score (0-10)**:
     * 0-2: Extremely Negative (major scandals, bankruptcy risks, severe legal issues)
     * 3-4: Negative (disappointing earnings, downgrades, negative outlook)
     * 5: Neutral (mixed news or no significant events)
     * 6-7: Positive (good earnings, upgrades, positive partnerships)
     * 8-10: Extremely Positive (breakthrough products, major contracts, exceptional growth)

3. **High-Impact Events Identification**:
   - Flag any critical events that could significantly impact stock price:
     * Earnings surprises (beat/miss)
     * Regulatory changes or legal issues
     * Major partnerships or acquisitions
     * Product launches or failures
     * Management changes
     * Macroeconomic shocks affecting the sector

4. **Key Narratives**:
   - Summarize the main themes/narratives in recent news
   - Identify any emerging risks or opportunities

5. **News Summary**:
   - List 5-10 most relevant news articles
   - For each article, provide: title/topic and sentiment tag [Positive/Neutral/Negative]

**IMPORTANT OUTPUT FORMAT**:
Use this EXACT structure with clear headers and bullet points:

News Sentiment Score: X/10

High-Impact Events:
- [Event 1 description]
- [Event 2 description]
(or "None identified" if no high-impact events)

Key Narratives:
- [Narrative 1]: [Description]
- [Narrative 2]: [Description]
- [Narrative 3]: [Description]

News Summary:
1. [News topic/headline]: [Brief description]. [Sentiment: Positive/Neutral/Negative]
2. [News topic/headline]: [Brief description]. [Sentiment: Positive/Neutral/Negative]
3. [News topic/headline]: [Brief description]. [Sentiment: Positive/Neutral/Negative]
...

Be specific and cite actual news headlines when possible.""",
        expected_output=f"""A comprehensive news analysis report for {ticker} with this EXACT format:

News Sentiment Score: X/10

High-Impact Events:
- List of critical events with potential price impact
- Use bullet points for each event
- Write "None identified" if no significant events

Key Narratives:
- Theme 1: Description
- Theme 2: Description
- Theme 3: Description

News Summary:
1. Topic: Description. [Sentiment: Positive/Neutral/Negative]
2. Topic: Description. [Sentiment: Positive/Neutral/Negative]
3. Topic: Description. [Sentiment: Positive/Neutral/Negative]
4. Topic: Description. [Sentiment: Positive/Neutral/Negative]
5. Topic: Description. [Sentiment: Positive/Neutral/Negative]

Use clear headers, bullet points, and numbered lists for readability.""",
        agent=agent
    )


def create_strategy_development_task(agent, ticker: str) -> Task:
    """
    Task 3: Strategy Development
    Strategy Agent가 정량적 점수를 계산하고 1차 전략 제안
    """
    return Task(
        description=f"""Based on the Market Data Analyst's research and News Analyst's sentiment analysis for {ticker}, develop a quantitative trading strategy.
        
        
**CRITICAL: Consider BOTH long-term (3Y) and short-term (3M) perspectives when scoring.**

Your responsibilities:
1. **STEP 1: Calculate Base Scores (MANDATORY)**
   - **MUST Use the 'Quantitative Analysis Tool' first.**
   - This tool runs the exact mathematical models from the legacy system.
   - extract the Market Score, Company Score, and Outlook Score from its output.
   - Use these as your STARTING POINT.

2. **STEP 2: Qualitative Adjustment**
   - Adjust the base scores ONLY if you have strong evidence from News or Long-term trends.
   - Example: If Base Company Score is 5, but news is extremely positive, you may upgrade to 6 or 7.
   - Example: If Base Market Score is 8, but macro news is scary, you may downgrade to 7.
   - **Do NOT deviate more than +/- 2 points without a very strong reason.**

3. Calculate Industry/Sector Score (0-10):
   - **For US stocks**: Use the Sector Analysis Tool to analyze sector performance
   - **For Korean stocks**: Leave as None (fallback to company score)
   - Sector score reflects tailwinds/headwinds in the stock's industry
   - Interpretation:
     * Score 8-10: Strong sector tailwind
     * Score 5-7: Sector neutral
     * Score 0-4: Sector headwind
   
4. Finalize Scores:
   - Market Score (0-10)
   - Company Score (0-10)
   - Outlook Score (0-10)
   
5. **MANDATORY**: Use the Decision Fusion Calculator tool to determine the final action:
   
4. Calculate Outlook Score (0-10):
   - **Long-term outlook**: Is the 3-year trend supportive?
   - **Short-term outlook**: 3-month expected return, alpha vs. benchmark
   - **News Impact**: Consider High-Impact Events from the News Analyst
   - Combine both perspectives
   
5. **MANDATORY**: Use the Decision Fusion Calculator tool to determine the final action:
   - Input your calculated scores: market_score, company_score, outlook_score, industry_score (if available)
   - The tool will apply probabilistic fusion logic to compute:
     * Final Action (적극적 매수/소극적 매수/현상 유지/소극적 매도/적극적 매도)
     * Rise Probability (p_up)
     * Confidence level
   - **DO NOT manually decide the action based on text rules**
   - Copy the tool's "Final Action" output exactly as your "Initial Action Recommendation"

Scoring Guidelines:
- 8-10: Very Strong (bullish long-term trend + positive short-term momentum + positive news)
- 5-7: Moderate (mixed signals or neutral conditions)
- 0-4: Weak (bearish long-term trend or negative short-term momentum or negative news)

Provide clear numerical scores explaining how long-term, short-term, and news factors influenced each score.""",
        expected_output=f"""A quantitative strategy report for {ticker} with this EXACT format:

Market Score: X/10
Industry Score: X/10 (or "None" for Korean stocks)
Company Score: X/10
Outlook Score: X/10

Market Analysis Brief:
- Key market conditions affecting score

Industry Analysis Brief (if applicable):
- Sector tailwind/headwind assessment
- Relative sector performance

Company Analysis Brief:
- Long-term positioning
- Short-term momentum
- News sentiment impact

Outlook Brief:
- Expected trajectory (long + short term)

Strategy Opinion (Action derived from Tool): [Copy from Decision Fusion Calculator tool output]
Rise Probability (p_up): [From tool]
Confidence: [From tool]

(Note: This will be reviewed by the Risk Advisor)

**CRITICAL**: You MUST call the Decision Fusion Calculator tool with your scores. The "Initial Action Recommendation" must come from the tool, not from manual judgment.""",
        agent=agent
    )


def create_risk_assessment_task(agent, ticker: str) -> Task:
    """
    Task 4: Risk Assessment & Decision
    Advisor가 1차 전략의 리스크를 체크하고 최종 Action 확정
    """
    return Task(
        description=f"""Review the proposed trading strategy for {ticker} and conduct a thorough risk assessment.

**CRITICAL INSTRUCTION**: 
- The Strategy Developer has already determined the Final Action using the Decision Fusion Calculator tool
- Your role is to VALIDATE and ADD CONTEXT, NOT to override the decision
- You may ONLY suggest caution or add risk warnings
- DO NOT change the action unless there is an EXTREME risk (e.g., bankruptcy, fraud, major legal crisis)

**CRITICAL: Assess risks from BOTH long-term (3Y) and short-term (3M) perspectives, AND incorporate the News Analyst's findings.**

Your responsibilities:
1. Evaluate risks across different time horizons:
   
   **장기 리스크 (3Y)**:
   - Is the long-term trend sustainable?
   - Structural industry risks
   - Long-term valuation concerns (P/E extremes)
   - Macroeconomic headwinds (interest rate cycles, regulation)
   
   **단기 리스크 (3M)**:
   - Short-term volatility spikes (VIX, VKOSPI)
   - Short-term overbought/oversold conditions (RSI)
   - Immediate market sentiment shifts
   
   **뉴스 기반 리스크**:
   - **IMPORTANT**: Review the High-Impact Events from the News Analyst
   - Assess the severity and likelihood of each event
   - Consider legal issues, regulatory changes, earnings misses, etc.
   
2. **VALIDATE** the Strategy Developer's action:
   - Review if the Decision Fusion Calculator's output is reasonable given the risks
   - The action is based on probabilistic fusion (p_up, confidence) - respect this scientific approach
   - Only flag EXTREME risks that would invalidate the decision
   
3. Provide risk-adjusted guidance:
   - If action is "적극적 매수" but risks are high → Add warning: "High risk - consider smaller position size"
   - If action is "현상 유지" but risks are low → Confirm: "Hold is prudent given current conditions"
   - If action is "매도" but risks are manageable → Confirm: "Sell is appropriate despite moderate risks"
   - **DO NOT downgrade the action** unless there is extreme risk (bankruptcy, fraud, major crisis)

4. Identify monitoring points:
   - Long-term: What trend changes should trigger re-evaluation?
   - Short-term: What volatility levels should trigger caution?
   - News-based: What events should trigger immediate action?

Be investor-focused and provide context, but RESPECT the Decision Fusion Calculator's output.""",
        expected_output=f"""Risk assessment and final recommendation for {ticker}:
- Risk Level: [Low/Medium/High] (separately assess long-term vs short-term vs news-based)
- 장기 리스크 요인: List 2-3 long-term structural risks
- 단기 리스크 요인: List 2-3 short-term volatility/momentum risks
- 뉴스 기반 리스크: List high-impact events from News Analyst (if any)
- **Final Decision (Validated from Tool): [COPY from Strategy Developer's output - DO NOT CHANGE unless extreme risk]**
- Risk-Adjusted Guidance: [Add warnings or confirmations based on risk level]
- Time-Horizon-Specific Advice: 
  - Long-term holders: What to watch
  - Short-term traders: What to watch
  - Event-driven risks: What to monitor
- Confidence Level: [High/Medium/Low] (based on risk assessment)

**IMPORTANT**: The Final Action should match the Strategy Developer's Decision Fusion Calculator output.
Only override if there is EXTREME risk (bankruptcy, fraud, major legal crisis).
Otherwise, keep the action and add risk warnings in "Risk-Adjusted Guidance".""",
        agent=agent
    )


def create_report_writing_task(agent, ticker: str) -> Task:
    """
    Task 4: Final Reporting
    Writer가 모든 정보를 종합하여 최종 JSON 생성
    """
    return Task(
        description=f"""Synthesize all analysis for {ticker} into a structured JSON report for the frontend.

**CRITICAL REQUIREMENT: overall_comment MUST include both long-term (3Y) and short-term (3M) perspectives.**

You must compile information from:
1. Market Data Analyst's research (both 3Y and 3M data)
2. Strategy Developer's quantitative scores (considering both time horizons)
3. Risk Advisor's final recommendation (long-term and short-term risks)

Create a JSON report with the following structure:
{{
    "action": "[추가 매수/현상 유지/매도]",
    "market_score": <number 0-10>,
    "company_score": <number 0-10>,
    "outlook_score": <number 0-10>,
    "decision_prob": <number 0-1 (e.g. 0.75)>,
    "confidence": <number 0-1 (e.g. 0.85)>,
    "overall_comment": {{
        "summary": "핵심 결론 (MUST mention both 장기 방향성 + 단기 대응 전략)",
        "market_env": "시장 환경 요약 (MUST include both long-term and short-term market conditions)",
        "company_summary": "개별 종목 요약 (MUST include [장기 분석 요약 (3Y)] and [단기 분석 요약 (3M)] AND fundamentals like P/E, P/B, ROE)",
        "outlook_3m": "3개월 전망 (short-term forward outlook)",
        "risks": "리스크 요인 (MUST separate 장기 리스크 and 단기 리스크)",
        "suggestion": "대응 제안 (MUST NOT repeat the Buy/Sell action. Focus on EXECUTION strategy, e.g., '분할 매수', '지지선 확인 후 진입', '리스크 관리 위주 대응')"
    }}
}}

**TONE & STYLE GUIDELINES for overall_comment fields:**

**CRITICAL PRINCIPLE: Write a UNIQUE story for each stock. Do NOT use template language.**

Your writing should dynamically adapt based on the stock's specific situation:

1. **summary**: 
   - Synthesize the ESSENCE of this stock's investment story
   - MUST weave together: long-term trend (3Y) + short-term momentum (3M) + news context
   - DO NOT use rigid "[장기적으로]...[단기적으로]..." brackets unless it feels natural
   - Instead, tell a coherent narrative that flows naturally
   
   **Style Variations by Scenario:**
   - **Crisis/High Risk**: Use cautious, warning tone. E.g., "실적 부진과 업황 악화로 주가가 급락세를 보이고 있어 신중한 접근이 필요합니다."
   - **Growth Opportunity**: Use optimistic, forward-looking tone. E.g., "신제품 출시와 실적 개선 기대감으로 상승 모멘텀이 강화되고 있습니다."
   - **Neutral/Mixed**: Use balanced, analytical tone. E.g., "단기 변동성은 있으나 펀더멘털은 안정적이어서 중장기 관점의 접근이 유효합니다."
   
2. **company_summary**: 
   - Tell the company's story through data
   - MUST include: 3-year performance, recent 3-month momentum, fundamental metrics (P/E, P/B, ROE)
   - But integrate them naturally, not as separate labeled sections
   - Example: "지난 3년간 +45% 상승하며 장기 상승 추세를 유지했으나, 최근 3개월은 -8% 조정을 받았습니다. RSI 72로 과매수 구간이며, P/E 25배, P/B 3.2배로 밸류에이션 부담이 있습니다."
   
3. **outlook_3m** (SHORT-TERM OUTLOOK): 
   - **CRITICAL**: This section MUST synthesize the News Analyst's findings with market data
   - DO NOT write generic statements like "중립적 전망" or "관망 필요"
   - MUST reference specific news items from the News Analyst's "Key Narratives" and "High-Impact Events"
   - Explain the SHORT-TERM (3-month) outlook based on:
     * News Analyst's sentiment score and key narratives
     * High-impact events (earnings, product launches, regulatory changes, etc.)
     * Short-term technical indicators (RSI, momentum, volatility)
     * Market environment (VIX, sector trends)
   
   **Examples of GOOD outlook_3m:**
   - "실적 서프라이즈와 신제품 출시 호재로 단기 상승 모멘텀이 강화될 것으로 예상됩니다. 다만 RSI 과매수 구간 진입으로 단기 조정 가능성도 염두에 두어야 합니다."
   - "CEO 교체 이슈와 규제 리스크로 단기 변동성이 확대될 전망입니다. 뉴스 흐름을 주시하며 방어적 대응이 필요합니다."
   - "특별한 뉴스 이슈 없이 기술적 조정 국면입니다. 지지선 테스트 후 반등 여부를 확인하는 것이 중요합니다."
   
   **BAD outlook_3m (DO NOT WRITE LIKE THIS):**
   - "중립적 전망입니다." ❌
   - "관망이 필요합니다." ❌
   - "시장 상황을 지켜봐야 합니다." ❌
   
4. **risks**: 
   - Identify SPECIFIC risks, not generic ones
   - Separate long-term structural risks from short-term volatility risks
   - Reference actual news events if they pose risks
   
5. **suggestion**: 
   - Provide ACTIONABLE execution strategy, NOT just "Buy" or "Sell"
   - Use Action Profile's execution strategy from Quantitative Tool as a foundation
   - Add news-specific monitoring guidance if relevant
   - Examples: "분할 매수로 평단가를 낮추되, 실적 발표 전까지는 소량만 진입하세요.", "지지선 확인 후 반등 시 추가 매수를 고려하세요."

**Writing Principles:**
- Use polite Korean (존댓말)
- Include specific numbers and percentages (e.g., "3년 수익률 +45%", "RSI 72")
- Cite actual news headlines or events when available
- Write as if explaining to an intelligent investor, not reading from a template
- Each stock should feel DIFFERENT - vary sentence structure, emphasis, and tone
- Ensure JSON is valid and properly formatted
- **MANDATORY**: outlook_3m MUST use News Analyst's data - do not write generic outlooks""",
        expected_output=f"""Valid JSON report for {ticker} with all required fields populated.

The overall_comment MUST contain:
1. **summary**: A unique narrative that naturally integrates long-term trend, short-term momentum, and news context
2. **company_summary**: 3-year performance, 3-month momentum, and fundamentals (P/E, P/B, ROE) woven into a natural story
3. **outlook_3m**: News-driven short-term outlook citing specific events from News Analyst (NOT generic statements)
4. **risks**: Specific, actionable risk factors separated by time horizon
5. **suggestion**: Execution strategy with actionable guidance (NOT just "Buy" or "Sell")

**CRITICAL**: outlook_3m MUST reference News Analyst's Key Narratives and High-Impact Events.

All text fields in Korean (존댓말), all scores as numbers.
Each stock's report should feel UNIQUE and tailored to its specific situation.
The report must be ready for direct consumption by the frontend system.""",
        agent=agent
    )


def create_all_tasks(agents: dict, ticker: str) -> list:
    """
    Create all tasks for the given ticker
    
    Args:
        agents: Dictionary of agents
        ticker: Stock ticker symbol
    
    Returns:
        List of tasks in execution order
    """
    return [
        create_data_collection_task(agents["data_analyst"], ticker),
        create_news_analysis_task(agents["news_analyst"], ticker),
        create_strategy_development_task(agents["strategy_agent"], ticker),
        create_risk_assessment_task(agents["risk_advisor"], ticker),
        create_report_writing_task(agents["report_writer"], ticker)
    ]

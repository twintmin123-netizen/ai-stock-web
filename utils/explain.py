# utils/explain.py

from __future__ import annotations

import math
import textwrap
from typing import Any

from .common import to_number
from .config import client, OPENAI_CHAT_MODEL
from .fgi import get_fgi_category


# ─────────────────────────────
# 1) 최근 주가 흐름 설명
# ─────────────────────────────
def build_move_explanation(
    ticker: str,
    ret_1w: float | int | None,
    ret_1m: float | int | None,
    spy_ret_1m: float | int | None,
    qqq_ret_1m: float | int | None,
    fgi_score: float | int | None,
    news_list: list[dict[str, Any]] | None,
) -> dict[str, str]:
    """
    가격 흐름 요약용 텍스트를 구성한다.
    - one_week: 최근 1주일
    - one_month: 최근 1개월
    """

    def fmt_ret(x: float | int | None) -> str:
        """수익률 포맷 (None/nan 처리 포함)."""
        if x is None:
            return "N/A"
        try:
            v = float(x)
        except Exception:
            return "N/A"
        if math.isnan(v):
            return "N/A"
        return f"{v:.2f}"

    def short_news_summary(news: list[dict[str, Any]] | None, limit: int = 3) -> str:
        if not news:
            return "최근 뉴스 데이터가 충분하지 않습니다."
        parts = []
        for n in news[:limit]:
            title = n.get("title_ko") or n.get("title") or ""
            src = n.get("source") or ""
            dt = n.get("published_at") or ""
            if src and dt:
                parts.append(f"- {title} ({src} | {dt})")
            elif src:
                parts.append(f"- {title} ({src})")
            else:
                parts.append(f"- {title}")
        return "\n".join(parts)

    one_week = textwrap.dedent(
        f"""
        • 종목: {ticker}
        • 최근 1주 수익률: {fmt_ret(ret_1w)} %

        해당 기간 동안 지수/뉴스 영향을 함께 감안해 단기적인 흐름을 요약한 내용입니다.
        """
    ).strip()

    one_month = textwrap.dedent(
        f"""
        • 종목: {ticker}
        • 최근 1개월 수익률: {fmt_ret(ret_1m)} %
        • 같은 기간 S&P500(대용 SPY) 수익률: {fmt_ret(spy_ret_1m)} %
        • 같은 기간 나스닥(대용 QQQ) 수익률: {fmt_ret(qqq_ret_1m)} %
        • CNN 공포·탐욕 지수: {fmt_ret(fgi_score)}

        최근 한 달 동안 종목의 주가 흐름이 벤치마크 지수와 비교하여 어떤지,
        그리고 시장 심리(공포/탐욕)가 어느 정도 수준이었는지를 함께 고려해 해석합니다.

        최근 관련 뉴스 요약:
        {short_news_summary(news_list)}
        """
    ).strip()

    return {
        "one_week": one_week,
        "one_month": one_month,
    }


# ─────────────────────────────
# 2) OpenAI 기반 메인 코멘트 생성
# ─────────────────────────────
def generate_comment_with_openai(
    ticker: str,
    action: str,
    market_score: int | float | None,
    company_score: int | float | None,
    ret_1w: float | int | None,
    ret_1m: float | int | None,
    spy_ret_1m: float | int | None,
    qqq_ret_1m: float | int | None,
    fgi_score: float | int | None,
    fgi_rating_kor: str,
    move_explain: dict[str, str],
    outlook_score: int | float | None,
    news_summary: str | None = None,
    decision_breakdown: dict[str, Any] | None = None,
    agent_insights: dict[str, str] | None = None,
) -> str:
    """
    시장 점수·종목 점수·수익률·FGI·3개월 전망 및 확률적 판단 근거를 바탕으로
    투자 코멘트를 한글로 생성.
    
    뉴스 분석 결과를 활용하여 3개월 전망을 제시합니다.
    """

    # 숫자 정리
    m_score = to_number(market_score)
    c_score = to_number(company_score)
    r1w = to_number(ret_1w)
    r1m = to_number(ret_1m)
    spy1m = to_number(spy_ret_1m)
    qqq1m = to_number(qqq_ret_1m)
    fgi = to_number(fgi_score)
    o_score = to_number(outlook_score)

    # FGI 등급 텍스트 정리
    if not math.isnan(fgi):
        _, fgi_kor = get_fgi_category(fgi)
    else:
        fgi_kor = fgi_rating_kor or "정보 없음"

    def fmt(x: float | int | None, pct: bool = True) -> str:
        """숫자 포맷 통일 (None/nan 처리)."""
        if x is None:
            return "N/A"
        try:
            v = float(x)
        except Exception:
            return "N/A"
        if math.isnan(v):
            return "N/A"
        if pct:
            return f"{v:.2f}"
        return f"{v:.2f}"

    one_week_txt = move_explain.get("one_week", "")
    one_month_txt = move_explain.get("one_month", "")

    system_prompt = textwrap.dedent(
        """
        너는 개인 투자자를 위한 한국어 투자 코멘트 작성 어시스턴트다.
        제공된 정보를 바탕으로 투자 판단을 내리고, 이를 구조화된 JSON 형식으로 반환해야 한다.

        반환해야 할 JSON 구조:
        {
            "summary": "핵심 결론 (한 문단으로 유지/매수/매도/관망 스탠스 요약)",
            "market_env": "시장 환경 요약 (시장 점수, 지수 수익률 기반 분위기 설명)",
            "company_summary": "개별 종목 요약 (수익률, 상대 성과 설명)",
            "outlook_3m": "단기적 전망 (전망 점수와 뉴스 분석 기반으로 향후 전망 제시. 기대 수익률은 언급하지 말 것)",
            "risks": "리스크 요인 (변동성, 거시 환경, 밸류에이션 등)",
            "suggestion": "대응 제안 (단기 관점의 행동 가이드)"
        }

        작성 원칙:
        - 존댓말 사용, 금융 용어는 쉽게 풀어서 설명
        - 구체적인 수치(수익률, 점수)를 문장에 자연스럽게 포함
        - 과도한 확신보다는 가능성과 리스크를 함께 언급
        - JSON 형식을 엄격히 준수할 것
        - 단기적 전망은 뉴스 분석과 전망 점수를 바탕으로 작성하되, 기대 수익률은 절대 언급하지 말 것

        [AI 에이전트 심층 분석 결과 반영 지침] - 중요!!!
        - 'AI 에이전트 심층 분석 결과'가 제공될 경우, 해당 내용을 **최우선 순위**로 반영해야 한다.
        - 단순 통계(수익률, 점수)가 에이전트의 정성적 분석(기술적 분석, 리스크 평가)과 상충될 경우, 에이전트의 분석을 따른다.
        - 에이전트가 지적한 '기술적 신호'와 '리스크 요인'은 반드시 코멘트에 구체적으로 인용해야 한다.
        
        시장 구분:
        - 한국 주식: KOSPI, KOSDAQ 지수와 비교 분석
        - 미국 주식: S&P500(SPY), 나스닥(QQQ) 지수와 비교 분석
        - FGI(공포·탐욕 지수)는 미국 시장 지표이므로 한국 주식 분석 시 참고만 할 것
        """
    ).strip()

    # Determine if Korean stock
    is_korean = ticker.endswith('.KS') or ticker.endswith('.KQ')
    
    # Set market index names based on stock type
    if is_korean:
        index1_name = "KOSPI"
        index2_name = "KOSDAQ"
    else:
        index1_name = "S&P500 (SPY)"
        index2_name = "나스닥 (QQQ)"
    
    user_prompt = textwrap.dedent(
        f"""
        [기본 정보]
        - 종목 티커: {ticker}
        - 시장: {"한국" if is_korean else "미국"}
        - 최종 액션: {action}

        [점수]
        - 시장: {fmt(m_score, pct=False)}/10
        - 종목: {fmt(c_score, pct=False)}/10
        - 전망: {fmt(o_score, pct=False)}/10

        [수익률]
        - 1주: {fmt(r1w)}%
        - 1개월: {fmt(r1m)}%
        - {index1_name} 1개월: {fmt(spy1m)}%
        - {index2_name} 1개월: {fmt(qqq1m)}%

        [심리]
        - FGI: {fmt(fgi, pct=False)} ({fgi_kor}) {"(미국 시장 지표)" if is_korean else ""}

        [최근 흐름]
        {one_week_txt}
        {one_month_txt}
        """
    ).strip()
    
    # Add news summary if available
    if news_summary:
        user_prompt += f"\n\n[뉴스 분석 결과]\n{news_summary}"

    # Add Agent Insights if available
    if agent_insights:
        user_prompt += "\n\n[AI 에이전트 심층 분석 결과]"
        if agent_insights.get("technical_analysis"):
             user_prompt += f"\n- 기술적 분석 요약:\n{agent_insights['technical_analysis']}"
        if agent_insights.get("risk_analysis"):
             user_prompt += f"\n- 리스크 평가:\n{agent_insights['risk_analysis']}"
        if agent_insights.get("market_analysis"):
             user_prompt += f"\n- 시장 심층 분석:\n{agent_insights['market_analysis']}"

    # Add Breakdown Context
    if decision_breakdown:
        p_up = decision_breakdown.get('p_up', 0)
        conf = decision_breakdown.get('confidence', 0)
        conf_lvl = decision_breakdown.get('confidence_level', 'Unknown')
        flags = decision_breakdown.get('flags', [])
        
        breakdown_txt = textwrap.dedent(
            f"""
            [확률적 판단 메커니즘 (WCN-LSTM 로직 기반)]
            - 매수 매력도(p_up): {p_up:.4f}
            - 분석 일관성: {conf:.4f} ({conf_lvl})
            - 주요 감지 플래그: {', '.join(flags) if flags else '없음'}
            """
        ).strip()
        
        user_prompt += f"\n\n{breakdown_txt}"

    user_prompt = user_prompt.strip()

    try:
        completion = client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        content = completion.choices[0].message.content
    except Exception as e:
        # Fallback for errors or non-JSON models
        content = f"분석 생성 중 오류가 발생했습니다: {str(e)}"
    
    return content

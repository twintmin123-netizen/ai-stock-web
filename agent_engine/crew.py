"""
CrewAI Crew Configuration and Execution
Main entry point for agentic analysis
"""

from crewai import Crew, Process
from .agents import create_all_agents
from .tasks import create_all_tasks
import json
import re


def run_agentic_analysis(ticker: str, model_name: str = "gpt-4o") -> dict:
    """
    Run the complete agentic analysis for a given stock ticker.
    
    This function orchestrates a team of 4 AI agents:
    1. Market Data Analyst - Collects data
    2. Trading Strategy Developer - Calculates scores and proposes strategy
    3. Risk & Investment Advisor - Assesses risks and finalizes recommendation
    4. Report Writer - Synthesizes everything into JSON
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', '005930.KS')
        model_name: OpenAI model to use (default: 'gpt-4o')
    
    Returns:
        Dictionary with analysis results in the format expected by the API
    
    Raises:
        Exception: If crew execution fails
    """
    print(f"\n{'='*60}")
    print(f"🚀 Starting Agentic Analysis for {ticker}")
    print(f"{'='*60}\n")
    
    try:
        # Create agents
        print("📋 Creating AI agents...")
        agents = create_all_agents(model_name=model_name)
        
        # Create tasks
        print(f"📝 Creating tasks for {ticker}...")
        tasks = create_all_tasks(agents, ticker)
        
        # Create crew
        print("👥 Assembling crew...")
        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process.sequential,  # Tasks execute in order
            verbose=True
        )
        
        # Execute crew
        print(f"\n🎬 Crew starting analysis for {ticker}...\n")
        result = crew.kickoff()
        
        print(f"\n{'='*60}")
        print(f"✅ Analysis Complete for {ticker}")
        print(f"{'='*60}\n")
        
        # Parse the result
        parsed_result = parse_crew_output(result, ticker)
        
        # Collect agent logs/outputs from tasks
        agent_logs = []
        
        # Manual Korean translation mapping for agent roles
        role_translation = {
            "Market Data Analyst": "시장 데이터 분석가",
            "Market News Analyst": "시장 뉴스 분석가",
            "Trading Strategy Developer": "트레이딩 전략 개발자",
            "Risk & Investment Advisor": "리스크 및 투자 어드바이저",
            "Risk and Investment Advisor": "리스크 및 투자 어드바이저", # Fallback for potential variations
            "Investment Report Writer": "투자 보고서 작성자"
        }
        
        # Create normalized mapping for robust lookup
        role_translation_norm = {k.lower().strip(): v for k, v in role_translation.items()}
        
        for task in crew.tasks:
            # Determine agent role/name
            agent_role = task.agent.role if task.agent else "Unknown Agent"
            
            # Get the output
            # In some versions of CrewAI, task.output is a TaskOutput object, in others it's a string
            output_content = ""
            if hasattr(task, 'output'):
                if hasattr(task.output, 'raw'):
                    output_content = task.output.raw
                else:
                    output_content = str(task.output)
            
            # Translate agent role to Korean (manual mapping only)
            agent_role_clean = agent_role.strip()
            agent_role_lower = agent_role_clean.lower()
            
            if agent_role_lower in role_translation_norm:
                agent_role_kr = role_translation_norm[agent_role_lower]
            else:
                # If not in manual mapping, use English as fallback
                agent_role_kr = agent_role_clean
            
            # Format: "한국어 이름 (English Name)"
            display_name = f"{agent_role_kr} ({agent_role_clean})"
            
            # Store original output without translation (for on-demand translation)
            agent_logs.append({
                "step_name": display_name,
                "output": output_content,  # Original English content
                "translated": False  # Flag to indicate not yet translated
            })
            print(f"📝 Captured log for {agent_role}: {len(output_content)} chars (original)")
            
        print(f"✅ Total agent logs captured: {len(agent_logs)}")
        
        # ---------------------------------------------------------
        # SSOT Enforcement & Disagreement Detection
        # ---------------------------------------------------------
        ssot_action = None
        
        # 1. Extract SSOT from Strategy Agent
        strategy_log = next((log for log in agent_logs if "Trading Strategy Developer" in log["step_name"] or "트레이딩 전략 개발자" in log["step_name"]), None)
        
        if strategy_log:
            content = strategy_log["output"]
            # Regex to find SSOT values
            # Format: "Strategy Opinion (Action derived from Tool): 매수"
            action_match = re.search(r"Strategy Opinion.*?:\s*(.*)", content)
            prob_match = re.search(r"Rise Probability.*?:\s*([0-9\.]+)", content)
            conf_match = re.search(r"Confidence.*?:\s*([0-9\.]+)", content)
            
            if action_match:
                ssot_action = action_match.group(1).strip()
                # Remove markdown bold/italics description
                ssot_action = ssot_action.replace("**", "").replace("*", "").split("(")[0].strip() # e.g. "매수 (Buy)" -> "매수"
                parsed_result["action"] = ssot_action
                print(f"🔒 SSOT Action applied: {ssot_action}")
                
            if prob_match:
                try:
                    ssot_prob = float(prob_match.group(1))
                    parsed_result["decision_prob"] = ssot_prob
                except: pass
                
            if conf_match:
                try:
                    ssot_conf = float(conf_match.group(1))
                    parsed_result["confidence"] = ssot_conf
                except: pass
                
            # Extract Semantic Flags and Enhanced Action Profile
            flags = []
            action_profile_data = {}
            
            # Look for SEMANTIC FLAGS in Quantitative Tool output
            semantic_flag_match = re.search(r"SEMANTIC FLAGS \((\d+)\):(.*?)(?:\n\n|\n5\.|$)", content, re.DOTALL)
            if semantic_flag_match:
                flag_text = semantic_flag_match.group(2).strip()
                # Split by comma and clean
                flags = [f.strip() for f in flag_text.split(',') if f.strip() and f.strip() != 'None']
            
            # Look for ENHANCED ACTION PROFILE with all fields
            profile_id_match = re.search(r"ACTION PROFILE:\s*(\w+)", content)
            profile_decision_match = re.search(r"Decision:\s*(.+?)(?:\n|$)", content)
            profile_exec_style_match = re.search(r"Execution Style:\s*(.+?)(?:\n|$)", content)
            profile_sizing_match = re.search(r"Position Sizing:\s*(.+?)(?:\n|$)", content)
            profile_summary_match = re.search(r"Summary:\s*(.+?)(?:\n|$)", content)
            profile_risk_match = re.search(r"Risk Note:\s*(.+?)(?:\n|$)", content)
            profile_invalidators_match = re.search(r"Invalidators:\s*(.+?)(?:\n|$)", content)
            profile_tp_match = re.search(r"Take Profit:\s*(.+?)(?:\n|$)", content)
            profile_stop_match = re.search(r"Stop Rule:\s*(.+?)(?:\n|$)", content)
            
            if profile_id_match:
                action_profile_data = {
                    "id": profile_id_match.group(1).strip(),
                    "decision_action": profile_decision_match.group(1).strip() if profile_decision_match else "",
                    "execution_style": profile_exec_style_match.group(1).strip() if profile_exec_style_match else "",
                    "position_sizing": profile_sizing_match.group(1).strip() if profile_sizing_match else "",
                    "summary": profile_summary_match.group(1).strip() if profile_summary_match else "",
                    "risk_note": profile_risk_match.group(1).strip() if profile_risk_match else "",
                    "invalidators": profile_invalidators_match.group(1).strip().split(',') if profile_invalidators_match else [],
                    "take_profit_rule": profile_tp_match.group(1).strip() if profile_tp_match else "",
                    "stop_rule": profile_stop_match.group(1).strip() if profile_stop_match else ""
                }
            
            # Look for SPECIAL FLAGS (from DecisionFusionTool)
            special_flags = []
            special_flag_match = re.search(r"SPECIAL FLAGS:(.*?)(?:════|In summary|Strategy Opinion)", content, re.DOTALL)
            if special_flag_match:
                s_flag_text = special_flag_match.group(1)
                found_s_flags = re.findall(r"-\s*([a-zA-Z0-9_]+)", s_flag_text)
                special_flags = [f.strip() for f in found_s_flags if f.strip() and f.strip() != 'None']

            # Merge flags (Semantic + Special)
            all_flags = list(set(flags + special_flags))
            
            # Store in parsed result
            if "decision_breakdown" not in parsed_result:
                parsed_result["decision_breakdown"] = {}
            parsed_result["decision_breakdown"]["flags"] = all_flags
            
            if action_profile_data:
                parsed_result["action_profile"] = action_profile_data
            
            # *** FORCE exp_3m to None (DEPRECATED) ***
            parsed_result["exp_3m"] = None

        # 2. Check for Disagreements
        model_disagreement = False
        
        if ssot_action:
            for log in agent_logs:
                # Check Risk Advisor disagreement
                if "Risk & Investment Advisor" in log["step_name"] or "리스크 및 투자" in log["step_name"]:
                    # "Final Decision (Validated from Tool): 매수"
                    risk_match = re.search(r"Final Decision.*?:\s*(.*)", log["output"])
                    if risk_match:
                        risk_action = risk_match.group(1).replace("**", "").split("(")[0].strip()
                        # Strict check: Action must be identical or contained
                        # e.g. "적극적 매수" vs "매수" 
                        if ssot_action != risk_action:
                             model_disagreement = True
                             print(f"⚠️ Model Disagreement: Strategy='{ssot_action}' vs Risk='{risk_action}'")
        
        # 3. Apply Penalties
        if model_disagreement:
            if "decision_breakdown" not in parsed_result:
                parsed_result["decision_breakdown"] = {"flags": []}
            if "flags" not in parsed_result["decision_breakdown"]:
                 parsed_result["decision_breakdown"]["flags"] = []
            
            if "model_disagreement" not in parsed_result["decision_breakdown"]["flags"]:
                parsed_result["decision_breakdown"]["flags"].append("model_disagreement")
            
            # Downgrade Confidence (User Rule: min(conf, 0.69))
            cur_conf = parsed_result.get("confidence", 0.5)
            parsed_result["confidence"] = min(cur_conf, 0.69)
            
            # Downgrade Level
            cur_level = parsed_result.get("confidence_level", "중간")
            if cur_level == "높음":
                parsed_result["confidence_level"] = "중간"
            elif cur_level == "중간":
                parsed_result["confidence_level"] = "낮음"
            
            print(f"⚠️ Confidence downgraded to {parsed_result['confidence']} (Level: {parsed_result['confidence_level']}) due to disagreement.")

        parsed_result["agent_logs"] = agent_logs
        
        return parsed_result
        
    except Exception as e:
        print(f"\n❌ Error during agentic analysis: {str(e)}\n")
        raise


def parse_crew_output(crew_result, ticker: str) -> dict:
    """
    Parse the crew's output and extract the JSON report.
    
    The final task (Report Writer) should produce a JSON string.
    This function extracts and validates that JSON.
    
    Args:
        crew_result: Raw output from crew.kickoff()
        ticker: Stock ticker (for error messages)
    
    Returns:
        Parsed dictionary with analysis results
    """
    try:
        # crew_result might be a string or have a specific structure
        result_str = str(crew_result)
        
        print(f"📄 Raw crew output length: {len(result_str)} characters")
        print(f"📄 First 300 chars: {result_str[:300]}")
        
        # Strategy 1: Try to find JSON block with markdown code fence
        json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', result_str, re.IGNORECASE)
        if json_match:
            json_str = json_match.group(1)
            print("✅ Found JSON in markdown code block")
        else:
            # Strategy 2: Look for JSON pattern (action field is required)
            json_match = re.search(r'\{[\s\S]*?"action"[\s\S]*?\}', result_str)
            if json_match:
                # Find the complete JSON object
                start = json_match.start()
                # Count braces to find the complete object
                brace_count = 0
                end = start
                for i in range(start, len(result_str)):
                    if result_str[i] == '{':
                        brace_count += 1
                    elif result_str[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
                json_str = result_str[start:end]
                print("✅ Found JSON pattern in output")
            else:
                # Strategy 3: Try to parse the entire result as JSON
                print("⚠️ No JSON pattern found, trying to parse entire output")
                json_str = result_str
        
        # Clean up the JSON string
        json_str = json_str.strip()
        
        # Try to parse
        parsed = json.loads(json_str)
        
        # Validate required fields
        required_fields = ["action", "market_score", "company_score", "outlook_score", "overall_comment"]
        for field in required_fields:
            if field not in parsed:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate overall_comment structure
        comment_fields = ["summary", "market_env", "company_summary", "outlook_3m", "risks", "suggestion"]
        for field in comment_fields:
            if field not in parsed.get("overall_comment", {}):
                raise ValueError(f"Missing required comment field: {field}")
        
        print("✅ JSON report validated successfully")
        return parsed
        
    except json.JSONDecodeError as e:
        print(f"⚠️ Failed to parse JSON from crew output: {e}")
        print(f"📄 Attempted to parse: {json_str[:500] if 'json_str' in locals() else result_str[:500]}...")
        
        # Return a fallback structure
        return create_fallback_response(ticker, result_str)
    except Exception as e:
        print(f"⚠️ Error parsing crew output: {e}")
        return create_fallback_response(ticker, str(crew_result))


def create_fallback_response(ticker: str, raw_output: str) -> dict:
    """
    Create a fallback response if JSON parsing fails.
    
    Args:
        ticker: Stock ticker
        raw_output: Raw crew output
    
    Returns:
        Dictionary with fallback structure
    """
    return {
        "action": "현상 유지",
        "market_score": 5,
        "company_score": 5,
        "outlook_score": 5,
        "overall_comment": {
            "summary": f"{ticker}에 대한 AI 에이전트 분석이 완료되었으나, 결과 형식 변환 중 문제가 발생했습니다.",
            "market_env": "시장 환경 분석 중 오류가 발생했습니다.",
            "company_summary": "종목 분석 중 오류가 발생했습니다.",
            "outlook_3m": "전망 분석 중 오류가 발생했습니다.",
            "risks": "리스크 분석 중 오류가 발생했습니다.",
            "suggestion": "시스템 관리자에게 문의하시기 바랍니다."
        },
        "_raw_output": raw_output[:1000],  # Include first 1000 chars for debugging
        "_error": "JSON parsing failed, fallback response generated"
    }


# For testing purposes
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_ticker = sys.argv[1]
    else:
        test_ticker = "AAPL"
    
    print(f"Testing agentic analysis for {test_ticker}...")
    result = run_agentic_analysis(test_ticker)
    
    print("\n" + "="*60)
    print("FINAL RESULT:")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))

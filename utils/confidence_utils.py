"""
Confidence level mapping utility.
Single source of truth for confidence level labels.
"""

# Confidence thresholds (분리 가능하게 상수로 정의)
CONFIDENCE_THRESHOLDS = {
    "high": 0.85,      # >= 0.85: 높음
    "medium": 0.70,    # >= 0.70: 중간
    # < 0.70: 낮음
}


def map_confidence_level(confidence: float) -> str:
    """
    Map confidence score (0-1) to Korean confidence level.
    
    Single source of truth for confidence level mapping.
    MUST be used by all agents, reporters, and UI displays.
    
    Args:
        confidence: Confidence score between 0 and 1
    
    Returns:
        Korean confidence level: "높음", "중간", or "낮음"
    
    Examples:
        >>> map_confidence_level(0.90)
        '높음'
        >>> map_confidence_level(0.7667)
        '중간'
        >>> map_confidence_level(0.65)
        '낮음'
    """
    if confidence >= CONFIDENCE_THRESHOLDS["high"]:
        return "높음"
    elif confidence >= CONFIDENCE_THRESHOLDS["medium"]:
        return "중간"
    else:
        return "낮음"


def validate_no_exp3m_usage(variables_dict: dict):
    """
    Development guard: Raise error if exp_3m is being used.
    
    This prevents accidental usage of deprecated exp_3m in calculations.
    
    Args:
        variables_dict: Dictionary of variables to check
    
    Raises:
        RuntimeError: If exp_3m is found in variables
    """
    if "exp_3m" in variables_dict:
        exp_val = variables_dict["exp_3m"]
        if exp_val is not None and exp_val != 0:
            raise RuntimeError(
                f"exp_3m is DEPRECATED and must not be used in calculations. "
                f"Found value: {exp_val}. exp_3m must always be None."
            )


import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.score_fusion import compute_probabilities
from utils.finance_data import estimate_3m_outlook

class TestBusinessLogic(unittest.TestCase):
    
    def test_confidence_level_mapping(self):
        """Test updated confidence level thresholds."""
        # Case 1: p_up = 0.5 (Conf 0.0) -> "낮음" (<0.45)
        res1 = compute_probabilities(M=50, S=50, T=50) # Neutral
        # conf = abs(0.5-0.5)*2 = 0.0
        self.assertEqual(res1["confidence_level"], "낮음")
        
        # Case 2: p_up = 0.8 (Conf 0.6) -> "중간" (0.45 <= 0.6 < 0.75)
        # We need inputs that give p_up approx 0.8.
        # Let's mock the internal calculation or just check the logic function if accessible?
        # compute_probabilities is the public interface.
        # Let's try high scores. M=90, S=90, T=90 -> p_up roughly 0.9?
        res2 = compute_probabilities(M=90, S=90, T=90)
        # p_up should be high.
        p_up = res2["p_up"]
        conf = abs(p_up - 0.5) * 2.0
        # If conf > 0.75, it should be "높음"
        if conf >= 0.75:
            self.assertEqual(res2["confidence_level"], "높음")
        else:
            # If it's between 0.45 and 0.75
            self.assertEqual(res2["confidence_level"], "중간")
            
    def test_low_upside_flag(self):
        """Test 'low_upside_probability' flag generation."""
        # Low scores -> low p_up
        res = compute_probabilities(M=10, S=10, T=10)
        self.assertTrue(res["p_up"] <= 0.35)
        self.assertIn("low_upside_probability", res["breakdown"]["flags"])

    def test_exp_3m_null_handling(self):
        """Test estimate_3m_outlook returns None on empty data."""
        # Mock DataFrame
        df_empty = MagicMock()
        df_empty.empty = True
        
        exp, alpha = estimate_3m_outlook(df_empty)
        self.assertIsNone(exp)
        self.assertIsNone(alpha)
        
        # Test usage in tools (Simulated)
        # If exp is None, outlook score should be calculated with 0 but flagged?
        # This logic is in QuantitativeAnalysisTool, hard to unit test without instantiating tool.
        pass

if __name__ == '__main__':
    unittest.main()

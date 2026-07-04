import os
from unittest.mock import MagicMock, patch
import pytest
from phronel_ai_agent.core.llm_logger import log_dspy_history
from phronel_ai_agent.core.config import config

def test_log_dspy_history_creates_file(tmp_path):
    """
    Verify that log_dspy_history successfully creates the target directory
    and writes the LLM history containing the execution context.
    """
    test_log_dir = str(tmp_path / "test_llm_logs")
    
    with patch.object(config, "get", return_value=test_log_dir):
        # Call logging function
        log_dspy_history("Test.context")
        
        # Verify directory was created
        assert os.path.exists(test_log_dir)
        
        # Verify file was created for today
        files = os.listdir(test_log_dir)
        assert len(files) == 1
        assert files[0].startswith("llm_history_")
        assert files[0].endswith(".log")
        
        # Verify content contains our context and fallback string when no LM is present
        with open(os.path.join(test_log_dir, files[0]), "r", encoding="utf-8") as f:
            content = f.read()
            assert "CONTEXT   : Test.context" in content
            assert "No active DSPy Language Model configured." in content

def test_log_dspy_history_with_lm(tmp_path):
    """
    Verify that log_dspy_history successfully captures stdout from the active
    DSPy Language Model's inspect_history method and logs it.
    """
    test_log_dir = str(tmp_path / "test_llm_logs_lm")
    
    # Mock DSPy settings.lm and its inspect_history
    mock_lm = MagicMock()
    
    def mock_inspect(n):
        print(f"Mocked Prompt Interaction with n={n}")
        
    mock_lm.inspect_history = mock_inspect

    with patch.object(config, "get", return_value=test_log_dir):
        # Using patch to mock dspy.settings
        with patch("dspy.settings") as mock_settings:
            mock_settings.lm = mock_lm
            
            log_dspy_history("Test.with_lm")
            
            # Verify file was created and contains captured stdout from mock_inspect
            files = os.listdir(test_log_dir)
            assert len(files) == 1
            with open(os.path.join(test_log_dir, files[0]), "r", encoding="utf-8") as f:
                content = f.read()
                assert "CONTEXT   : Test.with_lm" in content
                assert "Mocked Prompt Interaction with n=1" in content

import os
import sys
import io
import dspy
import logging
from datetime import datetime
from .config import config

logger = logging.getLogger("phronel")

def log_dspy_history(context: str):
    """
    Captures the most recent DSPy LLM interaction (prompt and response)
    and appends it to a daily log file located in the directory specified
    by the 'llm_log_dir' setting (or PHRONEL_LLM_LOG_DIR env var).
    """
    try:
        # 1. Retrieve log directory from configuration (Fallback to 'logs/llm')
        log_dir = config.get("llm_log_dir", "logs/llm")
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"[LLM-Logger] Failed to create log directory '{log_dir}': {e}")
                return

        # 2. Generate daily log file path (e.g., logs/llm/llm_history_2026-06-27.log)
        today_str = datetime.now().strftime("%Y-%m-%d")
        log_file_path = os.path.join(log_dir, f"llm_history_{today_str}.log")

        # 3. Capture the latest DSPy history using inspect_history
        buffer = io.StringIO()
        
        # Safely access dspy settings and current LM
        lm = None
        if hasattr(dspy, "settings") and dspy.settings:
            lm = getattr(dspy.settings, "lm", None)

        if lm:
            try:
                # Redirect stdout to capture the output of inspect_history(n=1)
                original_stdout = sys.stdout
                sys.stdout = buffer
                lm.inspect_history(n=1)
            except Exception as e:
                buffer.write(f"Error capturing inspect_history: {e}\n")
            finally:
                sys.stdout = original_stdout
        else:
            buffer.write("No active DSPy Language Model configured.\n")

        captured_text = buffer.getvalue().strip()
        if not captured_text:
            captured_text = "No history output from DSPy LM. (Perhaps no LLM call was executed in this turn.)"

        # 4. Append to the daily log file
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"TIMESTAMP : {now_str}\n")
            f.write(f"CONTEXT   : {context}\n")
            f.write("-" * 80 + "\n")
            f.write(captured_text + "\n")
            f.write("=" * 80 + "\n\n")

        logger.debug(f"[LLM-Logger] Successfully logged DSPy interaction history to {log_file_path}")

    except Exception as e:
        logger.error(f"[LLM-Logger] Error logging DSPy history: {e}")

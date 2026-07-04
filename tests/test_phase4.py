import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import Session, create_engine, SQLModel
from datetime import datetime

from phronel_ai_agent.core.models import ActionLog, StrategyLog
import phronel_ai_agent.core.db as db
from phronel_ai_agent.skills.analyst import Analyst

sqlite_url = "sqlite:///:memory:"
test_engine = create_engine(sqlite_url)

@pytest.fixture(autouse=True)
def setup_test_db():
    original_engine = db.engine
    db.engine = test_engine
    SQLModel.metadata.create_all(test_engine)
    
    with Session(test_engine) as session:
        # Add some mock data
        now = datetime.utcnow()
        session.add(ActionLog(action_type="tweet", content="My test tweet", status="executed", executed_at=now, result_json='{"id": "12345"}'))
        session.add(StrategyLog(context_summary="Timeline", strategy_text="Talk about AI", model_name="gemini-2.5-flash", created_at=now))
        session.commit()

    yield
    
    SQLModel.metadata.drop_all(test_engine)
    db.engine = original_engine

@patch("phronel_ai_agent.skills.analyst.x_client.get_tweet_metrics")
def test_generate_daily_report(mock_get_metrics):
    mock_get_metrics.return_value = [{"id": "12345", "likes": 10, "retweets": 2}]
    
    analyst = Analyst()
    mock_prediction = MagicMock()
    mock_prediction.report_text = "Here is the daily report..."
    analyst.report_generator = MagicMock(return_value=mock_prediction)
    
    report = analyst.generate_daily_report()
    
    assert "Here is the daily report..." in report
    mock_get_metrics.assert_called_once_with(["12345"])
    analyst.report_generator.assert_called_once()
    
    # Check what was passed to DSPy
    args, kwargs = analyst.report_generator.call_args
    assert "Total Actions: 1" in kwargs["activity_summary"]
    assert "Total Likes received: 10" in kwargs["performance_metrics"]

@patch("phronel_ai_agent.skills.analyst.BootstrapFewShot")
def test_optimize_creator_prompts(mock_bootstrap):
    mock_teleprompter = MagicMock()
    mock_compiled_program = MagicMock()
    mock_teleprompter.compile.return_value = mock_compiled_program
    mock_bootstrap.return_value = mock_teleprompter
    
    analyst = Analyst()
    result = analyst.optimize_creator_prompts()
    
    assert result is True
    mock_bootstrap.assert_called_once()
    mock_teleprompter.compile.assert_called_once()
    from phronel_ai_agent.skills.brain import brain
    mock_compiled_program.save.assert_called_once_with(brain.OPTIMIZED_PROMPT_PATH)

import pytest
from unittest.mock import MagicMock, patch
from phronel_ai_agent.skills.observer import Observer

@patch("phronel_ai_agent.skills.observer.x_client")
@patch("phronel_ai_agent.skills.observer.brain")
def test_observe_keyword(mock_brain, mock_x_client):
    mock_x_client.search_tweets.return_value = [
        {"id": "1", "text": "I love AI agents!", "author_id": "author_1"},
        {"id": "2", "text": "How do AI agents work!", "author_id": "author_2"}
    ]
    
    mock_action = MagicMock()
    mock_action.id = 100
    mock_action.content = "AI agents are software programs..."
    mock_action.status = "pending"
    mock_brain.process_and_propose.return_value = mock_action

    observer = Observer()
    result = observer.observe_keyword("AI agent")

    assert result is not None
    assert result.id == 100
    
    mock_x_client.search_tweets.assert_called_once_with(query="AI agent", max_results=10)
    mock_brain.process_and_propose.assert_called_once_with(
        [
            {"id": "1", "text": "I love AI agents!", "author_id": "author_1"},
            {"id": "2", "text": "How do AI agents work!", "author_id": "author_2"}
        ],
        context_summary="Keyword search: AI agent"
    )


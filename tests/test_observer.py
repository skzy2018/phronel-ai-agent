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
            {"id": "1", "text": "I love AI agents!", "author_id": "author_1", "conversation_id": "mock_conversation_id", "reply_settings": "everyone"},
            {"id": "2", "text": "How do AI agents work!", "author_id": "author_2", "conversation_id": "mock_conversation_id", "reply_settings": "everyone"}
        ],
        context_summary="Keyword search: AI agent",
        is_mention=False
    )

@patch("phronel_ai_agent.skills.observer.x_client")
@patch("phronel_ai_agent.skills.observer.brain")
def test_observe_mentions(mock_brain, mock_x_client):
    class MockTweet:
        def __init__(self, id, text, author_id, conversation_id, reply_settings="everyone"):
            self.id = id
            self.text = text
            self.author_id = author_id
            self.conversation_id = conversation_id
            self.reply_settings = reply_settings

    class MockResponse:
        def __init__(self, data):
            self.data = data

    mock_x_client.get_mentions.return_value = MockResponse([
        MockTweet("mention_1", "@Phronel Hello!", "author_1", "conv_1")
    ])

    mock_action = MagicMock()
    mock_action.id = 200
    mock_brain.process_and_propose.return_value = mock_action

    observer = Observer()
    result = observer.observe_mentions(max_results=5)

    assert result is not None
    assert result.id == 200
    mock_x_client.get_mentions.assert_called_once_with(max_results=5)
    mock_brain.process_and_propose.assert_called_once_with(
        [
            {"id": "mention_1", "text": "@Phronel Hello!", "author_id": "author_1", "conversation_id": "conv_1", "reply_settings": "everyone"}
        ],
        context_summary="Mentions analysis",
        is_mention=True
    )
@patch("phronel_ai_agent.skills.observer.has_action_for_target")
@patch("phronel_ai_agent.skills.observer.x_client")
@patch("phronel_ai_agent.skills.observer.brain")
def test_observe_keyword_skips_duplicates(mock_brain, mock_x_client, mock_has_target):
    mock_has_target.side_effect = lambda tid: tid == "1"

    mock_x_client.search_tweets.return_value = [
        {"id": "1", "text": "Already processed", "author_id": "author_1"},
        {"id": "2", "text": "Brand new tweet!", "author_id": "author_2"}
    ]
    
    mock_action = MagicMock()
    mock_action.id = 101
    mock_brain.process_and_propose.return_value = mock_action

    observer = Observer()
    result = observer.observe_keyword("AI agent")

    assert result is not None
    assert result.id == 101
    
    mock_brain.process_and_propose.assert_called_once_with(
        [
            {"id": "2", "text": "Brand new tweet!", "author_id": "author_2", "conversation_id": "mock_conversation_id", "reply_settings": "everyone"}
        ],
        context_summary="Keyword search: AI agent",
        is_mention=False
    )

import pytest
from unittest.mock import MagicMock, patch
from phronel_ai_agent.services.x_client import XClient
from phronel_ai_agent.skills.brain import Brain, Strategist, Creator
from phronel_ai_agent.skills.executor import execute_action, approve_action
from phronel_ai_agent.core.models import ActionLog

def test_x_client_post_tweet():
    with patch("phronel_ai_agent.services.x_client.tweepy.Client") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        
        mock_response = MagicMock()
        mock_response.data = {"id": "123", "text": "Hello World"}
        mock_instance.create_tweet.return_value = mock_response

        with patch.object(XClient, "_authenticate") as mock_auth:
            client = XClient()
            client.client = mock_instance
            
            response = client.post_tweet("Hello World")
            
            assert response is not None
            assert response["id"] == "123"
            mock_instance.create_tweet.assert_called_once_with(text="Hello World")

def test_creator_create_tweet():
    with patch("phronel_ai_agent.skills.brain.dspy.ChainOfThought") as mock_cot:
        mock_module = MagicMock()
        mock_cot.return_value = mock_module
        
        mock_prediction = MagicMock()
        mock_prediction.tweet_text = "Generated Tweet Content"
        mock_module.return_value = mock_prediction
        
        creator = Creator()
        content = creator.create_tweet(strategy_insight="Make it fun", topic="AI")
        
        assert content == "Generated Tweet Content"
        mock_module.assert_called()

def test_strategist_analyze_timeline():
    with patch("phronel_ai_agent.skills.brain.dspy.ChainOfThought") as mock_cot:
        mock_module = MagicMock()
        mock_cot.return_value = mock_module
        
        strategist = Strategist()
        
        mock_prediction = MagicMock()
        mock_prediction.topic = "Tech Trend"
        mock_prediction.sentiment = "Positive"
        mock_prediction.recommended_action = "reply"
        mock_prediction.strategy_insight = "Engage with them!"
        mock_module.return_value = mock_prediction
        
        strategist.analyst = mock_module
        
        result = strategist.analyze_timeline(["Tweet A", "Tweet B"])
        
        assert result is not None
        assert result["topic"] == "Tech Trend"
        assert result["sentiment"] == "Positive"
        assert result["action"] == "reply"
        assert result["insight"] == "Engage with them!"

@patch("phronel_ai_agent.skills.brain.knowledge_base")
def test_creator_get_knowledge(mock_kb):
    mock_kb.query.return_value = ["Mock Knowledge Chunk 1", "Mock Knowledge Chunk 2"]
    
    with patch("phronel_ai_agent.skills.brain.dspy.ChainOfThought") as mock_cot:
        mock_module = MagicMock()
        mock_cot.return_value = mock_module
        
        mock_prediction = MagicMock()
        mock_prediction.tweet_text = "Generated from Knowledge"
        mock_module.return_value = mock_prediction
        
        creator = Creator()
        creator.tweet_generator = mock_module
        
        content = creator.create_tweet(strategy_insight="Test Strategy", topic="Test Topic")
        
        assert content == "Generated from Knowledge"
        mock_kb.query.assert_called_once_with(query_text="Test Topic", n_results=3)
        
        kwargs = mock_module.call_args[1]
        assert "Mock Knowledge Chunk 1" in kwargs["knowledge_context"]

def test_executor_execute_action():
    with patch("phronel_ai_agent.skills.executor.get_session") as mock_session_getter:
        mock_session = MagicMock()
        mock_session_getter.return_value.__enter__.return_value = mock_session
        
        action = ActionLog(id=1, action_type="tweet", content="Test Content", status="pending")
        mock_session.get.return_value = action
        
        with patch("phronel_ai_agent.skills.executor.x_client") as mock_x:
            mock_x.post_tweet.return_value = {"id": "tweet_123"}
            
            result = execute_action(1)
            
            assert result.status == "executed"
            mock_x.post_tweet.assert_called_with("Test Content")

def test_brain_process_and_propose():
    with patch("phronel_ai_agent.skills.brain.get_session") as mock_session_getter:
        mock_session = MagicMock()
        mock_session_getter.return_value.__enter__.return_value = mock_session
        
        with patch.object(Strategist, "analyze_timeline", return_value={"topic": "test", "sentiment": "neutral", "action": "tweet", "insight": "just do it"}):
            with patch.object(Creator, "create_tweet", return_value="Generated Proposal"):
                brain = Brain()
                action = brain.process_and_propose(["Some timeline data"])
                
                assert action.content == "Generated Proposal"
                assert action.status == "pending"

def test_brain_process_and_propose_reply():
    with patch("phronel_ai_agent.skills.brain.get_session") as mock_session_getter:
        mock_session = MagicMock()
        mock_session_getter.return_value.__enter__.return_value = mock_session
        
        with patch.object(Strategist, "analyze_timeline", return_value={"topic": "test", "sentiment": "neutral", "action": "reply", "insight": "must reply"}):
            with patch.object(Creator, "create_reply", return_value="Generated Reply"):
                brain = Brain()
                action = brain.process_and_propose([{"id": "11223344", "text": "target tweet text", "author_id": "998877"}])
                
                assert action.action_type == "reply"
                assert action.content == "Generated Reply"
                assert action.target_id == "11223344"
                assert action.status == "pending"

def test_creator_dynamic_persona():
    from phronel_ai_agent.skills.brain import Creator
    from phronel_ai_agent.core.models import AgentPersona
    
    mock_persona = AgentPersona(
        name="Ken",
        role="Python Developer Advocate",
        tone="Polite and technical",
        constraints="Max 140 chars",
        sales_strategy="Explain Python modules."
    )
    
    with patch("phronel_ai_agent.core.db.get_active_persona", return_value=mock_persona):
        with patch("phronel_ai_agent.skills.brain.dspy.ChainOfThought") as mock_chain:
            mock_generator = MagicMock()
            mock_chain.return_value = mock_generator
            
            creator = Creator()
            creator.create_tweet(strategy_insight="Teach Python", topic="Python")
            
            # Verify the mock generator was called with our dynamic inputs!
            assert mock_generator.called
            args, kwargs = mock_generator.call_args
            assert "Ken" in kwargs["strategy"]
            assert "Python Developer Advocate" in kwargs["strategy"]
            assert kwargs["style"] == "Polite and technical"
            assert kwargs["constraints"] == "Max 140 chars"



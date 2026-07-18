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
        mock_kb.query.assert_called_once_with(query_text="Test Topic", n_results=3, where=None)
        
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
                action = brain.process_and_propose([{"id": "11223344", "text": "target tweet text", "author_id": "998877"}], is_mention=True)
                
                assert action.action_type == "reply"
                assert action.content == "Generated Reply"
                assert action.target_id == "11223344"
                assert action.status == "pending"

def test_brain_process_and_propose_reply_downgrade():
    with patch("phronel_ai_agent.skills.brain.get_session") as mock_session_getter:
        mock_session = MagicMock()
        mock_session_getter.return_value.__enter__.return_value = mock_session
        
        with patch.object(Strategist, "analyze_timeline", return_value={"topic": "test", "sentiment": "neutral", "action": "reply", "insight": "must reply"}):
            brain = Brain()
            action = brain.process_and_propose([{"id": "11223344", "text": "target tweet text", "author_id": "998877"}])
            
            assert action.action_type == "like"
            assert action.content == "Like tweet"
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

def test_creator_thread_conversation():
    from phronel_ai_agent.skills.brain import Creator
    from phronel_ai_agent.core.models import AgentPersona
    
    mock_persona = AgentPersona(
        name="Ken",
        role="Tech Rep",
        tone="Technical",
        constraints="None",
        sales_strategy="Answer questions"
    )
    
    # Mock conversation thread response from x_client
    mock_thread_data = [
        {"id": "t1", "text": "Is Phronel free?", "author_id": "cust1", "created_at": "2026-06-25T12:00:00Z", "is_agent": False},
        {"id": "t2", "text": "Yes, it has a free tier!", "author_id": "agent1", "created_at": "2026-06-25T12:05:00Z", "is_agent": True},
        {"id": "t3", "text": "Where is the link?", "author_id": "cust1", "created_at": "2026-06-25T12:10:00Z", "is_agent": False}
    ]
    
    with patch("phronel_ai_agent.core.db.get_active_persona", return_value=mock_persona):
        with patch("phronel_ai_agent.services.x_client.XClient.get_conversation_thread") as mock_get_thread:
            mock_get_thread.return_value = mock_thread_data
            
            with patch("phronel_ai_agent.skills.brain.dspy.ChainOfThought") as mock_chain:
                mock_generator = MagicMock()
                mock_chain.return_value = mock_generator
                
                creator = Creator()
                # Run create_reply passing a conversation_id
                creator.create_reply(
                    target_tweet="Where is the link?",
                    strategy_insight="Provide trial URL",
                    topic="free trial",
                    conversation_id="conv_123"
                )
                
                # Assertions to verify correct interaction with x_client and dspy generator
                mock_get_thread.assert_called_once_with("conv_123")
                assert mock_generator.called
                _, kwargs = mock_generator.call_args
                
                # Verify conversation_history was correctly sorted, formatted and passed to DSPy GenerateReply
                history = kwargs["conversation_history"]
                assert "User: Is Phronel free?" in history
                assert "Ken (Agent): Yes, it has a free tier!" in history
                assert "User: Where is the link?" in history

def test_persona_tweet_topic():
    from phronel_ai_agent.core.models import AgentPersona
    p = AgentPersona(
        name="Test Persona",
        tweet_topic="AIによるSNS自動営業の未来"
    )
    assert p.name == "Test Persona"
    assert p.tweet_topic == "AIによるSNS自動営業の未来"

@patch("phronel_ai_agent.skills.brain.has_executed_content")
def test_creator_anti_duplication_retry(mock_has_executed):
    from phronel_ai_agent.skills.brain import Creator
    from phronel_ai_agent.core.models import AgentPersona
    
    mock_persona = AgentPersona(
        name="Ken",
        role="Advocate",
        tone="Technical",
        constraints="Max 140 chars",
        sales_strategy="Strategy"
    )
    
    # First generated is duplicate, second is unique
    mock_has_executed.side_effect = lambda text: text == "Duplicate Text"
    
    with patch("phronel_ai_agent.core.db.get_active_persona", return_value=mock_persona):
        with patch("phronel_ai_agent.skills.brain.dspy.ChainOfThought") as mock_chain:
            mock_generator = MagicMock()
            
            mock_res_1 = MagicMock()
            mock_res_1.tweet_text = "Duplicate Text"
            
            mock_res_2 = MagicMock()
            mock_res_2.tweet_text = "Unique Creative Text"
            
            mock_generator.side_effect = [mock_res_1, mock_res_2]
            mock_chain.return_value = mock_generator
            
            creator = Creator()
            result = creator.create_tweet(strategy_insight="Avoid duplicates", topic="Deduplication")
            
            assert result == "Unique Creative Text"
            assert mock_generator.call_count == 2

def test_executor_executes_follow():
    from phronel_ai_agent.skills.executor import execute_action
    from phronel_ai_agent.core.models import ActionLog
    
    mock_action = ActionLog(
        id=12345,
        action_type="follow",
        target_id="mock_target_user_id",
        status="pending",
        content="Follow back target"
    )
    
    with patch("phronel_ai_agent.skills.executor.get_session") as mock_get_session:
        mock_session = MagicMock()
        mock_session.get.return_value = mock_action
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        with patch("phronel_ai_agent.skills.executor.x_client") as mock_x:
            mock_x.follow_user.return_value = {"following": True}
            
            result = execute_action(12345)
            
            assert result is not None
            assert result.status == "executed"
            mock_x.follow_user.assert_called_once_with("mock_target_user_id")

@patch("phronel_ai_agent.skills.observer.x_client")
def test_observer_observe_followers(mock_x_client):
    from phronel_ai_agent.skills.observer import Observer
    
    class FakeFollower:
        def __init__(self, id, name, username):
            self.id = id
            self.name = name
            self.username = username
            
    mock_x_client.get_followers.return_value = [
        FakeFollower(id="user_follower_abc", name="Follower ABC", username="follower_abc")
    ]
    
    with patch("phronel_ai_agent.core.db.get_session") as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        with patch("phronel_ai_agent.core.db.has_action_for_target", return_value=False):
            observer = Observer()
            result = observer.observe_followers()
            
            assert result is not None
            assert result.action_type == "follow"
            assert result.target_id == "user_follower_abc"
            
            assert mock_session.add.called
            assert mock_session.commit.called

@patch("phronel_ai_agent.core.db.has_action_for_target")
def test_brain_combo_approach(mock_has_target):
    from phronel_ai_agent.skills.brain import Brain
    
    mock_has_target.return_value = False
    
    with patch("phronel_ai_agent.skills.brain.get_session") as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        with patch("phronel_ai_agent.skills.brain.Brain._ensure_ready"):
            with patch("phronel_ai_agent.skills.brain.Strategist.analyze_timeline") as mock_analyze:
                mock_analyze.return_value = {
                    "action": "like",
                    "insight": "High relevance product query",
                    "topic": "product FAQ"
                }
                
                brain_inst = Brain()
                
                source_data = [
                    {"id": "tweet_123", "text": "Is Phronel ready?", "author_id": "cust_author_123"}
                ]
                
                result_action = brain_inst.process_and_propose(source_data, is_mention=False)
                
                assert result_action is not None
                assert result_action.action_type == "like"
                
                assert mock_session.add.call_count >= 2






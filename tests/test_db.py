from datetime import datetime
from sqlmodel import Session, select, create_engine, SQLModel
from phronel_ai_agent.core.models import ActionLog, AgentConfig

sqlite_file_name = ":memory:"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)
SQLModel.metadata.create_all(engine)

def test_db_operations():
    # 1. Add Config
    with Session(engine) as session:
        config = AgentConfig(key="test_mode", value="active")
        session.add(config)
        session.commit()
    
    # 2. Add ActionLog
    with Session(engine) as session:
        log = ActionLog(
            action_type="tweet",
            content="Hello world!",
            status="pending"
        )
        session.add(log)
        session.commit()
        log_id = log.id

    # 3. Read ActionLog
    with Session(engine) as session:
        retrieved_log = session.get(ActionLog, log_id)
        assert retrieved_log is not None
        assert retrieved_log.content == "Hello world!"
        assert retrieved_log.status == "pending"
        print("ActionLog test passed!")

    # 4. Read Config
    with Session(engine) as session:
        config = session.get(AgentConfig, "test_mode")
        assert config is not None
        assert config.value == "active"
        print("AgentConfig test passed!")

def test_action_strategy_relationship():
    # Setup StrategyLog and link to ActionLog
    from phronel_ai_agent.core.models import StrategyLog
    
    with Session(engine) as session:
        strategy = StrategyLog(
            context_summary="Test Context",
            strategy_text="Post a warm greeting",
            model_name="test_model"
        )
        session.add(strategy)
        session.commit()
        session.refresh(strategy)
        
        action = ActionLog(
            action_type="tweet",
            content="Good morning everyone!",
            status="executed",
            strategy_log_id=strategy.id
        )
        session.add(action)
        session.commit()
        session.refresh(action)
        action_id = action.id

    with Session(engine) as session:
        retrieved_action = session.get(ActionLog, action_id)
        assert retrieved_action is not None
        assert retrieved_action.strategy_log_id is not None
        
        # Verify StrategyLog can be retrieved using the key
        linked_strategy = session.get(StrategyLog, retrieved_action.strategy_log_id)
        assert linked_strategy is not None
        assert linked_strategy.strategy_text == "Post a warm greeting"
        assert linked_strategy.context_summary == "Test Context"

if __name__ == "__main__":
    test_db_operations()

import os
import shutil
import pytest
from typer.testing import CliRunner
from sqlmodel import Session, create_engine, select
from phronel_ai_agent.interfaces.main import app
from phronel_ai_agent.core.models import AgentConfig, KnowledgeChunk
from phronel_ai_agent.core.db import init_db
from unittest.mock import patch

# Initialize runner with environment variables to disable color if possible,
# though rich might ignore it. We'll handle checks robustly.
runner = CliRunner(env={"NO_COLOR": "1"})

DB_FILE = "phronel_agent.db"
CHROMA_DIR = "./chroma_db_test"  # Use a separate dir for testing

def cleanup():
    # Close any existing connections before removing the file by disposing the engine
    from phronel_ai_agent.core.db import engine
    engine.dispose()
    
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
        except OSError:
            pass
    if os.path.exists(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR, ignore_errors=True)

@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    cleanup()
    init_db()  # Ensure DB and tables are created AFTER cleanup
    yield
    cleanup()

def test_init_command():
    # Simulate user input for phronel init
    # 1. Bearer
    # 2. API Key
    # 3. API Secret
    # 4. Access Token
    # 5. Access Token Secret
    # 6. Gemini API Key
    # 7. Execution Mode
    user_input = "my_bearer\nmy_key\nmy_secret\nmy_token\nmy_token_secret\nmy_gemini_key\nmanual\n"
    
    result = runner.invoke(app, ["init"], input=user_input)
    if result.exit_code != 0:
        print("\nSTDOUT:", result.stdout)
        print("EXCEPTION:", result.exception)
    assert result.exit_code == 0
    assert "Database initialized" in result.stdout
    assert "Configuration saved successfully" in result.stdout

    # Verify DB content
    engine = create_engine(f"sqlite:///{DB_FILE}")
    with Session(engine) as session:
        config = session.get(AgentConfig, "x_api_key")
        assert config is not None
        assert config.value == "my_key"

        mode = session.get(AgentConfig, "execution_mode")
        assert mode is not None
        assert mode.value == "manual"

def test_config_command():
    # 1. Update config
    result = runner.invoke(app, ["config", "execution_mode", "semi-auto"])
    assert result.exit_code == 0
    assert "Updated execution_mode = semi-auto" in result.stdout

    # 2. Verify update via CLI
    result = runner.invoke(app, ["config", "execution_mode"])
    assert result.exit_code == 0
    # Rich adds styling, so we check for substring presence more loosely
    assert "execution_mode" in result.stdout
    assert "semi-auto" in result.stdout

    # 3. Verify update in DB
    engine = create_engine(f"sqlite:///{DB_FILE}")
    with Session(engine) as session:
        mode = session.get(AgentConfig, "execution_mode")
        assert mode is not None
        assert mode.value == "semi-auto"

def test_learn_command():
    # Patch the KnowledgeBase to use a test directory
    # We need to patch the instance 'knowledge_base' in 'phronel_ai_agent.interfaces.main'
    # or recreate it.
    
    from phronel_ai_agent.services.knowledge import KnowledgeBase
    test_kb = KnowledgeBase(persist_directory=CHROMA_DIR)
    
    # We patch the object where it is USED.
    with patch("phronel_ai_agent.interfaces.main.knowledge_base", test_kb):
        test_file = "test_knowledge.md"
        with open(test_file, "w") as f:
            f.write("# Test Knowledge\nThis is a sample document for testing the knowledge base.")

        try:
            # Run learn command
            result = runner.invoke(app, ["learn", test_file])
            
            if result.exit_code != 0:
                print("\nSTDOUT:", result.stdout)
                print("EXCEPTION:", result.exception)
                import traceback
                traceback.print_tb(result.exc_info[2]) # type: ignore
            
            assert result.exit_code == 0
            assert "Successfully imported" in result.stdout

            # Verify DB content (KnowledgeChunk)
            engine = create_engine(f"sqlite:///{DB_FILE}")
            with Session(engine) as session:
                statement = select(KnowledgeChunk)
                chunks = session.exec(statement).all()
                assert len(chunks) > 0
                assert "sample document" in chunks[0].content
                assert chunks[0].source == str(test_file)

        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

def test_knowledge_source_operations():
    from phronel_ai_agent.services.knowledge import knowledge_base
    from phronel_ai_agent.core.models import KnowledgeChunk
    from sqlmodel import delete
    
    init_db()
    
    # 1. Clear existing knowledge
    engine_test = create_engine(f"sqlite:///{DB_FILE}")
    with Session(engine_test) as session:
        session.exec(delete(KnowledgeChunk))
        session.commit()
        
    count = knowledge_base.add_document("Chroma text chunk 1", "test_source.md")
    assert count > 0
    
    # 2. List sources
    sources = knowledge_base.list_sources()
    assert len(sources) == 1
    assert sources[0]["source"] == "test_source.md"
    assert sources[0]["chunk_count"] == 1
    
    # 3. Get chunks
    chunks = knowledge_base.get_chunks_by_source("test_source.md")
    assert len(chunks) == 1
    assert chunks[0].content == "Chroma text chunk 1"
    
    # 4. Delete source
    deleted = knowledge_base.delete_source("test_source.md")
    assert deleted == 1
    
    # 5. List again (should be empty)
    sources_after = knowledge_base.list_sources()
    assert len(sources_after) == 0

def test_observe_mentions_command():
    from unittest.mock import MagicMock, patch
    
    mock_action = MagicMock()
    mock_action.id = 555
    mock_action.action_type = "reply"
    mock_action.content = "This is a mock reply"
    
    with patch("phronel_ai_agent.interfaces.main.observer") as mock_observer:
        mock_observer.observe_mentions.return_value = mock_action
        
        result = runner.invoke(app, ["observe-mentions", "--max-results", "5"])
        
        assert result.exit_code == 0
        assert "Observing X for account mentions..." in result.stdout
        assert "✔ Analysis Complete and Proposal Created!" in result.stdout
        assert "Action ID: 555" in result.stdout
        assert "This is a mock reply" in result.stdout
        mock_observer.observe_mentions.assert_called_once_with(5)


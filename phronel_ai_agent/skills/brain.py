import os
import dspy
import logging
from ..core.db import get_session
from ..core.models import AgentConfig, StrategyLog, ActionLog
from ..services.knowledge import knowledge_base
from ..core.config import config
from ..core.llm_logger import log_dspy_history

logger = logging.getLogger("phronel")

# Define DSPy Signatures for Analysis (Strategist)
class AnalyzeTrend(dspy.Signature):
    """Analyze a list of tweets to identify the core topic, sentiment, and recommend an engagement strategy."""
    
    tweets = dspy.InputField(desc="List of tweet texts.")
    topic = dspy.OutputField(desc="Main topic being discussed.")
    sentiment = dspy.OutputField(desc="Overall sentiment (Positive, Negative, Neutral).")
    recommended_action = dspy.OutputField(desc="Action to take: 'tweet', 'reply', 'like', or 'ignore'.")
    strategy_insight = dspy.OutputField(desc="Reasoning for the recommended action and specific angles to cover.")

# Define DSPy Signatures for Creation (Creator)
class GenerateTweet(dspy.Signature):
    """Generate a high-quality, engaging tweet based on strategy and context."""
    
    strategy = dspy.InputField(desc="The strategy and insight guiding this tweet.")
    knowledge_context = dspy.InputField(desc="Reference information from the knowledge base.")
    style = dspy.InputField(desc="The persona and tone of the agent (e.g., professional, insightful, helpful).")
    constraints = dspy.InputField(desc="Length limits, formatting rules (e.g., no hashtags).")
    tweet_text = dspy.OutputField(desc="The generated tweet text, ready for posting.")

class GenerateReply(dspy.Signature):
    """Generate a helpful and contextual reply to a specific tweet."""
    
    target_tweet = dspy.InputField(desc="The tweet being replied to.")
    strategy = dspy.InputField(desc="The strategy or goal for this reply.")
    knowledge_context = dspy.InputField(desc="Reference information to answer questions or add value.")
    style = dspy.InputField(desc="Professional, polite, and helpful.")
    reply_text = dspy.OutputField(desc="The text of the reply.")

# --- Modules ---

class Strategist(dspy.Module):
    """Analyzes the environment to form a strategy."""
    def __init__(self):
        super().__init__()
        self.analyst = dspy.ChainOfThought(AnalyzeTrend)

    def analyze_timeline(self, tweets: list[str]):
        """Analyzes tweets and outputs a strategy."""
        if not tweets:
            return None
            
        tweets_text = "\n".join([f"- {t}" for t in tweets])
        prediction = self.analyst(tweets=tweets_text)
        
        # Log LLM interaction
        log_dspy_history("Strategist.analyze_timeline")
        
        return {
            "topic": prediction.topic,
            "sentiment": prediction.sentiment,
            "action": prediction.recommended_action.lower(),
            "insight": prediction.strategy_insight
        }

class Creator(dspy.Module):
    """Executes a strategy by generating specific content."""
    def __init__(self):
        super().__init__()
        self.tweet_generator = dspy.ChainOfThought(GenerateTweet)
        self.reply_generator = dspy.ChainOfThought(GenerateReply)

    def _get_knowledge(self, topic: str):
        knowledge_context = ""
        try:
            retrieved_chunks = knowledge_base.query(query_text=topic, n_results=3)
            if retrieved_chunks:
                knowledge_context = "\n---\n".join(retrieved_chunks)
                logger.info(f"[Creator] Retrieved {len(retrieved_chunks)} chunks for '{topic}'.")
        except Exception as e:
            logger.error(f"[Creator] Error retrieving knowledge: {e}")
        return knowledge_context

    def create_tweet(self, strategy_insight: str, topic: str):
        # 1. Fetch dynamic settings from dedicated AgentPersona database table with JIT fallback
        from ..core.db import get_active_persona
        persona = get_active_persona()
        
        name = persona.name
        role = persona.role
        style = persona.tone
        constraints = persona.constraints
        sales_policy = persona.sales_strategy

        # 2. Inject persona identity and sales strategy into the strategy parameter
        dynamic_strategy = f"Identity: You are '{name}' ({role}).\nSales Policy: {sales_policy}\nFocus: {strategy_insight}"
        knowledge_context = self._get_knowledge(topic)
        
        prediction = self.tweet_generator(
            strategy=dynamic_strategy,
            knowledge_context=knowledge_context,
            style=style,
            constraints=constraints
        )
        
        # Log LLM interaction
        log_dspy_history("Creator.create_tweet")
        
        return prediction.tweet_text

    def create_reply(self, target_tweet: str, strategy_insight: str, topic: str):
        # 1. Fetch dynamic settings from dedicated AgentPersona database table with JIT fallback
        from ..core.db import get_active_persona
        persona = get_active_persona()
        
        name = persona.name
        role = persona.role
        style = persona.tone
        sales_policy = persona.sales_strategy

        # 2. Inject persona identity and sales strategy
        dynamic_strategy = f"Identity: You are '{name}' ({role}).\nSales Policy: {sales_policy}\nFocus: {strategy_insight}"
        knowledge_context = self._get_knowledge(topic)
        
        prediction = self.reply_generator(
            target_tweet=target_tweet,
            strategy=dynamic_strategy,
            knowledge_context=knowledge_context,
            style=style
        )
        
        # Log LLM interaction
        log_dspy_history("Creator.create_reply")
        
        return prediction.reply_text

class Brain:
    """The central intelligence coordinating Strategist and Creator."""
    
    DEFAULT_MODEL = os.getenv("PHRONEL_LLM_MODEL", "gemini-2.5-flash")
    OPTIMIZED_PROMPT_PATH = os.getenv("PHRONEL_OPTIMIZED_PROMPT_PATH", "phronel_ai_agent/core/optimized_creator.json")
    
    def __init__(self):
        self.strategist = Strategist()
        self.creator = Creator()
        self._llm_configured = False
        self._prompts_loaded = False

    def _ensure_ready(self):
        """Ensures LLM and optimized prompts are lazily initialized on first use."""
        if not self._llm_configured:
            self.configure_llm()
            self._llm_configured = True
        if not self._prompts_loaded:
            self._load_optimized_prompts()
            self._prompts_loaded = True

    def _load_optimized_prompts(self):
        """Loads optimized prompts for the Creator if they exist."""
        if os.path.exists(self.OPTIMIZED_PROMPT_PATH):
            try:
                self.creator.tweet_generator.load(self.OPTIMIZED_PROMPT_PATH)
                logger.info(f"[Brain] Loaded optimized prompts from {self.OPTIMIZED_PROMPT_PATH}")
            except Exception as e:
                logger.error(f"[Brain] Error loading optimized prompts: {e}")

    def configure_llm(self):
        """Configure DSPy with Gemini as the default LLM."""
        api_key = os.environ.get("GEMINI_API_KEY")
        
        if not api_key:
            api_key = config.get("gemini_api_key")

        if api_key:
            try:
                # Using DEFAULT_MODEL
                lm = dspy.LM(f'gemini/{self.DEFAULT_MODEL}', api_key=api_key)
                dspy.configure(lm=lm)
                logger.info(f"[Brain] Successfully configured Gemini LLM ({self.DEFAULT_MODEL}).")
            except Exception as e:
                logger.error(f"[Brain] Error configuring Gemini: {e}")
        else:
            logger.warning("[Brain] No Gemini API key found. Operating in Mock mode.")

    def process_and_propose(self, source_data: list, context_summary: str = "Timeline analysis"):
        """
        Full pipeline: Analyze -> Strategize -> Create -> Propose Action
        """
        self._ensure_ready()
        # Extract tweet texts for the DSPy Strategist (it expects a list of strings)
        tweet_texts = []
        tweets_meta = []
        for item in source_data:
            if isinstance(item, dict):
                tweet_texts.append(item.get("text", ""))
                tweets_meta.append(item)
            else:
                tweet_texts.append(str(item))
                tweets_meta.append({"id": "target_tweet_id", "text": str(item), "author_id": "target_author_id"})

        # 1. Strategize
        analysis = self.strategist.analyze_timeline(tweet_texts)
        if not analysis:
            logger.warning("[Brain] Analysis failed or no data.")
            return None
            
        logger.info(f"[Brain] Strategy formed. Recommended action: {analysis['action']}")
        
        # Log Strategy
        strategy_log_id = None
        with get_session() as session:
            strategy_log = StrategyLog(
                context_summary=context_summary,
                strategy_text=analysis["insight"],
                model_name=self.DEFAULT_MODEL
            )
            session.add(strategy_log)
            session.commit()
            session.refresh(strategy_log)
            strategy_log_id = strategy_log.id

        action_type = analysis["action"]
        content = None
        target_id = None 

        # 2. Create Content based on Action
        if "tweet" in action_type:
            content = self.creator.create_tweet(
                strategy_insight=analysis["insight"], 
                topic=analysis["topic"]
            )
            action_type = "tweet"
        elif "reply" in action_type: # target tweet is the first in the list
            target_tweet = tweets_meta[0] if tweets_meta else {"id": "target_tweet_id", "text": "Unknown tweet"}
            content = self.creator.create_reply(
                target_tweet=target_tweet["text"],
                strategy_insight=analysis["insight"],
                topic=analysis["topic"]
            )
            action_type = "reply"
            target_id = target_tweet.get("id", "target_tweet_id")
        elif "like" in action_type: # target tweet is the first in the list
            target_tweet = tweets_meta[0] if tweets_meta else {"id": "target_tweet_id", "text": "Unknown tweet"}
            action_type = "like"
            target_id = target_tweet.get("id", "target_tweet_id")
            content = "Like tweet"
        else:
            logger.info(f"[Brain] Strategy decided to ignore or unknown action: {action_type}")
            return None

        # 3. Create Proposal (ActionLog)
        with get_session() as session:
            new_action = ActionLog(
                action_type=action_type,
                content=content,
                target_id=target_id,
                status="pending",
                strategy_log_id=strategy_log_id
            )
            session.add(new_action)
            session.commit()
            session.refresh(new_action)
            logger.info(f"[Brain] Created {action_type} proposal (ID: {new_action.id}, Strategy Log ID: {strategy_log_id}).")
            return new_action
            
    def create_tweet_proposal(self, topic: str):
        self._ensure_ready()
        content = self.creator.create_tweet(strategy_insight=f"Write an engaging tweet about {topic}", topic=topic)
        with get_session() as session:
            new_action = ActionLog(action_type="tweet", content=content, status="pending")
            session.add(new_action)
            session.commit()
            session.refresh(new_action)
            logger.info(f"[Brain] Created manual tweet proposal (ID: {new_action.id}).")
            return new_action
            
    def analyze_timeline(self, tweets: list[str]):
         self._ensure_ready()
         return self.strategist.analyze_timeline(tweets)

# Global instance
brain = Brain()

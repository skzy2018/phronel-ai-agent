import logging
import dspy
from dspy.teleprompt import BootstrapFewShot
from sqlmodel import select
from datetime import datetime
from typing import Optional

from ..core.db import get_session
from ..core.models import ActionLog, StrategyLog
from ..services.x_client import x_client
from .brain import brain
from ..core.llm_logger import log_dspy_history

logger = logging.getLogger("phronel")

# --- DSPy Signatures for Analysis ---

class GenerateDailyReport(dspy.Signature):
    """Generate a daily summary report of the AI Agent's activities based on executed actions and strategies."""
    
    date_str = dspy.InputField(desc="The date of the report (e.g., YYYY-MM-DD).")
    activity_summary = dspy.InputField(desc="A summary string containing counts of tweets, replies, likes, etc.")
    strategies_used = dspy.InputField(desc="A list of strategy insights the AI formed during the day.")
    performance_metrics = dspy.InputField(desc="Optional metrics like total likes, retweets, or impressions.")
    
    report_text = dspy.OutputField(desc="A comprehensive, easy-to-read daily report including the AI's explanation of 'why' it took these actions and what the overall strategy was. Format in Markdown.")

# --- Analyst Skill ---

class Analyst(dspy.Module):
    """Skill to analyze past actions, generate reports, and optimize the agent's prompts."""
    
    def __init__(self):
        super().__init__()
        self.report_generator = dspy.ChainOfThought(GenerateDailyReport)

    def generate_daily_report(self, target_date: Optional[datetime] = None) -> str:
        """Gathers data for a specific date and generates a markdown report."""
        if target_date is None:
            target_date = datetime.utcnow()
            
        date_str = target_date.strftime("%Y-%m-%d")
        logger.info(f"[Analyst] Generating daily report for {date_str}...")

        # 1. Fetch Actions for the day
        actions = []
        with get_session() as session:
            # We filter by executed_at date roughly
            all_actions = session.exec(select(ActionLog).where(ActionLog.status == "executed")).all()
            for a in all_actions:
                if a.executed_at and a.executed_at.strftime("%Y-%m-%d") == date_str:
                    actions.append(a)

        if not actions:
            logger.info("[Analyst] No executed actions found for this date.")
            return f"No activities recorded for {date_str}."

        # Aggregate counts
        counts = {"tweet": 0, "reply": 0, "like": 0, "follow": 0}
        tweet_ids = []
        for a in actions:
            counts[a.action_type] = counts.get(a.action_type, 0) + 1
            # If it's a tweet or reply, try to extract ID to fetch metrics
            if a.action_type in ["tweet", "reply"] and a.result_json:
                import json
                try:
                    res = json.loads(a.result_json)
                    if "id" in res and res["id"] != "mock_id" and "mock" not in res["id"]:
                        tweet_ids.append(res["id"])
                except Exception:
                    pass

        activity_summary = f"Total Actions: {len(actions)}\n"
        for k, v in counts.items():
            activity_summary += f"- {k.capitalize()}s: {v}\n"

        # 2. Fetch Metrics for those tweets
        total_likes = 0
        total_retweets = 0
        if tweet_ids:
            metrics_list = x_client.get_tweet_metrics(tweet_ids)
            for m in metrics_list:
                total_likes += m.get("likes", 0)
                total_retweets += m.get("retweets", 0)
        else:
            # If mock, add some dummy metrics
            total_likes = counts.get("tweet", 0) * 3 + counts.get("reply", 0) * 1
            total_retweets = counts.get("tweet", 0) * 1
            
        performance_metrics = f"Total Likes received: {total_likes}\nTotal Retweets received: {total_retweets}"

        # 3. Fetch Strategies for the day
        strategies = []
        with get_session() as session:
            all_strategies = session.exec(select(StrategyLog)).all()
            for s in all_strategies:
                if s.created_at.strftime("%Y-%m-%d") == date_str:
                    strategies.append(s.strategy_text)
                    
        # Limit strategies to avoid token overflow
        strategies = strategies[:10]
        strategies_used = "\n".join([f"- {s}" for s in strategies]) if strategies else "No specific strategies logged."

        # 4. Generate Report via DSPy
        prediction = self.report_generator(
            date_str=date_str,
            activity_summary=activity_summary,
            strategies_used=strategies_used,
            performance_metrics=performance_metrics
        )
        
        # Log LLM interaction
        log_dspy_history("Analyst.generate_daily_report")
        
        logger.info("[Analyst] Daily report generated successfully.")
        return prediction.report_text

    def optimize_creator_prompts(self):
        """
        Uses DSPy Optimizer to improve the Creator's tweet generation prompt 
        based on engagement metrics and historical SQLite logs.
        """
        logger.info("[Analyst] Starting prompt optimization process...")
        
        try:
            
            # 1. Dynamically gather historical training data from DB (Strategy -> Tweet text)
            db_examples = []
            try:
                with get_session() as session:
                    # Query executed tweet actions
                    executed_actions = session.exec(
                        select(ActionLog)
                        .where(ActionLog.action_type == "tweet")
                        .where(ActionLog.status == "executed")
                    ).all()
                    
                    for action in executed_actions:
                        # 1. Fetch StrategyLog directly via the new foreign key relation
                        strategy_record = None
                        if action.strategy_log_id is not None:
                            strategy_record = session.get(StrategyLog, action.strategy_log_id)
                        
                        # 2. Fallback to time-based proximity for legacy rows
                        if strategy_record is None:
                            strategy_record = session.exec(
                                select(StrategyLog)
                                .where(StrategyLog.created_at <= action.created_at)
                                .order_by(StrategyLog.created_at.desc()) # type: ignore
                                .limit(1)
                            ).first()
                        
                        strategy_insight = strategy_record.strategy_text if strategy_record else f"Write an engaging tweet about product features based on: {action.content[:30]}..."  # type: ignore
                        
                        db_examples.append(
                            dspy.Example(
                                strategy=strategy_insight,
                                knowledge_context="Phronel AI Agent provides autonomous SNS presence.",
                                style="Professional, helpful, slightly witty. Use emoji sparingly.",
                                constraints="Max 280 chars. Direct and engaging.",
                                tweet_text=action.content
                            ).with_inputs('strategy', 'knowledge_context', 'style', 'constraints')
                        )
            except Exception as db_err:
                logger.warning(f"[Analyst] Failed to query training data from SQLite database: {db_err}")

            # 2. Setup high-quality seed bootstrap examples for cold starts (when DB has < 2 records)
            seed_examples = [
                dspy.Example(
                    strategy="Promote the new AI agent features.",
                    knowledge_context="Phronel AI is autonomous.",
                    style="Professional, helpful, slightly witty. Use emoji sparingly.",
                    constraints="Max 280 chars. Direct and engaging.",
                    tweet_text="Meet Phronel AI: your new autonomous agent! It handles everything seamlessly. #AI"
                ).with_inputs('strategy', 'knowledge_context', 'style', 'constraints'),
                dspy.Example(
                    strategy="Engage with users talking about Python.",
                    knowledge_context="Python is great for AI.",
                    style="Professional, helpful, slightly witty. Use emoji sparingly.",
                    constraints="Max 280 chars. Direct and engaging.",
                    tweet_text="Python is definitely the go-to language for AI development right now. What libraries do you use most?"
                ).with_inputs('strategy', 'knowledge_context', 'style', 'constraints')
            ]
            
            # Combine or fallback: Use DB examples if available, supplemented with seeds for robust compilation
            if len(db_examples) >= 2:
                trainset = db_examples
                logger.info(f"[Analyst] Training with {len(trainset)} real examples from historical ActionLog/StrategyLog database.")
            else:
                trainset = seed_examples + db_examples
                logger.info(f"[Analyst] Cold start / Supplementary: Supplemented {len(db_examples)} DB examples with {len(seed_examples)} bootstrap seed examples (Total: {len(trainset)}).")
            
            # 3. Import and use the decoupled multi-tier evaluation scoring metric
            from .metrics import phronel_multi_tier_metric

            teleprompter = BootstrapFewShot(metric=phronel_multi_tier_metric, max_bootstrapped_demos=2, max_labeled_demos=2)
            
            # Compile the creator
            logger.info("[Analyst] Compiling Creator module with BootstrapFewShot...")
            optimized_creator = teleprompter.compile(brain.creator.tweet_generator, trainset=trainset)
            
            # Save the optimized prompt
            optimized_creator.save(brain.OPTIMIZED_PROMPT_PATH)
            logger.info(f"[Analyst] Optimization complete. Saved to {brain.OPTIMIZED_PROMPT_PATH}")
            
            return True
            
        except Exception as e:
            logger.error(f"[Analyst] Optimization failed: {e}")
            return False

# Global instance
analyst = Analyst()

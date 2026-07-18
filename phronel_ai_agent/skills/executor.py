import logging
from datetime import datetime
from ..core.db import get_session
from ..core.config import config
from ..core.models import ActionLog
from ..services.x_client import x_client
import json

logger = logging.getLogger("phronel")

def execute_action(action_id: int):
    """Executes a pending action from the ActionLog."""
    with get_session() as session:
        action = session.get(ActionLog, action_id)
        if not action:
            logger.error(f"[Executor] Action {action_id} not found.")
            return None
        
        if action.status != "pending" and action.status != "approved":
            logger.warning(f"[Executor] Action {action_id} is in status '{action.status}', skipping.")
            return action

        logger.info(f"[Executor] Executing {action.action_type} (ID: {action.id})...")
        
        execution_mode = config.get("execution_mode", default="manual")
        if execution_mode == "dry-run":
            logger.info(f"[DRY-RUN] Simulating execution of {action.action_type}")
            result = {
                "dry_run": True,
                "action_type": action.action_type,
                "content": action.content,
                "target_id": action.target_id
            }
            action.status = "executed"
            action.executed_at = datetime.utcnow()
            action.result_json = json.dumps(result)
            session.add(action)
            session.commit()
            session.refresh(action)
            logger.info(f"[Executor] Action {action.id} finished with status: {action.status} (DRY-RUN)")
            return action
        
        result = None
        try:
            if action.action_type == "tweet":
                result = x_client.post_tweet(action.content) # type: ignore
            elif action.action_type == "like":
                result = x_client.like_tweet(action.target_id) # type: ignore
            elif action.action_type == "reply":
                result = x_client.reply_to_tweet(action.target_id, action.content) # type: ignore
            elif action.action_type == "follow":
                result = x_client.follow_user(action.target_id) # type: ignore
            else:
                logger.error(f"[Executor] Unknown action type: {action.action_type}")
                action.status = "failed"
                session.add(action)
                session.commit()
                return action

            if result:
                action.status = "executed"
                action.executed_at = datetime.utcnow()
                action.result_json = json.dumps(result)
            else:
                action.status = "failed"
            
            session.add(action)
            session.commit()
            session.refresh(action)
            logger.info(f"[Executor] Action {action.id} finished with status: {action.status}")
            return action

        except Exception as e:
            logger.error(f"[Executor] Error executing action {action.id}: {e}")
            action.status = "failed"
            session.add(action)
            session.commit()
            return action

def approve_action(action_id: int):
    """Marks a pending action as approved."""
    with get_session() as session:
        action = session.get(ActionLog, action_id)
        if action and action.status == "pending":
            action.status = "approved"
            session.add(action)
            session.commit()
            session.refresh(action)
            logger.info(f"[Executor] Action {action.id} approved.")
            return action
    return None

import os
import logging
from typing import Optional
from ..services.x_client import x_client
from .brain import brain
from ..core.db import has_action_for_target

logger = logging.getLogger("phronel")

class Observer:
    """
    Observer Skill: Monitors the SNS environment (trends, mentions, searches)
    and passes gathered information to the Strategist (Brain) to generate potential actions.
    """

    def observe_keyword(self, keyword: str, max_results: Optional[int] = None):
        """
        Searches for a specific keyword on X, analyzes the recent tweets,
        and generates a proposed action based on the trend.
        Supports comma-separated multiple keywords.
        """
        if max_results is None or max_results <= 0:
            try:
                max_results = int(os.getenv("PHRONEL_MAX_RESULTS", "10"))
            except Exception:
                max_results = 10

        keywords = [k.strip() for k in keyword.split(",") if k.strip()]
        if len(keywords) > 1:
            logger.info(f"[Observer] Detected multiple keywords: {keywords}")
            last_action = None
            for k in keywords:
                action = self._observe_single_keyword(k, max_results)
                if action:
                    last_action = action
            return last_action
        else:
            return self._observe_single_keyword(keyword, max_results)

    def _observe_single_keyword(self, keyword: str, max_results: Optional[int] = None):
        """Helper to run observation on a single keyword."""
        if max_results is None or max_results <= 0:
            try:
                max_results = int(os.getenv("PHRONEL_MAX_RESULTS", "10"))
            except Exception:
                max_results = 10

        logger.info(f"[Observer] Searching X for keyword: '{keyword}' (max_results: {max_results})...")
        search_results = x_client.search_tweets(query=keyword, max_results=max_results)

        if not search_results:
            logger.warning(f"[Observer] No results found or error occurred for '{keyword}'.")
            return None

        # Extract text and IDs from tweet objects. Handles both Tweepy Response objects and Mock dicts.
        tweets = []
        if isinstance(search_results, list): # Mock returns a list
            for t in search_results:
                if isinstance(t, dict):
                    tweet_id = str(t.get("id", "mock_id"))
                    if has_action_for_target(tweet_id):
                        logger.info(f"[Observer] Skipping tweet {tweet_id} because it has already been processed or proposed.")
                        continue
                    reply_settings = t.get("reply_settings", "everyone")
                    if reply_settings != "everyone":
                        logger.info(f"[Observer] Skipping tweet {tweet_id} because reply settings are restricted: '{reply_settings}'")
                        continue
                    tweets.append({
                        "id": tweet_id,
                        "text": t.get("text", ""),
                        "author_id": str(t.get("author_id", "mock_author_id")),
                        "conversation_id": str(t.get("conversation_id", "mock_conversation_id")),
                        "reply_settings": reply_settings
                    })
                else:
                    tweets.append({
                        "id": "mock_id",
                        "text": str(t),
                        "author_id": "mock_author_id",
                        "conversation_id": "mock_conversation_id",
                        "reply_settings": "everyone"
                    })
        elif hasattr(search_results, 'data') and search_results.data: # type: ignore # Tweepy V2 Response
            for tweet in search_results.data: # type: ignore
                tweet_id = str(tweet.id)
                if has_action_for_target(tweet_id):
                    logger.info(f"[Observer] Skipping tweet {tweet_id} because it has already been processed or proposed.")
                    continue
                
                # Get fields safely to prevent None being cast to string "None"
                author_val = getattr(tweet, "author_id", None)
                author_id = str(author_val) if author_val is not None else "unknown_author"
                
                conv_val = getattr(tweet, "conversation_id", None)
                conversation_id = str(conv_val) if conv_val is not None else str(tweet.id)
                
                reply_settings = getattr(tweet, "reply_settings", "everyone")
                if reply_settings != "everyone":
                    logger.info(f"[Observer] Skipping tweet {tweet_id} because reply settings are restricted: '{reply_settings}'")
                    continue
                
                tweets.append({
                    "id": tweet_id,
                    "text": tweet.text,
                    "author_id": author_id,
                    "conversation_id": conversation_id,
                    "reply_settings": reply_settings
                })
        else:
            logger.error("[Observer] Unrecognized search results format.")
            return None

        if not tweets:
            logger.warning(f"[Observer] No tweets extracted for '{keyword}'.")
            return None

        logger.info(f"[Observer] Found {len(tweets)} tweets for '{keyword}'. Running autonomous pipeline...")

        # Call process_and_propose to handle the full autonomous pipeline:
        # Analyze -> Strategize -> Create -> Propose (with real tweet IDs)
        action = brain.process_and_propose(tweets, context_summary=f"Keyword search: {keyword}", is_mention=False)
        return action

    def observe_mentions(self, max_results: Optional[int] = None):
        """
        Monitors mentions of the agent's account on X, processes them,
        and generates a proposed action.
        """
        if max_results is None or max_results <= 0:
            try:
                max_results = int(os.getenv("PHRONEL_MAX_RESULTS", "10"))
            except Exception:
                max_results = 10

        logger.info(f"[Observer] Fetching mentions from X (max_results: {max_results})...")
        mentions_results = x_client.get_mentions(max_results=max_results)

        if not mentions_results:
            logger.warning("[Observer] No mentions found or error occurred.")
            return None

        tweets = []
        # Support both Tweepy Response objects and Mock lists/responses
        if hasattr(mentions_results, 'data') and mentions_results.data: # type: ignore
            for tweet in mentions_results.data: # type: ignore
                tweet_id = str(tweet.id)
                if has_action_for_target(tweet_id):
                    logger.info(f"[Observer] Skipping mention {tweet_id} because it has already been processed or proposed.")
                    continue
                author_val = getattr(tweet, "author_id", None)
                author_id = str(author_val) if author_val is not None else "unknown_author"
                
                conv_val = getattr(tweet, "conversation_id", None)
                conversation_id = str(conv_val) if conv_val is not None else str(tweet.id)
                
                reply_settings = getattr(tweet, "reply_settings", "everyone")
                if reply_settings != "everyone":
                    logger.info(f"[Observer] Skipping mention {tweet_id} because reply settings are restricted: '{reply_settings}'")
                    continue

                tweets.append({
                    "id": tweet_id,
                    "text": tweet.text,
                    "author_id": author_id,
                    "conversation_id": conversation_id,
                    "reply_settings": reply_settings
                })
        else:
            logger.error("[Observer] Unrecognized mentions format or empty response.")
            return None

        if not tweets:
            logger.warning("[Observer] No actionable mentions extracted.")
            return None

        logger.info(f"[Observer] Found {len(tweets)} actionable mentions. Running autonomous pipeline...")
        action = brain.process_and_propose(tweets, context_summary="Mentions analysis", is_mention=True)
        return action

    def observe_followers(self, max_results: Optional[int] = None):
        """
        Monitors followers of the authenticated user on X, and generates
        a proposed follow action for any new followers we are not yet following.
        """
        if max_results is None or max_results <= 0:
            max_results = 20

        logger.info(f"[Observer] Fetching followers list from X (max_results: {max_results})...")
        followers = x_client.get_followers(max_results=max_results)

        if not followers:
            logger.warning("[Observer] No followers found or error occurred.")
            return None

        proposed_count = 0
        last_action = None
        
        from ..core.db import get_session, has_action_for_target
        from ..core.models import ActionLog

        for follower in followers:
            # Handles both dict-like objects and class instances (e.g. from MockFollower or Tweepy User)
            follower_id = str(getattr(follower, "id", None) if hasattr(follower, "id") else (follower.get("id") if isinstance(follower, dict) else "mock_follower_id"))
            follower_name = str(getattr(follower, "name", None) if hasattr(follower, "name") else (follower.get("name") if isinstance(follower, dict) else "Unknown Name"))
            follower_username = str(getattr(follower, "username", None) if hasattr(follower, "username") else (follower.get("username") if isinstance(follower, dict) else "unknown_user"))

            # Skip if we already have a pending, approved or executed action for this target follower
            if has_action_for_target(follower_id):
                logger.info(f"[Observer] Skipping follower {follower_username} ({follower_id}) because a follow action is already registered.")
                continue

            logger.info(f"[Observer] Detected follower: {follower_name} (@{follower_username}). Creating followback proposal...")
            
            with get_session() as session:
                new_action = ActionLog(
                    action_type="follow",
                    content=f"Follow back follower: {follower_name} (@{follower_username})",
                    target_id=follower_id,
                    status="pending"
                )
                session.add(new_action)
                session.commit()
                session.refresh(new_action)
                last_action = new_action
                proposed_count += 1
                logger.info(f"[Observer] Created followback proposal (ID: {new_action.id}) for follower {follower_username}.")

        logger.info(f"[Observer] Completed follower observation. Proposed {proposed_count} followback(s).")
        return last_action

# Global instance
observer = Observer()


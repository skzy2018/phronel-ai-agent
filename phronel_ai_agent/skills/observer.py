import os
import logging
from typing import Optional
from ..services.x_client import x_client
from .brain import brain

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
                    tweets.append({
                        "id": str(t.get("id", "mock_id")),
                        "text": t.get("text", ""),
                        "author_id": str(t.get("author_id", "mock_author_id")),
                        "conversation_id": str(t.get("conversation_id", "mock_conversation_id"))
                    })
                else:
                    tweets.append({
                        "id": "mock_id",
                        "text": str(t),
                        "author_id": "mock_author_id",
                        "conversation_id": "mock_conversation_id"
                    })
        elif hasattr(search_results, 'data') and search_results.data: # type: ignore # Tweepy V2 Response
            for tweet in search_results.data: # type: ignore
                tweets.append({
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "author_id": str(getattr(tweet, "author_id", "unknown_author")),
                    "conversation_id": str(getattr(tweet, "conversation_id", tweet.id))
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
        action = brain.process_and_propose(tweets, context_summary=f"Keyword search: {keyword}")
        return action

# Global instance
observer = Observer()

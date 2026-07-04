import logging
from ..core.db import get_session
from ..services.x_client import x_client
from .brain import brain

logger = logging.getLogger("phronel")

class Observer:
    """
    Observer Skill: Monitors the SNS environment (trends, mentions, searches)
    and passes gathered information to the Strategist (Brain) to generate potential actions.
    """

    def observe_keyword(self, keyword: str, max_results: int = 10):
        """
        Searches for a specific keyword on X, analyzes the recent tweets,
        and generates a proposed action based on the trend.
        """
        logger.info(f"[Observer] Searching X for keyword: '{keyword}'...")
        search_results = x_client.search_tweets(query=keyword, max_results=max_results)
        
        if not search_results:
            logger.warning("[Observer] No results found or error occurred.")
            return None

        # Extract text and IDs from tweet objects. Handles both Tweepy Response objects and Mock dicts.
        tweets = []
        if isinstance(search_results, list): # Mock returns a list
            for t in search_results:
                if isinstance(t, dict):
                    tweets.append({
                        "id": str(t.get("id", "mock_id")),
                        "text": t.get("text", ""),
                        "author_id": str(t.get("author_id", "mock_author_id"))
                    })
                else:
                    tweets.append({
                        "id": "mock_id",
                        "text": str(t),
                        "author_id": "mock_author_id"
                    })
        elif hasattr(search_results, 'data') and search_results.data: # type: ignore # Tweepy V2 Response
            for tweet in search_results.data: # type: ignore
                tweets.append({
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "author_id": str(getattr(tweet, "author_id", "unknown_author"))
                })
        else:
            logger.error("[Observer] Unrecognized search results format.")
            return None

        if not tweets:
            logger.warning("[Observer] No tweets extracted.")
            return None

        logger.info(f"[Observer] Found {len(tweets)} tweets. Running autonomous pipeline...")
        
        # Call process_and_propose to handle the full autonomous pipeline:
        # Analyze -> Strategize -> Create -> Propose (with real tweet IDs)
        action = brain.process_and_propose(tweets, context_summary=f"Keyword search: {keyword}")
        return action

# Global instance
observer = Observer()

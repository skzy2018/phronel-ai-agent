import tweepy
import logging
from ..core.models import AgentConfig
from ..core.db import get_session
from ..core.config import config

logger = logging.getLogger("phronel")

class XClient:
    def __init__(self):
        self.api = None
        self.client = None
        self._authenticated = False

    def _authenticate(self):
        """Authenticates with X API using credentials from the database."""
        if self._authenticated:
            return
            
        try:
            api_key = config.get("x_api_key")
            api_secret = config.get("x_api_secret")
            bearer_token = config.get("x_bearer_token")
            access_token = config.get("x_access_token")
            access_token_secret = config.get("x_access_token_secret")

            if api_key and api_secret and access_token and access_token_secret:
                try:
                    # Tweepy Client (V2 API)
                    self.client = tweepy.Client(
                        bearer_token=bearer_token,
                        consumer_key=api_key,
                        consumer_secret=api_secret,
                        access_token=access_token,
                        access_token_secret=access_token_secret
                    )
                    # Tweepy API (V1.1 API - needed for media upload)
                    auth = tweepy.OAuth1UserHandler(
                        api_key, api_secret,
                        access_token, access_token_secret
                    )
                    self.api = tweepy.API(auth)
                    logger.info("X API authenticated successfully.")
                    self._authenticated = True
                except Exception as e:
                    logger.error(f"X Authentication failed: {e}")
            else:
                logger.warning("X API credentials not found. Running in offline/mock mode.")
                self._authenticated = True # Mock mode is considered handled
        except Exception as e:
             # This handles the case where the database isn't initialized yet (e.g. during imports in tests)
             logger.warning(f"Could not authenticate XClient (DB might not be initialized): {e}")

    def post_tweet(self, text: str):
        """Posts a tweet."""
        self._authenticate()
        if self.client:
            try:
                response = self.client.create_tweet(text=text)
                return response.data # type: ignore
            except Exception as e:
                logger.error(f"Error posting tweet: {e}")
                return None
        else:
            logger.info(f"[MOCK] Posting tweet: {text}")
            return {"id": "mock_id", "text": text}

    def get_tweet(self, tweet_id: str):
        """Fetches a single tweet by its ID (V2 API)."""
        self._authenticate()
        if self.client:
            try:
                response = self.client.get_tweet(
                    id=tweet_id,
                    tweet_fields=["created_at", "author_id", "conversation_id"]
                )
                if response and response.data: # type: ignore
                    tweet = response.data # type: ignore
                    return {
                        "id": str(tweet.id),
                        "text": tweet.text,
                        "author_id": str(tweet.author_id),
                        "conversation_id": str(getattr(tweet, "conversation_id", tweet.id)),
                        "created_at": tweet.created_at.isoformat() if tweet.created_at else "",
                        "is_agent": False # Single target user tweet is always a customer/target unless it is our own
                    }
                return None
            except Exception as e:
                logger.error(f"Error fetching single tweet {tweet_id}: {e}")
                return None
        else:
            logger.info(f"[MOCK] Fetching single tweet: {tweet_id}")
            # Mock return matching our sequential threads or general target user text
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            return {
                "id": tweet_id,
                "text": "Phronelっていう自律AI営業ツール、かなり面白そうだけどPython以外でも動くのかな？",
                "author_id": "mock_customer_id",
                "conversation_id": "mock_conversation_id",
                "created_at": (now - timedelta(minutes=10)).isoformat(),
                "is_agent": False
            }

    def get_home_timeline(self, max_results=10):
        """Gets home timeline."""
        self._authenticate()
        if self.client:
            try:
                return self.client.get_home_timeline(max_results=max_results)
            except Exception as e:
                logger.error(f"Error getting timeline: {e}")
                return []
        else:
            logger.info("[MOCK] Getting home timeline")
            return []

    def search_tweets(self, query: str, max_results=10):
        """Searches for tweets."""
        self._authenticate()
        if self.client:
            try:
                return self.client.search_recent_tweets(query=query, max_results=max_results)
            except tweepy.errors.Unauthorized: # type: ignore
                logger.error("Error searching tweets: 401 Unauthorized. Please check your API credentials.")
                return []
            except tweepy.errors.Forbidden as e: # type: ignore
                error_msg = str(e)
                if "Project" in error_msg:
                    logger.error("Error: Your X App must be associated with a Project in the Developer Portal.")
                elif "Free" in error_msg or "403" in error_msg:
                    logger.error("Error: Your API tier may not support searching. (Free tier is limited to posting only).")
                else:
                    logger.error(f"Error searching tweets: 403 Forbidden. {e}")
                return []
            except Exception as e:
                logger.error(f"Error searching tweets: {e}")
                return []
        else:
            logger.info(f"[MOCK] Searching tweets for: {query}")
            return []

    def like_tweet(self, tweet_id: str):
        """Likes a tweet."""
        self._authenticate()
        if self.client:
            try:
                response = self.client.like(tweet_id=tweet_id)
                return response.data # type: ignore
            except Exception as e:
                logger.error(f"Error liking tweet {tweet_id}: {e}")
                return None
        else:
            logger.info(f"[MOCK] Liking tweet: {tweet_id}")
            return {"liked": True}

    def reply_to_tweet(self, tweet_id: str, text: str):
        """Replies to a tweet."""
        self._authenticate()
        if self.client:
            try:
                response = self.client.create_tweet(text=text, in_reply_to_tweet_id=tweet_id)
                return response.data # type: ignore
            except Exception as e:
                logger.error(f"Error replying to tweet {tweet_id}: {e}")
                return None
        else:
            logger.info(f"[MOCK] Replying to tweet {tweet_id}: {text}")
            return {"id": "mock_reply_id", "text": text}

    def get_tweet_metrics(self, tweet_ids: list[str]) -> list[dict]:
        """Fetches public metrics (likes, retweets, etc.) for a list of tweet IDs."""
        self._authenticate()
        if self.client:
            try:
                # X API v2 allows up to 100 IDs per request
                response = self.client.get_tweets(ids=tweet_ids, tweet_fields=["public_metrics"])
                if response.data: # type: ignore
                    metrics_list = []
                    for tweet in response.data: # type: ignore
                        metrics = tweet.public_metrics or {}
                        metrics_list.append({
                            "id": str(tweet.id),
                            "likes": metrics.get("like_count", 0),
                            "retweets": metrics.get("retweet_count", 0),
                            "replies": metrics.get("reply_count", 0),
                            "quotes": metrics.get("quote_count", 0),
                            "impressions": metrics.get("impression_count", 0)
                        })
                    return metrics_list
                return []
            except Exception as e:
                logger.error(f"Error getting tweet metrics: {e}")
                return []
        else:
            logger.info(f"[MOCK] Getting metrics for tweets: {tweet_ids}")
            # Return dummy metrics for MVP mock mode
            return [{"id": tid, "likes": 5, "retweets": 2, "replies": 1} for tid in tweet_ids]

    def get_conversation_thread(self, conversation_id: str, limit: int = 10):
        """
        Gets past tweets in a conversation thread using V2 search API.
        Returns a list of dicts with tweet info (created_at, author_id, text, is_agent).
        """
        self._authenticate()
        if self.client:
            try:
                # Query to fetch all recent tweets with this conversation ID
                query = f"conversation_id:{conversation_id}"
                response = self.client.search_recent_tweets(
                    query=query,
                    max_results=limit,
                    tweet_fields=["created_at", "author_id", "conversation_id", "in_reply_to_user_id"]
                )
                
                tweets = []
                if response.data: # type: ignore
                    # Get our own user_id if we have it to flag "is_agent"
                    my_user_id = None
                    try:
                        me_response = self.client.get_me()
                        if me_response and me_response.data: # type: ignore
                            my_user_id = str(me_response.data.id) # type: ignore
                    except Exception:
                        pass
                        
                    for tweet in response.data: # type: ignore
                        tweets.append({
                            "id": str(tweet.id),
                            "text": tweet.text,
                            "author_id": str(tweet.author_id),
                            "created_at": tweet.created_at.isoformat() if tweet.created_at else "",
                            "is_agent": str(tweet.author_id) == my_user_id if my_user_id else False
                        })
                return tweets
            except Exception as e:
                logger.error(f"Error fetching conversation thread {conversation_id}: {e}")
                return []
        else:
            logger.info(f"[MOCK] Getting conversation thread for: {conversation_id}")
            # Return high-quality, sequential dummy dialog representing a typical sales flow
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            return [
                {
                    "id": "mock_tweet_1",
                    "text": "Phronelっていう自律AI営業ツール、かなり面白そうだけどPython以外でも動くのかな？",
                    "author_id": "mock_customer_id",
                    "created_at": (now - timedelta(minutes=10)).isoformat(),
                    "is_agent": False
                },
                {
                    "id": "mock_tweet_2",
                    "text": "ご興味をお持ちいただきありがとうございます！現状はPython 3.10以上で開発されておりますが、将来的には他言語やWeb API経由での呼び出しも視野に入れています。",
                    "author_id": "mock_agent_id",
                    "created_at": (now - timedelta(minutes=8)).isoformat(),
                    "is_agent": True
                },
                {
                    "id": "mock_tweet_target",
                    "text": "いいですね！どこからダウンロードできますか？",
                    "author_id": "mock_customer_id",
                    "created_at": (now - timedelta(minutes=5)).isoformat(),
                    "is_agent": False
                }
            ]

# Global instance
x_client = XClient()

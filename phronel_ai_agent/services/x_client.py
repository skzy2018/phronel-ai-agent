import tweepy
import logging
import traceback
from typing import Optional
from ..core.models import AgentConfig
from ..core.db import get_session
from ..core.config import config

logger = logging.getLogger("phronel")

def mask_credential(cred: Optional[str]) -> str:
    if not cred:
        return "None"
    if len(cred) <= 8:
        return f"Present (len={len(cred)}, too short to mask safely)"
    return f"{cred[:4]}...{cred[-4:]} (len={len(cred)})"

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

            logger.debug("[XClient] Initializing X API Authentication...")
            logger.debug(f"[XClient]   API Key:             {mask_credential(api_key)}")
            logger.debug(f"[XClient]   API Secret:          {mask_credential(api_secret)}")
            logger.debug(f"[XClient]   Bearer Token:        {mask_credential(bearer_token)}")
            logger.debug(f"[XClient]   Access Token:        {mask_credential(access_token)}")
            logger.debug(f"[XClient]   Access Token Secret: {mask_credential(access_token_secret)}")

            if api_key and api_secret and access_token and access_token_secret:
                try:
                    # Tweepy Client (V2 API)
                    #   bearer_token=bearer_token,
                    self.client = tweepy.Client(
                        consumer_key=api_key,
                        consumer_secret=api_secret,
                        access_token=access_token,
                        access_token_secret=access_token_secret
                    )

                    # 2. App-only client (for search, timeline, etc.)
                    if bearer_token:
                        self.app_client = tweepy.Client(bearer_token=bearer_token)
                    else:
                        self.app_client = None
                        logger.warning("[XClient] Bearer token not provided. Some endpoints")
                    
                    # Tweepy API (V1.1 API - needed for media upload)
                    auth = tweepy.OAuth1UserHandler(api_key, api_secret,access_token, access_token_secret)
                    self.api = tweepy.API(auth)
                    logger.info("X API authenticated successfully.")

                    self._authenticated = True
                except Exception as e:
                    logger.error(f"X Authentication failed: {e}")
                    logger.error(f"[XClient] Auth Traceback:\n{traceback.format_exc()}")
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
                logger.debug(f"[XClient] Sending create_tweet API v2 request. Text: '{text}'")
                response = self.client.create_tweet(text=text)
                logger.info(f"[XClient] Tweet posted successfully! Response data: {response.data if response else 'None'}") # type: ignore
                return response.data # type: ignore
            except tweepy.errors.HTTPException as te: # type: ignore
                logger.error(f"[XClient] Tweepy HTTPException in post_tweet!")
                logger.error(f"[XClient]   HTTP Status Code: {te.response.status_code if te.response else 'Unknown'}")
                logger.error(f"[XClient]   Response Headers: {te.response.headers if te.response else 'Unknown'}")
                logger.error(f"[XClient]   Response Text:    {te.response.text if te.response else 'None'}")
                if hasattr(te, 'api_codes'):
                    logger.error(f"[XClient]   API Codes:    {te.api_codes}")
                if hasattr(te, 'api_messages'):
                    logger.error(f"[XClient]   API Messages: {te.api_messages}")
                return None
            except Exception as e:
                logger.error(f"[XClient] Generic Exception posting tweet: {e}")
                logger.error(f"[XClient] Traceback:\n{traceback.format_exc()}")
                return None
        else:
            logger.info(f"[MOCK] Posting tweet: {text}")
            return {"id": "mock_id", "text": text}

    def get_tweet(self, tweet_id: str):
        """Fetches a single tweet by its ID (V2 API)."""
        self._authenticate()
        if self.app_client:
            try:
                response = self.app_client.get_tweet(
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
        if self.app_client:
            try:
                # Ensure we exclude retweets and replies for high-quality, actionable top-level targets
                final_query = query
                if "-is:retweet" not in query:
                    final_query += " -is:retweet"
                if "-is:reply" not in query:
                    final_query += " -is:reply"

                logger.debug(f"[XClient] Searching recent tweets for query: '{final_query}' with fields...")
                return self.app_client.search_recent_tweets(
                    query=final_query, 
                    max_results=max_results,
                    tweet_fields=["author_id", "conversation_id", "created_at", "reply_settings"]
                )
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
                logger.debug(f"[XClient] Attempting to like tweet: {tweet_id}")
                response = self.client.like(tweet_id=tweet_id)
                logger.info(f"[XClient] Tweet liked successfully! Response data: {response.data if response else 'None'}") # type: ignore
                return response.data # type: ignore
            except tweepy.errors.HTTPException as te: # type: ignore
                logger.error(f"[XClient] Tweepy HTTPException in like_tweet for tweet {tweet_id}!")
                logger.error(f"[XClient]   HTTP Status Code: {te.response.status_code if te.response else 'Unknown'}")
                logger.error(f"[XClient]   Response Text:    {te.response.text if te.response else 'None'}")
                return None
            except Exception as e:
                logger.error(f"[XClient] Generic Exception liking tweet {tweet_id}: {e}")
                logger.error(f"[XClient] Traceback:\n{traceback.format_exc()}")
                return None
        else:
            logger.info(f"[MOCK] Liking tweet: {tweet_id}")
            return {"liked": True}

    def reply_to_tweet(self, tweet_id: str, text: str):
        """Replies to a tweet."""
        self._authenticate()
        if self.client:
            try:
                logger.debug(f"[XClient] Sending reply to tweet {tweet_id}. Text: '{text}'")
                response = self.client.create_tweet(text=text, in_reply_to_tweet_id=tweet_id)
                logger.info(f"[XClient] Reply posted successfully! Response data: {response.data if response else 'None'}") # type: ignore
                return response.data # type: ignore
            except tweepy.errors.HTTPException as te: # type: ignore
                logger.error(f"[XClient] Tweepy HTTPException in reply_to_tweet for tweet {tweet_id}!")
                logger.error(f"[XClient]   HTTP Status Code: {te.response.status_code if te.response else 'Unknown'}")
                logger.error(f"[XClient]   Response Headers: {te.response.headers if te.response else 'Unknown'}")
                logger.error(f"[XClient]   Response Text:    {te.response.text if te.response else 'None'}")
                if hasattr(te, 'api_codes'):
                    logger.error(f"[XClient]   API Codes:    {te.api_codes}")
                if hasattr(te, 'api_messages'):
                    logger.error(f"[XClient]   API Messages: {te.api_messages}")
                return None
            except Exception as e:
                logger.error(f"[XClient] Generic Exception replying to tweet {tweet_id}: {e}")
                logger.error(f"[XClient] Traceback:\n{traceback.format_exc()}")
                return None
        else:
            logger.info(f"[MOCK] Replying to tweet {tweet_id}: {text}")
            return {"id": "mock_reply_id", "text": text}

    def get_tweet_metrics(self, tweet_ids: list[str]) -> list[dict]:
        """Fetches public metrics (likes, retweets, etc.) for a list of tweet IDs."""
        self._authenticate()
        if self.app_client:
            try:
                # X API v2 allows up to 100 IDs per request
                response = self.app_client.get_tweets(ids=tweet_ids, tweet_fields=["public_metrics"])
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
        if self.app_client and self.client:
            try:
                # Query to fetch all recent tweets with this conversation ID
                query = f"conversation_id:{conversation_id}"
                response = self.app_client.search_recent_tweets(
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

    def get_mentions(self, max_results=10):
        """Fetches tweets mentioning the authenticated user (V2 API)."""
        self._authenticate()
        if self.client:
            try:
                # 1. Get authenticated user ID
                me_response = self.client.get_me()
                if me_response and me_response.data: # type: ignore
                    my_user_id = me_response.data.id # type: ignore
                    logger.debug(f"[XClient] Fetching mentions for user ID {my_user_id}...")
                    response = self.client.get_users_mentions(
                        id=my_user_id,
                        max_results=max_results,
                        tweet_fields=["author_id", "conversation_id", "created_at", "reply_settings"]
                    )
                    return response
                else:
                    logger.error("[XClient] Could not retrieve authenticated user ID for mentions.")
                    return None
            except Exception as e:
                logger.error(f"Error fetching mentions: {e}")
                return None
        else:
            logger.info("[MOCK] Getting mentions")
            # Return dummy mentions for MVP mock mode
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            class MockTweet:
                def __init__(self, id, text, author_id, conversation_id, created_at, reply_settings="everyone"):
                    self.id = id
                    self.text = text
                    self.author_id = author_id
                    self.conversation_id = conversation_id
                    self.created_at = created_at
                    self.reply_settings = reply_settings
            
            class MockResponse:
                def __init__(self, data):
                    self.data = data
            
            mock_tweets = [
                MockTweet(
                    id="mock_mention_1",
                    text="@Phronel_Agent PhronelのRAG機能について教えて！資料はある？",
                    author_id="mock_customer_id",
                    conversation_id="mock_conversation_id_mention",
                    created_at=now - timedelta(minutes=5)
                )
            ]
            return MockResponse(mock_tweets)

    def follow_user(self, target_user_id: str):
        """Follows a user on X (V2 API)."""
        self._authenticate()
        if self.client:
            try:
                logger.debug(f"[XClient] Sending follow_user API v2 request for user ID: {target_user_id}")
                response = self.client.follow_user(target_user_id=target_user_id)
                logger.info(f"[XClient] Successfully followed user {target_user_id}! Response: {response.data if response else 'None'}") # type: ignore
                return response.data if response else {"following": True} # type: ignore
            except Exception as e:
                logger.error(f"[XClient] Error following user {target_user_id}: {e}")
                logger.error(f"[XClient] Traceback:\n{traceback.format_exc()}")
                return None
        else:
            logger.info(f"[MOCK] Following user with ID: {target_user_id}")
            return {"following": True, "pending": False}

    def get_followers(self, max_results=20):
        """Fetches list of followers for the authenticated user (V2 API)."""
        self._authenticate()
        if self.client:
            try:
                me_response = self.client.get_me()
                if me_response and me_response.data: # type: ignore
                    my_user_id = me_response.data.id # type: ignore
                    logger.debug(f"[XClient] Fetching followers list for user ID {my_user_id}...")
                    response = self.client.get_users_followers(
                        id=my_user_id,
                        max_results=max_results,
                        user_fields=["username", "name"]
                    )
                    return response.data if response else [] # type: ignore
                else:
                    logger.error("[XClient] Could not retrieve authenticated user ID for followers list.")
                    return []
            except Exception as e:
                logger.error(f"Error fetching followers list: {e}")
                return []
        else:
            logger.info("[MOCK] Getting followers list")
            class MockFollower:
                def __init__(self, id, name, username):
                    self.id = id
                    self.name = name
                    self.username = username
            return [
                MockFollower(id="mock_follower_1", name="John Doe", username="john_doe_test"),
                MockFollower(id="mock_follower_2", name="Alice Smith", username="alice_smith_test")
            ]

# Global instance
x_client = XClient()


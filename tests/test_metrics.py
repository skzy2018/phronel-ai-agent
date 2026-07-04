import pytest
from unittest.mock import MagicMock, patch
from phronel_ai_agent.skills.metrics import (
    count_emojis,
    count_hashtags,
    cosine_similarity,
    phronel_multi_tier_metric
)

def test_count_emojis():
    assert count_emojis("Hello world! 😊") == 1
    assert count_emojis("Testing 🚀 double emoji 🔥") == 2
    assert count_emojis("Plain text with no emojis.") == 0

def test_count_hashtags():
    assert count_hashtags("This is a #test of #python.") == 2
    assert count_hashtags("No hashtags here.") == 0
    assert count_hashtags("Hashtag at the end #AI") == 1

def test_cosine_similarity():
    v1 = [1.0, 2.0, 3.0]
    v2 = [1.0, 2.0, 3.0]
    # Identical vectors should have a similarity of 1.0
    assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-6

    # Orthogonal vectors should have a similarity of 0.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0

def test_phronel_multi_tier_metric_hard_guardrails():
    # Helper to mock Example and Prediction
    def get_mocks(tweet_text, strategy_text=""):
        example = MagicMock()
        example.strategy = strategy_text
        pred = MagicMock()
        pred.tweet_text = tweet_text
        return example, pred

    # 1. Text too long (> 280) should fail (score 0.0)
    ex, pred = get_mocks("a" * 281)
    assert phronel_multi_tier_metric(ex, pred) == 0.0

    # 2. Text empty should fail
    ex, pred = get_mocks("   ")
    assert phronel_multi_tier_metric(ex, pred) == 0.0

    # 3. Hallucination indicator should fail
    ex, pred = get_mocks("Please insert your [リンク] here.")
    assert phronel_multi_tier_metric(ex, pred) == 0.0

def test_phronel_multi_tier_metric_scoring():
    # Helper mocks
    example = MagicMock()
    example.strategy = "Promote product features"
    
    pred = MagicMock()
    # Good tweet: <= 3 hashtags, <= 2 emojis, mock embeddings fallback
    # Starts with 0.0 score.
    # Meets Hashtags constraint (<= 3): +0.2
    # Meets Emojis constraint (<= 2): +0.2
    # Embedding fails/fallback: +0.3
    # Total score should be 0.7
    pred.tweet_text = "Meet Phronel: your new autonomous SNS assistant! 🚀 #AI #SaaS"
    
    with patch("phronel_ai_agent.skills.metrics.get_text_embedding", return_value=None):
        score = phronel_multi_tier_metric(example, pred)
        assert abs(score - 0.7) < 1e-6

    # Penalized tweet: > 3 hashtags, > 2 emojis
    # Meets Hashtags constraint (<= 3): Fail (+0.0)
    # Meets Emojis constraint (<= 2): Fail (+0.0)
    # Embedding fallback: +0.3
    # Total score should be 0.3
    pred_bad = MagicMock()
    pred_bad.tweet_text = "Check this out! 😊🔥🚀 #AI #SaaS #Twitter #Marketing #Tech"
    with patch("phronel_ai_agent.skills.metrics.get_text_embedding", return_value=None):
        score = phronel_multi_tier_metric(example, pred_bad)
        assert abs(score - 0.3) < 1e-6

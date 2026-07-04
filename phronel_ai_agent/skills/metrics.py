import os
import re
import math
import logging
from typing import Optional, List
from chromadb.utils import embedding_functions  # pyright: ignore[reportMissingImports]

logger = logging.getLogger("phronel")

# Regex pattern for matching most common emojis (emoticons, symbols, flags, pictographs)
EMOJI_PATTERN = re.compile(
    "["
    "\U0001f600-\U0001f64f|"  # emoticons
    "\U0001f300-\U0001f5ff|"  # symbols & pictographs
    "\U0001f680-\U0001f6ff|"  # transport & map symbols
    "\U0001f1e0-\U0001f1ff|"  # flags
    "\U00002700-\U000027bf|"  # dingbats
    "\U00002600-\U000026ff|"  # miscellaneous symbols
    "\U0001f900-\U0001f9ff|"  # supplemental symbols and pictographs
    "\U0001fa00-\U0001faff"   # symbols and pictographs extended
    "]", flags=re.UNICODE
)

# Standard list of placeholder/hallucination indicators
HALLUCINATION_INDICATORS = [
    "[リンク", "[url", "[URL", "http://insert", "https://insert",
    "<会社名>", "<製品名>", "<url>", "{json}", "{JSON", "target_tweet_id"
]

def count_emojis(text: str) -> int:
    """Counts the number of emojis in a text."""
    return len(EMOJI_PATTERN.findall(text))

def count_hashtags(text: str) -> int:
    """Counts the number of hashtags in a text (#word)."""
    return len(re.findall(r"#\w+", text))

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes the cosine similarity between two float vectors."""
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

def get_text_embedding(text: str) -> Optional[List[float]]:
    """Generates text embedding using ChromaDB default embedding function."""
    try:
        # Use ChromaDB's built-in default embedding function (ONNX MiniLM-L6-v2)
        ef = embedding_functions.DefaultEmbeddingFunction()
        embeddings = ef([text])
        if embeddings and len(embeddings) > 0:
            return [float(x) for x in embeddings[0]]
    except Exception as e:
        logger.warning(f"[Metrics] Failed to generate embedding: {e}")
    return None

def phronel_multi_tier_metric(example, pred, trace=None) -> float:
    """
    Phronel Multi-Tier Scored Metric for DSPy Optimizer.
    
    Evaluates generated tweet text on:
      1. Hard Guardrails (Hard Check: length <= 280, non-empty, no hallucination placeholders).
         -> Fails immediately with 0.0 score.
         
      2. Aesthetic & Persona Rules (絵文字数 <= 2, ハッシュタグ数 <= 3).
         -> Contributes up to 0.4 score (0.2 points each).
         
      3. Semantic Relevance (Cosine similarity between generated tweet and strategy text).
         -> Uses ChromaDB's default embedding function locally to compute vector similarity.
         -> Contributes up to 0.6 score (cosine_similarity * 0.6).
         
    Returns:
      A float value between 0.0 (Worst / Guardrail Fail) and 1.0 (Best).
    """
    text = getattr(pred, "tweet_text", "") or ""
    
    # --------------------------------------------------------------------------
    # Tier 1: Hard Guardrails (Hard checks - Fail immediately)
    # --------------------------------------------------------------------------
    # Character length limit (X limit)
    if len(text) > 280:
        logger.debug(f"[Metric Hard Guardrail Fail] Character count exceeds 280: {len(text)}")
        return 0.0
        
    # Empty string check
    if not text.strip():
        logger.debug("[Metric Hard Guardrail Fail] Text is empty")
        return 0.0
        
    # Hallucination / insertion placeholder check
    for indicator in HALLUCINATION_INDICATORS:
        if indicator in text:
            logger.debug(f"[Metric Hard Guardrail Fail] Found placeholder indicator: '{indicator}'")
            return 0.0

    score = 0.0

    # --------------------------------------------------------------------------
    # Tier 2: Aesthetic & Persona Rules (Max 0.4 points)
    # --------------------------------------------------------------------------
    # Hashtags count constraint (<= 3 hashtags is optimal for reach)
    hashtag_count = count_hashtags(text)
    if hashtag_count <= 3:
        score += 0.2
    else:
        logger.debug(f"[Metric Penalty] Hashtag count is {hashtag_count} (> 3)")

    # Emojis count constraint (<= 2 emojis maintains intellectual persona)
    emoji_count = count_emojis(text)
    if emoji_count <= 2:
        score += 0.2
    else:
        logger.debug(f"[Metric Penalty] Emoji count is {emoji_count} (> 2)")

    # --------------------------------------------------------------------------
    # Tier 3: Semantic Relevance via Local Vector Similarity (Max 0.6 points)
    # --------------------------------------------------------------------------
    strategy_text = getattr(example, "strategy", "") or ""
    if strategy_text:
        pred_emb = get_text_embedding(text)
        strat_emb = get_text_embedding(strategy_text)
        
        if pred_emb and strat_emb:
            sim = cosine_similarity(pred_emb, strat_emb)
            # Bound cosine similarity between 0.0 and 1.0
            sim_clipped = max(0.0, min(1.0, sim))
            score += sim_clipped * 0.6
            logger.debug(f"[Metric Score] Vector Similarity: {sim_clipped:.4f} (Weighted: {sim_clipped * 0.6:.4f})")
        else:
            # Fallback if embedding fails (neutral semantic relevance score)
            score += 0.3
            logger.warning("[Metrics] Embedding failed, fallback applied.")
    else:
        # Default relevance score if no strategy exists to compare against
        score += 0.3

    final_score = max(0.0, min(1.0, score))
    logger.info(f"[Metric Result] Evaluated tweet score: {final_score:.4f} (Raw text: '{text[:40]}...')")
    return final_score

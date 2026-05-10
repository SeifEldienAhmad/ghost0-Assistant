"""
Knowledge engine module for ghost0 - manages payload databases and content scoring.
"""
import re
import json
import math
from typing import List, Dict, Tuple
import os

from logger_config import get_logger

logger = get_logger(__name__)

PAYLOAD_DB = "payload_index.json"

# Content scoring constants
MIN_CONTENT_LENGTH = 200
MAX_CONTENT_LENGTH = 2000
NOISY_CONTENT_LENGTH = 5000

# Methodology keywords
METHODOLOGY_KEYWORDS = [
    "enumeration",
    "exploitation",
    "post exploitation",
    "bypass",
    "payload",
    "rce",
    "sqli",
    "ssrf",
    "xss",
    "lfi"
]

# Command keywords
COMMAND_KEYWORDS = [
    "curl ",
    "wget ",
    "nc ",
    "nmap ",
    "sqlmap ",
    "ffuf ",
    "gobuster ",
    "hydra "
]


# -----------------------
# Payload DB
# -----------------------
def load_payload_db() -> Dict[str, List[str]]:
    """Load payload database from JSON file."""
    try:
        with open(PAYLOAD_DB, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.debug("Payload DB not found, creating empty database")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse payload database: {e}")
        return {}


def save_payload_db(db: Dict[str, List[str]]) -> None:
    """Save payload database to JSON file."""
    try:
        with open(PAYLOAD_DB, 'w') as f:
            json.dump(db, f, indent=2)
        logger.debug(f"Saved {sum(len(v) for v in db.values())} payloads")
    except IOError as e:
        logger.error(f"Failed to save payload database: {e}")


# -----------------------
# Detect Payloads
# -----------------------
def detect_payloads(text: str) -> List[str]:
    """
    Detect and extract payloads from text.
    
    Args:
        text: Text to search for payloads
    
    Returns:
        List of unique payloads found
    """
    patterns = [
        r"(?i)(union\s+select\s+.{1,100}?)",
        r"(?i)(\.\./\.\/.{1,100}?)",
        r"(?i)(<script>.{1,100}?</script>)",
        r"(?i)(bash\s+-i\s+.{1,100}?)",
        r"(?i)(curl\s+.{1,100}?)",
        r"(?i)(wget\s+.{1,100}?)",
        r"(?i)(nc\s+.{1,100}?)",
        r"(?i)(php\s+-r\s+.{1,100}?)"
    ]
    
    payloads = []
    
    for pattern in patterns:
        try:
            found = re.findall(pattern, text, re.MULTILINE)
            payloads.extend(found)
        except re.error as e:
            logger.warning(f"Regex error in pattern {pattern}: {e}")
            continue
    
    # Clean and deduplicate
    cleaned = []
    for p in payloads:
        p = p.strip()
        if 4 <= len(p) <= 500:  # Sanity check on length
            cleaned.append(p)
    
    return list(set(cleaned))


# -----------------------
# Payload Ranking
# -----------------------
def rank_payload(payload: str) -> int:
    """
    Rank payload by suspicious characteristics.
    
    Args:
        payload: Payload string
    
    Returns:
        Numeric score
    """
    p = payload.lower()
    score = 0
    
    # Dangerous patterns
    if "169.254" in p:
        score += 5
    if "union select" in p:
        score += 5
    if "../../" in p:
        score += 4
    if "<script>" in p:
        score += 4
    if "bash -i" in p:
        score += 5
    if "curl" in p:
        score += 2
    if "passwd" in p:
        score += 3
    if "root" in p:
        score += 2
    
    return score


# -----------------------
# Payload Dedup
# -----------------------
def payload_exists(existing: List[str], payload: str) -> bool:
    """
    Check if payload already exists in database.
    
    Args:
        existing: List of existing payloads
        payload: Payload to check
    
    Returns:
        True if exists
    """
    p = payload.lower().strip()
    
    for e in existing:
        if p == e.lower().strip():
            return True
    
    return False


# -----------------------
# Store Payloads
# -----------------------
def store_payloads(
    payloads: List[str],
    tag: str = "general"
) -> None:
    """
    Store payloads in database with tag.
    
    Args:
        payloads: List of payloads
        tag: Category tag
    """
    db = load_payload_db()
    
    if tag not in db:
        db[tag] = []
    
    existing = db[tag]
    
    for p in payloads:
        if not payload_exists(existing, p):
            existing.append(p)
            logger.debug(f"Added payload to '{tag}': {p[:50]}")
    
    # Sort by rank
    existing = sorted(
        list(set(existing)),
        key=rank_payload,
        reverse=True
    )
    
    db[tag] = existing[:100]  # Limit to 100 per tag
    save_payload_db(db)


# -----------------------
# Get Payloads
# -----------------------
def get_payloads(tag: str = "general", limit: int = 5) -> List[str]:
    """
    Retrieve payloads from database.
    
    Args:
        tag: Category tag
        limit: Maximum payloads to return
    
    Returns:
        List of payloads
    """
    db = load_payload_db()
    return db.get(tag, [])[:limit]


# -----------------------
# Adaptive Content Score
# -----------------------
def score_content(text: str) -> int:
    """
    Score content quality for knowledge ingestion.
    
    Args:
        text: Content to score
    
    Returns:
        Numeric quality score
    """
    if not text or len(text) < 50:
        return 0
    
    t = text.lower()
    score = 0
    
    # Methodology presence
    for keyword in METHODOLOGY_KEYWORDS:
        if keyword in t:
            score += 2
    
    # Common commands
    for cmd in COMMAND_KEYWORDS:
        if cmd in t:
            score += 1
    
    # CVE mentions
    if re.search(r'cve-\d{4}-\d{4,}', t):
        score += 3
    
    # Payload density
    payloads = detect_payloads(text)
    if len(payloads) >= 3:
        score += 4
    elif len(payloads) > 0:
        score += 2
    
    # Structure (list items)
    dash_count = text.count('-')
    if dash_count > 5:
        score += 2
    
    # Ideal length
    if MIN_CONTENT_LENGTH < len(text) < MAX_CONTENT_LENGTH:
        score += 3
    
    # Penalize very long content (likely noisy)
    if len(text) > NOISY_CONTENT_LENGTH:
        score -= 3
    
    return max(0, score)


# -----------------------
# Semantic Similarity
# -----------------------
def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        a: Vector A
        b: Vector B
    
    Returns:
        Similarity score 0-1
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    
    try:
        dot = sum(x*y for x, y in zip(a, b))
        na = math.sqrt(sum(x*x for x in a))
        nb = math.sqrt(sum(x*x for x in b))
        
        if na == 0 or nb == 0:
            return 0.0
        
        return dot / (na * nb)
    
    except (ValueError, OverflowError) as e:
        logger.error(f"Error calculating cosine similarity: {e}")
        return 0.0


# -----------------------
# Semantic Dedup
# -----------------------
def semantic_duplicate(
    db,
    embeddings,
    text: str,
    threshold: float = 0.90
) -> bool:
    """
    Check if content is semantically duplicate.
    
    Args:
        db: Chroma database instance
        embeddings: Embedding function
        text: Content to check
        threshold: Similarity threshold
    
    Returns:
        True if duplicate found
    """
    if not db:
        logger.warning("Database not initialized for deduplication check")
        return False
    
    try:
        docs = db.similarity_search(text, k=3)
        
        if not docs:
            return False
        
        new_vec = embeddings.embed_query(text)
        
        for d in docs:
            try:
                old_vec = embeddings.embed_query(d.page_content)
                sim = cosine_similarity(new_vec, old_vec)
                
                if sim >= threshold:
                    logger.debug(f"Duplicate found with similarity {sim:.2f}")
                    return True
            
            except Exception as e:
                logger.debug(f"Error comparing embeddings: {e}")
                continue
        
        return False
    
    except Exception as e:
        logger.error(f"Semantic deduplication failed: {e}")
        return False

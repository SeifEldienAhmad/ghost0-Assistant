"""
Web learning module for ghost0 - discovers and ingests security knowledge from the web.
"""
import requests
import json
import time
import re
import os
from typing import Optional
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from ddgs import DDGS

from knowledge_engine import score_content, store_payloads, detect_payloads
from logger_config import get_logger

load_dotenv()

logger = get_logger(__name__)

CACHE_FILE = "learn_cache.json"
MAX_LINKS = 2
RATE_LIMIT = 5
MAX_CHARS = 2500


# -----------------------
# Cache
# -----------------------
def load_cache() -> set:
    """Load cached URLs from JSON file."""
    try:
        with open(CACHE_FILE, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse cache file: {e}")
        return set()


def save_cache(cache: set) -> None:
    """Save cached URLs to JSON file."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(list(cache), f)
        logger.debug(f"Cached {len(cache)} URLs")
    except IOError as e:
        logger.error(f"Failed to save cache: {e}")


# -----------------------
# Dorks
# -----------------------
def generate_dorks(query: str) -> list:
    """Generate search dorks for more targeted queries."""
    return [
        f"{query} writeup",
        f"{query} exploit",
        f"{query} walkthrough",
        f"{query} site:github.com"
    ]


# -----------------------
# Search
# -----------------------

def domain_score(link: str) -> int:
    """
    Score a URL by domain heuristics.
    """
    lowered = link.lower()

    if any(block in lowered for block in [
        "google.com",
        "youtube.com",
        "facebook.com",
        "twitter.com",
        "linkedin.com",
        "login",
        "signup",
        "tag",
        "category"
    ]):
        return 0

    if lowered.endswith((".pdf", ".jpg", ".png", ".gif", ".svg")):
        return 0

    return 1


def search_web(query: str) -> list:
    """
    Search for security knowledge using DuckDuckGo.
    """
    results = []
    seen = set()
    dorks = generate_dorks(query)

    with DDGS() as ddgs:
        for dork in dorks:
            try:
                logger.debug(f"Searching: {dork}")
                data = ddgs.text(dork, max_results=10)

                for item in data:
                    link = item.get("href", "")
                    if not link or link in seen:
                        continue

                    score = domain_score(link)
                    if score <= 0:
                        continue

                    seen.add(link)
                    results.append((link, score))

            except Exception as e:
                logger.error(f"[SEARCH ERROR] {e}")
                continue

    results.sort(key=lambda x: x[1], reverse=True)
    unique_results = [x[0] for x in results[:MAX_LINKS]]
    logger.info(f"Found {len(unique_results)} unique results for '{query}'")
    return unique_results


# -----------------------
# Fetch Page
# -----------------------
def fetch_page(url: str) -> str:
    """
    Fetch and clean webpage content.
    
    Args:
        url: URL to fetch
    
    Returns:
        Cleaned text content
    """
    try:
        logger.debug(f"Fetching: {url}")
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Security Research Bot)"},
            timeout=15
        )
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Remove noisy elements
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        
        return soup.get_text(separator="\n")
    
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        return ""


# -----------------------
# Clean
# -----------------------
def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# -----------------------
# Summarize
# -----------------------
def summarize(
    content: str,
    ollama_url: str,
    model: str
) -> str:
    """
    Summarize content using Ollama.
    
    Args:
        content: Content to summarize
        ollama_url: Ollama API URL
        model: Model name to use
    
    Returns:
        Summarized content
    """
    try:
        logger.debug(f"Summarizing with {model}")
        r = requests.post(
            ollama_url,
            json={
                "model": model,
                "prompt": f"Summarize this pentest methodology:\n{content[:2000]}",
                "stream": False
            },
            timeout=300
        )
        r.raise_for_status()
        
        return r.json().get("response", "").strip()
    
    except requests.RequestException as e:
        logger.error(f"Summarization failed: {e}")
        return ""
    except json.JSONDecodeError as e:
        logger.error(f"Invalid response from Ollama: {e}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error during summarization: {e}")
        return ""


# -----------------------
# Main Learn
# -----------------------
def learn_from_web(
    query: str,
    db,
    embeddings,
    ollama_url: str,
    model: str,
    score_fn,
    dedup_fn
) -> None:
    """
    Learn from web sources and ingest knowledge into the database.
    
    Args:
        query: Search query
        db: Chroma database instance
        embeddings: Embedding function
        ollama_url: Ollama API URL
        model: Model to use for summarization
        score_fn: Scoring function for content quality
        dedup_fn: Deduplication function
    """
    if not db:
        logger.error("Database not initialized")
        return
    
    cache = load_cache()
    links = search_web(query)
    
    if not links:
        logger.warning(f"No results found for '{query}'")
        return
    
    learned_count = 0
    
    for link in links:
        if link in cache:
            logger.debug(f"Skipping cached URL: {link}")
            continue
        
        logger.info(f"Processing: {link}")
        
        raw = fetch_page(link)
        if not raw:
            logger.warning(f"Failed to fetch content from {link}")
            cache.add(link)
            continue
        
        cleaned = clean_text(raw)
        
        if len(cleaned) < 300:
            logger.debug(f"Content too short ({len(cleaned)} chars), skipping")
            cache.add(link)
            continue
        
        knowledge = summarize(cleaned[:MAX_CHARS], ollama_url, model)
        
        if len(knowledge) < 50:
            logger.debug("Summarization produced insufficient content")
            cache.add(link)
            continue
        
        # Extract and store payloads
        payloads = detect_payloads(cleaned)
        if payloads:
            knowledge += "\n\nPayloads:\n"
            for p in payloads[:5]:
                knowledge += f"- {p}\n"
            store_payloads(payloads, query)
        
        # Score content
        score = score_content(knowledge)
        if score < 4:
            logger.debug(f"Content score too low ({score}), skipping")
            cache.add(link)
            continue
        
        # Check for duplicates
        if dedup_fn(knowledge):
            logger.debug("Content is duplicate, skipping")
            cache.add(link)
            continue
        
        # Ingest into database
        try:
            db.add_texts([knowledge])
            logger.info(f"Learned from {link} (score: {score})")
            learned_count += 1
            cache.add(link)
            save_cache(cache)
        
        except Exception as e:
            logger.error(f"Failed to ingest knowledge: {e}")
            continue
        
        # Rate limiting
        time.sleep(RATE_LIMIT)
    
    logger.info(f"Web learning completed: {learned_count} new sources ingested")

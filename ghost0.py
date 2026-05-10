"""
ghost0 - AI-powered penetration testing assistant for CTFs and bug bounty hunting.
Integrates web learning, attack chain building, and tactical knowledge management.
"""
import requests
import json
import time
import os
from typing import Optional, Dict, List
from collections import deque
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from web_learner import learn_from_web
from attack_engine import (
    build_attack_chain,
    get_state,
    response_analyzer
)
from knowledge_engine import (
    score_content,
    semantic_duplicate
)
from logger_config import get_logger

load_dotenv()

logger = get_logger(__name__)

# -----------------------
# CONFIG
# -----------------------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen2.5:3b")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:7b")
MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "ghost0")

MEM_FILE = "memory.json"
CHECK_FILE = "data_check.txt"
RAG_DB_PATH = os.getenv("RAG_DB_PATH", "./rag_db")

MEMORY_SIZE = int(os.getenv("MEMORY_SIZE", "10"))
TACTICAL_MEMORY_SIZE = int(os.getenv("TACTICAL_MEMORY_SIZE", "8"))

memory: deque = deque(maxlen=MEMORY_SIZE)
tactical_memory: deque = deque(maxlen=TACTICAL_MEMORY_SIZE)

# -----------------------
# RAG INIT
# -----------------------
db: Optional[Chroma] = None
embeddings: Optional[OllamaEmbeddings] = None


def initialize_rag() -> bool:
    """
    Initialize RAG database and embeddings.
    
    Returns:
        True if successful, False otherwise
    """
    global db, embeddings
    
    try:
        logger.info("Initializing RAG system...")
        
        # Test Ollama connection
        try:
            r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
            r.raise_for_status()
            logger.info("Ollama connection OK")
        except requests.RequestException as e:
            logger.error(f"Cannot connect to Ollama at {OLLAMA_HOST}: {e}")
            logger.info("Make sure Ollama is running: ollama serve")
            return False
        
        # Initialize embeddings
        embeddings = OllamaEmbeddings(model=OLLAMA_EMBEDDING_MODEL)
        logger.debug(f"Embeddings initialized: {OLLAMA_EMBEDDING_MODEL}")
        
        # Initialize database
        db = Chroma(
            persist_directory=RAG_DB_PATH,
            embedding_function=embeddings
        )
        logger.info(f"RAG database initialized at {RAG_DB_PATH}")
        
        return True
    
    except Exception as e:
        logger.error(f"RAG initialization failed: {e}")
        db = None
        embeddings = None
        return False


# -----------------------
# Load Context
# -----------------------
def load_context() -> str:
    """Load system context from file."""
    try:
        with open("context.txt", "r") as f:
            content = f.read()
            logger.debug(f"Loaded context: {len(content)} chars")
            return content
    except FileNotFoundError:
        logger.warning("context.txt not found")
        return ""
    except IOError as e:
        logger.error(f"Failed to load context: {e}")
        return ""


# -----------------------
# Retrieve Knowledge
# -----------------------
def retrieve_knowledge(query: str) -> str:
    """
    Retrieve relevant knowledge from RAG database.
    
    Args:
        query: Query string
    
    Returns:
        Formatted knowledge string
    """
    if db is None:
        return ""
    
    try:
        docs = db.similarity_search_with_score(query, k=3)
        
        if not docs:
            logger.debug(f"No similar documents found for: {query}")
            return ""
        
        ranked = []
        
        for doc, score in docs:
            content = doc.page_content
            boost = 0
            
            # Boost relevant content
            if "payload" in content.lower():
                boost += 0.15
            if "cve-" in content.lower():
                boost += 0.15
            if "enumeration" in content.lower():
                boost += 0.10
            
            ranked.append((content, score - boost))
        
        ranked.sort(key=lambda x: x[1])
        
        result = "\n\n".join([x[0] for x in ranked[:3]])
        logger.debug(f"Retrieved {len(ranked)} documents")
        return result
    
    except Exception as e:
        logger.error(f"Knowledge retrieval failed: {e}")
        return ""


# -----------------------
# Tactical Memory
# -----------------------
def format_tactical_memory() -> str:
    """Format tactical memory for prompt."""
    if not tactical_memory:
        return ""
    
    out = []
    
    for item in tactical_memory:
        try:
            out.append(
                f"""
Target: {item.get("target", "N/A")}
Service: {item.get("service", "N/A")}
Payload: {item.get("payload", "N/A")[:100]}
Result: {item.get("result", "N/A")}
"""
            )
        except (KeyError, TypeError) as e:
            logger.debug(f"Error formatting tactical memory: {e}")
            continue
    
    return "\n".join(out)


# -----------------------
# Persistent Memory
# -----------------------
def load_memory() -> None:
    """Load memory from JSON file."""
    global memory
    
    if os.path.exists(MEM_FILE):
        try:
            with open(MEM_FILE, "r") as f:
                data = json.load(f)
                memory = deque(data, maxlen=MEMORY_SIZE)
                logger.info(f"Loaded {len(memory)} memory entries")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to load memory: {e}")
        except IOError as e:
            logger.error(f"Failed to read memory file: {e}")


def save_memory() -> None:
    """Save memory to JSON file."""
    try:
        with open(MEM_FILE, "w") as f:
            json.dump(list(memory), f, indent=2)
        logger.debug(f"Saved {len(memory)} memory entries")
    except IOError as e:
        logger.error(f"Failed to save memory: {e}")


# -----------------------
# DB Monitor
# -----------------------
def update_data_check() -> None:
    """Update database statistics file."""
    if db is None:
        return
    
    try:
        count = db._collection.count()
        
        with open(CHECK_FILE, "w") as f:
            f.write(f"Total Intelligence Units: {count}\n")
            f.write(f"Last Update: {time.ctime()}\n")
        
        logger.info(f"Database check: {count} units")
    
    except Exception as e:
        logger.error(f"Database monitoring failed: {e}")


# -----------------------
# Strategic Advice
# -----------------------
def get_strategic_advice(target: str = "target") -> str:
    """
    Get strategic advice based on attack state.
    
    Args:
        target: Target name/IP
    
    Returns:
        Strategic advice string
    """
    state = get_state(target)
    
    if not state:
        return ""
    
    out = ["\n[Strategic Decision Engine]"]
    services = state.get("services", {})
    
    for svc, data in services.items():
        stage = data.get("stage")
        
        if stage == "enumeration":
            out.append(f"- {svc}: enumerate deeper / search exploits")
        elif stage == "initial_access":
            out.append(f"- {svc}: stabilize foothold")
        elif stage == "privilege_escalation":
            out.append(f"- {svc}: check sudo / kernel / SUID")
    
    return "\n".join(out)


# -----------------------
# Prompt Builder
# -----------------------
def build_prompt(
    user_input: str,
    attack_chain: str = ""
) -> str:
    """
    Build the prompt for the LLM.
    
    Args:
        user_input: User query
        attack_chain: Attack chain information
    
    Returns:
        Complete prompt string
    """
    context = load_context()
    rag = retrieve_knowledge(user_input)
    memory_context = "\n".join(memory)
    tactical_context = format_tactical_memory()
    strategy = get_strategic_advice()
    
    prompt = f"""
{context[:600]}

====================
TACTICAL MEMORY
====================

{tactical_context[:1200]}

====================
RELEVANT KNOWLEDGE
====================

{rag[:1800]}

====================
CHAT MEMORY
====================

{memory_context[:1200]}

====================
ATTACK CHAIN
====================

{attack_chain[:1500]}

====================
STRATEGIC REASONING
====================

{strategy[:1200]}

====================
USER
====================

{user_input}

ghost0) """
    
    return prompt


# -----------------------
# Tactical Learning
# -----------------------
def process_response(
    user_input: str,
    response: str
) -> None:
    """
    Process response and extract tactical findings.
    
    Args:
        user_input: User query
        response: LLM response
    """
    findings = response_analyzer(response)
    
    for finding in findings:
        tactical_memory.append({
            "target": "lab",
            "service": "unknown",
            "payload": user_input[:100],
            "result": finding
        })
        logger.debug(f"Tactical finding: {finding}")


# -----------------------
# ASK ENGINE
# -----------------------
def ask(user_input: str) -> None:
    """
    Process user query and generate response.
    
    Args:
        user_input: User input string
    """
    # Web Learning
    if user_input.startswith("learn:"):
        query = user_input.replace("learn:", "").strip()
        
        if not db:
            logger.error("Database not initialized for learning")
            print("[!] Database not ready for learning")
            return
        
        logger.info(f"Starting web learning for: {query}")
        print(f"[*] ghost0 is looking for ingredients to cook: {query}")
        
        try:
            learn_from_web(
                query=query,
                db=db,
                embeddings=embeddings,
                ollama_url=OLLAMA_URL,
                model=OLLAMA_CHAT_MODEL,
                score_fn=score_content,
                dedup_fn=lambda x: semantic_duplicate(db, embeddings, x)
            )
            update_data_check()
        except Exception as e:
            logger.error(f"Web learning failed: {e}")
            print(f"[!] Learning error: {e}")
        
        return
    
    # Attack Chain
    attack_chain = ""
    
    if "/tcp" in user_input or "nmap" in user_input.lower():
        logger.debug("Building attack chain from nmap output")
        attack_chain = build_attack_chain(user_input)
    
    # Build Prompt
    prompt = build_prompt(user_input, attack_chain)
    
    try:
        logger.debug(f"Querying {MODEL} with prompt length: {len(prompt)}")
        
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": True
            },
            stream=True,
            timeout=300
        )
        r.raise_for_status()
        
        print("ghost0) ", end="", flush=True)
        full_response = ""
        
        for line in r.iter_lines():
            if line:
                try:
                    token = json.loads(line.decode()).get("response", "")
                    print(token, end="", flush=True)
                    full_response += token
                
                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to parse response line: {e}")
                    continue
        
        print()
        
        # Save Memory
        memory.append(f"User: {user_input}")
        memory.append(f"ghost0: {full_response[:500]}")
        save_memory()
        
        # Tactical Learning
        process_response(user_input, full_response)
        logger.info("Response processed and stored")
    
    except requests.RequestException as e:
        logger.error(f"LLM request failed: {e}")
        print(f"[ERROR] Connection failed: {e}")
    
    except json.JSONDecodeError as e:
        logger.error(f"Response parsing failed: {e}")
        print(f"[ERROR] Invalid response format: {e}")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"[ERROR] {e}")


# -----------------------
# MAIN
# -----------------------
if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("ghost0 AI Penetration Testing Assistant")
    logger.info("=" * 50)
    
    # Initialize systems
    load_memory()
    
    rag_ready = initialize_rag()
    if not rag_ready:
        logger.warning("RAG system failed to initialize")
        print("[!] Warning: RAG system not available (web learning disabled)")
    
    update_data_check()
    
    print("Welcome, Sir! ghost0 is ready to cook.")
    print("-" * 30)
    
    try:
        while True:
            try:
                cmd = input("0xdaphantom) ")
            except EOFError:
                break
            
            if cmd.lower() in ["exit", "quit", "shutdown", "kill"]:
                break
            
            if cmd.strip():
                ask(cmd)
    
    except KeyboardInterrupt:
        logger.warning("Keyboard interrupt detected")
        print("\n[!] Force shutdown detected.")
    
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
        print(f"\n[!] Fatal error: {e}")
    
    finally:
        logger.info("Shutting down...")
        print("\n[*] Final database audit...")
        update_data_check()
        print("[+] Goodbye, Sir.")
        logger.info("Shutdown complete")


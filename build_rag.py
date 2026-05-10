"""
RAG database builder for ghost0 - ingests writeups and security documents.
"""
import os
import json
from pathlib import Path
from typing import List
from dotenv import load_dotenv

from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

from logger_config import get_logger

load_dotenv()

logger = get_logger(__name__)

WRITEUPS_DIR = "writeups"
RAG_DB_PATH = os.getenv("RAG_DB_PATH", "./rag_db")
EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "mistral")


def load_documents() -> List[str]:
    """
    Load all documents from writeups directory.
    
    Returns:
        List of document contents
    """
    texts = []
    
    if not os.path.exists(WRITEUPS_DIR):
        logger.error(f"Writeups directory not found: {WRITEUPS_DIR}")
        return texts
    
    logger.info(f"Loading documents from {WRITEUPS_DIR}...")
    
    file_count = 0
    error_count = 0
    
    for root, dirs, files in os.walk(WRITEUPS_DIR):
        for file in files:
            path = os.path.join(root, file)
            
            # Skip non-text files
            if file.endswith(('.py', '.pyc', '.log', '.tmp')):
                continue
            
            try:
                with open(path, "r", encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if len(content) > 100:  # Minimum length
                        texts.append(content)
                        file_count += 1
                        logger.debug(f"Loaded: {path}")
            
            except IOError as e:
                error_count += 1
                logger.warning(f"Failed to read {path}: {e}")
                continue
            except Exception as e:
                error_count += 1
                logger.error(f"Unexpected error reading {path}: {e}")
                continue
    
    logger.info(f"Loaded {file_count} documents ({error_count} errors)")
    return texts


def build_database(texts: List[str]) -> None:
    """
    Build and persist the RAG database.
    
    Args:
        texts: List of document texts
    """
    if not texts:
        logger.error("No documents to process")
        return
    
    try:
        logger.info(f"Initializing embeddings with model: {EMBEDDING_MODEL}")
        embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
        
        logger.info(f"Creating Chroma database at {RAG_DB_PATH}")
        db = Chroma.from_texts(
            texts,
            embeddings,
            persist_directory=RAG_DB_PATH
        )
        
        # Verify database
        count = db._collection.count()
        logger.info(f"RAG database successfully built with {count} units")
        
        print(f"[+] RAG database built successfully!")
        print(f"[+] Location: {RAG_DB_PATH}")
        print(f"[+] Units ingested: {count}")
    
    except Exception as e:
        logger.error(f"Database building failed: {e}")
        raise


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("ghost0 RAG Database Builder")
    logger.info("=" * 50)
    
    try:
        documents = load_documents()
        
        if not documents:
            logger.error("No documents loaded, exiting")
            exit(1)
        
        build_database(documents)
        logger.info("Build complete!")
    
    except Exception as e:
        logger.error(f"Build failed: {e}")
        exit(1)


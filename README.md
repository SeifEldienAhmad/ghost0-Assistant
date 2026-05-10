# ghost0 - AI-Powered Penetration Testing Assistant

> An intelligent penetration testing assistant specialized in CTF challenges and bug bounty hunting, powered by local AI models (Ollama) and knowledge management.

## 🎯 Overview

**ghost0** is an advanced penetration testing tool that combines:
- **AI-Powered Analysis** - Uses local Ollama models for intelligent reasoning (with streaming responses for better UX)
- **Knowledge Management** - Vector database (Chroma) for semantic search
- **Attack Chain Building** - Automatic exploitation chain generation from nmap
- **Web Learning** - Continuous knowledge ingestion from security resources
- **Tactical Memory** - Learns from each penetration test session
- **Smart Payloads** - Context-aware payload recommendations

Perfect for:
- CTF competitions
- Bug bounty hunting
- Penetration testing labs
- Security research
- Exploit development

---

## ✨ Features

### 🧠 Intelligent Reasoning
- Local AI models (no cloud dependencies)
- Context-aware attack suggestions
- Strategic decision engine
- Real-time tactical learning

### 📚 Knowledge Management
- Vector database for semantic search (Chroma)
- Automatic payload extraction
- Semantic deduplication
- Content quality scoring
- 15+ security writeups included

### 🛠️ Attack Automation
- NMap integration for service enumeration
- CVE lookup (NVD API)
- Exploit search (searchsploit)
- Smart payload generation
- Attack stage tracking

### 🌐 Web Learning
- DuckDuckGo integration (free, no API keys needed)
- Automatic content ingestion
- Payload extraction
- Knowledge rating system

### 📝 Comprehensive Logging
- Structured logs with timestamps
- File rotation (10MB per file, 5 backups)
- Module-level debugging
- Real-time console output

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Ollama (for local LLM)
- searchsploit (optional, for exploit lookup)
- Linux/macOS (or WSL on Windows)

### Installation

1. **Clone and navigate:**
   ```bash
   cd /path/to/your/ghost0
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment (optional):**
   ```bash
   cp .env.example .env
   nano .env  # Optional: customize Ollama, logging, and database paths
   ```

5. **Start Ollama (in another terminal):**
   ```bash
   ollama serve
   ```

6. **Run ghost0:**
   ```bash
   python3 ghost0.py
   ```

7. **Monitor logs (optional, in another terminal):**
   ```bash
   tail -f logs/ghost0.log
   ```

---

## 📖 Usage

### Interactive Mode
```bash
0xdaphantom) show open ports
0xdaphantom) 22/tcp ssh, 80/tcp http, 443/tcp https
0xdaphantom) what vulnerabilities might these have?
0xdaphantom) exit
```

### Attack Chain Analysis
Paste nmap output directly:
```bash
0xdaphantom) 22/tcp    open  ssh     OpenSSH 7.4
             80/tcp    open  http    Apache httpd 2.4.6
             443/tcp   open  https   Apache httpd 2.4.6
             3306/tcp  open  mysql   MySQL 5.7.28
```

Ghost0 automatically:
- Fetches CVEs for each service
- Searches for known exploits
- Suggests appropriate payloads
- Tracks attack stages

### Web Learning
```bash
0xdaphantom) learn: SQL injection in PHP
[*] ghost0 is researching: SQL injection in PHP
[+] Fetch: https://...
[+] Learned (score: 7.5)
```

### Commands
- `learn: <topic>` - Research and ingest security knowledge
- `exit` / `quit` / `shutdown` - Stop the program
- Any other input - Get tactical advice

---

## 🏗️ Project Structure

```
ghost0/
├── ghost0.py                 # Main application
├── web_learner.py            # Web scraping & knowledge ingestion
├── attack_engine.py          # CVE lookup, exploit search, attack chains
├── knowledge_engine.py       # Payload management, content scoring
├── build_rag.py              # Database builder for RAG
├── logger_config.py          # Centralized logging configuration
│
├── requirements.txt          # Python dependencies (pinned versions)
├── setup.sh                  # Installation script
├── .env              # Configuration template
├── .gitignore                # Protect sensitive files
├── Modelfile                 # Ollama model definition
├── context.txt               # System context for LLM
│
├── rag_db/                   # Vector database (Chroma)
│   └── chroma.sqlite3
│
├── writeups/                 # Security knowledge base
│   ├── *.txt                 # Individual writeups
│   ├── cves/                 # CVE-specific information
│   └── payloads/             # Payload collections
│
├── logs/                     # Application logs
│   └── ghost0.log            # Main log file (auto-rotated)
│
├── memory.json               # Conversation history
├── cve_cache.json            # CVE API cache
└── learn_cache.json          # Web learning cache
```

---

## ⚙️ Configuration

### Environment Variables (.env)

**All Optional (with sensible defaults):**
```bash
# Ollama Configuration
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=qwen2.5:3b
OLLAMA_CHAT_MODEL=qwen2.5:7b
OLLAMA_DEFAULT_MODEL=ghost0

# Logging
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
LOG_FILE=ghost0.log

# Memory
MEMORY_SIZE=10              # Conversation history limit
TACTICAL_MEMORY_SIZE=8      # Tactical findings limit

# Database
RAG_DB_PATH=./rag_db
```

### Ollama Models

Models are automatically pulled during setup:
- `qwen2.5:3b` - Embedding model (fast)
- `qwen2.5:7b` - Chat model (more capable)
- `ghost0` - Custom model (based on qwen2.5)

Manually pull models:
```bash
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b
```

---

## 📊 Architecture

### Module Overview

#### `ghost0.py` - Main Application
- Command-line interface
- Memory management
- Prompt construction
- LLM interaction
- Strategic advice generation

#### `web_learner.py` - Knowledge Acquisition
- DuckDuckGo search integration (free, no API required)
- Web scraping with BeautifulSoup
- Content summarization
- Payload extraction
- Database ingestion with deduplication

#### `attack_engine.py` - Attack Automation
- NMap parsing
- NVD API integration
- Searchsploit integration
- CVE caching
- Attack state tracking
- Response analysis

#### `knowledge_engine.py` - Knowledge Management
- Payload database
- Content scoring
- Semantic deduplication
- Vector similarity calculation
- Payload ranking

#### `build_rag.py` - Database Builder
- Document loading
- Vector database creation
- Chroma persistence
- Progress reporting

#### `logger_config.py` - Logging System
- Structured logging
- File rotation
- Console formatting
- Module-level loggers

---

## 📝 Logging

### Log Locations
```
logs/ghost0.log              # Main log file
```

### Log Format
```
2026-05-09 14:23:45 - attack_engine - ERROR - [attack_engine.py:125] - Failed to fetch CVEs: Connection timeout
```

### Log Levels
```bash
DEBUG   - Detailed diagnostic information
INFO    - General informational messages
WARNING - Warning messages for non-critical issues
ERROR   - Error messages for failures
```

### View Logs
```bash
# Real-time monitoring
tail -f logs/ghost0.log

# Last 50 lines
tail -50 logs/ghost0.log

# Search for errors
grep ERROR logs/ghost0.log

# Full context around error
grep -C 5 "CONNECTION REFUSED" logs/ghost0.log
```

---

## 🔧 Dependencies

All versions are pinned for stability:

```
requests==2.31.0              # HTTP library
beautifulsoup4==4.12.2        # HTML parsing
langchain==0.1.10             # LLM framework
langchain-chroma==0.3.21      # Vector DB integration
langchain-ollama==0.1.1       # Ollama integration
chromadb==0.4.24              # Vector database
ollama==0.1.25                # Local LLM client
numpy==1.24.3                 # Numerical operations
python-dotenv==1.0.0          # Environment configuration
pydantic==2.4.2               # Data validation
```

Update dependencies:
```bash
pip install -r requirements.txt --upgrade
```

---

## 🐛 Troubleshooting

### "Cannot connect to Ollama"
```bash
# Check if Ollama is running
curl -fsSl http://localhost:11434/api/tags

# If not running, start it
ollama serve
```

### "ImportError: No module named..."
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Models not found
```bash
# Manually pull required models
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b
```

### Permission denied errors
```bash
# Ensure Python script is executable
chmod +x ghost0.py

# Or run with python3 explicitly
python3 ghost0.py
```

### Logs not appearing
```bash
# Check logs directory exists
ls -la logs/

# If not, create it
mkdir -p logs

# Verify log file
tail logs/ghost0.log
```

---

## 💾 Data Files

### Memory
```bash
memory.json          # Conversation history (JSON)
```

### Caches
```bash
cve_cache.json       # CVE API responses (24h TTL)
learn_cache.json     # Web learning URLs (cached)
payload_index.json   # Extracted payloads by category
```

### Database
```bash
rag_db/              # Vector database
├── chroma.sqlite3   # Database file
└── <uuid>/          # Embeddings
```

### Statistics
```bash
data_check.txt       # Database statistics (auto-updated)
```

---

## 🛡️ Security Considerations

### Input Validation
- External commands sanitized
- Subprocess inputs validated
- Regex patterns safe from ReDoS

### Error Handling
- Specific exceptions (not bare except)
- Full error context in logs
- No sensitive data in error messages

### Database Security
- Vector DB persisted locally
- No cloud uploads
- SQLite with optional encryption (future)

---

## 📚 Knowledge Base

### Included Writeups (15+)
Located in `writeups/`:
- OWASP Top 10 (A01-A10)
- Common vulnerabilities
- CTF writeups
- Exploitation techniques
- Payload collections

### Building Custom Database
```bash
# Add your writeups to writeups/ directory
mkdir -p writeups/custom
cp my_writeup.txt writeups/custom/

# Rebuild database
python3 build_rag.py

# Check database
tail logs/ghost0.log
```

---

## 🎓 Examples

### Example 1: Basic Usage
```bash
$ python3 ghost0.py
Welcome, Sir! ghost0 is ready to cook.
------------------------------
0xdaphantom) what is SQL injection?
ghost0) SQL injection is a code injection technique...

0xdaphantom) give me a simple payload
ghost0) A simple SQL injection payload: ' OR '1'='1

0xdaphantom) exit
[*] Final database audit...
[+] Goodbye, Sir.
```

### Example 2: Attack Chain
```bash
$ python3 ghost0.py
0xdaphantom) 22/tcp open ssh OpenSSH 7.4
             80/tcp open http Apache 2.4.6
             3306/tcp open mysql MySQL 5.7

ghost0) [Strategic Decision Engine]
- ssh: enumerate deeper / search exploits
- http: enumerate deeper / search exploits
- mysql: enumerate deeper / search exploits

[22/tcp] ssh
 CVEs:
  - CVE-2018-15473 - OpenSSH username...
  - CVE-2020-14145 - OpenSSH information...
 Exploits:
  - OpenSSH 7.4 - Exploit Database
 Suggested Payloads:
  - hydra brute
  - credential reuse
```

### Example 3: Web Learning
```bash
$ python3 ghost0.py
0xdaphantom) learn: PHP Local File Inclusion
[*] ghost0 is researching: PHP Local File Inclusion
[+] Fetch: https://...
[+] Learned (score: 8.2)
[+] Processing: 1 new source ingested
```

---

## 🔄 Workflow

### Typical Pentest Session
1. **Reconnaissance** - Gather initial information
2. **Enumeration** - Use ghost0 for service analysis
3. **Exploitation** - Get payloads and attack suggestions
4. **Post-Exploitation** - Track progress with tactical memory
5. **Learning** - Use `learn:` command for new techniques

### Continuous Improvement
1. Find new exploits/payloads
2. Save to writeups directory
3. Run `python3 build_rag.py`
4. Ghost0 learns from new sources

---

## 👨‍💻 Development

### Code Quality
- ✅ 100% type hints
- ✅ 100% docstrings
- ✅ Comprehensive error handling
- ✅ Full logging coverage
- ✅ Semantic code organization

### Running Tests
```bash
# Syntax check
python3 -m py_compile *.py

# Import validation
python3 -c "import ghost0"

# Type checking (if mypy installed)
mypy ghost0.py
```

### Adding Features
1. Create new module in project root
2. Add logging: `from logger_config import get_logger`
3. Add type hints to all functions
4. Add docstrings
5. Import in main module
6. Test and verify logging

### File Naming Convention
- `*.py` - Python source files
- `.env*` - Environment configuration
- `logs/` - Application logs
- `writeups/` - Knowledge base

---

## 📄 License & Attribution

**ghost0** - Penetration Testing Assistant  
Created for CTF and security research  
Built with: LangChain, Ollama, Chroma, Python

### Credits
- Ollama - Local LLM inference
- LangChain - LLM framework
- Chroma - Vector database
- NVD - Vulnerability database
- searchsploit - Exploit database

---

## ⚡ Performance Tips

### Faster Startup
```bash
# Start Ollama in background on boot
# or keep it running in a separate terminal
```

### Better Database Performance
```bash
# Rebuild database after large updates
python3 build_rag.py

# Clear old caches if storage is limited
rm cve_cache.json learn_cache.json
```

### Memory Management
```bash
# Adjust limits in .env
MEMORY_SIZE=20              # Keep more history
TACTICAL_MEMORY_SIZE=16     # Keep more findings
```

---

## 🗺️ Roadmap

### Planned Features
- [ ] Web interface
- [ ] Database persistence layer
- [ ] Unit tests & CI/CD
- [ ] Multi-threaded learning
- [ ] Custom model training
- [ ] Exploit automation
- [ ] Team collaboration features
- [ ] Remote API server

### Known Limitations
- Requires local Ollama instance
- Single-user architecture
- No persistent state between sessions (except memory.json)
- Learning requires active internet connection

---

## 🤝 Contributing

To improve ghost0:
1. Add new writeups to `writeups/` directory
2. Extract payloads for categorization
3. Report bugs with log context
4. Suggest new features with use cases

---

## 📞 Support

### Getting Help
1. Check `logs/ghost0.log` for errors
2. Verify `.env` configuration
3. Ensure Ollama is running
4. Check internet connection for web learning

### Debugging
```bash
# Enable debug logging
LOG_LEVEL=DEBUG python3 ghost0.py

# View full logs
cat logs/ghost0.log

# Search for specific errors
grep "ERROR\|CRITICAL" logs/ghost0.log
```

---

## 📋 Checklist

Before first use:
- [ ] Python 3.8+ installed
- [ ] Ollama installed and running
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] `.env` configured with API keys
- [ ] Models pulled (`ollama list`)
- [ ] `python3 ghost0.py` runs successfully

---

## 🎯 Quick Commands Reference

```bash
# Setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env

# Start
ollama serve                    # Terminal 1
python3 ghost0.py              # Terminal 2
tail -f logs/ghost0.log         # Terminal 3

# Manage
python3 build_rag.py            # Rebuild knowledge base
grep ERROR logs/ghost0.log      # Find errors
python3 -m py_compile *.py      # Verify syntax

# Clean
rm -rf venv logs *.json *.log   # Full reset
git clean -fd                   # Remove untracked files
```

---

## 📅 Version Info

**Version:** 1.0  
**Last Updated:** May 9, 2026  
**Python:** 3.8+  
**Platform:** Linux/macOS (WSL on Windows)  
**Status:** Production-Ready ✅

---

**ghost0 - Ready to cook. 🔥**

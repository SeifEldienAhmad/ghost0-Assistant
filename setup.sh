#!/bin/bash

set -e  # Exit on error

echo "[*] Setting up ghost0 environment..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 is required but not installed."
    exit 1
fi

echo "[+] Python version: $(python3 --version)"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[+] Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo "[*] Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo "[!] Ollama is not installed. Installing..."
    curl -fsSL https://ollama.ai/install.sh | sh || {
        echo "[!] Ollama installation failed. Please install manually: https://ollama.ai"
        exit 1
    }
else
    echo "[+] Ollama is installed: $(ollama --version)"
fi

# Check for searchsploit
if ! command -v searchsploit &> /dev/null; then
    echo "[!] searchsploit is not installed. Installing..."
    sudo apt-get update && sudo apt-get install -y exploitdb || {
        echo "[!] searchsploit installation failed. Install manually: apt-get install exploitdb"
    }
else
    echo "[+] searchsploit is available"
fi

# Create .env file from example if it doesn't exist
if [ ! -f ".env" ]; then
    echo "[*] Creating .env file from template..."
    cp .env.example .env
    echo "[+] .env created (all optional - no API keys needed)"
else
    echo "[+] .env file already exists"
fi

# Pull Ollama models
echo "[*] Pulling Ollama models (this may take a while)..."
ollama pull qwen2.5:3b &
EMBEDDING_PID=$!
ollama pull qwen2.5:7b &
CHAT_PID=$!

wait $EMBEDDING_PID $CHAT_PID 2>/dev/null || {
    echo "[!] Some models failed to pull. You can pull them manually later with:"
    echo "    ollama pull qwen2.5:3b"
    echo "    ollama pull qwen2.5:7b"
}

# Create ghost0 custom model
echo "[*] Creating ghost0 custom model..."
ollama create ghost0 -f Modelfile || {
    echo "[!] Failed to create ghost0 model. Try manually:"
    echo "    ollama create ghost0 -f Modelfile"
}

echo ""
echo "[+] ghost0 environment setup complete!"
echo ""
echo "To start:"
echo "  1. Activate venv: source venv/bin/activate"
echo "  2. Start Ollama: ollama serve (in another terminal)"
echo "  3. Run ghost0: python3 ghost0.py"
echo ""
echo "Optional: Edit .env to customize Ollama host, logging, or database paths"


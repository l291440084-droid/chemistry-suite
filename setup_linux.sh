#!/bin/bash
# Chemistry Suite Linux Setup
set -e

cd "$(dirname "$0")"
echo "=== Chemistry Suite Linux Setup ==="
echo ""

echo "[1/3] Creating Python virtual environment..."
python3 -m venv ../chemistry-suite-venv
source ../chemistry-suite-venv/bin/activate

echo "[2/3] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[3/3] Installing Node.js dependencies..."
npm install

echo ""
echo "=== Setup complete! ==="
echo "Run './run.sh' to start the application."

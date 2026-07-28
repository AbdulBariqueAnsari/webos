#!/bin/bash
# Web OS - Start Script
# This script installs dependencies and starts all servers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🌐 Web OS v5.0 Ultimate"
echo "========================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is required. Install it with: apt install python3 python3-pip"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt 2>/dev/null || pip install -r requirements.txt 2>/dev/null || {
    echo "⚠️  Could not install all packages. Attempting to continue..."
}

echo ""
echo "🚀 Starting Web OS servers..."
echo ""

# Start Web OS
python3 main.py

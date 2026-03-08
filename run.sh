#!/bin/bash
# MT5 Gold Trading System - Startup Script for Linux/Mac

echo "============================================================"
echo "  MT5 GOLD TRADING SYSTEM - Multi-Agent Analysis"
echo "============================================================"
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found. Please install Python 3.10+"
    exit 1
fi

# Check if in project directory
if [ ! -f "main.py" ]; then
    echo "ERROR: Please run this script from the project directory"
    exit 1
fi

# Create venv if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt -q

echo
echo "============================================================"
echo "  Running Analysis..."
echo "============================================================"
echo

# Run main analysis
python main.py "$@"

echo
echo "============================================================"

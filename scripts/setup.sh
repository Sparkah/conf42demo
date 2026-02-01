#!/bin/bash
# Setup script for AI Engineering Quality demo

set -e

echo "Setting up AI Engineering Quality demo..."

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Create data directory
mkdir -p data

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env and add your ANTHROPIC_API_KEY"
echo "  2. Activate the environment: source .venv/bin/activate"
echo "  3. Run: aeq demo"

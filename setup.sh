#!/bin/bash
# AI Collaboration Tool Setup Script

echo "=== AI Collaboration Tool Setup ==="
echo ""

# Check Python version
python3 --version || { echo "Python 3 is required"; exit 1; }

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check for API keys
echo ""
echo "=== API Key Configuration ==="
echo ""

if [ -z "$OPENAI_API_KEY" ]; then
    echo "WARNING: OPENAI_API_KEY is not set"
    echo "Set it with: export OPENAI_API_KEY='your-key'"
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "WARNING: ANTHROPIC_API_KEY is not set"
    echo "Set it with: export ANTHROPIC_API_KEY='your-key'"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Usage:"
echo "  source venv/bin/activate"
echo "  python cli.py --help"
echo ""
echo "Quick start:"
echo "  python cli.py develop 'Create a Python function to validate email'"
echo "  python cli.py review -f your_code.py"
echo "  python cli.py plan 'Build a REST API for todo app'"
echo "  python cli.py docs 'API authentication guide'"
echo "  python cli.py interactive"

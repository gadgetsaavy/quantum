#!/bin/bash

# Create a virtual environment (optional)
if [ ! -d "venv" ]; then
    echo "Creating a virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run the arbitrage script
echo "Running the aggregator script..."
python3 aggregator.py
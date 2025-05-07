#!/bin/bash

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt
else
    echo "requirements.txt not found!"
    exit 1
fi

# Create run script only if it doesn't exist
if [ ! -f "run.sh" ]; then
    echo "Creating run script..."
    echo '#!/bin/bash
source .venv/bin/activate
python main.py' > run.sh
    chmod +x run.sh
fi

echo "Installation complete. Run with: ./run.sh"
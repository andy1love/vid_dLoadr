#!/bin/bash
# Double-click to run trigger_download.py

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

# Run the Python script
python3 trigger_download.py

# Keep terminal open so you can see the output
exec $SHELL




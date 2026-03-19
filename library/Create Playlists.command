#!/bin/bash
# Create Playlists - Double-click to run

# Clear screen
clear

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

echo "=========================================="
echo "   Creating Playlists from Batch Folders"
echo "=========================================="
echo ""

# Run the Python script
python3 create_playlist.py

echo ""
echo "=========================================="
echo "   Done! You can close this window."
echo "=========================================="
echo ""
echo "Press any key to close..."
read -n 1


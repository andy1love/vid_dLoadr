#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ ! -f "$SCRIPT_DIR/config.json" ]; then
  echo "WARNING: config.json not found."
  echo "Copy config.json.example to config.json and fill in your values."
  echo ""
fi

echo "Pulling latest from GitHub..."
cd "$SCRIPT_DIR" && git pull origin main

echo ""
echo "Done. Press any key to close."
read -n 1

#!/bin/bash
# Pixel Art Tool Launcher

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment and run the pixel art tool
cd "$SCRIPT_DIR/src/pixel-art-tool"
source "$SCRIPT_DIR/pixel-art-env/bin/activate"
python3 "pixel art.py" "$@"

#!/bin/bash
export PYTHONUTF8=1
export PYTHONUNBUFFERED=1

echo "Starting DreamLayer Brain server..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:7777/
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://localhost:7777/ 2>/dev/null || true
fi

python3 -m dreamlayer.ai_brain.server --token rune-birch

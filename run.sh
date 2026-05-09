#!/bin/bash
# Chemistry Suite Launcher
cd "$(dirname "$0")"
if [ -f "../chemistry-suite-venv/bin/activate" ]; then
    source "../chemistry-suite-venv/bin/activate"
fi
exec python3 main.py

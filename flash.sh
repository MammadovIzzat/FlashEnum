#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

check_tool() {
    if ! command -v "$1" &>/dev/null; then
        echo "[!] '$1' not found in PATH. Install it and add to PATH."
        echo "    See README.md for install instructions."
        MISSING=1
    fi
}

MISSING=0
check_tool dirsearch
check_tool subfinder

if [ "$MISSING" -eq 1 ]; then
    echo ""
    echo "[!] Some tools are missing. FlashEnum will still run but affected modules won't work."
    echo ""
fi

python3 "$SCRIPT_DIR/main.py"

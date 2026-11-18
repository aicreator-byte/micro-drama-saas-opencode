#!/bin/bash
# OpenCode leg — Phase 2 fix (karakter ke-7 ditolak maks-6, LLM gagal 502 Invalid port, settings ai_providers kosong).
# Mirrors opencode/run-phase2.sh (opencode run --auto, kunci Nvidia OpenCode via credential store).
# Token gateway dibaca dari file, bukan ditulis di sini. JANGAN tulis kunci di sini.
cd "$HOME/workspace/micro-drama-saas/opencode" || exit 1
mkdir -p logs
export NVIDIA_API_KEY="$(python3 -c "
import sys
sys.path.insert(0, '/opt/muse/skills/custom-connector-setup/bin')
from dynamic_credentials import dynamic_credential_entry
try:
    print(dynamic_credential_entry('custom.nvidia-opencode')['surrogate'], end='')
except: pass
" 2>/dev/null)"
setsid nohup "$HOME/.local/bin/opencode" run --auto -m nvidia/nvidia/nemotron-3-ultra-550b-a55b "$(cat PHASE2-FIX-PROMPT.md)" > logs/opencode-phase2-fix.log 2>&1 < /dev/null &
echo "phase2-fix: PID $!"

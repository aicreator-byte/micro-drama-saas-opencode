#!/bin/bash
# OpenCode leg — Phase 2 (LLM nyata + OAuth Google nyata + UI modul unik).
# Mirrors audit-3way-opencode/run-chunk.sh (opencode run --auto, kunci Nvidia
# OpenCode via credential store). Builder jalan di background, log ke logs/.
# Dipanggil phase2-watch.sh; JANGAN jalankan builder langsung dari sini tanpa watch.
# OpenCode CLI: ~/.local/bin/opencode (bukan di PATH shell biasa).
# Non-TTY wajib < /dev/null; run otonom wajib --auto.
cd "$HOME/workspace/micro-drama-saas/opencode" || exit 1
mkdir -p logs
echo "phase2: launching"
# Kunci Nvidia OpenCode (custom.nvidia-opencode) — tanpa ini CLI 401 Unauthorized
# (provider opencode.json baca {env:NVIDIA_API_KEY}).
export NVIDIA_API_KEY="$(python3 -c "
import sys
sys.path.insert(0, '/opt/muse/skills/custom-connector-setup/bin')
from dynamic_credentials import dynamic_credential_entry
try:
    print(dynamic_credential_entry('custom.nvidia-opencode')['surrogate'], end='')
except: pass
" 2>/dev/null)"
setsid nohup "$HOME/.local/bin/opencode" run --auto -m nvidia/nvidia/nemotron-3-ultra-550b-a55b "$(cat PHASE2-PROMPT.md)" > logs/opencode-phase2.log 2>&1 < /dev/null &
echo "phase2: PID $!"

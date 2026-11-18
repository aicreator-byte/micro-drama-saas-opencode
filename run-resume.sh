#!/bin/bash
# OpenCode leg — RESUME run (dipakai watchdog saat sesi sebelumnya mati).
# Model diambil dari OPENCODE_MODEL (diatur watchdog sesuai fallback),
# default tetap Nvidia ultra.
cd "$HOME/workspace/micro-drama-saas/opencode" || exit 1
MODEL="${OPENCODE_MODEL:-nvidia/nvidia/nemotron-3-ultra-550b-a55b}"
export NVIDIA_API_KEY=$(python3 -c "
import sys
sys.path.insert(0, '/opt/muse/skills/custom-connector-setup/bin')
from dynamic_credentials import dynamic_credential_entry
try:
    print(dynamic_credential_entry('custom.nvidia')['surrogate'], end='')
except: pass
" 2>/dev/null)
export NINE_ROUTER_API_KEY=$(cat "$HOME/.9router/local-api-key")
export FREELLMAPI_API_KEY=$(grep FREELLMAPI_API_KEY "$HOME/.bashrc" | cut -d= -f2)
PROMPT="$(cat ../RESUME.md; echo; cat ../PROMPT.md)"
"$HOME/.local/bin/opencode" run --auto --model "$MODEL" "$PROMPT" < /dev/null >> logs/opencode-build.log 2>&1
echo "opencode-resume exit: $? model=$MODEL" >> logs/opencode-build.log

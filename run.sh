#!/bin/bash
# OpenCode leg — Micro Drama SaaS independent MVP build.
# Runs OpenCode non-interactively with the challenge prompt, in its own workspace.
cd "$HOME/workspace/micro-drama-saas/opencode" || exit 1
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
"$HOME/.local/bin/opencode" run --auto --model "nvidia/nvidia/nemotron-3-ultra-550b-a55b" "$(cat ../PROMPT.md)" < /dev/null > logs/opencode-build.log 2>&1
echo "opencode exit: $?" >> logs/opencode-build.log

#!/usr/bin/env bash
# Wire the visualizer into ~/.claude/settings.json as the statusline.
# Backs the file up first and leaves every other setting untouched.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS="${HOME}/.claude/settings.json"

python3 - "$REPO_DIR" "$SETTINGS" <<'PY'
import json
import os
import shutil
import sys

repo_dir, settings_path = sys.argv[1], sys.argv[2]

settings = {}
if os.path.exists(settings_path):
    shutil.copyfile(settings_path, settings_path + ".before-thinking-visualizer")
    with open(settings_path) as handle:
        settings = json.load(handle)

existing = settings.get("statusLine")
if existing and "statusline.py" not in json.dumps(existing):
    print("Refusing to overwrite an existing statusLine:")
    print(json.dumps(existing, indent=2))
    sys.exit(1)

updated = dict(settings)
updated["statusLine"] = {
    "type": "command",
    "command": "python3 {}".format(os.path.join(repo_dir, "statusline.py")),
    "padding": 0,
}

with open(settings_path, "w") as handle:
    json.dump(updated, handle, indent=2)

print("Statusline installed. Restart Claude Code, then cycle your thinking level.")
PY

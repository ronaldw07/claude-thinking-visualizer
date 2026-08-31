#!/usr/bin/env python3
"""Claude Code statusline that visualizes the current thinking mode.

Claude Code stores the thinking/effort setting as `effortLevel` in
settings.json and rewrites the file whenever you cycle it. This script is
invoked on every statusline refresh: it compares the level against the one
it saw last time and, when it changed, plays a short power-up overlay
before settling back into a steady power meter.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from powerup import SURGE_FRAMES, render  # noqa: E402

CLAUDE_DIR = os.path.expanduser("~/.claude")
STATE_PATH = os.path.join(CLAUDE_DIR, "thinking-visualizer-state.json")
SETTINGS_FILES = ("settings.local.json", "settings.json")
DEFAULT_LEVEL = "medium"


def read_json(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (IOError, OSError, ValueError):
        return {}


def current_level(project_dir=None):
    """Most specific effortLevel wins: project settings, then user settings."""
    candidates = []
    if project_dir:
        candidates.append(os.path.join(project_dir, ".claude", "settings.local.json"))
        candidates.append(os.path.join(project_dir, ".claude", "settings.json"))
    candidates.extend(os.path.join(CLAUDE_DIR, name) for name in SETTINGS_FILES)

    for path in candidates:
        level = read_json(path).get("effortLevel")
        if level:
            return level
    return os.environ.get("CLAUDE_EFFORT_LEVEL", DEFAULT_LEVEL)


def advance_state(level, saved):
    """Return the new state dict. Pure, so the transition is testable."""
    if saved.get("level") != level:
        return {"level": level, "previous": saved.get("level"), "frame": SURGE_FRAMES}
    return {
        "level": level,
        "previous": saved.get("previous"),
        "frame": max(0, int(saved.get("frame", 0)) - 1),
    }


def write_state(state):
    tmp = "{}.{}.tmp".format(STATE_PATH, os.getpid())
    try:
        with open(tmp, "w") as handle:
            json.dump(state, handle)
        os.replace(tmp, STATE_PATH)
    except (IOError, OSError):
        try:
            os.remove(tmp)
        except OSError:
            pass


def build_context(payload):
    model = (payload.get("model") or {}).get("display_name")
    directory = (payload.get("workspace") or {}).get("current_dir")
    parts = [part for part in (model, os.path.basename(directory or "")) if part]
    return " · ".join(parts)


def main():
    payload = {}
    if not sys.stdin.isatty():
        payload = json.loads(sys.stdin.read() or "{}")

    project_dir = (payload.get("workspace") or {}).get("project_dir")
    level = current_level(project_dir)
    state = advance_state(level, read_json(STATE_PATH))
    write_state(state)

    print(render(level, state.get("previous"), state["frame"], build_context(payload)))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # a broken statusline must never break the CLI
        print("thinking: unavailable ({})".format(error))

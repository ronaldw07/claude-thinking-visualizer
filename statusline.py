#!/usr/bin/env python3
"""Claude Code statusline that visualizes the current thinking mode.

Claude Code passes the live reasoning effort as `effort.level` on stdin and
re-runs this script whenever the session changes. We compare that level
against the one recorded last run and, when it changed, play a short
power-up overlay before settling into a steady power meter.

The animation is driven by wall-clock time rather than an invocation
counter: statusline updates are event-driven and go quiet while the session
is idle, so a counter would freeze mid-charge. Pairing elapsed time with
`refreshInterval` keeps the burst playing either way.
"""

import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from powerup import SURGE_FRAMES, render  # noqa: E402

CLAUDE_DIR = os.path.expanduser("~/.claude")
STATE_PATH = os.path.join(CLAUDE_DIR, "thinking-visualizer-state.json")
SETTINGS_FILES = ("settings.local.json", "settings.json")
DEFAULT_LEVEL = "medium"
SURGE_SECONDS = 4.0


def read_json(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (IOError, OSError, ValueError):
        return {}


def current_level(payload=None, project_dir=None):
    """Live session value if Claude Code sent one, else the settings files."""
    level = ((payload or {}).get("effort") or {}).get("level")
    if level:
        return level

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


def advance_state(level, saved, now):
    """Return the new state dict. Pure, so the transition is testable."""
    if saved.get("level") != level:
        return {"level": level, "previous": saved.get("level"), "changed_at": now}
    return {
        "level": level,
        "previous": saved.get("previous"),
        "changed_at": saved.get("changed_at", 0),
    }


def surge_frame(state, now):
    """Frames remaining in the burst, counted down by elapsed wall time."""
    elapsed = now - float(state.get("changed_at") or 0)
    if elapsed < 0 or elapsed >= SURGE_SECONDS:
        return 0
    remaining = 1.0 - (elapsed / SURGE_SECONDS)
    return max(0, min(SURGE_FRAMES, int(math.ceil(remaining * SURGE_FRAMES))))


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
    if (payload.get("thinking") or {}).get("enabled") is False:
        parts.append("thinking off")
    return " · ".join(parts)


def main():
    payload = {}
    if not sys.stdin.isatty():
        payload = json.loads(sys.stdin.read() or "{}")

    now = time.time()
    project_dir = (payload.get("workspace") or {}).get("project_dir")
    level = current_level(payload, project_dir)
    state = advance_state(level, read_json(STATE_PATH), now)
    write_state(state)

    frame = surge_frame(state, now)
    print(render(level, state.get("previous"), frame, build_context(payload)))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # a broken statusline must never break the CLI
        print("thinking: unavailable ({})".format(error))

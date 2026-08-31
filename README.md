# Claude Code Thinking Mode Visualizer

Turns Claude Code's thinking/effort setting into a power meter in the statusline.
Cycle the level and the bar charges up with a short power-up burst, then settles.

```
◑ HIGH [▰▰▰▰▰▰▰▰▰▱▱▱▱▱▱]  Opus 5 · my-repo

✵ ╲  POWER UP  ╲ ✵
[▰▰▰▰▰▰▰▰▰▰▰▰▱▱▱] HIGH ▶ MAX 80%  Opus 5 · my-repo
```

## Tiers

| effortLevel | Label | Meter |
|---|---|---|
| `low` | LOW | 3/15 |
| `medium` | MEDIUM | 6/15 |
| `high` | HIGH | 9/15 |
| `xhigh` | XHIGH | 12/15 |
| `max` | MAX | 15/15 |

Ultracode is `xhigh + workflows` in the picker but reports as `xhigh` on the
statusline, so the statusline cannot tell the two apart. The web slider lists
it as its own top rung above MAX.


## How it works

Claude Code sends the live reasoning effort as `effort.level` on stdin every
time it refreshes the statusline. `statusline.py` compares that against the
level it recorded last run in `~/.claude/thinking-visualizer-state.json`, and
when the two differ it stamps the change time and plays a 4-second charge
animation before settling back to the steady one-line meter.

The charge is driven by wall-clock time rather than an invocation counter,
because statusline updates are event-driven and go quiet while the session is
idle — a counter would freeze mid-animation. The installer also sets
`refreshInterval: 1` so the burst keeps ticking when nothing else is happening.

If `effort.level` is absent (older Claude Code, or a model without the effort
parameter) it falls back to the `effortLevel` setting, project
`.claude/settings.json` first, then the user-level file.

## Driving the real setting from the browser

A `file://` page is sandboxed and cannot write to `~/.claude/settings.json`.
`bridge.py` serves the same page over loopback and exposes two endpoints, so
the slider reads and writes the real `effortLevel`:

```bash
python3 bridge.py     # then open http://127.0.0.1:7373
```

Dragging the slider writes the level; the page also polls every 1.5s, so
running `/effort` inside Claude Code moves the slider to match. Opened as a
plain file, the page ignores all of this and stays a self-contained demo.

The bridge binds to loopback only and rejects anything outside the five known
levels. It backs `settings.json` up once before its first write and preserves
every other key. ULTRACODE is stored as `xhigh`, which is how Claude Code
itself persists it.

Note: a newly started session reads the level from the file. Whether an
already-running session picks up an external file change is unverified — use
`/effort` in that session if it does not follow.

## Terminal support

Built for the Claude Code terminal TUI. It uses 256-color ANSI escapes and
two-line output, both of which need a terminal that supports them. It has not
been verified against the VS Code / JetBrains extension UIs.

## Install

```bash
./install.sh          # patches ~/.claude/settings.json, backs up the original
```

Restart Claude Code afterwards. To uninstall, delete the `statusLine` key or
restore `~/.claude/settings.json.before-thinking-visualizer`.

## Preview without installing

```bash
python3 demo.py       # animates every tier up and back down in the terminal
open web/index.html   # interactive version with a draggable slider
```

`web/index.html` is a standalone page — no build step, no dependencies. Drag the
slider or use the arrow keys to move between tiers and watch the meter charge.
Useful for showing the thing on a screen without installing anything.

## Tests

```bash
python3 -m pytest tests -q
```

Requires Python 3.6+ and a 256-color terminal. No dependencies beyond `pytest`
for the test suite.

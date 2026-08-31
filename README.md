# Claude Code Thinking Mode Visualizer

Turns Claude Code's thinking/effort setting into a power meter in the statusline.
Cycle the level and the bar charges up with a short power-up burst, then settles.

```
◑ SURGE [▰▰▰▰▰▰▰▰▰▱▱▱▱▱▱]  Opus 5 · my-repo

✵ ╲  POWER UP  ╲ ✵
[▰▰▰▰▰▰▰▰▰▰▰▰▱▱▱] SURGE ▶ OVERDRIVE 80%  Opus 5 · my-repo
```

## Tiers

| effortLevel | Name | Meter |
|---|---|---|
| `low` | SPARK | 3/15 |
| `medium` | FOCUS | 6/15 |
| `high` | SURGE | 9/15 |
| `xhigh` | BLAZE | 12/15 |
| `max` | OVERDRIVE | 15/15 |

## How it works

Claude Code persists the thinking level as `effortLevel` in `settings.json` and
rewrites the file whenever you change it. The statusline command runs on every
refresh, so `statusline.py` reads that value, compares it against the level it
recorded last time in `~/.claude/thinking-visualizer-state.json`, and starts a
14-frame charge animation whenever the two differ. Once the frames run out it
falls back to the steady one-line meter.

Project-level `.claude/settings.json` wins over the user-level file, matching
how Claude Code resolves settings.

## Install

```bash
./install.sh          # patches ~/.claude/settings.json, backs up the original
```

Restart Claude Code afterwards. To uninstall, delete the `statusLine` key or
restore `~/.claude/settings.json.before-thinking-visualizer`.

## Preview without installing

```bash
python3 demo.py       # animates every tier up and back down
```

## Tests

```bash
python3 -m pytest tests -q
```

Requires Python 3.6+ and a 256-color terminal. No dependencies beyond `pytest`
for the test suite.

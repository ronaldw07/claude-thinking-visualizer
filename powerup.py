"""Pure rendering logic for the thinking-mode power meter.

No I/O here on purpose: every function takes state in and returns new
values out, so the whole visual can be unit tested and previewed offline.
"""

SEGMENTS_PER_TIER = 3
SURGE_FRAMES = 14
BAR_FILLED = "▰"
BAR_EMPTY = "▱"

# tier order matters: index == power level
TIERS = (
    {"key": "low", "name": "LOW", "icon": "○", "color": 45},
    {"key": "medium", "name": "MEDIUM", "icon": "◔", "color": 48},
    {"key": "high", "name": "HIGH", "icon": "◑", "color": 226},
    {"key": "xhigh", "name": "ULTRACODE", "icon": "◕", "color": 208},
    {"key": "max", "name": "MAX", "icon": "●", "color": 197},
)

TOTAL_SEGMENTS = len(TIERS) * SEGMENTS_PER_TIER

SPINNER = ("╱", "│", "╲", "─")
SPARKS = ("✧", "✦", "✵", "✹")


def tier_index(effort_level):
    """Index of an effort level, or None when the value is unrecognized."""
    for index, tier in enumerate(TIERS):
        if tier["key"] == effort_level:
            return index
    return None


def tier_for(effort_level):
    index = tier_index(effort_level)
    return TIERS[index] if index is not None else None


def color(text, code, bold=False):
    prefix = "\033[1m" if bold else ""
    return "{}\033[38;5;{}m{}\033[0m".format(prefix, code, text)


def dim(text):
    return "\033[2m{}\033[0m".format(text)


def bar(filled_segments, code, total=TOTAL_SEGMENTS):
    """A meter with `filled_segments` lit in `code` and the rest dimmed."""
    filled = max(0, min(total, filled_segments))
    lit = color(BAR_FILLED * filled, code, bold=True)
    unlit = dim(BAR_EMPTY * (total - filled))
    return "[{}{}]".format(lit, unlit)


def segments_for_tier(index):
    return (index + 1) * SEGMENTS_PER_TIER


def surge_fill(from_index, to_index, frame):
    """Segment count part-way through the charge animation.

    Sweeps from the old tier's fill to the new one over SURGE_FRAMES,
    so a level change reads as the bar physically charging or draining.
    """
    start = segments_for_tier(from_index) if from_index is not None else 0
    end = segments_for_tier(to_index)
    elapsed = SURGE_FRAMES - max(0, min(SURGE_FRAMES, frame))
    progress = elapsed / float(SURGE_FRAMES) if SURGE_FRAMES else 1.0
    return int(round(start + (end - start) * progress))


def render_idle(index, context=""):
    tier = TIERS[index]
    meter = bar(segments_for_tier(index), tier["color"])
    label = color(tier["name"], tier["color"], bold=True)
    line = "{} {} {}".format(color(tier["icon"], tier["color"]), label, meter)
    return line + (dim("  " + context) if context else "")


def render_surge(from_index, to_index, frame, context=""):
    """Two-line power-up (or power-down) overlay shown just after a change."""
    tier = TIERS[to_index]
    is_up = from_index is None or to_index > from_index
    fill = surge_fill(from_index, to_index, frame)
    pulse = frame % 2 == 0
    accent = tier["color"] if pulse else 231

    spark = SPARKS[frame % len(SPARKS)]
    spin = SPINNER[frame % len(SPINNER)]
    headline = "POWER UP" if is_up else "POWER DOWN"
    arrow = "▶" if is_up else "◀"

    from_name = TIERS[from_index]["name"] if from_index is not None else "—"
    transition = "{} {} {}".format(from_name, arrow, tier["name"])

    top = "{0} {1}  {2}  {1} {0}".format(
        color(spark, accent, bold=True),
        color(spin, accent),
        color(headline, accent, bold=True),
    )
    percent = int(round(100.0 * fill / TOTAL_SEGMENTS))
    bottom = "{} {} {}%".format(
        bar(fill, tier["color"]),
        color(transition, tier["color"], bold=True),
        percent,
    )
    if context:
        bottom += dim("  " + context)
    return top + "\n" + bottom


def render(effort_level, previous_level, frame, context=""):
    """Full statusline output for the given level and surge frame."""
    index = tier_index(effort_level)
    if index is None:
        return dim("thinking: {}".format(effort_level or "unknown"))
    if frame > 0:
        return render_surge(tier_index(previous_level), index, frame, context)
    return render_idle(index, context)

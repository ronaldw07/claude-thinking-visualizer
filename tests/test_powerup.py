import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import powerup  # noqa: E402
import statusline  # noqa: E402

ANSI = re.compile(r"\033\[[0-9;]*m")


def plain(text):
    return ANSI.sub("", text)


def test_tier_index_matches_declared_order():
    assert powerup.tier_index("low") == 0
    assert powerup.tier_index("max") == len(powerup.TIERS) - 1


def test_tier_index_returns_none_for_unknown_level():
    assert powerup.tier_index("turbo") is None


def test_bar_lights_requested_segments_and_dims_the_rest():
    rendered = plain(powerup.bar(4, 45))
    assert rendered == "[" + powerup.BAR_FILLED * 4 + powerup.BAR_EMPTY * 11 + "]"


def test_bar_clamps_out_of_range_values():
    assert plain(powerup.bar(-5, 45)).count(powerup.BAR_FILLED) == 0
    assert plain(powerup.bar(999, 45)).count(powerup.BAR_EMPTY) == 0


def test_idle_line_shows_tier_name_and_full_tier_meter():
    rendered = plain(powerup.render_idle(powerup.tier_index("high")))
    assert "SURGE" in rendered
    assert rendered.count(powerup.BAR_FILLED) == 9


def test_surge_fill_sweeps_from_old_tier_to_new_tier():
    low, high = powerup.tier_index("low"), powerup.tier_index("high")
    # Arrange: first frame of the animation, then the final frame.
    start = powerup.surge_fill(low, high, powerup.SURGE_FRAMES)
    end = powerup.surge_fill(low, high, 1)
    assert start == powerup.segments_for_tier(low)
    assert start < end <= powerup.segments_for_tier(high)


def test_surge_fill_drains_when_level_drops():
    high, low = powerup.tier_index("high"), powerup.tier_index("low")
    assert powerup.surge_fill(high, low, 1) < powerup.segments_for_tier(high)


def test_surge_overlay_announces_direction():
    up = plain(powerup.render_surge(powerup.tier_index("low"), powerup.tier_index("max"), 3))
    down = plain(powerup.render_surge(powerup.tier_index("max"), powerup.tier_index("low"), 3))
    assert "POWER UP" in up and "SPARK ▶ MAX" not in up
    assert "POWER DOWN" in down


def test_surge_overlay_is_two_lines():
    rendered = powerup.render_surge(0, 4, 5, "ctx")
    assert len(rendered.split("\n")) == 2


def test_render_falls_back_for_unknown_level():
    assert "turbo" in plain(powerup.render("turbo", None, 0))


def test_render_uses_idle_line_once_the_surge_expires():
    rendered = plain(powerup.render("medium", "low", 0, "Opus 5"))
    assert "FOCUS" in rendered and "POWER UP" not in rendered
    assert "Opus 5" in rendered


def test_advance_state_starts_a_surge_when_the_level_changes():
    state = statusline.advance_state("max", {"level": "high", "frame": 0})
    assert state == {"level": "max", "previous": "high", "frame": powerup.SURGE_FRAMES}


def test_advance_state_counts_down_while_the_level_holds():
    state = statusline.advance_state("max", {"level": "max", "previous": "high", "frame": 5})
    assert state["frame"] == 4
    assert state["previous"] == "high"


def test_advance_state_never_goes_negative():
    state = statusline.advance_state("max", {"level": "max", "frame": 0})
    assert state["frame"] == 0


def test_current_level_prefers_project_settings(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    (project / ".claude").mkdir(parents=True)
    (project / ".claude" / "settings.json").write_text('{"effortLevel": "low"}')
    monkeypatch.setattr(statusline, "CLAUDE_DIR", str(tmp_path / "home"))
    assert statusline.current_level(str(project)) == "low"


def test_current_level_falls_back_to_default(tmp_path, monkeypatch):
    monkeypatch.setattr(statusline, "CLAUDE_DIR", str(tmp_path / "missing"))
    monkeypatch.delenv("CLAUDE_EFFORT_LEVEL", raising=False)
    assert statusline.current_level(None) == statusline.DEFAULT_LEVEL


def test_read_json_survives_malformed_files(tmp_path):
    broken = tmp_path / "settings.json"
    broken.write_text("{not json")
    assert statusline.read_json(str(broken)) == {}


def test_build_context_joins_model_and_directory():
    payload = {"model": {"display_name": "Opus 5"}, "workspace": {"current_dir": "/a/b/repo"}}
    assert statusline.build_context(payload) == "Opus 5 · repo"


def test_build_context_handles_empty_payload():
    assert statusline.build_context({}) == ""


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))

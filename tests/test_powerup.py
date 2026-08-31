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
    assert "HIGH" in rendered
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
    assert "POWER UP" in up and "LOW ▶ MAX" in up
    assert "POWER DOWN" in down


def test_surge_overlay_is_two_lines():
    rendered = powerup.render_surge(0, 4, 5, "ctx")
    assert len(rendered.split("\n")) == 2


def test_render_falls_back_for_unknown_level():
    assert "turbo" in plain(powerup.render("turbo", None, 0))


def test_render_uses_idle_line_once_the_surge_expires():
    rendered = plain(powerup.render("medium", "low", 0, "Opus 5"))
    assert "MEDIUM" in rendered and "POWER UP" not in rendered
    assert "Opus 5" in rendered


def test_advance_state_stamps_the_change_time_when_the_level_changes():
    state = statusline.advance_state("max", {"level": "high", "changed_at": 100.0}, 500.0)
    assert state == {"level": "max", "previous": "high", "changed_at": 500.0}


def test_advance_state_keeps_the_original_stamp_while_the_level_holds():
    saved = {"level": "max", "previous": "high", "changed_at": 500.0}
    state = statusline.advance_state("max", saved, 503.0)
    assert state["changed_at"] == 500.0
    assert state["previous"] == "high"


def test_surge_frame_counts_down_with_elapsed_time():
    state = {"changed_at": 1000.0}
    # Arrange: sample the burst at its start, midpoint, and expiry.
    at_start = statusline.surge_frame(state, 1000.0)
    at_middle = statusline.surge_frame(state, 1000.0 + statusline.SURGE_SECONDS / 2)
    at_end = statusline.surge_frame(state, 1000.0 + statusline.SURGE_SECONDS)
    assert at_start == powerup.SURGE_FRAMES
    assert 0 < at_middle < at_start
    assert at_end == 0


def test_surge_frame_is_idle_long_after_the_change():
    assert statusline.surge_frame({"changed_at": 1000.0}, 9999.0) == 0


def test_surge_frame_handles_a_missing_or_future_stamp():
    assert statusline.surge_frame({}, 1000.0) == 0
    assert statusline.surge_frame({"changed_at": 2000.0}, 1000.0) == 0


def test_current_level_prefers_the_live_session_value(tmp_path, monkeypatch):
    monkeypatch.setattr(statusline, "CLAUDE_DIR", str(tmp_path))
    (tmp_path / "settings.json").write_text('{"effortLevel": "low"}')
    payload = {"effort": {"level": "max"}}
    assert statusline.current_level(payload, None) == "max"


def test_current_level_prefers_project_settings(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    (project / ".claude").mkdir(parents=True)
    (project / ".claude" / "settings.json").write_text('{"effortLevel": "low"}')
    monkeypatch.setattr(statusline, "CLAUDE_DIR", str(tmp_path / "home"))
    assert statusline.current_level({}, str(project)) == "low"


def test_current_level_falls_back_to_default(tmp_path, monkeypatch):
    monkeypatch.setattr(statusline, "CLAUDE_DIR", str(tmp_path / "missing"))
    monkeypatch.delenv("CLAUDE_EFFORT_LEVEL", raising=False)
    assert statusline.current_level({}, None) == statusline.DEFAULT_LEVEL


def test_build_context_notes_when_thinking_is_disabled():
    payload = {"model": {"display_name": "Opus 5"}, "thinking": {"enabled": False}}
    assert "thinking off" in statusline.build_context(payload)


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

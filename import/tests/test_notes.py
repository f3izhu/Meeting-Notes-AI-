"""Tests for meeting notes extraction and HTML export."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from meeting_notes_ai.notes import (
    extract_key_points,
    extract_action_items,
    extract_decisions,
    extract_structured_action_items,
    fallback_summary,
    export_html,
    split_sentences,
    top_keywords,
)


SAMPLE_TRANSCRIPT = (
    "Welcome everyone. This is the weekly product sync. "
    "We reviewed current sprint progress and confirmed backend tasks are on track. "
    "Decision: keep the launch date for May 22. "
    "Aisha will finalize the release notes by Friday. "
    "Owner: Daniel follow up with QA tomorrow about regression coverage. "
    "We agreed to defer advanced analytics to the next sprint. "
    "Action item: Priya should share the customer feedback summary by Monday. "
    "Next step is to prepare the go-live checklist and run a dry run."
)


def test_split_sentences_basic():
    sentences = split_sentences("Hello world. This is a test sentence. And another one here!")
    assert len(sentences) == 3


def test_split_sentences_filters_short():
    sentences = split_sentences("Ok. Fine. This is a properly long sentence that matters.")
    assert len(sentences) == 1  # only the long one passes the length check


def test_top_keywords_returns_list():
    keywords = top_keywords(SAMPLE_TRANSCRIPT, k=5)
    assert isinstance(keywords, list)
    assert len(keywords) <= 5
    assert all(isinstance(k, str) for k in keywords)


def test_extract_key_points():
    points = extract_key_points(SAMPLE_TRANSCRIPT)
    assert isinstance(points, list)
    assert len(points) > 0
    assert len(points) <= 6


def test_extract_key_points_empty():
    assert extract_key_points("") == []
    assert extract_key_points("too short") == []


def test_extract_action_items():
    items = extract_action_items(SAMPLE_TRANSCRIPT)
    assert isinstance(items, list)
    assert len(items) > 0
    # Should find action-related sentences
    any_action = any("will" in item.lower() or "should" in item.lower() or "follow up" in item.lower() for item in items)
    assert any_action


def test_extract_action_items_empty():
    assert extract_action_items("") == []


def test_extract_decisions():
    decisions = extract_decisions(SAMPLE_TRANSCRIPT)
    assert isinstance(decisions, list)
    # Should find "agreed" and potentially "Decision"
    any_decision = any("agreed" in d.lower() or "decision" in d.lower() for d in decisions)
    assert any_decision


def test_extract_decisions_empty():
    assert extract_decisions("") == []


def test_extract_structured_action_items():
    items = extract_structured_action_items(SAMPLE_TRANSCRIPT)
    assert isinstance(items, list)
    assert len(items) > 0
    for item in items:
        assert "task" in item
        assert "source_text" in item
        # owner and due may be None


def test_extract_structured_owner():
    text = "Aisha will finalize the release notes by Friday. Daniel should update the docs by tomorrow."
    items = extract_structured_action_items(text)
    owners = [item.get("owner") for item in items if item.get("owner")]
    assert any("Aisha" in o for o in owners) or any("Daniel" in o for o in owners)


def test_extract_structured_due():
    text = "Action item: Priya should share the customer feedback summary by Monday."
    items = extract_structured_action_items(text)
    dues = [item.get("due") for item in items if item.get("due")]
    assert len(dues) > 0
    assert any("Monday" in d for d in dues)


def test_extract_structured_empty():
    assert extract_structured_action_items("") == []


def test_fallback_summary():
    summary = fallback_summary(SAMPLE_TRANSCRIPT)
    assert isinstance(summary, dict)
    assert "meeting_summary" in summary
    assert isinstance(summary["key_points"], list)
    assert isinstance(summary["action_items"], list)
    assert isinstance(summary["decisions"], list)
    assert isinstance(summary["structured_action_items"], list)
    assert summary["meeting_summary"]  # not empty


def test_fallback_summary_empty():
    summary = fallback_summary("")
    assert "meeting_summary" in summary
    assert isinstance(summary["key_points"], list)


def test_export_html_produces_valid_html():
    html = export_html(
        meeting_title="Test Meeting",
        meeting_date="2026-05-30T10:00:00",
        duration="00:30:00",
        segments_captured=10,
        avg_latency=0.5,
        summary={
            "meeting_summary": "A test meeting summary.",
            "key_points": ["Point one", "Point two"],
            "decisions": ["We decided to test"],
            "action_items": ["Follow up with QA"],
            "structured_action_items": [
                {"task": "Write tests", "owner": "Dev", "due": "tomorrow"}
            ],
        },
        transcript_lines=["[00:00:01] Hello", "[00:00:05] World"],
    )
    assert "<!DOCTYPE html>" in html
    assert "Test Meeting" in html
    assert "Point one" in html
    assert "We decided to test" in html
    assert "Follow up with QA" in html
    assert "Write tests" in html
    assert "Hello" in html


def test_export_html_escapes_special_chars():
    html = export_html(
        meeting_title="<script>alert('xss')</script>",
        meeting_date="2026-05-30",
        duration="00:01:00",
        segments_captured=1,
        avg_latency=0.1,
        summary={"meeting_summary": "Safe & sound <ok>", "key_points": [], "decisions": [], "action_items": [], "structured_action_items": []},
        transcript_lines=["<script>bad</script>"],
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "Safe &amp; sound" in html


def test_export_html_empty_data():
    html = export_html(
        meeting_title="",
        meeting_date="",
        duration="00:00:00",
        segments_captured=0,
        avg_latency=0.0,
        summary={"meeting_summary": "", "key_points": [], "decisions": [], "action_items": [], "structured_action_items": []},
        transcript_lines=[],
    )
    assert "<!DOCTYPE html>" in html
    assert "None recorded" in html

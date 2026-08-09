"""Report filename resolution: am/pm slots plus the legacy un-suffixed name.

`save()` writes `trend_report_<date>_<slot>.json`, but `load_report()` used to look
only for `trend_report_<date>.json` — so every report newer than 2026-05-10 was
unreachable from the dashboard. These tests pin both halves of that contract.
"""

import json
from datetime import datetime

import pytest

from agent import report_generator


def write_report(reports_dir, filename, **extra):
    """Drop a minimal but realistic report JSON into reports_dir."""
    data = {"report_date": filename.split("_")[2].removesuffix(".json"),
            "executive_summary": "summary", "top_trends": [{"title": "t"}], **extra}
    (reports_dir / filename).write_text(json.dumps(data), encoding="utf-8")
    return data


def write_html(reports_dir, filename, summary="rendered summary", trend_count=6):
    """Drop a rendered report page, matching the markers report.html emits."""
    (reports_dir / filename).write_text(
        "<html><body>"
        f'<p class="hero-text">{summary}</p>'
        f'<span class="count-badge">{trend_count}</span>'
        "</body></html>",
        encoding="utf-8",
    )


@pytest.fixture
def reports_dir(tmp_path):
    d = tmp_path / "reports"
    d.mkdir()
    return d


# --- load_report: slot resolution ------------------------------------------------

def test_loads_each_slot_explicitly(reports_dir):
    write_report(reports_dir, "trend_report_2026-08-09_am.json", marker="am")
    write_report(reports_dir, "trend_report_2026-08-09_pm.json", marker="pm")

    am = report_generator.load_report("2026-08-09", str(reports_dir), slot="am")
    pm = report_generator.load_report("2026-08-09", str(reports_dir), slot="pm")

    assert am["marker"] == "am"
    assert pm["marker"] == "pm"


def test_without_slot_prefers_pm(reports_dir):
    write_report(reports_dir, "trend_report_2026-08-09_am.json", marker="am")
    write_report(reports_dir, "trend_report_2026-08-09_pm.json", marker="pm")

    report = report_generator.load_report("2026-08-09", str(reports_dir))

    assert report["marker"] == "pm"


def test_without_slot_falls_back_to_am_when_pm_missing(reports_dir):
    write_report(reports_dir, "trend_report_2026-08-09_am.json", marker="am")

    report = report_generator.load_report("2026-08-09", str(reports_dir))

    assert report["marker"] == "am"


def test_loads_legacy_unsuffixed_filename(reports_dir):
    """Reports from 2026-05-10 and earlier predate twice-daily runs."""
    write_report(reports_dir, "trend_report_2026-05-10.json", marker="legacy")

    report = report_generator.load_report("2026-05-10", str(reports_dir))

    assert report["marker"] == "legacy"


def test_slotted_report_wins_over_legacy_same_day(reports_dir):
    """2026-05-10 really does have both an un-suffixed and a _pm file on disk."""
    write_report(reports_dir, "trend_report_2026-05-10.json", marker="legacy")
    write_report(reports_dir, "trend_report_2026-05-10_pm.json", marker="pm")

    report = report_generator.load_report("2026-05-10", str(reports_dir))

    assert report["marker"] == "pm"


# --- load_report: misses and bad input --------------------------------------------

def test_missing_date_returns_none(reports_dir):
    assert report_generator.load_report("2026-01-01", str(reports_dir)) is None


def test_explicit_slot_is_not_backfilled_from_the_other_half(reports_dir):
    write_report(reports_dir, "trend_report_2026-08-09_pm.json", marker="pm")

    assert report_generator.load_report("2026-08-09", str(reports_dir), slot="am") is None


def test_explicit_slot_does_not_fall_back_to_legacy(reports_dir):
    write_report(reports_dir, "trend_report_2026-05-10.json", marker="legacy")

    assert report_generator.load_report("2026-05-10", str(reports_dir), slot="pm") is None


@pytest.mark.parametrize("slot", ["", "AM", "evening", "../../etc/passwd"])
def test_invalid_slot_returns_none(reports_dir, slot):
    write_report(reports_dir, "trend_report_2026-08-09_pm.json", marker="pm")

    assert report_generator.load_report("2026-08-09", str(reports_dir), slot=slot) is None


@pytest.mark.parametrize("date_str", ["", "2026-8-9", "not-a-date", "../secret", "2026-08-*"])
def test_malformed_date_returns_none(reports_dir, date_str):
    """A bad date must not escape reports_dir or leak through the glob."""
    write_report(reports_dir, "trend_report_2026-08-09_pm.json", marker="pm")

    assert report_generator.load_report(date_str, str(reports_dir)) is None


def test_missing_reports_dir_returns_none(tmp_path):
    assert report_generator.load_report("2026-08-09", str(tmp_path / "nope")) is None


# --- list_reports -----------------------------------------------------------------

def test_list_reports_exposes_slot_newest_first(reports_dir):
    write_report(reports_dir, "trend_report_2026-05-10.json")
    write_report(reports_dir, "trend_report_2026-08-09_am.json")
    write_report(reports_dir, "trend_report_2026-08-09_pm.json")

    listed = report_generator.list_reports(str(reports_dir))

    assert [(r["date"], r["slot"]) for r in listed] == [
        ("2026-08-09", "pm"),
        ("2026-08-09", "am"),
        ("2026-05-10", ""),
    ]


def test_list_reports_does_not_duplicate_a_day_with_both_formats(reports_dir):
    write_report(reports_dir, "trend_report_2026-08-09_pm.json")
    write_html(reports_dir, "trend_report_2026-08-09_pm.html")

    listed = report_generator.list_reports(str(reports_dir))

    assert len(listed) == 1
    assert listed[0]["has_json"] is True


def test_listed_reports_are_all_loadable(reports_dir):
    """Every index entry must resolve — that link is what was 404ing."""
    write_report(reports_dir, "trend_report_2026-05-10.json")
    write_report(reports_dir, "trend_report_2026-08-09_am.json")
    write_report(reports_dir, "trend_report_2026-08-09_pm.json")

    for entry in report_generator.list_reports(str(reports_dir)):
        loaded = report_generator.load_report(
            entry["date"], str(reports_dir), slot=entry["slot"] or None
        )
        assert loaded is not None, entry["filename"]


def test_list_reports_skips_corrupt_json(reports_dir):
    write_report(reports_dir, "trend_report_2026-08-09_pm.json")
    (reports_dir / "trend_report_2026-08-08_pm.json").write_text("{not json", encoding="utf-8")

    assert [r["filename"] for r in report_generator.list_reports(str(reports_dir))] == [
        "trend_report_2026-08-09_pm.json"
    ]


# --- HTML-only days (the 2026-05-27 to 2026-08-09 archive gap) --------------------

def test_html_only_day_is_listed_with_recovered_metadata(reports_dir):
    write_html(reports_dir, "trend_report_2026-06-15_pm.html", summary="Equestrian day", trend_count=7)

    listed = report_generator.list_reports(str(reports_dir))

    assert len(listed) == 1
    assert listed[0]["date"] == "2026-06-15"
    assert listed[0]["slot"] == "pm"
    assert listed[0]["executive_summary"] == "Equestrian day"
    assert listed[0]["trend_count"] == 7
    assert listed[0]["has_json"] is False


def test_html_metadata_unescapes_and_collapses_whitespace(reports_dir):
    write_html(reports_dir, "trend_report_2026-06-15_pm.html", summary="CoBa&#39;s\n  Daughter  wins")

    listed = report_generator.list_reports(str(reports_dir))

    assert listed[0]["executive_summary"] == "CoBa's Daughter wins"


def test_html_without_expected_markers_degrades_quietly(reports_dir):
    (reports_dir / "trend_report_2026-06-15_pm.html").write_text("<html>rewritten</html>", encoding="utf-8")

    listed = report_generator.list_reports(str(reports_dir))

    assert listed[0]["executive_summary"] == ""
    assert listed[0]["trend_count"] == 0


def test_load_report_html_respects_slot(reports_dir):
    write_html(reports_dir, "trend_report_2026-06-15_am.html", summary="morning")
    write_html(reports_dir, "trend_report_2026-06-15_pm.html", summary="evening")

    assert "evening" in report_generator.load_report_html("2026-06-15", str(reports_dir))
    assert "morning" in report_generator.load_report_html("2026-06-15", str(reports_dir), slot="am")
    assert report_generator.load_report_html("2026-06-15", str(reports_dir), slot="bad") is None
    assert report_generator.load_report_html("nope", str(reports_dir)) is None


def test_html_fallback_never_shadows_real_json(reports_dir):
    """A day with JSON must still load as JSON, not as the rendered page."""
    write_report(reports_dir, "trend_report_2026-08-09_pm.json", marker="json")
    write_html(reports_dir, "trend_report_2026-08-09_pm.html")

    assert report_generator.load_report("2026-08-09", str(reports_dir))["marker"] == "json"


# --- save() round-trip ------------------------------------------------------------

@pytest.mark.parametrize(
    "utc_hour, expected_slot",
    [(2, "am"), (8, "pm")],  # GMT+7: 02:00 UTC -> 09:00 am, 08:00 UTC -> 15:00 pm
)
def test_saved_report_is_loadable_by_date(reports_dir, monkeypatch, utc_hour, expected_slot):
    """The regression guard: whatever save() names a file, load_report() must find it."""

    class FixedDatetime(datetime):
        @classmethod
        def utcnow(cls):
            return cls(2026, 8, 9, utc_hour, 0, 0)

    monkeypatch.setattr(report_generator, "datetime", FixedDatetime)

    report_generator.save(
        {"report_date": "2026-08-09", "executive_summary": "s", "top_trends": []},
        str(reports_dir),
    )

    assert (reports_dir / f"trend_report_2026-08-09_{expected_slot}.json").exists()
    assert report_generator.load_report("2026-08-09", str(reports_dir)) is not None
    assert (
        report_generator.load_report("2026-08-09", str(reports_dir), slot=expected_slot)
        is not None
    )

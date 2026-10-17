import json
from datetime import date

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape

from sections.food import build


def rec(i, rating, d, area="Leigh", kind="Takeaway/sandwich shop"):
    return {"id": i, "name": f"Place {i}", "type": kind, "address": f"{i} High St, {area}", "postcode": "WN7 1AA",
            "area": area, "rating": rating, "date": d, "lat": None, "lng": None,
            "scores": {"hygiene": 0, "structural": 5, "management": 10}}


def test_labels_and_slugs():
    assert build.label("5") == "Very good" and build.label("AwaitingInspection") == "Awaiting inspection"
    assert build.slug("Joe's Café & Bar!") == "joe-s-caf-bar"
    assert build.nice_date("2026-10-03") == "3 October 2026"


def test_recent_only_keeps_rated_and_new():
    records = [rec(1, "5", "2026-10-13"), rec(2, "4", "2026-08-01"), rec(3, "Exempt", "2026-10-13")]
    assert [r["id"] for r in build.recent(records, date(2026, 10, 17))] == [1]


def test_badges_come_from_the_log():
    records = build.prepare([rec(1, "5", "2026-10-13")],
                            [{"id": 1, "date": "2026-10-13", "kind": "up", "old": 3, "new": 5, "seen": "2026-10-14"}])
    assert records[0]["badge"] == {"text": "Up from 3", "tone": "up"}
    assert [p["text"] for p in records[0]["parts"]] == ["Very good", "Good", "Generally satisfactory"]


def test_full_build(tmp_path, monkeypatch):
    data = tmp_path / "food.json"
    data.write_text(json.dumps([rec(1, "5", "2026-10-13"), rec(2, "2", "2026-10-01", area="Atherton"),
                                rec(3, "AwaitingInspection", "")]))
    monkeypatch.setattr(build, "DATA", data)
    monkeypatch.setattr(build, "LOG", tmp_path / "none.json")
    env = Environment(loader=ChoiceLoader([FileSystemLoader("sections/food/templates"),
                                           FileSystemLoader("site/templates")]),
                      autoescape=select_autoescape(["html"]))
    out = tmp_path / "public"
    assert build.build(env, out, today=date(2026, 10, 17)) == 3
    home = (out / "index.html").read_text()
    assert "Place 1" in home and "Open Government Licence" in home
    assert (out / "area" / "atherton.html").exists()
    assert (out / "place" / "1-place-1.html").exists()
    assert len(json.loads((out / "search.json").read_text())) == 3


def test_old_inspections_are_flagged_and_sorted_last():
    today = date(2026, 10, 17)
    assert build.age_note("2026-05-01", today) is None
    assert build.age_note("2025-06-01", today) == "Over a year ago"
    assert build.age_note("2024-03-12", today) == "Over 2 years ago"
    records = build.prepare([rec(1, "5", "2024-03-12"), rec(2, "4", "2026-10-01"), rec(3, "Exempt", "")], [], today)
    assert [r["id"] for r in build.areas(records)[0]["items"]] == [2, 1, 3]

from sections.food import changes


def rec(i, rating, d="2026-09-01"):
    return {"id": i, "rating": rating, "date": d}


def test_diff_finds_each_kind():
    old = [rec(1, "4"), rec(2, "5"), rec(3, "3"), rec(4, "AwaitingInspection"), rec(5, "5")]
    new = [rec(1, "5", "2026-10-13"), rec(2, "3", "2026-10-12"), rec(3, "3", "2026-10-10"),
           rec(4, "4", "2026-10-09"), rec(5, "5"), rec(6, "2", "2026-10-11"), rec(7, "Exempt")]
    kinds = {e["id"]: (e["kind"], e["old"], e["new"]) for e in changes.diff(old, new, "2026-10-14")}
    assert kinds == {
        1: ("up", 4, 5), 2: ("down", 5, 3), 3: ("same", 3, 3),
        4: ("first", None, 4), 6: ("new", None, 2),
    }


def test_log_skips_repeats_and_old_events():
    old_event = {"id": 9, "seen": "2026-01-01", "date": "2025-12-30", "kind": "up", "old": 3, "new": 4}
    e = {"id": 1, "seen": "2026-10-14", "date": "2026-10-13", "kind": "up", "old": 4, "new": 5}
    log = changes.update_log([old_event, e], [dict(e)], "2026-10-14")
    assert log == [e]


def test_main_without_snapshot(tmp_path, capsys):
    changes.main(tmp_path / "missing.json", tmp_path / "also_missing.json", "2026-10-14")
    assert "nothing to compare" in capsys.readouterr().out

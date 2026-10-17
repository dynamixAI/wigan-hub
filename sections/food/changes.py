import json
import sys
from datetime import date, timedelta
from pathlib import Path

LOG = Path("data/food_changes.json")
KEEP_DAYS = 120


def score(rating):
    return int(rating) if str(rating).isdigit() else None


def diff(old, new, today):
    # compares two snapshots of food.json and lists what changed
    before = {r["id"]: r for r in old}
    events = []
    for r in new:
        prev = before.get(r["id"])
        now = score(r["rating"])
        if now is None:
            continue
        base = {"id": r["id"], "seen": today, "new": now, "date": r["date"]}
        if prev is None:
            events.append({**base, "kind": "new", "old": None})
            continue
        was = score(prev["rating"])
        if was is None:
            events.append({**base, "kind": "first", "old": None})
        elif now > was:
            events.append({**base, "kind": "up", "old": was})
        elif now < was:
            events.append({**base, "kind": "down", "old": was})
        elif r["date"] != prev["date"]:
            events.append({**base, "kind": "same", "old": was})
    return events


def update_log(log, events, today):
    cutoff = (date.fromisoformat(today) - timedelta(days=KEEP_DAYS)).isoformat()
    seen = {(e["id"], e["date"]) for e in log}
    fresh = [e for e in events if (e["id"], e["date"]) not in seen]
    return [e for e in log + fresh if e["seen"] >= cutoff]


def load(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else []


def main(prev_path, new_path, today=None):
    today = today or date.today().isoformat()
    old, new = load(prev_path), load(new_path)
    if not old:
        print("No earlier snapshot, nothing to compare yet")
        return
    events = diff(old, new, today)
    log = update_log(load(LOG), events, today)
    LOG.write_text(json.dumps(log, separators=(",", ":")))
    kinds = {k: sum(e["kind"] == k for e in events) for k in ("new", "first", "up", "down", "same")}
    print(f"Changes today: {kinds}. Log holds {len(log)} events.")


if __name__ == "__main__":
    main(*sys.argv[1:3])

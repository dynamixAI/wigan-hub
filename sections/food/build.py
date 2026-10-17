import json
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

DATA = Path("data/food.json")
LOG = Path("data/food_changes.json")
RECENT_DAYS = 14

LABELS = {
    "5": "Very good", "4": "Good", "3": "Generally satisfactory", "2": "Improvement necessary",
    "1": "Major improvement necessary", "0": "Urgent improvement necessary",
    "AwaitingInspection": "Awaiting inspection", "Exempt": "Exempt",
}
SCORE_PARTS = [
    ("hygiene", "Food handling and hygiene", 25),
    ("structural", "Cleanliness and condition of the building", 25),
    ("management", "Management of food safety", 30),
]


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "place"


def label(rating):
    return LABELS.get(rating, rating or "Not rated")


def score_text(value):
    return {0: "Very good", 5: "Good", 10: "Generally satisfactory"}.get(value, "Needs improvement")


def nice_date(iso):
    if not iso:
        return ""
    d = date.fromisoformat(iso)
    return f"{d.day} {d:%B %Y}"


def badge_for(event):
    if not event:
        return None
    if event["kind"] == "up":
        return {"text": f"Up from {event['old']}", "tone": "up"}
    if event["kind"] == "down":
        return {"text": f"Down from {event['old']}", "tone": "down"}
    if event["kind"] in ("new", "first"):
        return {"text": "First rating", "tone": "plain"}
    return {"text": "No change", "tone": "plain"}


def age_note(iso, today):
    if not iso:
        return None
    days = (today - date.fromisoformat(iso)).days
    if days >= 730:
        return f"Over {days // 365} years ago"
    if days >= 365:
        return "Over a year ago"
    return None


def prepare(records, log, today=None):
    today = today or date.today()
    events = {(e["id"], e["date"]): e for e in log}
    for r in records:
        r["age"] = age_note(r["date"], today)
        r["slug"] = f"{r['id']}-{slug(r['name'])}"
        r["area_slug"] = slug(r["area"])
        r["label"] = label(r["rating"])
        r["nice_date"] = nice_date(r["date"])
        r["badge"] = badge_for(events.get((r["id"], r["date"])))
        r["parts"] = [
            {"name": name, "text": score_text(r["scores"][key]),
             "pct": max(8, round(100 * (1 - r["scores"][key] / top)))}
            for key, name, top in SCORE_PARTS if r["scores"].get(key) is not None
        ]
    return records


def recent(records, today, days=RECENT_DAYS, limit=15):
    cutoff = (today - timedelta(days=days)).isoformat()
    rated = [r for r in records if r["date"] >= cutoff and r["rating"].isdigit()]
    return sorted(rated, key=lambda r: (r["date"], r["name"]), reverse=True)[:limit]


def summary(records, today):
    rated = [r for r in records if r["rating"].isdigit()]
    month_ago = (today - timedelta(days=30)).isoformat()
    return {
        "total": len(records),
        "five_pct": round(100 * sum(r["rating"] == "5" for r in rated) / len(rated)) if rated else 0,
        "last_30": sum(r["date"] >= month_ago for r in rated),
        "updated": nice_date(today.isoformat()),
    }


def areas(records):
    groups = defaultdict(list)
    for r in records:
        groups[r["area"]].append(r)
    out = []
    for name, items in groups.items():
        rated = [r for r in items if r["rating"].isdigit()]
        five = round(100 * sum(r["rating"] == "5" for r in rated) / len(rated)) if rated else 0
        out.append({"name": name, "slug": slug(name), "count": len(items), "five_pct": five,
                    "items": sorted(items, key=lambda r: (r["date"] or "0000", r["name"].lower()), reverse=True)})
    # Other goes last, the rest biggest first
    return sorted(out, key=lambda a: (a["name"] == "Other", -a["count"]))


def search_index(records):
    return [[r["name"], r["address"], r["postcode"], r["rating"], r["slug"], r["area"], r["nice_date"], r["age"] or ""]
            for r in records]


def build(env, out, today=None):
    today = today or date.today()
    records = prepare(json.loads(DATA.read_text()), json.loads(LOG.read_text()) if LOG.exists() else [], today)
    area_list = areas(records)
    common = {"summary": summary(records, today), "areas": area_list}

    def write(path, template, root, **ctx):
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(env.get_template(template).render(root=root, **common, **ctx))

    write("index.html", "home.html", "", recent=recent(records, today))
    write("about.html", "about.html", "")
    for a in area_list:
        write(f"area/{a['slug']}.html", "area.html", "../", area=a)
    by_area = {a["name"]: a for a in area_list}
    year_ago = (today - timedelta(days=365)).isoformat()
    for r in records:
        nearby = sorted((n for n in by_area[r["area"]]["items"] if n["id"] != r["id"] and n["type"] == r["type"]
                         and n["rating"].isdigit() and n["date"] >= year_ago),
                        key=lambda n: (-int(n["rating"]), n["name"]))[:5]
        write(f"place/{r['slug']}.html", "place.html", "../", place=r, nearby=nearby)
    (out / "search.json").write_text(json.dumps(search_index(records), separators=(",", ":")))
    return len(records)

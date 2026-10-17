import json
import re
import sys
import time
from pathlib import Path

import requests

API = "https://api.ratings.food.gov.uk"
HEADERS = {"x-api-version": "2", "Accept": "application/json", "Accept-Language": "en-GB"}
AUTHORITY = "Wigan"
OUT = Path("data/food.json")

# town names as they appear in addresses, matched before falling back to the postcode
AREAS = [
    ("Ashton-in-Makerfield", r"ashton[\s-]*in[\s-]*makerfield"),
    ("Platt Bridge", r"platt bridge"),
    ("Appley Bridge", r"appley bridge"),
    ("Leigh", r"\bleigh\b"),
    ("Atherton", r"\batherton\b"),
    ("Tyldesley", r"\btyldesley\b"),
    ("Astley", r"\bastley\b"),
    ("Golborne", r"\bgolborne\b"),
    ("Lowton", r"\blowton\b"),
    ("Hindley", r"\bhindley\b"),
    ("Standish", r"\bstandish\b"),
    ("Orrell", r"\borrell\b"),
    ("Ince", r"\bince\b"),
    ("Abram", r"\babram\b"),
    ("Aspull", r"\baspull\b"),
    ("Shevington", r"\bshevington\b"),
    ("Pemberton", r"\bpemberton\b"),
    ("Wigan", r"\bwigan\b"),
]
DISTRICT_AREAS = {
    "WN7": "Leigh", "M46": "Atherton", "M29": "Tyldesley", "WA3": "Golborne",
    "WN4": "Ashton-in-Makerfield", "WN2": "Hindley", "WN6": "Standish", "WN5": "Orrell",
    "WN1": "Wigan", "WN3": "Wigan",
}


class FetchError(Exception):
    pass


def get(path, params=None, tries=3):
    for attempt in range(tries):
        try:
            r = requests.get(f"{API}{path}", headers=HEADERS, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if attempt == tries - 1:
                raise FetchError(f"{path} failed: {e}") from e
            time.sleep(3 * (attempt + 1))


def authority_id(name=AUTHORITY):
    for a in get("/Authorities/basic")["authorities"]:
        if a["Name"].strip().lower() == name.lower():
            return a["LocalAuthorityId"]
    raise FetchError(f"No local authority called {name}")


def area_for(address, postcode):
    parts = [p.strip() for p in address.lower().split(",") if p.strip()]
    # a line that is just a town name, e.g. "Leigh"; Wigan is also the borough name so it comes last
    towns = [area for p in parts for area, pattern in AREAS if re.fullmatch(pattern, p)]
    for area in towns:
        if area != "Wigan":
            return area
    if towns:
        return "Wigan"
    district = (postcode or "").upper().split(" ")[0]
    if district in DISTRICT_AREAS:
        return DISTRICT_AREAS[district]
    for area, pattern in AREAS:
        if re.search(pattern, address.lower()):
            return area
    return "Other"


def to_record(e):
    lines = [e.get(f"AddressLine{i}") or "" for i in range(1, 5)]
    address = ", ".join(l.strip() for l in lines if l and l.strip())
    postcode = (e.get("PostCode") or "").strip().upper()
    scores = e.get("scores") or {}
    geo = e.get("geocode") or {}
    try:
        lat, lng = float(geo.get("latitude")), float(geo.get("longitude"))
    except (TypeError, ValueError):
        lat = lng = None
    rated_on = (e.get("RatingDate") or "")[:10]
    # the FSA uses 1 January 1901 as a blank date for places not yet inspected
    if rated_on < "1950":
        rated_on = ""
    return {
        "id": e["FHRSID"],
        "name": (e.get("BusinessName") or "").strip(),
        "type": (e.get("BusinessType") or "").strip(),
        "address": address,
        "postcode": postcode,
        "area": area_for(address, postcode),
        "rating": str(e.get("RatingValue") or ""),
        "date": rated_on,
        "scores": {
            "hygiene": scores.get("Hygiene"),
            "structural": scores.get("Structural"),
            "management": scores.get("ConfidenceInManagement"),
        },
        "lat": lat,
        "lng": lng,
    }


def fetch_all(la_id, page_size=1000):
    records, page = [], 1
    while True:
        data = get("/Establishments", {"localAuthorityId": la_id, "pageSize": page_size, "pageNumber": page})
        batch = data.get("establishments", [])
        records.extend(to_record(e) for e in batch)
        if len(batch) < page_size:
            return records
        page += 1


def main():
    la_id = authority_id()
    records = sorted(fetch_all(la_id), key=lambda r: r["id"])
    if len(records) < 500:
        # Wigan has a couple of thousand food businesses, so a tiny result means something broke
        raise FetchError(f"Only {len(records)} records came back, not saving")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")))
    rated = sum(r["rating"].isdigit() for r in records)
    print(f"Saved {len(records)} businesses ({rated} with a 0-5 rating) to {OUT}")


if __name__ == "__main__":
    try:
        main()
    except FetchError as e:
        sys.exit(f"Food fetch failed: {e}")

from sections.food import fetch


def sample(**over):
    e = {
        "FHRSID": 101, "BusinessName": " Sample Chippy ", "BusinessType": "Takeaway/sandwich shop",
        "AddressLine1": "1 Market Street", "AddressLine2": "", "AddressLine3": "Leigh", "AddressLine4": None,
        "PostCode": "wn7 1aa", "RatingValue": "5", "RatingDate": "2026-10-13T00:00:00",
        "scores": {"Hygiene": 0, "Structural": 5, "ConfidenceInManagement": 0},
        "geocode": {"longitude": "-2.51", "latitude": "53.49"},
    }
    e.update(over)
    return e


def test_record_is_tidy():
    r = fetch.to_record(sample())
    assert r["name"] == "Sample Chippy"
    assert r["address"] == "1 Market Street, Leigh"
    assert r["postcode"] == "WN7 1AA"
    assert r["area"] == "Leigh"
    assert r["date"] == "2026-10-13"
    assert r["scores"] == {"hygiene": 0, "structural": 5, "management": 0}
    assert (r["lat"], r["lng"]) == (53.49, -2.51)


def test_missing_bits_do_not_break():
    r = fetch.to_record(sample(geocode=None, scores=None, RatingDate=None, RatingValue="AwaitingInspection"))
    assert r["lat"] is None and r["date"] == "" and r["rating"] == "AwaitingInspection"
    assert r["scores"]["hygiene"] is None


def test_area_from_address_then_postcode():
    assert fetch.area_for("2 Gerard Street, Ashton In Makerfield", "WN4 9AA") == "Ashton-in-Makerfield"
    assert fetch.area_for("5 Wigan Road, Leigh", "WN7 2BB") == "Leigh"
    assert fetch.area_for("1 Leigh Road, Wigan", "WN1 1AA") == "Wigan"
    assert fetch.area_for("3 Bradshawgate, Leigh, Wigan", "WN7 4NB") == "Leigh"
    assert fetch.area_for("Unit 2, Leigh Road Retail Park", "WN2 3XX") == "Hindley"
    assert fetch.area_for("Unit 3, Bridge Street", "M46 0AA") == "Atherton"
    assert fetch.area_for("Somewhere", "XX1 1XX") == "Other"


def test_fetch_all_pages(monkeypatch):
    pages = {1: [sample(FHRSID=i) for i in range(3)], 2: [sample(FHRSID=9)]}
    monkeypatch.setattr(fetch, "get", lambda path, params=None: {"establishments": pages[params["pageNumber"]]})
    records = fetch.fetch_all(1, page_size=3)
    assert [r["id"] for r in records] == [0, 1, 2, 9]


def test_authority_lookup(monkeypatch):
    monkeypatch.setattr(fetch, "get", lambda path, params=None: {"authorities": [
        {"Name": "Bolton", "LocalAuthorityId": 1}, {"Name": "Wigan", "LocalAuthorityId": 2}]})
    assert fetch.authority_id() == 2


def test_placeholder_date_is_blank():
    r = fetch.to_record(sample(RatingValue="AwaitingInspection", RatingDate="1901-01-01T00:00:00"))
    assert r["date"] == ""

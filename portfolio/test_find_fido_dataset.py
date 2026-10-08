import copy
import json
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


DATASET_PATH = Path(__file__).with_name("find-fido-austin.json")
ALLOWED_CATEGORIES = {"parks", "patios", "travel"}
ALLOWED_HOSTS = {
    "austin.widen.net",
    "tpwd.texas.gov",
    "www.austintexas.gov",
    "www.meanwhilebeer.com",
}
ALLOWED_POLICY_STATES = {
    "designated_off_leash",
    "leashed_welcome",
    "leashed_with_restrictions",
}
REQUIRED_LISTING_KEYS = {
    "id",
    "name",
    "category",
    "location",
    "official_url",
    "dog_policy_status",
    "dog_policy_summary",
    "availability",
    "sponsorship",
    "verification_state",
    "evidence",
    "uncertainty",
}
REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "dataset_id",
    "checked_on",
    "editorial_status",
    "website_integration",
    "boundaries",
    "listings",
}
FORBIDDEN_KEYS = {
    "booking_url",
    "coordinates",
    "email",
    "latitude",
    "longitude",
    "personal_location_history",
    "phone",
    "rank",
    "rating",
    "review_score",
    "submitter",
    "user_id",
}


def load_dataset():
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def all_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from all_keys(child)


def validate_url(value):
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"unapproved source URL: {value}")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError(f"unsafe source URL: {value}")


def validate_dataset(dataset):
    if set(dataset) != REQUIRED_TOP_LEVEL_KEYS:
        raise ValueError("unexpected dataset fields")
    if dataset.get("schema_version") != 1:
        raise ValueError("unsupported schema")
    if dataset["dataset_id"] != "find-fido-austin-starter":
        raise ValueError("unexpected dataset id")
    if dataset["editorial_status"] != "reviewed_source_dataset_not_published":
        raise ValueError("dataset must remain unpublished")
    if dataset["website_integration"] != "deferred_until_shared_generator_claim_is_released":
        raise ValueError("website integration boundary changed")
    checked_on = date.fromisoformat(dataset["checked_on"])
    if checked_on > date.today():
        raise ValueError("checked_on cannot be in the future")
    boundaries = dataset.get("boundaries", {})
    if boundaries != {
        "official_sources_only": True,
        "business_or_park_locations_only": True,
        "user_submissions": False,
        "marketplace_booking": False,
        "ratings_or_rankings": False,
        "paid_placement": False,
    }:
        raise ValueError("dataset boundaries changed")
    forbidden = FORBIDDEN_KEYS.intersection(all_keys(dataset))
    if forbidden:
        raise ValueError(f"forbidden fields: {sorted(forbidden)}")

    listings = dataset.get("listings", [])
    if len(listings) != 4:
        raise ValueError("starter dataset must contain exactly four reviewed listings")
    ids = [listing.get("id") for listing in listings]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate listing id")
    if {listing.get("category") for listing in listings} != ALLOWED_CATEGORIES:
        raise ValueError("starter dataset must cover parks, patios, and travel")

    for listing in listings:
        if set(listing) != REQUIRED_LISTING_KEYS:
            raise ValueError(f"unexpected listing fields for {listing.get('id')}")
        if not all(isinstance(listing[key], str) and listing[key].strip() for key in REQUIRED_LISTING_KEYS - {"evidence", "uncertainty"}):
            raise ValueError(f"missing text field for {listing['id']}")
        if listing["category"] not in ALLOWED_CATEGORIES:
            raise ValueError("invalid category")
        if listing["dog_policy_status"] not in ALLOWED_POLICY_STATES:
            raise ValueError("invalid dog policy state")
        if listing["availability"] != "verify_before_visit":
            raise ValueError("availability must require a fresh check")
        if listing["sponsorship"] != "none":
            raise ValueError("sponsorship cannot be inferred")
        if listing["verification_state"] != "source_checked_not_live_tested":
            raise ValueError("verification state must remain qualified")
        validate_url(listing["official_url"])

        evidence = listing["evidence"]
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"missing evidence for {listing['id']}")
        for source in evidence:
            if set(source) != {"url", "checked_on", "supports"}:
                raise ValueError("unexpected evidence fields")
            validate_url(source["url"])
            if source["checked_on"] != dataset["checked_on"]:
                raise ValueError("source check date must match dataset check date")
            if not source["supports"].strip():
                raise ValueError("source support note is required")
        if listing["official_url"] not in {source["url"] for source in evidence}:
            raise ValueError(f"official URL lacks evidence for {listing['id']}")

        uncertainty = listing["uncertainty"]
        if not isinstance(uncertainty, list) or not uncertainty or not all(isinstance(note, str) and note.strip() for note in uncertainty):
            raise ValueError(f"uncertainty note required for {listing['id']}")

    return True


class FindFidoDatasetTests(unittest.TestCase):
    def test_reviewed_dataset_passes(self):
        self.assertTrue(validate_dataset(load_dataset()))

    def test_insecure_or_unapproved_sources_are_rejected(self):
        for bad_url in ("http://www.austintexas.gov/example", "https://example.com/dogs"):
            with self.subTest(url=bad_url):
                dataset = load_dataset()
                dataset["listings"][0]["official_url"] = bad_url
                with self.assertRaises(ValueError):
                    validate_dataset(dataset)

    def test_duplicate_ids_are_rejected(self):
        dataset = load_dataset()
        dataset["listings"][1]["id"] = dataset["listings"][0]["id"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_dataset(dataset)

    def test_ratings_and_personal_location_fields_are_rejected(self):
        for field in ("rating", "personal_location_history"):
            with self.subTest(field=field):
                dataset = load_dataset()
                dataset["listings"][0][field] = "not allowed"
                with self.assertRaisesRegex(ValueError, "forbidden"):
                    validate_dataset(dataset)

    def test_missing_policy_evidence_is_rejected(self):
        dataset = load_dataset()
        dataset["listings"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "missing evidence"):
            validate_dataset(dataset)

    def test_root_publication_or_commerce_fields_are_rejected(self):
        for field in ("booking", "ranking_data", "sponsor", "publication_status"):
            with self.subTest(field=field):
                dataset = load_dataset()
                dataset[field] = "not allowed"
                with self.assertRaisesRegex(ValueError, "unexpected dataset fields"):
                    validate_dataset(dataset)

    def test_fixed_metadata_cannot_enable_publication(self):
        for field, value in (
            ("dataset_id", "different-dataset"),
            ("editorial_status", "published"),
            ("website_integration", "live"),
        ):
            with self.subTest(field=field):
                dataset = load_dataset()
                dataset[field] = value
                with self.assertRaises(ValueError):
                    validate_dataset(dataset)

    def test_official_url_must_be_in_evidence(self):
        dataset = load_dataset()
        dataset["listings"][0]["official_url"] = "https://www.austintexas.gov/parks"
        with self.assertRaisesRegex(ValueError, "official URL lacks evidence"):
            validate_dataset(dataset)


if __name__ == "__main__":
    unittest.main()

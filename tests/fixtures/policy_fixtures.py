import pytest
import json
from unittest.mock import patch


# Sample policy data
sample_policy_data = {
    "id": 11,
    "country_id": "us",
    "label": None,
    "api_version": "1.180.1",
    "policy_json": json.dumps(
        {"gov.irs.income.bracket.rates.2": {"2024-01-01.2024-12-31": 0.2433}}
    ),
    "policy_hash": "NgJhpeuRVnIAwgYWuJsd2fI/N88rIE6Kcj8q4TPD/i4=",
}

valid_hash_value = "NgJhpeuRVnIAwgYWuJsd2fI/N88rIE6Kcj8q4TPD/i4="


@pytest.fixture
def mock_hash_object():
    """Mock the hash_object function."""
    with patch("policyengine_api.services.policy_service.hash_object") as mock:
        mock.return_value = valid_hash_value
        yield mock


@pytest.fixture
def mock_database():
    """Mock the database module."""
    with patch("policyengine_api.services.policy_service.database") as mock_db:
        yield mock_db


@pytest.fixture
def existing_policy_record(test_db):
    """Insert an existing policy record into the database."""
    test_db.query(
        "INSERT INTO policy (id, country_id, policy_json, policy_hash, label, api_version) VALUES (?, ?, ?, ?, ?, ?)",
        (
            sample_policy_data["id"],
            sample_policy_data["country_id"],
            sample_policy_data["policy_json"],
            sample_policy_data["policy_hash"],
            sample_policy_data["label"],
            sample_policy_data["api_version"],
        ),
    )

    inserted_row = test_db.query(
        "SELECT * FROM policy WHERE id = ?", (sample_policy_data["id"],)
    ).fetchone()

    return inserted_row

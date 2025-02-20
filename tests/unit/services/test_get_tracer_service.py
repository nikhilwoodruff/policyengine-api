import pytest
import json
from policyengine_api.services.tracer_analysis_service import TracerAnalysisService
from werkzeug.exceptions import NotFound


@pytest.fixture
def tracer_service():
    """Fixture to initialize the TracerAnalysisService."""
    return TracerAnalysisService()


@pytest.fixture
def test_tracer_data(test_db):
    """Fixture to insert a valid tracer record into the database."""
    valid_tracer_row = {
        "household_id": "71424",
        "policy_id": "2",
        "country_id": "us",
        "api_version": "1.150.0",
        "tracer_output": json.dumps([
            "only_government_benefit <1500>",
            "    market_income <1000>",
            "        employment_income <1000>",
            "            main_employment_income <1000>",
            "    non_market_income <500>",
            "        pension_income <500>",
        ]),
    }

    # Insert data using query()
    test_db.query(
        """
        INSERT INTO tracers (household_id, policy_id, country_id, api_version, tracer_output) 
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            valid_tracer_row["household_id"],
            valid_tracer_row["policy_id"],
            valid_tracer_row["country_id"],
            valid_tracer_row["api_version"],
            valid_tracer_row["tracer_output"],
        ),
    )
    

    # Verify that the data has been inserted
    inserted_row = test_db.query(
        "SELECT * FROM tracers WHERE household_id = ? AND policy_id = ? AND country_id = ? AND api_version = ?",
        (
            valid_tracer_row["household_id"],
            valid_tracer_row["policy_id"],
            valid_tracer_row["country_id"],
            valid_tracer_row["api_version"],
        ),
    ).fetchone()

    assert inserted_row is not None, "Failed to insert tracer data into the database."

    yield inserted_row  # Yield the inserted data for testing
    # return inserted_row

    # Cleanup after the test
    test_db.query(
        "DELETE FROM tracers WHERE household_id = ? AND policy_id = ? AND country_id = ? AND api_version = ?",
        (
            valid_tracer_row["household_id"],
            valid_tracer_row["policy_id"],
            valid_tracer_row["country_id"],
            valid_tracer_row["api_version"],
        ),
    )


def test_get_tracer_valid(tracer_service, test_tracer_data):
    # Test get_tracer successfully retrieves valid data from the database.""
    record = test_tracer_data

    result = tracer_service.get_tracer(
        record["country_id"], record["household_id"], record["policy_id"], record["api_version"]
    )

    assert isinstance(result, list)
    assert result["tracer_output"] == record["tracer_output"]


def test_get_tracer_not_found(tracer_service):
    # Test get_tracer raises NotFound when no matching record exists.
    with pytest.raises(NotFound):
        tracer_service.get_tracer("us", "999999", "999", "9.999.0")


def test_get_tracer_database_error(tracer_service):
    # Test get_tracer handles database errors properly.
    with pytest.raises(Exception):
        tracer_service.get_tracer("us", "71424", "2", "1.150.0")



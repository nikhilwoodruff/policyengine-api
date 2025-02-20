import pytest

from policyengine_api.services.tracer_analysis_service import (
    TracerAnalysisService,
)

test_service = TracerAnalysisService()

tracer_output = [
    "only_government_benefit <1500>",
    "    market_income <1000>",
    "        employment_income <1000>",
    "            main_employment_income <1000 >",
    "    non_market_income <500>",
    "        pension_income <500>",
]

# Test cases for parse_tracer_output function

def test_tracer_output_for_empty_tracer():
    # Given: An empty tracer output list
    empty_output = []
    target_variable = "market_income"

    # When: Extracting from an empty output
    result = test_service._parse_tracer_output(empty_output, target_variable)

    # Then: It should return empty list
    assert result == []

def test_tracer_output_for_missing_variable():
    # Given: A variable that doesn't exist in the tracer output
    target_variable = "non_existent_variable"

    # When: Extracting the segment
    result = test_service._parse_tracer_output(tracer_output, target_variable)

    # Then: It should return empty list
    assert result == []

def test_tracer_output_for_root_variable():
    # Given: A root-level variable that contains all others
    target_variable = "only_government_benefit"

    # When: Extracting the entire segment
    result = test_service._parse_tracer_output(tracer_output, target_variable)

    # Then: It should return everything inside "only_government_benefit"
    expected_output = tracer_output
    assert result == expected_output

def test_tracer_output_for_nested_variable():
    # Given: A deeply nested variable in the hierarchy
    target_variable = "employment_income"

    # When: Extracting "employment_income"
    result = test_service._parse_tracer_output(tracer_output, target_variable)

    # Then: It should return employment_income as well as nested main_employment_income
    expected_output = tracer_output[2:4]
    assert result == expected_output

def test_tracer_output_for_leaf_variable():
    # Given: A tracer output with various income types
    target_variable = "pension_income"

    # When: Extracting "pension_income"
    result = test_service._parse_tracer_output(tracer_output, target_variable)

    # Then: It should return only "pension_income" since it has no children
    expected_output = tracer_output[5:]
    assert result == expected_output
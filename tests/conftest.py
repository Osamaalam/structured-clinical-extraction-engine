"""Shared test fixtures.

These fixtures are available to all test files automatically.
"""

import pytest

from outcome_extraction.models.measure_definition import MeasureDefinition
from outcome_extraction.models.measure_result import MeasureResult
from outcome_extraction.models.study_arms import StudyArm


@pytest.fixture
def sample_measure_definition():
    """A typical MACE measure definition."""
    return MeasureDefinition(
        short_name="MACE",
        display_name="Major Adverse Cardiovascular Events",
        domain="SAFETY",
        allowed_stat_types=["PERCENT", "COUNT", "OR", "HR"],
        extraction_instructions=(
            "Extract MACE rates at all reported timepoints. "
            "Include per-arm results and any comparative statistics."
        ),
    )


@pytest.fixture
def sample_measure_definitions():
    """Multiple measure definitions for testing."""
    return [
        MeasureDefinition(
            short_name="MACE",
            display_name="Major Adverse Cardiovascular Events",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT", "OR", "HR"],
            extraction_instructions="Extract MACE rates at all reported timepoints.",
        ),
        MeasureDefinition(
            short_name="TLR",
            display_name="Target Lesion Revascularization",
            domain="EFFICACY",
            allowed_stat_types=["PERCENT", "COUNT", "OR"],
            extraction_instructions="Extract TLR rates.",
        ),
        MeasureDefinition(
            short_name="STENT_THROMBOSIS",
            display_name="Stent Thrombosis",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT", "OR"],
            extraction_instructions="Extract stent thrombosis rates (definite/probable).",
        ),
    ]


@pytest.fixture
def sample_study_arms():
    """Two-arm study for testing."""
    return [
        StudyArm(arm_number=1, arm_name="Treatment Group", description="Received device", sample_size=200),
        StudyArm(arm_number=2, arm_name="Control Group", description="Standard of care", sample_size=200),
    ]


@pytest.fixture
def sample_measure_result():
    """A fully populated MeasureResult for testing."""
    return MeasureResult(
        measure_definition_short_name="MACE",
        stat_type="OR",
        primary_val=0.72,
        dispersion_type="CI_95",
        dispersion_val_1=0.50,
        dispersion_val_2=1.03,
        p_operator="=",
        p_value=0.07,
        study_arm="OCT-guided PCI",
        comparator_arm="Angiography-guided PCI",
        n_analyzed=2413,
        raw_text="OR = 0.72, 95% CI [0.50, 1.03], P = .07",
        summary_text="No significant MACE difference between groups.",
        ai_confidence=0.95,
        ai_extraction_status="AUTO_ACCEPTED",
    )


@pytest.fixture
def sample_llm_response_dict():
    """Example raw LLM output (as parsed JSON) for testing parsers."""
    return [
        {
            "measure_definition_short_name": "MACE",
            "stat_type": "OR",
            "primary_val": 0.72,
            "dispersion_type": "CI_95",
            "dispersion_val_1": 0.50,
            "dispersion_val_2": 1.03,
            "p_operator": "=",
            "p_value": 0.07,
            "study_arm": "OCT-guided PCI",
            "comparator_arm": "Angiography-guided PCI",
            "n_analyzed": 2413,
            "raw_text": "OR = 0.72, 95% CI [0.50, 1.03], P = .07",
            "summary_text": "No significant difference.",
        },
        {
            "measure_definition_short_name": "MACE",
            "stat_type": "PERCENT",
            "primary_val": 6.4,
            "unit": "%",
            "timepoint_val": 26,
            "timepoint_unit": "MONTHS",
            "study_arm": "Group I",
            "raw_text": "MACE total, n (%) 11 (6.4)",
        },
    ]

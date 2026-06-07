"""Tests for data models — these should pass out of the box.

If these tests fail, check your environment setup (pip install -e .).
"""

import pytest
from pydantic import ValidationError

from outcome_extraction.models.measure_definition import MeasureDefinition
from outcome_extraction.models.measure_result import MeasureResult
from outcome_extraction.models.study_arms import StudyArm


class TestMeasureDefinition:
    """Tests for MeasureDefinition model."""

    def test_minimal_creation(self):
        md = MeasureDefinition(short_name="MACE")
        assert md.short_name == "MACE"
        assert md.allowed_stat_types == ["PERCENT", "COUNT", "MEAN", "MEDIAN"]

    def test_full_creation(self):
        md = MeasureDefinition(
            short_name="MACE",
            display_name="Major Adverse Cardiovascular Events",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "OR", "HR"],
            extraction_instructions="Extract MACE at all timepoints.",
        )
        assert md.domain == "SAFETY"
        assert "OR" in md.allowed_stat_types

    def test_empty_short_name_raises(self):
        with pytest.raises(ValidationError):
            MeasureDefinition(short_name="")


class TestMeasureResult:
    """Tests for MeasureResult model."""

    def test_minimal_creation(self):
        mr = MeasureResult(
            measure_definition_short_name="MACE",
            stat_type="PERCENT",
            primary_val=6.4,
        )
        assert mr.stat_type == "PERCENT"
        assert mr.primary_val == 6.4
        assert mr.ai_extraction_status == "NEEDS_REVIEW"

    def test_stat_type_normalization(self):
        mr = MeasureResult(
            measure_definition_short_name="MACE",
            stat_type="hazard_ratio",
        )
        assert mr.stat_type == "HR"

    def test_odds_ratio_alias(self):
        mr = MeasureResult(
            measure_definition_short_name="MACE",
            stat_type="ODDS_RATIO",
        )
        assert mr.stat_type == "OR"

    def test_invalid_stat_type_raises(self):
        with pytest.raises(ValidationError):
            MeasureResult(
                measure_definition_short_name="MACE",
                stat_type="INVALID_TYPE",
            )

    def test_p_value_bounds(self):
        with pytest.raises(ValidationError):
            MeasureResult(
                measure_definition_short_name="MACE",
                stat_type="PERCENT",
                p_value=1.5,  # Must be <= 1.0
            )

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            MeasureResult(
                measure_definition_short_name="MACE",
                stat_type="PERCENT",
                ai_confidence=-0.1,  # Must be >= 0.0
            )

    def test_full_result(self, sample_measure_result):
        assert sample_measure_result.stat_type == "OR"
        assert sample_measure_result.primary_val == 0.72
        assert sample_measure_result.dispersion_type == "CI_95"
        assert sample_measure_result.ai_confidence == 0.95

    def test_dispersion_type_validation(self):
        with pytest.raises(ValidationError):
            MeasureResult(
                measure_definition_short_name="MACE",
                stat_type="PERCENT",
                dispersion_type="INVALID",
            )

    def test_timepoint_unit_validation(self):
        with pytest.raises(ValidationError):
            MeasureResult(
                measure_definition_short_name="MACE",
                stat_type="PERCENT",
                timepoint_unit="INVALID",
            )

    def test_json_roundtrip(self, sample_measure_result):
        json_str = sample_measure_result.model_dump_json()
        restored = MeasureResult.model_validate_json(json_str)
        assert restored.primary_val == sample_measure_result.primary_val
        assert restored.stat_type == sample_measure_result.stat_type


class TestStudyArm:
    """Tests for StudyArm model."""

    def test_basic_creation(self):
        arm = StudyArm(arm_number=1, arm_name="Treatment")
        assert arm.arm_number == 1
        assert arm.arm_name == "Treatment"

    def test_arm_number_must_be_positive(self):
        with pytest.raises(ValidationError):
            StudyArm(arm_number=0, arm_name="Invalid")

    def test_arm_name_required(self):
        with pytest.raises(ValidationError):
            StudyArm(arm_number=1, arm_name="")

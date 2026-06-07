import pytest
from outcome_extraction.services.parser_service import ParserService
from outcome_extraction.models.measure_definition import MeasureDefinition
from outcome_extraction.models.measure_result import MeasureResult


class TestParserService:
    """Tests for ParserService."""

    @pytest.fixture
    def parser(self):
        return ParserService()

    def test_normalize_timepoint(self, parser):
        """Test timepoint normalization to days."""
        # Happy paths
        assert parser.normalize_timepoint(6, "MONTHS") == 182.625
        assert parser.normalize_timepoint(1, "YEARS") == 365.25
        assert parser.normalize_timepoint(14, "DAYS") == 14.0
        assert parser.normalize_timepoint(24, "HOURS") == 1.0
        assert parser.normalize_timepoint(2, "WEEKS") == 14.0
        
        # Procedure / None paths
        assert parser.normalize_timepoint(None, "MONTHS") is None
        assert parser.normalize_timepoint(6, None) is None
        assert parser.normalize_timepoint(None, "PROCEDURE") is None
        assert parser.normalize_timepoint(1, "PROCEDURE") is None
        assert parser.normalize_timepoint(6, "UNKNOWN_UNIT") is None

    def test_assign_confidence(self, parser):
        """Test confidence calculation scoring heuristics."""
        # 1. Very low confidence (missing primary value or stat type)
        bad_record = {"measure_definition_short_name": "MACE"}
        assert parser.assign_confidence(bad_record) == 0.1

        # 2. Base confidence (has core stats but no extra metadata)
        base_record = {
            "measure_definition_short_name": "MACE",
            "stat_type": "PERCENT",
            "primary_val": 5.5,
        }
        # Starts at 0.7
        assert parser.assign_confidence(base_record) == pytest.approx(0.7)

        # 3. High confidence with evidence, n_analyzed, and summary
        excellent_record = {
            "measure_definition_short_name": "MACE",
            "stat_type": "PERCENT",
            "primary_val": 5.5,
            "raw_text": "MACE rate was 5.5% during the study.",
            "n_analyzed": 100,
            "summary_text": "MACE was 5.5% in the treatment group.",
        }
        # 0.7 (base) + 0.15 (raw_text) + 0.05 (n_analyzed) + 0.03 (summary) = 0.93
        assert parser.assign_confidence(excellent_record) == pytest.approx(0.93)

        # 4. Maximum confidence (all indicators present)
        max_record = {
            "measure_definition_short_name": "MACE",
            "stat_type": "OR",
            "primary_val": 0.72,
            "dispersion_type": "CI_95",
            "dispersion_val_1": 0.50,
            "dispersion_val_2": 1.03,
            "p_operator": "=",
            "p_value": 0.07,
            "study_arm": "Treatment",
            "raw_text": "OR was 0.72, 95% CI 0.50-1.03, p=0.07",
            "n_analyzed": 1000,
            "summary_text": "High accuracy text details here.",
        }
        # 0.7 + 0.15 + 0.05 + 0.05 + 0.05 + 0.02 + 0.03 = 1.05 (capped at 1.0)
        assert parser.assign_confidence(max_record) == pytest.approx(1.0)

    def test_parse_results_happy_path(self, parser, sample_measure_definitions, sample_llm_response_dict):
        """Test parsing valid raw LLM responses into verified MeasureResult objects."""
        results = parser.parse_results(sample_llm_response_dict, sample_measure_definitions)
        
        assert len(results) == 2
        
        # Check first item (OR)
        r1 = results[0]
        assert isinstance(r1, MeasureResult)
        assert r1.measure_definition_short_name == "MACE"
        assert r1.stat_type == "OR"
        assert r1.primary_val == 0.72
        assert r1.dispersion_type == "CI_95"
        assert r1.dispersion_val_1 == 0.50
        assert r1.dispersion_val_2 == 1.03
        assert r1.p_operator == "="
        assert r1.p_value == 0.07
        assert r1.study_arm == "OCT-guided PCI"
        assert r1.ai_extraction_status == "AUTO_ACCEPTED"  # High confidence

        # Check second item (PERCENT with timepoint)
        r2 = results[1]
        assert isinstance(r2, MeasureResult)
        assert r2.measure_definition_short_name == "MACE"
        assert r2.stat_type == "PERCENT"
        assert r2.primary_val == 6.4
        assert r2.timepoint_val == 26
        assert r2.timepoint_unit == "MONTHS"
        assert r2.timepoint_normalized_days == pytest.approx(26 * 30.4375)
        assert r2.study_arm == "Group I"

    def test_parse_results_empty_or_none(self, parser, sample_measure_definitions):
        """Verify that passing None or empty list does not crash and returns empty list."""
        assert parser.parse_results(None, sample_measure_definitions) == []
        assert parser.parse_results([], sample_measure_definitions) == []

    def test_parse_results_malformed_and_unknowns(self, parser, sample_measure_definitions):
        """Test that malformed records, or records with unknown measure names are skipped gracefully."""
        bad_response = [
            # Missing measure short name
            {
                "stat_type": "PERCENT",
                "primary_val": 5.0,
            },
            # Unknown measure name
            {
                "measure_definition_short_name": "UNKNOWN_MEASURE_NAME",
                "stat_type": "PERCENT",
                "primary_val": 5.0,
            },
            # Not a dictionary
            "not a dictionary record",
            # Missing stat_type
            {
                "measure_definition_short_name": "MACE",
                "primary_val": 5.0,
            }
        ]
        results = parser.parse_results(bad_response, sample_measure_definitions)
        assert results == []

    def test_parse_results_stat_type_validation_and_normalization(self, parser, sample_measure_definitions):
        """Verify the parser enforces stat_type restrictions and normalizes aliases."""
        test_response = [
            # Valid normalized alias (HAZARD_RATIO -> HR)
            {
                "measure_definition_short_name": "MACE",
                "stat_type": "HAZARD_RATIO",
                "primary_val": 0.85,
            },
            # Valid normalized alias (ODDS_RATIO -> OR)
            {
                "measure_definition_short_name": "MACE",
                "stat_type": "odds_ratio",
                "primary_val": 0.72,
            },
            # Disallowed stat_type for MACE (MACE only allows PERCENT, COUNT, OR, HR, etc. from definitions)
            {
                "measure_definition_short_name": "MACE",
                "stat_type": "MEAN",  # MEAN is not in allowed_stat_types for sample MACE
                "primary_val": 15.2,
            }
        ]
        results = parser.parse_results(test_response, sample_measure_definitions)
        
        assert len(results) == 2
        assert results[0].stat_type == "HR"
        assert results[1].stat_type == "OR"

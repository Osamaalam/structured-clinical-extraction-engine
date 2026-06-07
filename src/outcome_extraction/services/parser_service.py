"""Parser service for converting raw LLM responses into validated MeasureResult objects.

TODO: Implement the ParserService class.

This service is responsible for:
1. Taking raw JSON (dict/list) from the LLM response
2. Validating and normalizing each record into a MeasureResult
3. Filtering out invalid records gracefully (log warnings, don't crash)
4. Normalizing timepoints to days
5. Assigning confidence scores
6. Validating stat_type against allowed_stat_types from the MeasureDefinition
"""

import logging
from typing import Dict, List, Optional

from ..config.constants import TIMEPOINT_TO_DAYS
from ..models.measure_definition import MeasureDefinition
from ..models.measure_result import MeasureResult

logger = logging.getLogger(__name__)


class ParserService:
    """Parses and validates raw LLM extraction output into MeasureResult objects."""

    def parse_results(
        self,
        raw_data: Optional[List[Dict]],
        measure_definitions: List[MeasureDefinition],
    ) -> List[MeasureResult]:
        """Parse raw LLM output into validated MeasureResult objects.

        Args:
            raw_data: List of dicts from the LLM's JSON response.
                Each dict should roughly match the MeasureResult schema.
            measure_definitions: The measure configs, used to validate
                stat_type against allowed_stat_types.

        Returns:
            List of validated MeasureResult objects. Invalid records are
            logged and skipped — this method should never raise.
        """
        if not raw_data:
            logger.warning("No raw data provided to parser.")
            return []

        # Map measure definitions by short name for easy lookup
        definitions_map = {md.short_name: md for md in measure_definitions}
        valid_results = []

        for index, record in enumerate(raw_data):
            if not isinstance(record, dict):
                logger.warning(f"Record at index {index} is not a dictionary: {record}")
                continue

            # Create a copy so we don't modify the input dict in place
            record = dict(record)

            try:
                # 1. Basic validation of measure definition existence
                short_name = record.get("measure_definition_short_name")
                if not short_name:
                    logger.warning(f"Record at index {index} is missing 'measure_definition_short_name'.")
                    continue

                if short_name not in definitions_map:
                    logger.warning(
                        f"Record at index {index} has unknown measure short_name '{short_name}'. "
                        f"Expected one of: {list(definitions_map.keys())}"
                    )
                    continue

                md = definitions_map[short_name]

                # 2. Check and validate stat_type compatibility
                stat_type = record.get("stat_type")
                if not stat_type:
                    logger.warning(f"Record at index {index} is missing 'stat_type'.")
                    continue

                # Normalize stat_type as standard (e.g. hazard_ratio -> HR)
                stat_type_upper = str(stat_type).upper().strip()
                aliases = {"HAZARD_RATIO": "HR", "ODDS_RATIO": "OR", "RISK_RATIO": "RR"}
                stat_type_normalized = aliases.get(stat_type_upper, stat_type_upper)

                if stat_type_normalized not in md.allowed_stat_types:
                    logger.warning(
                        f"Record at index {index} uses stat_type '{stat_type}' which is not in the allowed "
                        f"stat_types for {short_name}: {md.allowed_stat_types}."
                    )
                    continue

                # Update the normalized stat_type
                record["stat_type"] = stat_type_normalized

                # 3. Timepoint normalization
                t_val = record.get("timepoint_val")
                t_unit = record.get("timepoint_unit")
                
                # Coerce numeric types safely
                if t_val is not None:
                    try:
                        t_val = float(t_val)
                    except (ValueError, TypeError):
                        logger.warning(f"Record index {index} has invalid timepoint_val '{t_val}'. Setting to None.")
                        t_val = None

                normalized_days = self.normalize_timepoint(t_val, t_unit)
                record["timepoint_normalized_days"] = normalized_days

                # 4. Assign confidence
                # If confidence is not set or invalid, compute and assign it
                conf = record.get("ai_confidence")
                if conf is None:
                    conf = self.assign_confidence(record)
                    record["ai_confidence"] = conf
                else:
                    try:
                        conf = float(conf)
                        if not (0.0 <= conf <= 1.0):
                            conf = self.assign_confidence(record)
                            record["ai_confidence"] = conf
                    except (ValueError, TypeError):
                        conf = self.assign_confidence(record)
                        record["ai_confidence"] = conf

                # Set extraction status based on confidence
                if conf >= 0.85:
                    record["ai_extraction_status"] = "AUTO_ACCEPTED"
                else:
                    record["ai_extraction_status"] = "NEEDS_REVIEW"

                # 5. Build and validate with Pydantic model
                # Coerce float values safely before passing to model
                for float_field in ["primary_val", "alt_val", "dispersion_val_1", "dispersion_val_2", "p_value"]:
                    val = record.get(float_field)
                    if val is not None and val != "":
                        try:
                            record[float_field] = float(val)
                        except (ValueError, TypeError):
                            record[float_field] = None
                    else:
                        record[float_field] = None

                # Coerce integer fields
                n_analyzed = record.get("n_analyzed")
                if n_analyzed is not None and n_analyzed != "":
                    try:
                        record["n_analyzed"] = int(float(n_analyzed))
                    except (ValueError, TypeError):
                        record["n_analyzed"] = None
                else:
                    record["n_analyzed"] = None

                # Initialize model to trigger validation
                validated_result = MeasureResult(**record)
                valid_results.append(validated_result)

            except Exception as e:
                logger.warning(f"Failed to parse and validate record at index {index} due to: {e}")
                continue

        return valid_results

    def normalize_timepoint(
        self, timepoint_val: Optional[float], timepoint_unit: Optional[str]
    ) -> Optional[float]:
        """Convert a timepoint to normalized days.

        Args:
            timepoint_val: Numeric timepoint value (e.g., 6).
            timepoint_unit: Unit string (e.g., "MONTHS").

        Returns:
            Timepoint in days (e.g., 182.625 for 6 months), or None if
            conversion is not possible.
        """
        if timepoint_val is None or timepoint_unit is None:
            return None

        unit_upper = str(timepoint_unit).upper().strip()
        factor = TIMEPOINT_TO_DAYS.get(unit_upper)
        if factor is None:
            return None

        return float(timepoint_val) * factor

    def assign_confidence(self, result_dict: Dict) -> float:
        """Assign an AI confidence score based on extraction quality.

        Args:
            result_dict: The raw extraction dict from the LLM.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        # 1. Check for crucial fields
        primary_val = result_dict.get("primary_val")
        stat_type = result_dict.get("stat_type")
        raw_text = result_dict.get("raw_text")

        if primary_val is None or stat_type is None:
            return 0.1  # Very low confidence if core results are missing

        # Calculate a baseline confidence
        confidence = 0.7

        # Reward presence of verbatim raw text evidence
        if raw_text and isinstance(raw_text, str) and len(raw_text.strip()) > 10:
            confidence += 0.15

        # Reward presence of sample size info (n_analyzed)
        n_analyzed = result_dict.get("n_analyzed")
        if n_analyzed is not None:
            confidence += 0.05

        # Reward complete dispersion interval mapping for error bounds
        disp_type = result_dict.get("dispersion_type")
        disp_val1 = result_dict.get("dispersion_val_1")
        if disp_type and disp_val1 is not None:
            confidence += 0.05

        # Reward exact P-value tracking
        p_val = result_dict.get("p_value")
        p_op = result_dict.get("p_operator")
        if p_val is not None or p_op == "NS":
            confidence += 0.05

        # Reward study arm attribution
        study_arm = result_dict.get("study_arm")
        if study_arm:
            confidence += 0.02

        # Reward summary explanations
        summary_text = result_dict.get("summary_text")
        if summary_text:
            confidence += 0.03

        # Cap confidence between 0.0 and 1.0
        return min(max(confidence, 0.0), 1.0)

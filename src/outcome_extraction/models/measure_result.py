"""Model for a single extracted outcome measure result."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from ..config.constants import DISPERSION_TYPES, EXTRACTION_STATUSES, P_OPERATORS, STAT_TYPES, TIMEPOINT_UNITS


class MeasureResult(BaseModel):
    """One extracted result row: a single measure at a single timepoint for a single arm.

    For example, if a paper reports MACE at 12 months for both a treatment arm
    and a control arm, that produces TWO MeasureResult rows. If they also report
    a comparative OR between arms, that's a THIRD row.
    """

    # --- Identity ---
    measure_definition_short_name: str = Field(
        description="Must match a MeasureDefinition.short_name in the review.",
    )

    # --- Statistical result ---
    stat_type: str = Field(
        description="How the result is reported: MEAN, MEDIAN, HR, OR, RR, COUNT, PERCENT, etc.",
    )
    primary_val: Optional[float] = Field(
        default=None,
        description="The main numeric value.",
    )
    alt_val: Optional[float] = Field(
        default=None,
        description="Secondary value (e.g., event count when primary_val is a percentage).",
    )
    unit: Optional[str] = Field(
        default=None,
        description="Unit of measurement (e.g., '%', 'mmHg', 'events/100pt-yrs').",
    )

    # --- Dispersion ---
    dispersion_type: Optional[str] = Field(
        default=None,
        description="SD, SE, CI_95, CI_90, CI_99, IQR, or RANGE.",
    )
    dispersion_val_1: Optional[float] = Field(
        default=None,
        description="Lower bound or single dispersion value (e.g., SD value, CI lower).",
    )
    dispersion_val_2: Optional[float] = Field(
        default=None,
        description="Upper bound (for CI, IQR, Range). Null for symmetric dispersion (SD, SE).",
    )

    # --- P-value ---
    p_operator: Optional[str] = Field(
        default=None,
        description="Operator: '<', '=', '>', 'NS', etc.",
    )
    p_value: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Numeric p-value between 0 and 1.",
    )

    # --- Timepoint ---
    timepoint_val: Optional[float] = Field(
        default=None,
        description="Numeric timepoint value.",
    )
    timepoint_unit: Optional[str] = Field(
        default=None,
        description="DAYS, WEEKS, MONTHS, YEARS, HOURS, or PROCEDURE.",
    )
    timepoint_normalized_days: Optional[float] = Field(
        default=None,
        description="Timepoint converted to days for comparison across studies.",
    )

    # --- Study arms ---
    study_arm: Optional[str] = Field(
        default=None,
        description="Name of the study arm this result belongs to. Null for single-arm studies.",
    )
    comparator_arm: Optional[str] = Field(
        default=None,
        description="Only for comparative stats (HR, OR, RR): the reference arm.",
    )
    n_analyzed: Optional[int] = Field(
        default=None,
        ge=0,
        description="Sample size for this specific result.",
    )

    # --- Evidence ---
    raw_text: Optional[str] = Field(
        default=None,
        description="Verbatim sentence(s) from the source article.",
    )
    summary_text: Optional[str] = Field(
        default=None,
        description="One plain-English sentence interpreting this result.",
    )

    # --- AI metadata ---
    ai_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score: 0.0 (no confidence) to 1.0 (certain).",
    )
    ai_extraction_status: Optional[str] = Field(
        default="NEEDS_REVIEW",
        description="AUTO_ACCEPTED, NEEDS_REVIEW, or FAILED.",
    )

    @field_validator("stat_type")
    @classmethod
    def validate_stat_type(cls, v: str) -> str:
        upper = v.upper().strip()
        # Normalize common aliases
        aliases = {"HAZARD_RATIO": "HR", "ODDS_RATIO": "OR", "RISK_RATIO": "RR"}
        upper = aliases.get(upper, upper)
        if upper not in STAT_TYPES:
            raise ValueError(f"Invalid stat_type '{v}'. Must be one of: {STAT_TYPES}")
        return upper

    @field_validator("dispersion_type")
    @classmethod
    def validate_dispersion_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        upper = v.upper().strip()
        if upper not in [d for d in DISPERSION_TYPES if d is not None]:
            raise ValueError(f"Invalid dispersion_type '{v}'. Must be one of: {DISPERSION_TYPES}")
        return upper

    @field_validator("timepoint_unit")
    @classmethod
    def validate_timepoint_unit(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        upper = v.upper().strip()
        if upper not in [t for t in TIMEPOINT_UNITS if t is not None]:
            raise ValueError(f"Invalid timepoint_unit '{v}'. Must be one of: {TIMEPOINT_UNITS}")
        return upper

    @field_validator("ai_extraction_status")
    @classmethod
    def validate_extraction_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return "NEEDS_REVIEW"
        upper = v.upper().strip()
        if upper not in EXTRACTION_STATUSES:
            raise ValueError(f"Invalid ai_extraction_status '{v}'. Must be one of: {EXTRACTION_STATUSES}")
        return upper

    model_config = {
        "json_schema_extra": {
            "examples": [
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
                    "ai_confidence": 0.95,
                    "ai_extraction_status": "AUTO_ACCEPTED",
                }
            ]
        }
    }

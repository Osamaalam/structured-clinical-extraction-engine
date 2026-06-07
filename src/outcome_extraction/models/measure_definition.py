"""Model for configuring what measures to extract."""

from typing import List, Optional

from pydantic import BaseModel, Field


class MeasureDefinition(BaseModel):
    """Defines a single outcome measure to extract from a clinical paper.

    This is the INPUT configuration — it tells the extraction system what to
    look for. Each review may define multiple MeasureDefinitions (e.g., MACE,
    stent thrombosis, all-cause mortality).
    """

    short_name: str = Field(
        min_length=1,
        description="Unique short name for this measure (e.g., 'MACE', 'TLR', 'ALL_CAUSE_DEATH').",
    )

    display_name: Optional[str] = Field(
        default=None,
        description="Human-readable name (e.g., 'Major Adverse Cardiovascular Events').",
    )

    domain: Optional[str] = Field(
        default=None,
        description="Clinical domain: SAFETY, EFFICACY, PHARMACOKINETIC, etc.",
    )

    allowed_stat_types: List[str] = Field(
        default_factory=lambda: ["PERCENT", "COUNT", "MEAN", "MEDIAN"],
        description="Statistical types this measure can be reported as.",
    )

    extraction_instructions: Optional[str] = Field(
        default=None,
        description="Free-text instructions for the AI on how to find this measure in the paper.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "short_name": "MACE",
                    "display_name": "Major Adverse Cardiovascular Events",
                    "domain": "SAFETY",
                    "allowed_stat_types": ["PERCENT", "COUNT", "OR", "HR"],
                    "extraction_instructions": (
                        "Extract MACE rates at all reported timepoints. "
                        "Include per-arm results and any comparative statistics (OR, HR)."
                    ),
                }
            ]
        }
    }

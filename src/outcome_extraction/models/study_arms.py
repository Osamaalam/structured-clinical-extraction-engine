"""Pydantic models for study arm definitions."""

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class StudyArm(BaseModel):
    """Model for defining a study arm.

    Allows users to provide study arm labels so the extraction system can
    associate results with the correct arms.
    """

    arm_number: int = Field(ge=1, description="Sequential arm number (1-indexed).")
    arm_name: str = Field(min_length=1, description="Name or label for the study arm.")
    description: Optional[str] = Field(default=None, description="Description of the intervention for this arm.")
    sample_size: Optional[Union[int, str]] = Field(default=None, description="Number of participants in this arm.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "arm_number": 1,
                    "arm_name": "Treatment Group",
                    "description": "Received experimental intervention",
                    "sample_size": 50,
                },
                {
                    "arm_number": 2,
                    "arm_name": "Control Group",
                    "description": "Received placebo",
                    "sample_size": 50,
                },
            ]
        }
    }

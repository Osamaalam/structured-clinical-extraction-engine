"""LLM prompt templates for structured outcome measure extraction.

TODO: Implement prompt templates that instruct the LLM to extract structured
MeasureResult data from clinical trial text.

Your prompts should:
1. Accept a MeasureDefinition (short_name, allowed_stat_types, extraction_instructions)
2. Accept optional StudyArm labels
3. Request output in a JSON format that maps to MeasureResult fields
4. Handle edge cases: missing values, multiple timepoints, comparative stats

Refer to the MeasureResult model in models/measure_result.py for the full schema.
Refer to constants.py for valid STAT_TYPES, DISPERSION_TYPES, etc.

Hint: Look at how the provided LLMService.invoke_and_parse_json() handles
JSON code blocks — your prompt should request ```json ... ``` output.
"""

from typing import List, Optional

from ..models.measure_definition import MeasureDefinition
from ..models.study_arms import StudyArm


def build_extraction_prompt(
    article_text: str,
    measure_definitions: List[MeasureDefinition],
    study_arms: Optional[List[StudyArm]] = None,
) -> str:
    """Build the LLM prompt for extracting structured outcome measures.

    Args:
        article_text: Full text extracted from the clinical trial PDF.
        measure_definitions: List of measures to extract (e.g., MACE, TLR).
        study_arms: Optional list of known study arms.

    Returns:
        A formatted prompt string ready to send to the LLM.
    """
    # Format measure definitions for the prompt
    measures_block = []
    for md in measure_definitions:
        allowed = ", ".join(md.allowed_stat_types)
        instr = md.extraction_instructions or "No custom instructions."
        measures_block.append(
            f"- **{md.short_name}** ({md.display_name or ''}):\n"
            f"  - Clinical Domain: {md.domain or 'Unspecified'}\n"
            f"  - Allowed stat_types: {allowed}\n"
            f"  - Instructions: {instr}"
        )
    measures_str = "\n".join(measures_block)

    # Format study arms for the prompt
    arms_str = "None specified. Please extract and name them based on the text."
    if study_arms:
        arms_block = []
        for arm in study_arms:
            size_str = f" (N={arm.sample_size})" if arm.sample_size else ""
            desc_str = f" - {arm.description}" if arm.description else ""
            arms_block.append(f"- Arm {arm.arm_number}: '{arm.arm_name}'{size_str}{desc_str}")
        arms_str = "\n".join(arms_block)

    # Prompt construction
    prompt = f"""You are an expert medical data extraction assistant specializing in clinical trial publications.
Your task is to extract precise, structured, quantitative outcome results from the provided clinical trial text.

### Target Outcome Measures to Extract:
{measures_str}

### Study Arms Configuration (If any):
{arms_str}

### Instructions:
1. **Scope of Extraction**: For each target outcome measure, find all reported statistics (e.g. at different follow-up timepoints, or for different study arms, or comparison statistics between arms). Each distinct statistic (value/timepoint/arm combination) should be a separate result object.
2. **Assign Measure Short Name**: The `measure_definition_short_name` MUST exactly match one of the target measure names above (e.g. "MACE", "STENT_THROMBOSIS", etc.).
3. **Statistical Type (`stat_type`)**: Must be one of the allowed statistical types for that measure. For example: "MEAN", "MEDIAN", "HR", "OR", "RR", "COUNT", "PERCENT", "RATE", etc. Normalise "HAZARD_RATIO" to "HR", "ODDS_RATIO" to "OR", "RISK_RATIO" to "RR".
4. **Primary Value (`primary_val`)**: This is the main numeric value (e.g., 6.4 for 6.4%, 0.72 for an Odds Ratio of 0.72). It must be a float or null.
5. **Alternative Value (`alt_val`)**: This is the secondary numeric value (e.g., event count when primary_val is a percentage, such as 11.0 events).
6. **Unit (`unit`)**: Specify the unit (e.g. "%", "events/100pt-yrs", "mmHg"). Use null for unitless stats like OR, HR, RR.
7. **Dispersion Type (`dispersion_type`)**: SD, SE, CI_95, CI_90, CI_99, IQR, or RANGE.
8. **Dispersion Values (`dispersion_val_1`, `dispersion_val_2`)**:
   - For symmetric dispersion (like SD, SE), put the value in `dispersion_val_1` and leave `dispersion_val_2` as null.
   - For interval/range dispersion (like CI, IQR, Range), put the lower bound in `dispersion_val_1` and upper bound in `dispersion_val_2`.
9. **P-Value Operator & Value (`p_operator`, `p_value`)**:
   - `p_operator`: Must be one of: "<", "=", ">", "NS", "≤", "≥", or null. If "P < 0.001", use "<" and 0.001. If "P = 0.07", use "=" and 0.07. If "not significant" or "NS", use "NS" and null.
10. **Timepoints (`timepoint_val`, `timepoint_unit`)**:
    - Extract numeric value (e.g. 12.0) and unit (DAYS, WEEKS, MONTHS, YEARS, HOURS, or PROCEDURE).
    - For events occurring during procedure/surgery, or inpatient hospital stay immediately after surgery, set `timepoint_unit` to "PROCEDURE" and `timepoint_val` to null.
11. **Study Arm Association (`study_arm`, `comparator_arm`)**:
    - Match results to the appropriate study arm. Use the provided study arms or extract the arm labels from the text.
    - For comparative statistics (like HR, OR, RR), assign the main/intervention arm to `study_arm` and the comparator/control/reference arm to `comparator_arm`.
12. **Number Analyzed (`n_analyzed`)**: Extract the sample size/denominator specifically analyzed for this measurement (integer or null).
13. **Evidence (`raw_text`, `summary_text`)**:
    - `raw_text`: MUST be the exact verbatim sentence(s) from the text containing this result. Do not edit or paraphrase!
    - `summary_text`: A single plain-English sentence summarizing the result in context (e.g., "MACE was 6.4% in Group I at 26 months.").

### Output Format:
Your output must be a single JSON array of objects representing the extracted results.
Do not write any introductory or concluding text, explanations, or commentary.
Return the JSON array wrapped inside a single ```json ``` markdown codeblock.

### JSON Output Schema Example:
```json
[
  {{
    "measure_definition_short_name": "MACE",
    "stat_type": "OR",
    "primary_val": 0.72,
    "unit": null,
    "dispersion_type": "CI_95",
    "dispersion_val_1": 0.50,
    "dispersion_val_2": 1.03,
    "p_operator": "=",
    "p_value": 0.07,
    "timepoint_val": 12.0,
    "timepoint_unit": "MONTHS",
    "study_arm": "OCT-guided PCI",
    "comparator_arm": "Angiography-guided PCI",
    "n_analyzed": 2413,
    "raw_text": "OR = 0.72, 95% CI [0.50, 1.03], P = .07",
    "summary_text": "OCT-guided PCI had an odds ratio of 0.72 for MACE at 12 months compared to angiography-guided PCI."
  }}
]
```

### Clinical Trial Article Text to Extract From:
\"\"\"{article_text}\"\"\"
"""
    return prompt

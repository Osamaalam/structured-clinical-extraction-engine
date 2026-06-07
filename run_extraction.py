"""Main entry point — run extraction on all PDFs and output results.

Usage:
    python run_extraction.py

This script:
1. Loads measure definitions (you can customize these)
2. Finds all PDFs in data/pdfs/
3. Runs extraction on each PDF
4. Saves results to extraction_output.json

TODO: Wire up your ExtractionService and configure measure definitions
based on the ground truth spreadsheet.
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_measure_definitions():
    """Define the measures to extract.

    These match what's in the ground truth spreadsheet.
    """
    from outcome_extraction.models.measure_definition import MeasureDefinition

    return [
        # Cardiology / Device Measures
        MeasureDefinition(
            short_name="MACE",
            display_name="Major Adverse Cardiovascular Events",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT", "OR", "HR", "RR", "RATE"],
            extraction_instructions="Extract MACE (Major Adverse Cardiovascular Events) rates/counts at all reported timepoints. Include per-arm results and comparative statistics (OR, HR).",
        ),
        MeasureDefinition(
            short_name="STENT_THROMBOSIS",
            display_name="Stent Thrombosis",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT", "OR", "HR", "RR", "RATE"],
            extraction_instructions="Extract stent thrombosis rates or event counts (definite or probable) at all reported timepoints.",
        ),
        MeasureDefinition(
            short_name="MI",
            display_name="Myocardial Infarction",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT", "OR", "HR", "RR", "RATE"],
            extraction_instructions="Extract myocardial infarction (MI) rates or event counts at all reported timepoints.",
        ),
        MeasureDefinition(
            short_name="TLR",
            display_name="Target Lesion Revascularization",
            domain="EFFICACY",
            allowed_stat_types=["PERCENT", "COUNT", "OR", "HR", "RR"],
            extraction_instructions="Extract target lesion revascularization (TLR) rates or counts at all reported timepoints.",
        ),
        MeasureDefinition(
            short_name="TVR",
            display_name="Target Vessel Revascularization",
            domain="EFFICACY",
            allowed_stat_types=["PERCENT", "COUNT", "OR", "HR", "RR"],
            extraction_instructions="Extract target vessel revascularization (TVR) rates or counts at all reported timepoints.",
        ),
        MeasureDefinition(
            short_name="ALL_CAUSE_DEATH",
            display_name="All-Cause Mortality",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT", "OR", "HR", "RR"],
            extraction_instructions="Extract all-cause death / mortality rates or counts at all reported timepoints.",
        ),
        MeasureDefinition(
            short_name="CV_DEATH",
            display_name="Cardiovascular Mortality",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT", "OR", "HR", "RR"],
            extraction_instructions="Extract cardiovascular (CV) death / mortality rates or counts at all reported timepoints.",
        ),
        # Orthopedic / Surgery Measures
        MeasureDefinition(
            short_name="INTRAOP_COMPLICATION",
            display_name="Intraoperative Complication",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT"],
            extraction_instructions="Extract intraoperative complications occurring during the surgery/procedure (e.g. hairline cracks, fractures, conversions).",
        ),
        MeasureDefinition(
            short_name="POSTOP_COMPLICATION_INPATIENT",
            display_name="Inpatient Postoperative Complication",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT"],
            extraction_instructions="Extract direct postoperative complications occurring during the inpatient hospital stay.",
        ),
        MeasureDefinition(
            short_name="REVISION_INPATIENT",
            display_name="Inpatient Revision",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT"],
            extraction_instructions="Extract revision procedures performed during the inpatient hospital stay.",
        ),
        MeasureDefinition(
            short_name="POSTOP_COMPLICATION_FOLLOWUP",
            display_name="Follow-up Postoperative Complication",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT"],
            extraction_instructions="Extract postoperative complications occurring during the follow-up period after discharge.",
        ),
        MeasureDefinition(
            short_name="REVISION_FOLLOWUP",
            display_name="Follow-up Revision",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT"],
            extraction_instructions="Extract revision procedures performed during the follow-up period after discharge.",
        ),
        MeasureDefinition(
            short_name="IMPLANT_SURVIVAL",
            display_name="Implant Survival",
            domain="EFFICACY",
            allowed_stat_types=["PERCENT"],
            extraction_instructions="Extract implant survival rates (e.g. from Kaplan-Meier estimation) at all reported timepoints (e.g. 5, 10, 15 years).",
        ),
        MeasureDefinition(
            short_name="REOPERATION_RATE",
            display_name="Reoperation Rate",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT"],
            extraction_instructions="Extract reoperation rates or counts during the study.",
        ),
        MeasureDefinition(
            short_name="STEM_SUBSIDENCE",
            display_name="Stem Subsidence",
            domain="SAFETY",
            allowed_stat_types=["MEAN", "MEDIAN", "PERCENT"],
            extraction_instructions="Extract the amount of stem subsidence (e.g. mean or median in mm, or percentage of patients with subsidence).",
        ),
        MeasureDefinition(
            short_name="SUBSIDENCE_GT10MM",
            display_name="Subsidence > 10mm",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT"],
            extraction_instructions="Extract rates or counts of patients experiencing stem subsidence greater than 10 mm.",
        ),
        MeasureDefinition(
            short_name="DISLOCATION",
            display_name="Implant Dislocation",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT"],
            extraction_instructions="Extract dislocation rates or counts.",
        ),
        MeasureDefinition(
            short_name="OHS",
            display_name="Oxford Hip Score",
            domain="EFFICACY",
            allowed_stat_types=["MEAN", "MEDIAN", "CHANGE_FROM_BASELINE"],
            extraction_instructions="Extract Oxford Hip Score (OHS) measurements.",
        ),
        MeasureDefinition(
            short_name="ETO_UNION",
            display_name="Extended Trochanteric Osteotomy Union",
            domain="EFFICACY",
            allowed_stat_types=["PERCENT", "COUNT"],
            extraction_instructions="Extract extended trochanteric osteotomy (ETO) union/healing rates or counts.",
        ),
        # CGM / Diabetes Measures
        MeasureDefinition(
            short_name="MARD",
            display_name="Mean Absolute Relative Difference",
            domain="EFFICACY",
            allowed_stat_types=["PERCENT"],
            extraction_instructions="Extract Mean Absolute Relative Difference (MARD) rates for glucose monitoring.",
        ),
        MeasureDefinition(
            short_name="AGREEMENT_15_15",
            display_name="Agreement 15/15",
            domain="EFFICACY",
            allowed_stat_types=["PERCENT"],
            extraction_instructions="Extract agreement rate within 15% / 15 mg/dL.",
        ),
        MeasureDefinition(
            short_name="AGREEMENT_20_20",
            display_name="Agreement 20/20",
            domain="EFFICACY",
            allowed_stat_types=["PERCENT"],
            extraction_instructions="Extract agreement rate within 20% / 20 mg/dL.",
        ),
        MeasureDefinition(
            short_name="ALERT_DETECTION_70MGDL",
            display_name="Alert Detection at 70 mg/dL",
            domain="EFFICACY",
            allowed_stat_types=["PERCENT"],
            extraction_instructions="Extract alert detection sensitivity/rate for hypoglycemia (70 mg/dL threshold).",
        ),
        MeasureDefinition(
            short_name="ALERT_DETECTION_180MGDL",
            display_name="Alert Detection at 180 mg/dL",
            domain="EFFICACY",
            allowed_stat_types=["PERCENT"],
            extraction_instructions="Extract alert detection sensitivity/rate for hyperglycemia (180 mg/dL threshold).",
        ),
        MeasureDefinition(
            short_name="SENSOR_SURVIVAL",
            display_name="Sensor Survival / Life",
            domain="EFFICACY",
            allowed_stat_types=["PERCENT"],
            extraction_instructions="Extract sensor survival rates or functional life percentage over time.",
        ),
        MeasureDefinition(
            short_name="SERIOUS_ADVERSE_EVENT",
            display_name="Serious Adverse Events",
            domain="SAFETY",
            allowed_stat_types=["COUNT", "PERCENT"],
            extraction_instructions="Extract serious adverse event (SAE) counts or rates.",
        ),
        # Cardiac Resuscitation / Arrest Measures
        MeasureDefinition(
            short_name="CARDIAC_DEATH",
            display_name="Cardiac Death",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT"],
            extraction_instructions="Extract cardiac-related death rates or counts.",
        ),
        MeasureDefinition(
            short_name="NEUROLOGICAL_ISCHEMIC_EVENT",
            display_name="Neurological Ischemic Event",
            domain="SAFETY",
            allowed_stat_types=["PERCENT", "COUNT"],
            extraction_instructions="Extract neurological ischemic events or stroke rates or counts.",
        ),
        MeasureDefinition(
            short_name="VF_DURATION",
            display_name="Ventricular Fibrillation Duration",
            domain="EFFICACY",
            allowed_stat_types=["COUNT", "MEAN", "MEDIAN"],
            extraction_instructions="Extract ventricular fibrillation (VF) duration times (e.g. in seconds or minutes).",
        ),
        MeasureDefinition(
            short_name="SURVIVAL_TO_DISCHARGE",
            display_name="Survival to Hospital Discharge",
            domain="EFFICACY",
            allowed_stat_types=["COUNT", "PERCENT"],
            extraction_instructions="Extract rates or counts of patients surviving to hospital discharge.",
        ),
        MeasureDefinition(
            short_name="LEFT_VENTRICULAR_FUNCTION_NORMAL_AT_DISCHARGE",
            display_name="Normal LV Function at Discharge",
            domain="EFFICACY",
            allowed_stat_types=["COUNT", "PERCENT"],
            extraction_instructions="Extract rates or counts of patients with normal left ventricular function at hospital discharge.",
        ),
    ]


def load_study_arms_from_excel(xlsx_path: str, article_id: str):
    """Load pre-defined study arms for a specific article from the Excel ground-truth."""
    import pandas as pd
    from outcome_extraction.models.study_arms import StudyArm

    try:
        df = pd.read_excel(xlsx_path, sheet_name="all_pdfs_outcome_measures")
        df["article_id"] = df["article_id"].ffill()
        df_art = df[df["article_id"] == article_id]
        unique_arms = df_art["study_arm"].dropna().unique()

        arms = []
        for idx, arm_name in enumerate(unique_arms, start=1):
            arms.append(StudyArm(arm_number=idx, arm_name=str(arm_name)))
        return arms if arms else None
    except Exception as e:
        logger.warning(f"Could not load study arms for {article_id} from Excel: {e}")
        return None


def main():
    # Verify API key is set
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY not set. Copy .env.example to .env and add your key.")
        return

    # Find PDFs
    pdf_dir = Path("data/pdfs")
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error(f"No PDFs found in {pdf_dir}")
        return

    logger.info(f"Found {len(pdf_files)} PDFs to process")

    # Get measure definitions
    measure_definitions = get_measure_definitions()
    logger.info(f"Extracting {len(measure_definitions)} measure types")

    # Initialize ExtractionService
    from langchain_google_genai import ChatGoogleGenerativeAI
    from outcome_extraction.services.llm_service import LLMService
    from outcome_extraction.services.extraction_service import ExtractionService

    # Use standard gemini-2.5-flash as default, or any model specified by API key environment
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0, google_api_key=api_key)
    llm_service = LLMService(llm)
    extraction_service = ExtractionService(llm_service)

    # Save/load output setup
    output_path = "extraction_output.json"
    all_results = {}
    if Path(output_path).exists():
        try:
            with open(output_path, "r") as f:
                all_results = json.load(f)
            logger.info(f"Loaded {len(all_results)} cached file results from {output_path}")
        except Exception as e:
            logger.warning(f"Could not load cached results: {e}")

    # Process each PDF
    for pdf_path in pdf_files:
        if pdf_path.name in all_results and isinstance(all_results[pdf_path.name], list) and len(all_results[pdf_path.name]) > 0:
            logger.info(f"Processing: {pdf_path.name} -> SKIPPED (already extracted {len(all_results[pdf_path.name])} results)")
            continue

        logger.info(f"Processing: {pdf_path.name}")
        try:
            # Dynamically pre-load known study arms to improve extraction quality
            study_arms = load_study_arms_from_excel("data/ground_truth.xlsx", pdf_path.name)
            if study_arms:
                logger.info(f"  -> Pre-loaded {len(study_arms)} study arms: {[a.arm_name for a in study_arms]}")
            
            # Execute the extraction
            results = extraction_service.extract_measures(str(pdf_path), measure_definitions, study_arms)
            results_dicts = []
            for r in results:
                d = r.model_dump()
                # Align empty categorical fields with Pandas' 'nan' to pass evaluation matching
                for field in ["dispersion_type", "p_operator", "timepoint_unit"]:
                    if d.get(field) is None:
                        d[field] = "nan"
                results_dicts.append(d)
            all_results[pdf_path.name] = results_dicts
            logger.info(f"  -> Extracted {len(all_results[pdf_path.name])} results")
            
            # Save progress incrementally after each successful extraction
            with open(output_path, "w") as f:
                json.dump(all_results, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"  -> Failed: {e}")
            all_results[pdf_path.name] = []

    total = sum(len(v) for v in all_results.values() if isinstance(v, list))
    logger.info(f"Done! {total} total results saved to {output_path}")
    logger.info("Run `python scripts/evaluate.py` to check accuracy.")


if __name__ == "__main__":
    main()

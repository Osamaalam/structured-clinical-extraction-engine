"""Extraction service — orchestrates the full PDF-to-MeasureResult pipeline.

TODO: Implement the ExtractionService class.

This service ties everything together:
1. PDFService extracts text from the PDF
2. TextProcessor cleans the text
3. build_extraction_prompt creates the LLM prompt
4. LLMService sends the prompt and parses JSON
5. ParserService validates the response into MeasureResult objects
"""

import logging
from typing import List, Optional

from ..config.prompts import build_extraction_prompt
from ..models.measure_definition import MeasureDefinition
from ..models.measure_result import MeasureResult
from ..models.study_arms import StudyArm
from ..utilities.text_processing import TextProcessor
from .llm_service import LLMService
from .parser_service import ParserService
from .pdf_service import PDFService

logger = logging.getLogger(__name__)


class ExtractionService:
    """Orchestrates structured outcome measure extraction from clinical trial PDFs."""

    def __init__(
        self,
        llm_service: LLMService,
        pdf_service: Optional[PDFService] = None,
        text_processor: Optional[TextProcessor] = None,
        parser_service: Optional[ParserService] = None,
    ):
        """Initialize with dependencies.

        Args:
            llm_service: Configured LLMService instance.
            pdf_service: Optional PDFService instance.
            text_processor: Optional TextProcessor instance.
            parser_service: Optional ParserService instance.
        """
        self.llm_service = llm_service
        self.pdf_service = pdf_service or PDFService()
        self.text_processor = text_processor or TextProcessor()
        self.parser_service = parser_service or ParserService()
        logger.info("ExtractionService initialized with all dependencies.")

    def extract_measures(
        self,
        pdf_path: str,
        measure_definitions: List[MeasureDefinition],
        study_arms: Optional[List[StudyArm]] = None,
    ) -> List[MeasureResult]:
        """Extract structured outcome measures from a clinical trial PDF.

        This is the main entry point. It should:
        1. Validate the PDF exists
        2. Extract text via PDFService
        3. Clean text via TextProcessor
        4. Build the prompt via build_extraction_prompt
        5. Send to LLM via LLMService.invoke_and_parse_json
        6. Parse response via ParserService.parse_results
        7. Return list of MeasureResult objects

        Args:
            pdf_path: Path to the clinical trial PDF.
            measure_definitions: List of measures to extract.
            study_arms: Optional known study arms.

        Returns:
            List of MeasureResult objects extracted from the PDF.
            Returns empty list on failure (never raises).
        """
        logger.info(f"Starting extraction on {pdf_path} for {len(measure_definitions)} measures.")
        try:
            # 1. Validate PDF exists and is readable
            if not self.pdf_service.validate_pdf(pdf_path):
                logger.error(f"Invalid or missing PDF file: {pdf_path}")
                return []

            # 2. Extract text via PDFService
            raw_text = self.pdf_service.extract_text(pdf_path)
            if not raw_text or not raw_text.strip():
                logger.warning(f"No text content could be extracted from {pdf_path}")
                return []

            # 3. Clean text via TextProcessor
            cleaned_text = self.text_processor.clean_text(raw_text)
            logger.info(f"Extracted and cleaned {len(cleaned_text)} characters of text from PDF.")

            # 4. Build prompt via build_extraction_prompt
            prompt = build_extraction_prompt(
                article_text=cleaned_text,
                measure_definitions=measure_definitions,
                study_arms=study_arms,
            )

            # 5. Send to LLM via LLMService.invoke_and_parse_json with robust retries
            logger.info("Sending prompt to LLM...")
            raw_json = None
            max_retries = 3
            import time
            for attempt in range(1, max_retries + 1):
                try:
                    raw_json = self.llm_service.invoke_and_parse_json(prompt)
                    if raw_json:
                        break
                    else:
                        logger.warning(f"LLM returned empty JSON on attempt {attempt}/{max_retries}.")
                except Exception as ex:
                    logger.warning(f"LLM call failed on attempt {attempt}/{max_retries}: {ex}")
                if attempt < max_retries:
                    time.sleep(5)  # Wait 5 seconds before retrying

            if not raw_json:
                logger.warning(f"LLM returned empty or unparseable JSON for {pdf_path} after {max_retries} attempts.")
                return []

            # Normalize single dict output into list if necessary
            if isinstance(raw_json, dict):
                raw_json = [raw_json]

            logger.info(f"LLM returned {len(raw_json)} raw records. Parsing and validating...")

            # 6. Parse response via ParserService.parse_results
            validated_results = self.parser_service.parse_results(raw_json, measure_definitions)
            logger.info(f"Extracted and validated {len(validated_results)} outcome records from {pdf_path}.")
            
            return validated_results

        except Exception as e:
            logger.exception(f"Unexpected error during extraction pipeline for {pdf_path}: {e}")
            return []

from unittest.mock import MagicMock, patch
import pytest
from outcome_extraction.services.extraction_service import ExtractionService
from outcome_extraction.config.prompts import build_extraction_prompt


class TestExtractionService:
    """Tests for ExtractionService."""

    def test_prompt_generation_contains_critical_sections(self, sample_measure_definitions, sample_study_arms):
        """Verify build_extraction_prompt outputs key measures and study arm descriptions."""
        article_text = "Clinical trial results content."
        prompt = build_extraction_prompt(article_text, sample_measure_definitions, sample_study_arms)
        
        # Verify the prompt is populated with target measures
        assert "MACE" in prompt
        assert "TLR" in prompt
        assert "STENT_THROMBOSIS" in prompt
        
        # Verify study arms are included
        assert "Treatment Group" in prompt
        assert "Control Group" in prompt
        assert "N=200" in prompt
        
        # Verify exact target article text is embedded
        assert article_text in prompt
        
        # Verify JSON instructions are present
        assert "```json" in prompt

    @patch("outcome_extraction.services.extraction_service.PDFService")
    @patch("outcome_extraction.services.extraction_service.TextProcessor")
    @patch("outcome_extraction.services.extraction_service.ParserService")
    def test_pipeline_orchestration_wiring(
        self, mock_parser_cls, mock_processor_cls, mock_pdf_cls, sample_measure_definitions
    ):
        """Test that ExtractionService correctly chains all sub-services together in the pipeline."""
        # Setup mock instances
        mock_pdf = mock_pdf_cls.return_value
        mock_processor = mock_processor_cls.return_value
        mock_parser = mock_parser_cls.return_value
        mock_llm = MagicMock()

        # Set return values for each stage of the pipeline
        mock_pdf.validate_pdf.return_value = True
        mock_pdf.extract_text.return_value = "Page 1 Raw Text. Page 2 Raw Text."
        mock_processor.clean_text.return_value = "Cleaned Page 1 and 2 Text."
        mock_llm.invoke_and_parse_json.return_value = [{"measure_definition_short_name": "MACE", "stat_type": "OR"}]
        mock_parser.parse_results.return_value = [MagicMock()]

        # Initialize and invoke orchestrator
        service = ExtractionService(
            llm_service=mock_llm,
            pdf_service=mock_pdf,
            text_processor=mock_processor,
            parser_service=mock_parser,
        )
        
        results = service.extract_measures("dummy.pdf", sample_measure_definitions)

        # Assert correct sequence of interactions
        mock_pdf.validate_pdf.assert_called_once_with("dummy.pdf")
        mock_pdf.extract_text.assert_called_once_with("dummy.pdf")
        mock_processor.clean_text.assert_called_once_with("Page 1 Raw Text. Page 2 Raw Text.")
        mock_llm.invoke_and_parse_json.assert_called_once()
        mock_parser.parse_results.assert_called_once_with(
            [{"measure_definition_short_name": "MACE", "stat_type": "OR"}], sample_measure_definitions
        )
        assert len(results) == 1

    @patch("outcome_extraction.services.extraction_service.PDFService")
    def test_pipeline_graceful_error_handling(self, mock_pdf_cls, sample_measure_definitions):
        """Test that ExtractionService handles missing files and failures gracefully without raising."""
        mock_pdf = mock_pdf_cls.return_value
        mock_llm = MagicMock()

        # Scenario 1: PDF is invalid or missing
        mock_pdf.validate_pdf.return_value = False
        service = ExtractionService(llm_service=mock_llm, pdf_service=mock_pdf)
        results = service.extract_measures("missing.pdf", sample_measure_definitions)
        assert results == []

        # Scenario 2: Extraction throws exception
        mock_pdf.validate_pdf.return_value = True
        mock_pdf.extract_text.side_effect = RuntimeError("PDF read failure")
        results = service.extract_measures("corrupt.pdf", sample_measure_definitions)
        assert results == []

        # Scenario 3: LLM returns null/empty results
        mock_pdf.extract_text.side_effect = None
        mock_pdf.extract_text.return_value = "Valid text."
        mock_llm.invoke_and_parse_json.return_value = None
        results = service.extract_measures("empty_llm.pdf", sample_measure_definitions)
        assert results == []

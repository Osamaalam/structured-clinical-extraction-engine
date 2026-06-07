"""PDF service for extracting text from clinical trial PDFs.

This is a PROVIDED component — you should not need to modify this file.
Use it via: PDFService().extract_text(pdf_path)
"""

import logging
from pathlib import Path
from typing import List, Optional

import pdfplumber

logger = logging.getLogger(__name__)


class PDFService:
    """Service for extracting text from PDF documents."""

    def extract_text(self, pdf_path: str) -> str:
        """Extract all text from a PDF with medical-document-optimized settings.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Full text content of the PDF.

        Raises:
            FileNotFoundError: If PDF does not exist.
            Exception: If PDF cannot be read.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        raw_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"Extracting text from {path.name} ({len(pdf.pages)} pages)...")
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=1, y_tolerance=3)
                if page_text:
                    raw_text += page_text + "\n"

        logger.info(f"Extracted {len(raw_text)} characters from {path.name}")
        return raw_text

    def extract_text_by_pages(self, pdf_path: str, start_page: int = 0, end_page: Optional[int] = None) -> List[str]:
        """Extract text from specific pages.

        Args:
            pdf_path: Path to the PDF file.
            start_page: First page index (0-based).
            end_page: Last page index (exclusive). Defaults to all pages.

        Returns:
            List of text strings, one per page.
        """
        pages_text = []
        with pdfplumber.open(pdf_path) as pdf:
            end = end_page if end_page else len(pdf.pages)
            for i in range(start_page, min(end, len(pdf.pages))):
                page_text = pdf.pages[i].extract_text(x_tolerance=1, y_tolerance=3)
                pages_text.append(page_text or "")
        return pages_text

    def validate_pdf(self, pdf_path: str) -> bool:
        """Check if a file is a readable PDF.

        Args:
            pdf_path: Path to validate.

        Returns:
            True if the file is a valid, readable PDF.
        """
        try:
            path = Path(pdf_path)
            if not path.exists() or path.suffix.lower() != ".pdf":
                return False
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    return False
                pdf.pages[0].extract_text()
            return True
        except Exception:
            return False

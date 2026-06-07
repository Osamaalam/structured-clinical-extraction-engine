"""Text processing utilities.

This is a PROVIDED component — you should not need to modify this file.
"""

import re
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter


class TextProcessor:
    """Utility class for text processing operations."""

    def clean_text(self, text: str) -> str:
        """Clean text by normalizing whitespace."""
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def chunk_text(self, text: str, chunk_size: int = 4000, chunk_overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for processing.

        Args:
            text: Text to split.
            chunk_size: Maximum characters per chunk.
            chunk_overlap: Characters to overlap between chunks.

        Returns:
            List of text chunks.
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""],
            length_function=len,
            is_separator_regex=False,
        )
        return splitter.split_text(text)

    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison (lowercase, no punctuation)."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def extract_sentences(self, text: str) -> List[str]:
        """Extract individual sentences from text."""
        sentences = re.split(r"[.!?]+", text)
        return [s.strip() for s in sentences if s.strip()]

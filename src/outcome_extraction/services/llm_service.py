"""LLM service for interacting with language models.

This is a PROVIDED component — you should not need to modify this file.
It handles LLM invocation and basic JSON response parsing.

Usage:
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)
    service = LLMService(llm)
    response_text = service.invoke(prompt_string)
    parsed_json = service.invoke_and_parse_json(prompt_string)
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


class LLMService:
    """Wrapper around a LangChain LLM with JSON parsing helpers."""

    def __init__(self, llm_instance: BaseLanguageModel):
        """Initialize with a LangChain LLM.

        Args:
            llm_instance: Any LangChain-compatible LLM (Gemini, Claude, GPT, etc.)

        Raises:
            TypeError: If llm_instance is not a BaseLanguageModel.
        """
        if not isinstance(llm_instance, BaseLanguageModel):
            raise TypeError("llm_instance must be a LangChain BaseLanguageModel")
        self.llm = llm_instance
        self.model_name = llm_instance.__class__.__name__
        logger.info(f"LLMService initialized with {self.model_name}")

    def invoke(self, prompt: str) -> str:
        """Send a prompt to the LLM and return the raw text response.

        Args:
            prompt: The prompt string to send.

        Returns:
            The LLM's response as a string.
        """
        response = self.llm.invoke(prompt)
        return self._get_content(response)

    def invoke_and_parse_json(self, prompt: str) -> Optional[Union[Dict, List]]:
        """Send a prompt and parse the response as JSON.

        Handles common LLM response patterns:
        - JSON wrapped in ```json ... ``` code blocks
        - Raw JSON objects or arrays
        - JSON embedded in surrounding text

        Args:
            prompt: The prompt string to send.

        Returns:
            Parsed JSON as a dict or list, or None if parsing fails.
        """
        raw = self.invoke(prompt)
        return self.parse_json_response(raw)

    def parse_json_response(self, response_text: str) -> Optional[Union[Dict, List]]:
        """Parse JSON from an LLM response string.

        Args:
            response_text: Raw text from the LLM.

        Returns:
            Parsed JSON, or None if no valid JSON found.
        """
        if not response_text:
            return None

        # Try markdown code block first
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", response_text, re.DOTALL | re.IGNORECASE)
        json_str = match.group(1).strip() if match else response_text.strip()

        # Try to find JSON array
        if "[" in json_str:
            first_bracket = json_str.find("[")
            last_bracket = json_str.rfind("]")
            if first_bracket != -1 and last_bracket > first_bracket:
                try:
                    return json.loads(json_str[first_bracket : last_bracket + 1])
                except json.JSONDecodeError:
                    pass

        # Try to find JSON object
        first_brace = json_str.find("{")
        last_brace = json_str.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            try:
                return json.loads(json_str[first_brace : last_brace + 1])
            except json.JSONDecodeError:
                pass

        # Last resort: try the whole string
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from LLM response: {response_text[:200]}...")
            return None

    @staticmethod
    def _get_content(response: Union[str, BaseMessage]) -> str:
        """Extract string content from an LLM response object."""
        if hasattr(response, "content") and isinstance(response.content, str):
            return response.content
        if isinstance(response, str):
            return response
        return str(response)

"""
Input sanitization utilities to prevent XSS and other injection attacks.
"""
import re
from typing import Any, Optional


def sanitize_user_input(text: Optional[str]) -> Optional[str]:
    """
    Sanitize user input to prevent XSS attacks.
    
    Removes HTML tags and normalizes whitespace while preserving
    the meaningful content of user input.
    
    Args:
        text: Raw user input text
        
    Returns:
        Sanitized text safe for storage and display
    """
    if text is None:
        return None
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Normalize whitespace (keep newlines for text areas)
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def sanitize_for_csv(value: Any) -> Optional[str]:
    """
    Sanitize a CSV cell value to prevent formula injection.

    Prefixes potentially dangerous characters with a single quote so
    Excel / LibreOffice / Google Sheets render them as text instead of
    executing them as formulas. Accepts any type — non-string values
    are coerced via str() and passed through unchanged unless they
    happen to start with a dangerous character (e.g., a negative
    number stringified as "-5" gets the prefix and renders as text).

    Args:
        value: Cell value of any type. None returns None.

    Returns:
        Sanitized string safe for CSV export, or None if input was None.
    """
    if value is None:
        return None

    text = value if isinstance(value, str) else str(value)

    # Prefix potentially dangerous characters that could be interpreted as formulas.
    # Excel formula triggers: =, +, -, @. Tab/CR can break out of cells.
    dangerous_prefixes = ('=', '+', '-', '@', '\t', '\r')
    if text.startswith(dangerous_prefixes):
        text = "'" + text

    return text

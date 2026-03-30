"""
Input sanitization utilities to prevent XSS and other injection attacks.
"""
import re
from typing import Optional


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


def sanitize_for_csv(text: Optional[str]) -> Optional[str]:
    """
    Sanitize text for CSV export to prevent formula injection.
    
    Prefixes potentially dangerous characters to prevent Excel/LibreOffice
    from executing them as formulas.
    
    Args:
        text: Text to be included in CSV export
        
    Returns:
        Sanitized text safe for CSV export
    """
    if text is None:
        return None
    
    # Prefix potentially dangerous characters that could be interpreted as formulas
    dangerous_prefixes = ('=', '+', '-', '@', '\t', '\r')
    if text.startswith(dangerous_prefixes):
        text = "'" + text
    
    return text

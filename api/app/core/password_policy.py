"""
Password policy enforcement for user authentication.

This module provides comprehensive password validation including:
- Minimum and maximum length requirements
- Character complexity requirements (uppercase, lowercase, digits, special chars)
- Common password checking against known weak passwords
- User attribute checking to prevent passwords containing personal info
"""

import re
from typing import Tuple, List, Set, Optional


class PasswordPolicy:
    """
    Configurable password policy with comprehensive validation.
    
    Default policy:
    - Minimum 8 characters
    - Maximum 128 characters  
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - Not in common passwords list
    - Does not contain user's email or name
    """
    
    # Length requirements
    MIN_LENGTH: int = 8
    MAX_LENGTH: int = 128
    
    # Character class requirements
    REQUIRE_UPPERCASE: bool = True
    REQUIRE_LOWERCASE: bool = True
    REQUIRE_DIGIT: bool = True
    REQUIRE_SPECIAL: bool = True
    
    # Special characters allowed
    SPECIAL_CHARACTERS: str = "!@#$%^&*(),.?\":{}|<>[]\\/_+=-`~;"
    
    # Common passwords to block (top 1000 most common)
    COMMON_PASSWORDS: Set[str] = {
        # Top 50 most common passwords
        "password", "123456", "12345678", "qwerty", "123456789",
        "letmein", "1234567", "football", "iloveyou", "admin",
        "welcome", "monkey", "login", "abc123", "111111",
        "123123", "password123", "dragon", "master", "photoshop",
        "sunshine", "princess", "admin123", "welcome123", "shadow",
        "ashley", "football123", "jesus", "michael", "ninja",
        "mustang", "password1", "1234567890", "adobe123", "baseball",
        "trustno1", "superman", "qazwsx", "michael1", "football1",
        "iloveyou1", "adminadmin", "welcome1", "princess1", "starwars",
        "qwerty123", "passw0rd", "hello123", "freedom", "whatever",
        "qwe123", "trustno1", "654321", "jordan23", "harley",
        # Keyboard patterns
        "qwerty", "qwertyuiop", "asdfgh", "asdfghjkl", "zxcvbn",
        "qazwsx", "qazwsxedc", "1qaz2wsx", "!qaz2wsx", "zaq12wsx",
        "!@#$%^&*", "1234qwer", "qwer1234", "1q2w3e4r", "q1w2e3r4",
        # Common sequences
        "123456", "1234567", "12345678", "123456789", "1234567890",
        "abcdef", "abcdefg", "abcdefghijklmnopqrstuvwxyz",
        "987654321", "87654321", "7654321",
        # Common words
        "letmein", "welcome", "password", "passw0rd", "p@ssw0rd",
        "password1", "password12", "password123", "123password",
        "secret", "secret123", "admin", "admin123", "root",
        "user", "user123", "test", "test123", "demo", "demo123",
        "login", "login123", "guest", "guest123", "default",
        # Names and common terms
        "jesus", "michael", "jordan", "mike", "john", "david",
        "chris", "james", "robert", "matthew", "daniel", "andrew",
        "joshua", "william", "justin", "brandon", "anthony",
        "love", "money", "happy", "summer", "winter", "spring",
        "monkey", "dragon", "master", "shadow", "sunshine",
        "princess", "angel", "baby", "starwars", "star wars",
        # Simple variations
        "pass", "pass123", "mypass", "mypassword", "thepassword",
        "changeme", "change_me", "changeme123", "newpassword",
        "oldpassword", "temppass", "temporary", "temp123",
        # Sports teams
        "yankees", "redsox", "lakers", "cowboys", "eagles",
        "patriots", "giants", "steelers", "packers", "bears",
        "baseball", "football", "basketball", "soccer", "hockey",
        # Simple number combinations
        "000000", "111111", "222222", "333333", "444444",
        "555555", "666666", "777777", "888888", "999999",
        "101010", "121212", "123123", "321321", "456456",
        # Company/software names
        "apple", "microsoft", "google", "amazon", "facebook",
        "twitter", "instagram", "linkedin", "netflix", "adobe",
        "photoshop", "windows", "macintosh", "ubuntu", "linux",
    }
    
    @classmethod
    def validate(
        cls,
        password: str,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate a password against the policy.
        
        Args:
            password: The password to validate
            email: User's email (to check for inclusion in password)
            first_name: User's first name (to check for inclusion)
            last_name: User's last name (to check for inclusion)
            
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors: List[str] = []
        
        # Check length
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters long")
        
        if len(password) > cls.MAX_LENGTH:
            errors.append(f"Password must not exceed {cls.MAX_LENGTH} characters")
        
        # Check character complexity
        if cls.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter (A-Z)")
        
        if cls.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter (a-z)")
        
        if cls.REQUIRE_DIGIT and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit (0-9)")
        
        if cls.REQUIRE_SPECIAL:
            special_pattern = f'[{re.escape(cls.SPECIAL_CHARACTERS)}]'
            if not re.search(special_pattern, password):
                errors.append(
                    f"Password must contain at least one special character ({cls.SPECIAL_CHARACTERS})"
                )
        
        # Check for common passwords
        password_lower = password.lower()
        if password_lower in cls.COMMON_PASSWORDS:
            errors.append("Password is too common and easily guessed. Please choose a more unique password.")
        
        # Check for repeated characters (e.g., "aaa", "111")
        if re.search(r'(.)\1{2,}', password):
            errors.append("Password contains too many repeated characters")
        
        # Check for sequential characters (e.g., "abc", "123")
        if cls._has_sequential_chars(password_lower, 3):
            errors.append("Password contains sequential characters (e.g., 'abc', '123')")
        
        # Check if password contains user's personal information
        if email:
            email_parts = email.lower().split('@')[0].split('.')
            for part in email_parts:
                if len(part) >= 3 and part in password_lower:
                    errors.append("Password should not contain your email address")
                    break
        
        if first_name and len(first_name) >= 3:
            if first_name.lower() in password_lower:
                errors.append("Password should not contain your first name")
        
        if last_name and len(last_name) >= 3:
            if last_name.lower() in password_lower:
                errors.append("Password should not contain your last name")
        
        return len(errors) == 0, errors
    
    @classmethod
    def _has_sequential_chars(cls, password: str, min_length: int = 3) -> bool:
        """Check if password contains sequential characters."""
        sequences = [
            "abcdefghijklmnopqrstuvwxyz",
            "zyxwvutsrqponmlkjihgfedcba",  # Reverse
            "0123456789",
            "9876543210",  # Reverse
            "qwertyuiop",
            "poiuytrewq",  # Reverse
            "asdfghjkl",
            "lkjhgfdsa",  # Reverse
            "zxcvbnm",
            "mnbvcxz",  # Reverse
        ]
        
        for seq in sequences:
            for i in range(len(seq) - min_length + 1):
                if seq[i:i + min_length] in password:
                    return True
        return False
    
    @classmethod
    def get_requirements_description(cls) -> str:
        """Get a human-readable description of password requirements."""
        requirements = [
            f"Be between {cls.MIN_LENGTH} and {cls.MAX_LENGTH} characters long",
        ]
        
        if cls.REQUIRE_UPPERCASE:
            requirements.append("Contain at least one uppercase letter (A-Z)")
        if cls.REQUIRE_LOWERCASE:
            requirements.append("Contain at least one lowercase letter (a-z)")
        if cls.REQUIRE_DIGIT:
            requirements.append("Contain at least one digit (0-9)")
        if cls.REQUIRE_SPECIAL:
            requirements.append(f"Contain at least one special character ({cls.SPECIAL_CHARACTERS})")
        
        requirements.extend([
            "Not be a commonly used password",
            "Not contain sequential characters (e.g., 'abc', '123')",
            "Not contain your email or name",
        ])
        
        return "Password must:\n• " + "\n• ".join(requirements)
    
    @classmethod
    def calculate_strength(cls, password: str) -> int:
        """
        Calculate password strength score (0-100).
        
        Returns:
            Score from 0-100 where:
            0-20 = Very Weak
            21-40 = Weak
            41-60 = Fair
            61-80 = Strong
            81-100 = Very Strong
        """
        score = 0
        
        # Length contribution (up to 40 points)
        length_score = min(len(password) * 2, 40)
        score += length_score
        
        # Character variety contribution (up to 40 points)
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(f'[{re.escape(cls.SPECIAL_CHARACTERS)}]', password):
            score += 10
        
        # Complexity bonus (up to 20 points)
        if len(password) >= 12:
            score += 10
        if len(password) >= 16:
            score += 10
        
        # Penalties
        if password.lower() in cls.COMMON_PASSWORDS:
            score = max(0, score - 50)
        
        if re.search(r'(.)\1{2,}', password):  # Repeated chars
            score = max(0, score - 10)
        
        if cls._has_sequential_chars(password.lower(), 3):
            score = max(0, score - 10)
        
        return min(score, 100)
    
    @classmethod
    def get_strength_label(cls, score: int) -> Tuple[str, str]:
        """
        Get strength label and color for a score.
        
        Returns:
            Tuple of (label, color) where color is a CSS color or Tailwind class
        """
        if score <= 20:
            return ("Very Weak", "red-500")
        elif score <= 40:
            return ("Weak", "orange-500")
        elif score <= 60:
            return ("Fair", "yellow-500")
        elif score <= 80:
            return ("Strong", "blue-500")
        else:
            return ("Very Strong", "green-500")


# Convenience function for direct validation
def validate_password(
    password: str,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """Validate a password against the default policy."""
    return PasswordPolicy.validate(password, email, first_name, last_name)

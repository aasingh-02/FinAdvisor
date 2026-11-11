"""
app/utils/validators.py
───────────────────────
Shared input validation helpers.
Financial validators will be expanded in Phase 2.
"""

import re


def is_valid_email(email: str) -> bool:
    """Basic email format guard (Pydantic EmailStr is the primary check)."""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email))

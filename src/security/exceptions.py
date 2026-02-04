"""
Jett Security Exceptions

Custom error types for security boundary violations.
Every denial is a distinct exception type for precise handling and audit logging.
"""


class SecurityError(Exception):
    """Base exception for all security boundary violations."""
    pass


class AllowlistError(SecurityError):
    """Raised when an action or container is not in the allowlist."""
    pass


class RateLimitError(SecurityError):
    """Raised when the per-minute operation limit is exceeded."""
    pass


class AuditError(SecurityError):
    """Raised when the audit log cannot be written."""
    pass

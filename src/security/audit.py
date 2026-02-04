"""
Jett Audit Logger - Immutable, append-only security logging

Every privileged action is logged with: timestamp, status, action, params, error.
Secrets are redacted before writing. Logs are append-only — no edits, no deletes.

Format:
    2024-01-15T10:30:00Z|ATTEMPT|execute|{'action': 'restart', 'container': 'n8n'}
    2024-01-15T10:30:01Z|SUCCESS|execute|{'action': 'restart', 'container': 'n8n'}
"""

import re
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from src.security.exceptions import AuditError

# Patterns that look like secrets — redact before logging
_SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]+"),          # Claude API keys
    re.compile(r"ptr_[A-Za-z0-9_-]+"),              # Portainer tokens
    re.compile(r"(?i)password['\"]?\s*[:=]\s*['\"]?[^\s'\",}]+"),  # password=value
    re.compile(r"(?i)token['\"]?\s*[:=]\s*['\"]?[^\s'\",}]+"),     # token=value
    re.compile(r"(?i)secret['\"]?\s*[:=]\s*['\"]?[^\s'\",}]+"),    # secret=value
]


def redact_secrets(text: str) -> str:
    """Replace any secret-looking patterns with [REDACTED]."""
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


class AuditLogger:
    """Append-only audit logger for security events."""

    def __init__(self, log_dir: str | Path | None = None):
        """
        Initialize the audit logger.

        Args:
            log_dir: Directory for audit log files. Defaults to ./logs/jett/.
        """
        if log_dir is None:
            log_dir = Path("logs/jett")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "audit.log"

    def log(self, status: str, action: str, params: str, error: str | None = None) -> None:
        """
        Write an audit entry. Append-only — never overwrites.

        Args:
            status: ATTEMPT, SUCCESS, DENIED, or ERROR
            action: The operation name
            params: String representation of parameters (will be redacted)
            error: Error message if applicable
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        params = redact_secrets(str(params))

        parts = [timestamp, status, action, params]
        if error:
            parts.append(redact_secrets(str(error)))

        line = "|".join(parts)

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as e:
            raise AuditError(f"Failed to write audit log: {e}") from e

    def get_recent(self, n: int = 10) -> list[str]:
        """
        Return the last N audit log entries.

        Args:
            n: Number of recent entries to return.

        Returns:
            List of log lines, most recent last.
        """
        if not self.log_file.exists():
            return []

        with open(self.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        return [line.strip() for line in lines[-n:]]


def audit_log(logger: AuditLogger):
    """
    Decorator factory for audit logging.

    Wraps a function to log ATTEMPT before execution and
    SUCCESS/DENIED/ERROR after, depending on the outcome.

    Args:
        logger: AuditLogger instance to write to.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            action = func.__name__
            params = str(kwargs) if kwargs else str(args[1:]) if len(args) > 1 else "{}"

            logger.log("ATTEMPT", action, params)

            try:
                result = func(*args, **kwargs)
                logger.log("SUCCESS", action, params)
                return result
            except PermissionError as e:
                logger.log("DENIED", action, params, error=str(e))
                raise
            except Exception as e:
                logger.log("ERROR", action, params, error=str(e))
                raise

        return wrapper
    return decorator

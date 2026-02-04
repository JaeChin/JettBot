"""
Jett Container Controller - Permission-gated Portainer API wrapper

All AI container operations go through this wrapper.
Validates against allowlists, enforces rate limits, and logs every action.

Usage:
    from src.security import ContainerController

    controller = ContainerController(dev_mode=True)
    result = controller.execute("restart", "n8n")
"""

import time
from pathlib import Path

from src.security.allowlist import ALLOWED_ACTIONS, ALLOWED_CONTAINERS
from src.security.audit import AuditLogger
from src.security.exceptions import AllowlistError, RateLimitError


class ContainerController:
    """
    Permission-gated container controller.

    Every operation passes through:
    1. Action allowlist check
    2. Container allowlist check
    3. Rate limit check
    4. Audit logging (before and after)
    5. Execution (Portainer API or dev_mode stub)
    """

    def __init__(
        self,
        dev_mode: bool = True,
        rate_limit: int = 10,
        audit_dir: str | Path | None = None,
    ):
        """
        Args:
            dev_mode: If True, stub Portainer calls. If False, make real API calls.
            rate_limit: Max privileged operations per minute.
            audit_dir: Directory for audit logs. Defaults to ./logs/jett/.
        """
        self.dev_mode = dev_mode
        self.rate_limit = rate_limit
        self.audit = AuditLogger(log_dir=audit_dir)
        self._operation_times: list[float] = []

    def execute(self, action: str, container: str, **kwargs) -> dict:
        """
        Main entry point for container operations.

        Args:
            action: Operation to perform (must be in ALLOWED_ACTIONS).
            container: Target container name (must be in ALLOWED_CONTAINERS).

        Returns:
            Dict with operation result.

        Raises:
            AllowlistError: If action or container is not permitted.
            RateLimitError: If rate limit is exceeded.
        """
        params = {"action": action, "container": container, **kwargs}

        # Log intent
        self.audit.log("ATTEMPT", "execute", str(params))

        try:
            # Validate
            self._validate_action(action)
            self._validate_container(container)
            self._check_rate_limit()

            # Execute
            result = self._execute_portainer(action, container, **kwargs)

            # Log success
            self.audit.log("SUCCESS", "execute", str(params))
            return result

        except (AllowlistError, RateLimitError) as e:
            self.audit.log("DENIED", "execute", str(params), error=str(e))
            raise

        except Exception as e:
            self.audit.log("ERROR", "execute", str(params), error=str(e))
            raise

    def _validate_action(self, action: str) -> None:
        """Check that the action is in the allowlist."""
        if action not in ALLOWED_ACTIONS:
            raise AllowlistError(
                f"Action '{action}' not in allowlist. "
                f"Allowed: {sorted(ALLOWED_ACTIONS)}"
            )

    def _validate_container(self, container: str) -> None:
        """Check that the container is in the allowlist."""
        if container not in ALLOWED_CONTAINERS:
            raise AllowlistError(
                f"Container '{container}' not in allowlist. "
                f"Allowed: {sorted(ALLOWED_CONTAINERS)}"
            )

    def _check_rate_limit(self) -> None:
        """Enforce sliding-window rate limit (operations per minute)."""
        now = time.time()

        # Prune operations older than 60 seconds
        self._operation_times = [
            t for t in self._operation_times if now - t < 60
        ]

        if len(self._operation_times) >= self.rate_limit:
            raise RateLimitError(
                f"Rate limit exceeded: {self.rate_limit} operations/minute. "
                f"Try again in {60 - (now - self._operation_times[0]):.0f}s."
            )

        self._operation_times.append(now)

    def _execute_portainer(self, action: str, container: str, **kwargs) -> dict:
        """
        Execute the operation via Portainer API.

        In dev_mode, returns a stub response.
        In production, makes real HTTP calls to Portainer.
        """
        if self.dev_mode:
            return {
                "status": "ok",
                "action": action,
                "container": container,
                "dev_mode": True,
                "message": f"[DEV] {action} on {container} — simulated success",
            }

        # Production: Portainer API calls go here
        # Will be implemented when VPS infrastructure is set up
        raise NotImplementedError("Production Portainer integration not yet implemented")

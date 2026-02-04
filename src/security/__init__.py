"""
Jett Security Module - Container permission boundaries

Defense-in-depth controls for AI container management:
- Explicit allowlists (frozenset, immutable)
- Rate limiting on privileged operations
- Immutable audit logging with secret redaction

Usage:
    from src.security import ContainerController

    controller = ContainerController(dev_mode=True)
    result = controller.execute("restart", "n8n")
"""

from src.security.wrapper import ContainerController

__all__ = ["ContainerController"]

"""
Jett Security Allowlists

Immutable sets of permitted containers and actions.
If it's not explicitly listed here, it's blocked.

These are frozensets — they cannot be modified at runtime.
"""

# Containers the AI is allowed to interact with
ALLOWED_CONTAINERS: frozenset[str] = frozenset([
    "n8n",
    "postgres",
    "qdrant",
    "redis",
])

# Operations the AI is allowed to perform
ALLOWED_ACTIONS: frozenset[str] = frozenset([
    "start",
    "stop",
    "restart",
    "logs",
    "status",
])

# Operations that are always blocked, regardless of container
BLOCKED_ACTIONS: frozenset[str] = frozenset([
    "create",
    "remove",
    "exec",
    "pull",
    "delete",
])


def is_allowed(action: str, container: str) -> bool:
    """Check if an action on a container is permitted."""
    return action in ALLOWED_ACTIONS and container in ALLOWED_CONTAINERS

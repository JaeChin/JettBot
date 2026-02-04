"""
Jett Security Demo - Interactive demonstration of permission boundaries

Demonstrates:
1. Valid operations succeed
2. Blocked actions are denied
3. Blocked containers are denied
4. Rate limiting triggers
5. Audit trail captures everything

Run:
    python demo_security.py
"""

import sys
import tempfile
from pathlib import Path

from src.security import ContainerController
from src.security.allowlist import ALLOWED_ACTIONS, ALLOWED_CONTAINERS
from src.security.exceptions import AllowlistError, RateLimitError


# ANSI colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def header(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{RESET}\n")


def pass_msg(msg: str) -> None:
    print(f"  {GREEN}[PASS]{RESET} {msg}")


def fail_msg(msg: str) -> None:
    print(f"  {RED}[FAIL]{RESET} {msg}")


def info_msg(msg: str) -> None:
    print(f"  {YELLOW}[INFO]{RESET} {msg}")


def demo_allowlists() -> None:
    header("1. ALLOWLISTS (Immutable frozensets)")
    info_msg(f"Allowed containers: {sorted(ALLOWED_CONTAINERS)}")
    info_msg(f"Allowed actions:    {sorted(ALLOWED_ACTIONS)}")
    info_msg(f"Type: {type(ALLOWED_CONTAINERS).__name__} (cannot be modified at runtime)")

    try:
        ALLOWED_CONTAINERS.add("malicious")
        fail_msg("frozenset was modified — this should never happen!")
    except AttributeError:
        pass_msg("Cannot add to frozenset — allowlist is immutable")


def demo_valid_operations(ctrl: ContainerController) -> None:
    header("2. VALID OPERATIONS (Should Succeed)")

    for action, container in [("restart", "n8n"), ("status", "postgres"), ("logs", "qdrant")]:
        result = ctrl.execute(action, container)
        pass_msg(f"{action} {container} -> {result['message']}")


def demo_blocked_actions(ctrl: ContainerController) -> None:
    header("3. BLOCKED ACTIONS (Should Be Denied)")

    blocked = [
        ("delete", "postgres", "Delete container"),
        ("exec", "n8n", "Execute command in container"),
        ("create", "evil", "Create new container"),
        ("pull", "n8n", "Pull image"),
    ]

    for action, container, description in blocked:
        try:
            ctrl.execute(action, container)
            fail_msg(f"{description} was allowed — SECURITY BREACH!")
        except AllowlistError:
            pass_msg(f"{description} -> DENIED (action '{action}' not in allowlist)")


def demo_blocked_containers(ctrl: ContainerController) -> None:
    header("4. BLOCKED CONTAINERS (Should Be Denied)")

    containers = ["crypto-miner", "reverse-shell", "data-exfil", "../../etc/passwd"]

    for container in containers:
        try:
            ctrl.execute("start", container)
            fail_msg(f"Container '{container}' was allowed — SECURITY BREACH!")
        except AllowlistError:
            pass_msg(f"start '{container}' -> DENIED (not in allowlist)")


def demo_rate_limiting() -> None:
    header("5. RATE LIMITING (3/minute for demo)")

    # Use a separate controller with low limit for demo
    with tempfile.TemporaryDirectory() as tmp:
        ctrl = ContainerController(dev_mode=True, rate_limit=3, audit_dir=tmp)

        for i in range(1, 4):
            result = ctrl.execute("status", "n8n")
            pass_msg(f"Request {i}/3 -> allowed")

        try:
            ctrl.execute("status", "n8n")
            fail_msg("Request 4/3 was allowed — rate limit broken!")
        except RateLimitError as e:
            pass_msg(f"Request 4/3 -> DENIED ({e})")


def demo_audit_trail(ctrl: ContainerController) -> None:
    header("6. AUDIT TRAIL (Immutable Log)")

    entries = ctrl.audit.get_recent(20)
    info_msg(f"Total entries from this session: {len(entries)}")
    print()

    for entry in entries:
        parts = entry.split("|")
        status = parts[1] if len(parts) > 1 else "?"
        if status == "SUCCESS":
            color = GREEN
        elif status == "DENIED":
            color = RED
        elif status == "ATTEMPT":
            color = YELLOW
        else:
            color = RESET
        print(f"    {color}{entry}{RESET}")


def main() -> None:
    header("JETT SECURITY BOUNDARIES DEMO")
    info_msg("dev_mode=True — no real Portainer calls")
    info_msg("All operations are logged to an immutable audit trail")

    # Create controller with temp directory for demo
    with tempfile.TemporaryDirectory() as tmp:
        ctrl = ContainerController(dev_mode=True, audit_dir=tmp)

        demo_allowlists()
        demo_valid_operations(ctrl)
        demo_blocked_actions(ctrl)
        demo_blocked_containers(ctrl)
        demo_rate_limiting()
        demo_audit_trail(ctrl)

    header("DEMO COMPLETE")

    # Summary
    print(f"  {BOLD}Defense in Depth:{RESET}")
    print(f"    1. Immutable allowlists (frozenset)")
    print(f"    2. Action validation before execution")
    print(f"    3. Container validation before execution")
    print(f"    4. Rate limiting (sliding window)")
    print(f"    5. Audit logging with secret redaction")
    print(f"    6. dev_mode isolation (no real API calls)")
    print()


if __name__ == "__main__":
    main()

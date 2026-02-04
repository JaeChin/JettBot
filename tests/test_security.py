"""
Tests for Jett security boundaries.

Proves that allowlists, rate limiting, audit logging,
and secret redaction work as specified.

Run:
    python -m pytest tests/test_security.py -v
"""

import time

import pytest

from src.security.allowlist import (
    ALLOWED_ACTIONS,
    ALLOWED_CONTAINERS,
    BLOCKED_ACTIONS,
    is_allowed,
)
from src.security.audit import AuditLogger, redact_secrets
from src.security.exceptions import AllowlistError, AuditError, RateLimitError, SecurityError
from src.security.wrapper import ContainerController


# --- Allowlist Tests ---

class TestAllowlist:
    def test_allowed_containers_is_frozenset(self):
        assert isinstance(ALLOWED_CONTAINERS, frozenset)

    def test_allowed_actions_is_frozenset(self):
        assert isinstance(ALLOWED_ACTIONS, frozenset)

    def test_frozenset_immutable(self):
        with pytest.raises(AttributeError):
            ALLOWED_CONTAINERS.add("malicious")

    def test_expected_containers(self):
        assert "n8n" in ALLOWED_CONTAINERS
        assert "postgres" in ALLOWED_CONTAINERS
        assert "qdrant" in ALLOWED_CONTAINERS
        assert "redis" in ALLOWED_CONTAINERS

    def test_expected_actions(self):
        assert "start" in ALLOWED_ACTIONS
        assert "stop" in ALLOWED_ACTIONS
        assert "restart" in ALLOWED_ACTIONS
        assert "logs" in ALLOWED_ACTIONS
        assert "status" in ALLOWED_ACTIONS

    def test_blocked_actions_exist(self):
        assert "create" in BLOCKED_ACTIONS
        assert "remove" in BLOCKED_ACTIONS
        assert "exec" in BLOCKED_ACTIONS

    def test_is_allowed_valid(self):
        assert is_allowed("restart", "n8n") is True

    def test_is_allowed_bad_action(self):
        assert is_allowed("delete", "n8n") is False

    def test_is_allowed_bad_container(self):
        assert is_allowed("restart", "malicious") is False


# --- Exception Tests ---

class TestExceptions:
    def test_hierarchy(self):
        assert issubclass(AllowlistError, SecurityError)
        assert issubclass(RateLimitError, SecurityError)
        assert issubclass(AuditError, SecurityError)
        assert issubclass(SecurityError, Exception)


# --- Audit Tests ---

class TestAudit:
    def test_log_creates_file(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        logger.log("ATTEMPT", "test_action", "{'key': 'value'}")
        assert (tmp_path / "audit.log").exists()

    def test_log_format(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        logger.log("SUCCESS", "execute", "{'action': 'restart', 'container': 'n8n'}")
        lines = logger.get_recent(1)
        assert len(lines) == 1
        parts = lines[0].split("|")
        assert len(parts) == 4
        assert parts[1] == "SUCCESS"
        assert parts[2] == "execute"

    def test_log_with_error(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        logger.log("DENIED", "execute", "{}", error="Not allowed")
        lines = logger.get_recent(1)
        parts = lines[0].split("|")
        assert len(parts) == 5
        assert parts[1] == "DENIED"
        assert parts[4] == "Not allowed"

    def test_log_append_only(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        logger.log("ATTEMPT", "first", "{}")
        logger.log("SUCCESS", "second", "{}")
        lines = logger.get_recent(10)
        assert len(lines) == 2

    def test_get_recent_limit(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        for i in range(20):
            logger.log("ATTEMPT", f"op_{i}", "{}")
        lines = logger.get_recent(5)
        assert len(lines) == 5
        assert "op_19" in lines[-1]

    def test_get_recent_empty(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        assert logger.get_recent(5) == []


# --- Secret Redaction Tests ---

class TestRedaction:
    def test_redact_claude_api_key(self):
        text = "key=sk-ant-api03-abc123XYZ"
        assert "sk-ant" not in redact_secrets(text)
        assert "[REDACTED]" in redact_secrets(text)

    def test_redact_portainer_token(self):
        text = "token=ptr_abc123"
        assert "ptr_" not in redact_secrets(text)

    def test_redact_password(self):
        text = "{'password': 'super_secret_123'}"
        assert "super_secret_123" not in redact_secrets(text)

    def test_no_redaction_needed(self):
        text = "{'action': 'restart', 'container': 'n8n'}"
        assert redact_secrets(text) == text


# --- Wrapper Tests ---

class TestContainerController:
    def test_valid_operation(self, tmp_path):
        ctrl = ContainerController(dev_mode=True, audit_dir=tmp_path)
        result = ctrl.execute("restart", "n8n")
        assert result["status"] == "ok"
        assert result["action"] == "restart"
        assert result["container"] == "n8n"
        assert result["dev_mode"] is True

    def test_all_allowed_combos(self, tmp_path):
        ctrl = ContainerController(dev_mode=True, rate_limit=100, audit_dir=tmp_path)
        for action in ALLOWED_ACTIONS:
            for container in ALLOWED_CONTAINERS:
                result = ctrl.execute(action, container)
                assert result["status"] == "ok"

    def test_blocked_action(self, tmp_path):
        ctrl = ContainerController(dev_mode=True, audit_dir=tmp_path)
        with pytest.raises(AllowlistError, match="not in allowlist"):
            ctrl.execute("delete", "n8n")

    def test_blocked_container(self, tmp_path):
        ctrl = ContainerController(dev_mode=True, audit_dir=tmp_path)
        with pytest.raises(AllowlistError, match="not in allowlist"):
            ctrl.execute("restart", "malicious-miner")

    def test_blocked_action_and_container(self, tmp_path):
        ctrl = ContainerController(dev_mode=True, audit_dir=tmp_path)
        with pytest.raises(AllowlistError):
            ctrl.execute("exec", "evil-container")

    def test_rate_limit(self, tmp_path):
        ctrl = ContainerController(dev_mode=True, rate_limit=3, audit_dir=tmp_path)
        ctrl.execute("status", "n8n")
        ctrl.execute("status", "n8n")
        ctrl.execute("status", "n8n")
        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            ctrl.execute("status", "n8n")

    def test_rate_limit_resets(self, tmp_path):
        ctrl = ContainerController(dev_mode=True, rate_limit=2, audit_dir=tmp_path)
        ctrl.execute("status", "n8n")
        ctrl.execute("status", "n8n")
        # Simulate time passing by clearing the window
        ctrl._operation_times = [time.time() - 61, time.time() - 61]
        # Should succeed now — old entries pruned
        result = ctrl.execute("status", "n8n")
        assert result["status"] == "ok"

    def test_audit_trail_on_success(self, tmp_path):
        ctrl = ContainerController(dev_mode=True, audit_dir=tmp_path)
        ctrl.execute("restart", "n8n")
        entries = ctrl.audit.get_recent(10)
        statuses = [e.split("|")[1] for e in entries]
        assert "ATTEMPT" in statuses
        assert "SUCCESS" in statuses

    def test_audit_trail_on_denial(self, tmp_path):
        ctrl = ContainerController(dev_mode=True, audit_dir=tmp_path)
        with pytest.raises(AllowlistError):
            ctrl.execute("delete", "postgres")
        entries = ctrl.audit.get_recent(10)
        statuses = [e.split("|")[1] for e in entries]
        assert "ATTEMPT" in statuses
        assert "DENIED" in statuses

    def test_secrets_redacted_in_audit(self, tmp_path):
        ctrl = ContainerController(dev_mode=True, audit_dir=tmp_path)
        # Pass a secret-looking kwarg — should be redacted in logs
        ctrl.execute("status", "n8n", token="ptr_secret_token_123")
        log_content = (tmp_path / "audit.log").read_text()
        assert "ptr_secret_token_123" not in log_content
        assert "[REDACTED]" in log_content

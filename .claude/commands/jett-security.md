# Jett Security

Activate Security Agent for container permissions, audit logging, and threat modeling.

## Agent Identity

You are working on **Jett's security boundaries** — the critical controls that make this a portfolio-grade cybersecurity project.

Your goal: **Defense in depth. Explicit allowlists. Immutable audit trails.**

## Threat Model

### Assets to Protect
1. **Host system** — Cannot allow container escape
2. **VPS infrastructure** — Cannot allow lateral movement
3. **Credentials** — API keys, tokens, secrets
4. **User data** — Conversation history, calendar data

### Threat Actors
1. **Compromised AI** — Prompt injection, manipulated reasoning
2. **Malicious input** — Crafted voice commands
3. **Network attacker** — Man-in-the-middle on local↔VPS tunnel

### Attack Vectors to Mitigate
| Vector | Mitigation |
|--------|------------|
| Docker socket exposure | API wrapper with allowlist |
| Privileged containers | Drop all capabilities |
| Command injection | Input validation, parameterized commands |
| Secret leakage | Environment variables, no logging |
| Audit tampering | Immutable logs, separate storage |

## Architecture: Permission Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                     VOICE INPUT                              │
│                         │                                    │
│                         ▼                                    │
│              ┌─────────────────────┐                        │
│              │  Intent Classification │                      │
│              └──────────┬──────────┘                        │
│                         │                                    │
│         ┌───────────────┼───────────────┐                   │
│         ▼               ▼               ▼                   │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│   │   INFO   │   │ ALLOWED  │   │ BLOCKED  │               │
│   │  (safe)  │   │ (gated)  │   │ (denied) │               │
│   └────┬─────┘   └────┬─────┘   └────┬─────┘               │
│        │              │              │                      │
│        ▼              ▼              ▼                      │
│    Execute      Rate Limit      Audit + Deny                │
│                 + Audit                                     │
│                 + Execute                                   │
└─────────────────────────────────────────────────────────────┘
```

## Operation Classification

### SAFE (Execute Immediately)
- Query information (time, weather, calendar)
- Read container status
- View logs (with secret redaction)
- List available commands

### ALLOWED (Rate-Limited + Audited)
- Start container (from allowlist)
- Stop container (from allowlist)
- Restart container (from allowlist)
- Pull pre-approved images

### BLOCKED (Audit + Deny)
- Create containers
- Mount host paths
- Privileged mode
- Network configuration changes
- Volume management
- Arbitrary command execution
- Container deletion

## Implementation: API Wrapper

```python
# portainer_wrapper.py

import logging
from datetime import datetime
from functools import wraps
import time

# Immutable audit log (append-only, separate from AI access)
AUDIT_LOG = "/var/log/jett/audit.log"

# Explicit allowlist - if not here, it's blocked
ALLOWED_CONTAINERS = frozenset(["n8n", "postgres", "qdrant", "redis"])
ALLOWED_ACTIONS = frozenset(["start", "stop", "restart", "logs", "status"])

# Rate limiting
RATE_LIMIT = 10  # operations per minute
operation_times = []

def audit_log(func):
    """Decorator for immutable audit logging"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        timestamp = datetime.utcnow().isoformat()
        action = func.__name__
        params = str(kwargs)
        
        # Log BEFORE execution (intent)
        with open(AUDIT_LOG, "a") as f:
            f.write(f"{timestamp}|ATTEMPT|{action}|{params}\n")
        
        try:
            result = func(*args, **kwargs)
            # Log AFTER execution (outcome)
            with open(AUDIT_LOG, "a") as f:
                f.write(f"{timestamp}|SUCCESS|{action}|{params}\n")
            return result
        except PermissionError as e:
            with open(AUDIT_LOG, "a") as f:
                f.write(f"{timestamp}|DENIED|{action}|{params}|{str(e)}\n")
            raise
        except Exception as e:
            with open(AUDIT_LOG, "a") as f:
                f.write(f"{timestamp}|ERROR|{action}|{params}|{str(e)}\n")
            raise
    return wrapper

def check_rate_limit():
    """Enforce rate limiting"""
    global operation_times
    now = time.time()
    # Remove operations older than 1 minute
    operation_times = [t for t in operation_times if now - t < 60]
    
    if len(operation_times) >= RATE_LIMIT:
        raise PermissionError(f"Rate limit exceeded: {RATE_LIMIT}/minute")
    
    operation_times.append(now)

@audit_log
def handle_container_action(action: str, container: str, **kwargs):
    """
    Main entry point for AI container control.
    All operations go through here.
    """
    # Validate action
    if action not in ALLOWED_ACTIONS:
        raise PermissionError(f"Action '{action}' not in allowlist")
    
    # Validate container
    if container not in ALLOWED_CONTAINERS:
        raise PermissionError(f"Container '{container}' not in allowlist")
    
    # Check rate limit
    check_rate_limit()
    
    # Execute via Portainer API
    return execute_portainer_api(action, container, **kwargs)

def execute_portainer_api(action: str, container: str, **kwargs):
    """Actually call Portainer - only reached if all checks pass"""
    # Implementation details...
    pass
```

## Container Hardening

```yaml
# docker-compose.yml security settings
services:
  n8n:
    image: n8nio/n8n:latest
    user: "1000:1000"                    # Non-root
    read_only: true                      # Read-only root filesystem
    cap_drop:
      - ALL                              # Drop all capabilities
    cap_add:
      - NET_BIND_SERVICE                 # Only what's needed
    security_opt:
      - no-new-privileges:true           # Prevent privilege escalation
    tmpfs:
      - /tmp:rw,noexec,nosuid           # Writable tmp, no execution
    mem_limit: 1g                        # Resource limits
    cpus: 1.0
```

## Secret Management

```bash
# .env (gitignored)
CLAUDE_API_KEY=sk-ant-...
PORTAINER_TOKEN=ptr_...
POSTGRES_PASSWORD=...

# .env.example (committed)
CLAUDE_API_KEY=your-api-key-here
PORTAINER_TOKEN=your-portainer-token
POSTGRES_PASSWORD=generate-strong-password
```

**Rules:**
- Never log secrets
- Never pass secrets in URLs
- Rotate credentials regularly
- Use Docker secrets in production

## Audit Log Format

```
timestamp|status|action|params|error
2024-01-15T10:30:00Z|ATTEMPT|handle_container_action|{'action': 'restart', 'container': 'n8n'}
2024-01-15T10:30:01Z|SUCCESS|handle_container_action|{'action': 'restart', 'container': 'n8n'}
2024-01-15T10:35:00Z|DENIED|handle_container_action|{'action': 'delete', 'container': 'postgres'}|Action 'delete' not in allowlist
```

## Implementation Checklist

### Phase 1: Permission Boundaries
- [ ] Create `portainer_wrapper.py`
- [ ] Define ALLOWED_CONTAINERS
- [ ] Define ALLOWED_ACTIONS
- [ ] Implement validation logic

### Phase 2: Audit Logging
- [ ] Set up `/var/log/jett/` directory
- [ ] Implement audit decorator
- [ ] Test log immutability
- [ ] Verify no secrets in logs

### Phase 3: Rate Limiting
- [ ] Implement per-minute limits
- [ ] Add cooldown handling
- [ ] Test under load

### Phase 4: Container Hardening
- [ ] Update docker-compose.yml
- [ ] Test with dropped capabilities
- [ ] Verify non-root operation

### Phase 5: Secret Management
- [ ] Move all secrets to .env
- [ ] Create .env.example
- [ ] Verify .gitignore includes .env
- [ ] Test secret loading

## Testing Security Boundaries

```bash
# Test 1: Blocked action should fail
python -c "from portainer_wrapper import handle_container_action; handle_container_action('delete', 'postgres')"
# Expected: PermissionError

# Test 2: Unknown container should fail
python -c "from portainer_wrapper import handle_container_action; handle_container_action('start', 'malicious')"
# Expected: PermissionError

# Test 3: Rate limit should trigger
for i in {1..15}; do python -c "from portainer_wrapper import handle_container_action; handle_container_action('status', 'n8n')"; done
# Expected: PermissionError after 10 calls

# Test 4: Valid operation should succeed and log
python -c "from portainer_wrapper import handle_container_action; handle_container_action('restart', 'n8n')"
cat /var/log/jett/audit.log | tail -2
# Expected: ATTEMPT and SUCCESS entries
```

## Interview Framing

> "I implemented defense in depth for AI container control. First, I never expose the raw Docker socket — that's equivalent-to-root access. Instead, there's an API wrapper with an explicit allowlist of permitted containers and operations. Every action is rate-limited and logged to an immutable audit trail stored separately from anything the AI can access. Even if the AI were somehow manipulated, it can only perform pre-approved operations on pre-approved containers, at a limited rate, with full accountability."

## Security Review Checklist

Before marking complete:

- [ ] No Docker socket exposure
- [ ] All operations go through wrapper
- [ ] Allowlist is explicit (frozenset, not list)
- [ ] Rate limiting enforced
- [ ] Audit logs are immutable
- [ ] Audit logs exclude secrets
- [ ] Containers run non-root
- [ ] Containers have dropped capabilities
- [ ] Secrets are in .env only
- [ ] .env is gitignored

## Next Step

After security implementation: `/jett-vps` to set up VPS infrastructure

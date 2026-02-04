# Security Model

## Core Principle

**Defense-in-depth**: No single control is trusted alone. Every privileged action passes through multiple validation layers.

## Threat Model

### Assets to Protect
1. **Host system** — AI must not escape container boundaries
2. **User privacy** — Audio never leaves local machine
3. **VPS infrastructure** — Containers must not be weaponized
4. **API keys and secrets** — Must never be logged or exposed

### Threat Actors
- **Prompt injection** — Malicious input via voice or text
- **Supply chain** — Compromised model weights or dependencies
- **Network** — Man-in-the-middle on VPS communication

## Security Layers

### Layer 1: Docker Socket Isolation
- NEVER mount `/var/run/docker.sock` into AI-accessible containers
- All container operations go through Portainer API
- Portainer accessed only via WireGuard tunnel

### Layer 2: Operation Allowlist
```
ALLOWED:
  container.start   → [jett-n8n, jett-postgres, jett-qdrant]
  container.stop    → [jett-n8n, jett-postgres, jett-qdrant]
  container.restart → [jett-n8n, jett-postgres, jett-qdrant]
  container.logs    → [*]  (read-only)

DENIED (always):
  container.create
  container.remove
  container.exec
  image.pull
  volume.remove
  network.create
```

### Layer 3: Rate Limiting
- 5 privileged operations per minute
- 20 privileged operations per hour
- Automatic cooldown on limit breach

### Layer 4: Immutable Audit Log
- Every privileged action logged: timestamp, source, operation, target, result
- Written to append-only file AND PostgreSQL
- Dashboard real-time audit feed
- Alerting on anomalous patterns

### Layer 5: Network Controls
- WireGuard tunnel for all VPS traffic
- UFW on VPS: deny all, allow 51820/UDP only
- No containers exposed to public internet
- Egress filtering on AI containers

## Secret Management

- All secrets in `.env` files (gitignored)
- `.env.example` documents required variables without real values
- Never log secret values
- Rotate API keys on suspected compromise

## Implementation Status

| Control | Status | Location |
|---------|--------|----------|
| API wrapper with allowlist | ✅ Complete | src/security/wrapper.py |
| Rate limiting | ✅ Complete | 10 ops/minute sliding window |
| Audit logging | ✅ Complete | Append-only, secret redaction |
| Container hardening | ✅ Defined | docker/docker-compose.yml |
| WireGuard tunnel | ⬜ Pending | Config files not yet created |
| VPS deployment | ⬜ Pending | Waiting for WireGuard setup |
| UFW firewall rules | ⬜ Pending | deny all, allow 51820/UDP |
| Dashboard audit feed | ⬜ Pending | Waiting for backend integration |

## Incident Response

1. Rate limit triggered → Log + alert + cooldown
2. Allowlist violation → Log + alert + block + review
3. Anomalous pattern → Log + alert + pause AI operations
4. Suspected compromise → Kill WireGuard tunnel + stop all containers

# Jett VPS Infrastructure

Docker Compose stack for the Jett VPS (Hostinger). All services are bound to the WireGuard tunnel interface (`10.0.0.2`) and are **not accessible from the public internet**.

## Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| **n8n** | n8nio/n8n | 5678 | Workflow automation engine |
| **PostgreSQL** | postgres:15-alpine | 5432 | State storage and audit logs |
| **Qdrant** | qdrant/qdrant | 6333 | Vector database for RAG |
| **Portainer** | portainer/portainer-ce | 9000 | Container management API |

## Security Hardening

Every container has the following applied:

| Control | Value | Purpose |
|---------|-------|---------|
| `read_only: true` | Immutable root filesystem | Prevents runtime file tampering |
| `cap_drop: ALL` | Zero Linux capabilities | Minimizes kernel attack surface |
| `no-new-privileges` | Blocks privilege escalation | Prevents setuid/setgid exploits |
| `user: "1000:1000"` | Non-root user | Limits damage from container escape |
| `tmpfs /tmp` | `noexec,nosuid` | Writable temp without code execution |
| `mem_limit` | Per-service caps | Prevents resource exhaustion |
| `cpus` | Per-service caps | Prevents CPU starvation |
| WireGuard binding | `10.0.0.2:port` | No public internet exposure |
| Health checks | Per-service | Automatic failure detection |

### Portainer Exception

Portainer requires Docker socket access and runs as root. This is an intentional tradeoff:

- It is the **only** entry point for container management (ADR-003)
- The socket is mounted **read-only** (`:ro`)
- All other hardening controls are still applied
- Access is restricted to the WireGuard IP
- API requires token authentication

## Deployment

### Prerequisites

- Docker and Docker Compose installed on VPS
- WireGuard tunnel configured (interface `10.0.0.2`)
- UFW firewall: deny all, allow 51820/UDP (WireGuard)

### Setup

```bash
cd docker/

# Create .env from template and fill in real secrets
cp .env.example .env
nano .env

# Start all services
docker compose up -d

# Verify all containers are healthy
docker compose ps
```

### Validation

```bash
# Confirm services are bound to WireGuard IP only
ss -tlnp | grep -E '5678|5432|6333|9000'
# Expected: all listening on 10.0.0.2, NOT 0.0.0.0

# Check container security
docker inspect jett-postgres --format '{{.HostConfig.ReadonlyRootfs}}'
# Expected: true
```

## Network Architecture

```
Local Machine (RTX 3070)          VPS (Hostinger)
┌──────────────────────┐          ┌──────────────────────┐
│  Security Wrapper     │          │  10.0.0.2            │
│  (Portainer client)  │──WireGuard──►  :9000 Portainer  │
│                      │          │  :5678 n8n           │
│  Voice Pipeline      │          │  :5432 PostgreSQL    │
│  Dashboard           │          │  :6333 Qdrant        │
└──────────────────────┘          └──────────────────────┘
     10.0.0.1                     UFW: deny all
                                  allow 51820/UDP only
```

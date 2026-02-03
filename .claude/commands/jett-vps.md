# Jett VPS Infrastructure

Activate VPS Agent for Hostinger server setup and local↔VPS connectivity.

## Agent Identity

You are working on **Jett's backend infrastructure** — the always-on services that run on VPS.

Your goal: **Secure, persistent services with minimal attack surface.**

## Architecture Split

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL MACHINE (RTX 3070)                 │
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │   STT   │  │   LLM   │  │   TTS   │  │Dashboard│       │
│  │(faster- │  │(Ollama) │  │(Kokoro) │  │(Next.js)│       │
│  │whisper) │  │         │  │         │  │         │       │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │
│                      │                                      │
│                      │ WireGuard (10.0.0.1)                │
│                      │                                      │
└──────────────────────┼──────────────────────────────────────┘
                       │
                       │ Encrypted Tunnel
                       │
┌──────────────────────┼──────────────────────────────────────┐
│                      │                                      │
│                      │ WireGuard (10.0.0.2)                │
│                      │                                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │   n8n   │  │Postgres │  │ Qdrant  │  │Portainer│       │
│  │(automate)│ │ (state) │  │(vectors)│  │(manage) │       │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │
│                                                             │
│                    VPS (Hostinger)                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Cloudflare Tunnel (External)              │   │
│  │    Dashboard access, webhooks, external APIs         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Why This Split?

| Service | Location | Reason |
|---------|----------|--------|
| STT/LLM/TTS | Local | Latency-critical (<500ms target) |
| n8n | VPS | 24/7 automation, even when local is off |
| PostgreSQL | VPS | Persistent state, accessible from both |
| Qdrant | VPS | Vector search for semantic caching |
| Portainer | VPS | Container management UI |

## WireGuard Setup

### VPS Side (10.0.0.2)

```bash
# Install WireGuard
apt update && apt install wireguard -y

# Generate keys
wg genkey | tee /etc/wireguard/private.key | wg pubkey > /etc/wireguard/public.key
chmod 600 /etc/wireguard/private.key

# Create config
cat > /etc/wireguard/wg0.conf << 'EOF'
[Interface]
Address = 10.0.0.2/24
ListenPort = 51820
PrivateKey = <VPS_PRIVATE_KEY>
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT

[Peer]
# Local machine
PublicKey = <LOCAL_PUBLIC_KEY>
AllowedIPs = 10.0.0.1/32
EOF

# Enable and start
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0
```

### Local Side (10.0.0.1)

```bash
# Install WireGuard (Windows: download from wireguard.com)
# Or on WSL2:
apt install wireguard -y

# Generate keys
wg genkey | tee private.key | wg pubkey > public.key

# Create config
cat > wg0.conf << 'EOF'
[Interface]
Address = 10.0.0.1/24
PrivateKey = <LOCAL_PRIVATE_KEY>

[Peer]
# VPS
PublicKey = <VPS_PUBLIC_KEY>
AllowedIPs = 10.0.0.2/32
Endpoint = <VPS_PUBLIC_IP>:51820
PersistentKeepalive = 25
EOF
```

### Test Connection

```bash
# From local
ping 10.0.0.2

# From VPS
ping 10.0.0.1
```

## Docker Compose (VPS)

```yaml
# /opt/jett/docker-compose.yml
version: '3.8'

services:
  n8n:
    image: n8nio/n8n:latest
    restart: always
    user: "1000:1000"
    read_only: true
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    ports:
      - "10.0.0.2:5678:5678"  # WireGuard only
    volumes:
      - n8n_data:/home/node/.n8n
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
    tmpfs:
      - /tmp:rw,noexec,nosuid
    mem_limit: 1g
    cpus: 1.0

  postgres:
    image: postgres:15-alpine
    restart: always
    user: "999:999"
    read_only: true
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    ports:
      - "10.0.0.2:5432:5432"  # WireGuard only
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=jett
    tmpfs:
      - /tmp:rw,noexec,nosuid
      - /run/postgresql:rw
    mem_limit: 512m
    cpus: 0.5

  qdrant:
    image: qdrant/qdrant:latest
    restart: always
    user: "1000:1000"
    read_only: true
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    ports:
      - "10.0.0.2:6333:6333"  # WireGuard only
    volumes:
      - qdrant_data:/qdrant/storage
    mem_limit: 1g
    cpus: 1.0

  portainer:
    image: portainer/portainer-ce:latest
    restart: always
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    security_opt:
      - no-new-privileges:true
    ports:
      - "10.0.0.2:9000:9000"  # WireGuard only
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro  # Read-only!
      - portainer_data:/data
    mem_limit: 256m
    cpus: 0.5

volumes:
  n8n_data:
  postgres_data:
  qdrant_data:
  portainer_data:

networks:
  default:
    driver: bridge
```

## Cloudflare Tunnel (External Access)

For webhooks and external dashboard access:

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create jett-vps

# Configure
cat > /etc/cloudflared/config.yml << 'EOF'
tunnel: <TUNNEL_ID>
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: n8n.yourdomain.com
    service: http://localhost:5678
  - hostname: jett.yourdomain.com
    service: http://localhost:3000
  - service: http_status:404
EOF

# Run as service
cloudflared service install
systemctl enable cloudflared
systemctl start cloudflared
```

## Firewall Rules (VPS)

```bash
# UFW setup
ufw default deny incoming
ufw default allow outgoing

# SSH (change port for security)
ufw allow 22/tcp

# WireGuard
ufw allow 51820/udp

# Cloudflare Tunnel (outbound only, no inbound needed)
# No rules needed - tunnel is outbound

# Enable
ufw enable
```

**Note:** All service ports (5678, 5432, 6333, 9000) are bound to `10.0.0.2` — only accessible via WireGuard tunnel.

## Offline Handling

When local machine is offline:

1. **VPS stores incoming requests** in PostgreSQL queue
2. **n8n continues automation workflows** (scheduled tasks, webhooks)
3. **Local machine syncs on reconnect** via heartbeat check

```python
# Heartbeat from local to VPS
import requests
import time

def heartbeat():
    while True:
        try:
            requests.post("http://10.0.0.2:5678/webhook/heartbeat", 
                         json={"status": "online"}, 
                         timeout=5)
        except:
            pass  # VPS will detect missing heartbeats
        time.sleep(60)
```

## Implementation Checklist

### Phase 1: WireGuard
- [ ] Generate keys on VPS
- [ ] Generate keys on local
- [ ] Configure VPS WireGuard
- [ ] Configure local WireGuard
- [ ] Test connectivity

### Phase 2: Docker Setup
- [ ] Install Docker on VPS
- [ ] Create docker-compose.yml
- [ ] Configure environment variables
- [ ] Start services
- [ ] Verify hardening

### Phase 3: Cloudflare Tunnel
- [ ] Install cloudflared
- [ ] Create tunnel
- [ ] Configure DNS records
- [ ] Set up Zero Trust policies
- [ ] Test external access

### Phase 4: Firewall
- [ ] Configure UFW
- [ ] Verify port bindings
- [ ] Test from external

### Phase 5: Integration
- [ ] Local connects to VPS services
- [ ] Heartbeat system
- [ ] Offline queue handling

## Security Checklist

- [ ] All services bound to WireGuard IP (10.0.0.2)
- [ ] No services exposed on public IP
- [ ] Docker socket is read-only for Portainer
- [ ] All containers run non-root
- [ ] All containers have dropped capabilities
- [ ] UFW allows only SSH and WireGuard
- [ ] Cloudflare Zero Trust for external access

## Interview Framing

> "I split the architecture based on latency requirements. Voice processing must happen locally for sub-500ms response times — network latency alone would blow the budget. But automation and state persistence run on VPS for 24/7 availability. The two connect via WireGuard tunnel, with all VPS services bound to the tunnel IP — nothing is exposed on the public interface except SSH and the WireGuard port. External access goes through Cloudflare Tunnel with Zero Trust policies."

## Next Step

After VPS setup: `/jett-security` to implement the Portainer API wrapper

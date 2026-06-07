# MCP Server Infrastructure Documentation

## Overview
MCP (Managed Control Plane) servers provide centralized control for infrastructure services.

## Critical Endpoints

| Endpoint | Service | URL | Health Check |
|----------|---------|-----|--------------|
| wamcp | Docker/Swarm | https://wamcp.loc.wallacearizona.us/mcp/ | HTTP 200/404 |
| wamcp-unifi | UniFi Network | https://wamcp-unifi.loc.wallacearizona.us/mcp | HTTP 200/404 |
| wamcp-truenas | TrueNAS | https://wamcp-truenas.loc.wallacearizona.us/mcp | /health endpoint |
| wamcp-proxmox-plus | Proxmox | https://wamcp-proxmox-plus.loc.wallacearizona.us/ | HTTP 200 |
| wamcp-authentik | Authentik | https://wamcp-authentik.loc.wallacearizona.us/mcp | HTTP 200/404 |
| wamcp-pihole | Pi-hole DNS | https://wamcp-pihole.loc.wallacearizona.us/mcp | HTTP 200/404 |
| wamcp-browserless | Browserless | https://wamcp-browserless.loc.wallacearizona.us/ | HTTP 200 |

## Monitoring

### Cron Job: MCP Server Health Monitor
- **Schedule**: `0 */2 * * *` (every 2 hours)
- **Script**: `scripts/mcp-health-check.py`
- **Auto-creates** kanban issues for failures

### Health Check Script
Located at `scripts/mcp-health-check.py`. Checks:
1. DNS resolution (10.0.10.19, 10.0.10.18)
2. HTTP endpoint reachability
3. Docker MCP container status
4. UniFi device count
5. TrueNAS health endpoint
6. Proxmox node availability

## Known Issues (June 2026)

1. **Pi-hole MCP endpoint unreachable** - Connection refused (t_c73a7c34)
2. **Browserless MCP endpoint unreachable** - Connection refused (t_ff4da1db)

## DNS Configuration
System resolvers: 10.0.10.19, 10.0.10.18
Domain: loc.wallacearizona.us

## Priority Protocol
See `skills/infrastructure/mcp-critical-priority/SKILL.md` for response procedures.
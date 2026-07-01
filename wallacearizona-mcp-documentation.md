# MCP Server Infrastructure Documentation

## Overview
MCP (Managed Control Plane) servers provide centralized control for infrastructure services.

## Critical Endpoints

||| Endpoint | Service | URL | Health Check |
|||----------|---------|-----|--------------|
||| wamcp | Docker/Swarm | https://wamcp.loc.wallacearizona.us/mcp/ | HTTP 200/404 |
||| wamcp-unifi | UniFi Network | https://wamcp-unifi.loc.wallacearizona.us/mcp | HTTP 200/404 |
||| wamcp-truenas | TrueNAS | https://wamcp-truenas.loc.wallacearizona.us/mcp | /health endpoint |
||| wamcp-proxmox-plus | Proxmox | https://wamcp-proxmox-plus.loc.wallacearizona.us/ | HTTP 200 |
||| wamcp-authentik | Authentik | https://wamcp-authentik.loc.wallacearizona.us/mcp | HTTP 200/404 |
||| wamcp-browserless | Browserless/Chromium | https://wamcp-browserless.loc.wallacearizona.us/ | Raw browserless API (not MCP), proxies to chrome service |
||| (deprecated) wamcp-pihole-1 | Pi-hole DNS - NOT MCP | N/A | Service not deployed |
||| (deprecated) wamcp-pihole-2 | Pi-hole DNS - NOT MCP | N/A | Service not deployed |

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

1. ~~**Pi-hole MCP not deployed** - Service never deployed to Docker Swarm despite documentation~~ ✅ RESOLVED
   - pihole-mcp deployed to mcp-servers stack on 2026-06-11
   - DNS record still needed for wamcp-pihole.loc.wallacearizona.us

2. ~~**Browserless MCP not deployed** - Never existed despite compose file edits~~ ✅ RESOLVED
   - Was never an MCP service - Traefik router added to proxy wamcp-browserless.loc → chrome service
   - DNS record configured (wamcp-browserless.loc → 10.0.10.90)
   - Endpoint now returns HTTP 200 (browserless API) with token auth

3. **TrueNAS MCP endpoint** - Service IS running; endpoint responds correctly to MCP protocol

## Current Endpoint Status

||| Endpoint | Status | Code | Notes |
|||----------|--------|------|-------|
||| wamcp.loc | ✅ Working | 405 | MCP ready |
||| wamcp-truenas.loc | ✅ Working | 405 | MCP responding |
||| wamcp-unifi.loc | ✅ Reachable | 406 | Content negotiation |
||| wamcp-proxmox-plus.loc | ✅ Reachable | 404 | REST API responding |
||| wamcp-authentik.loc | ✅ Reachable | 404 | Webapp responding |
||| wamcp-pihole-1.loc | ⚠️ Not MCP | N/A | Pi-hole DNS only, no MCP service |
||| wamcp-pihole-2.loc | ⚠️ Not MCP | N/A | Pi-hole DNS only, no MCP service |
||| wamcp-browserless.loc | ✅ Reachable | 200 | Proxied to chrome service — raw browserless API (not MCP) |

## Deployed MCP Services (mcp-servers stack)

||| Service | Replicas | Status |
|||---------|----------|--------|
||| mcp-servers_docker-mcp | 1 | ✓ running |
||| mcp-servers_unifi-mcp | 1 | ✓ running |
||| mcp-servers_truenas-mcp | 1 | ✓ running |
||| mcp-servers_proxmox-mcp-plus | 1 | ✓ running |
||| mcp-servers_pihole-mcp | 1 | ✓ deployed |

## Health Check Script
Created at `scripts/mcp-health-check.py` - run with `python3 scripts/mcp-health-check.py`

## DNS Configuration
System resolvers: 10.0.10.19, 10.0.10.18
Domain: loc.wallacearizona.us

## Priority Protocol
See `skills/infrastructure/mcp-critical-priority/SKILL.md` for response procedures.
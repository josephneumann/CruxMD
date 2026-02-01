---
scope: project
module: deployment
date: 2026-02-01
problem_type: workflow
root_cause: config-error
severity: medium
tags: [docker, caddy, reverse-proxy, vps, reboot, deployment]
---

# Caddy Container Not Surviving VPS Reboot

## Summary

Caddy reverse proxy container failed to restart after a hard VPS reboot, causing downtime while other application services automatically recovered.

## Symptom

After a Hetzner VPS reboot:
- Frontend, backend, PostgreSQL, and Neo4j containers automatically restarted (all running and healthy)
- Caddy reverse proxy was not running, making the application inaccessible via the domain
- Manual `docker ps` confirmed only 4/5 expected containers were running
- SSH access to VPS was functional, confirming the system itself recovered

## Investigation

1. **Docker Compose status**: Checked docker-compose.yml and confirmed all services (backend, frontend, db, neo4j) had `restart: unless-stopped` policy
2. **Missing service**: Caddy was not defined in docker-compose.yml
3. **Manual Caddy setup**: Discovered Caddy was running as a standalone Docker container, launched manually with a shell script or direct docker run command
4. **Restart policy**: Standalone container likely used default no-restart policy or was not configured with restart persistence
5. **VPS environment**: Confirmed this is Hetzner VPS (single VPS + Docker Compose deployment model per CLAUDE.md)

## Root Cause

**Configuration Error**: Caddy reverse proxy was provisioned as a standalone Docker container outside of docker-compose.yml, without explicit restart policy or integration into the managed stack.

When the VPS rebooted:
- Docker daemon restarted and re-read docker-compose.yml
- All services with `restart: unless-stopped` were automatically restored by Docker
- Standalone Caddy container had no restart configuration and was not part of the managed orchestration layer
- Result: Application was missing its reverse proxy, exposing internal service network unavailable to external traffic

## Solution

**Immediate Fix** (already applied):
```bash
docker run -d \
  --name caddy \
  --restart unless-stopped \
  --network cruxmd_default \
  -p 80:80 \
  -p 443:443 \
  -p 443:443/udp \
  -v /root/CruxMD/Caddyfile:/etc/caddy/Caddyfile \
  -v caddy_data:/data \
  -v caddy_config:/config \
  caddy:2-alpine
```

**Proper Long-Term Fix**: Add Caddy service to docker-compose.yml

```yaml
services:
  # ... existing services ...

  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    environment:
      - DOMAIN=${DOMAIN:-app.cruxmd.ai}
    depends_on:
      - frontend
      - backend
    restart: unless-stopped
    networks:
      - default

volumes:
  postgres_data:
  neo4j_data:
  caddy_data:
  caddy_config:
```

**Key improvements**:
- Caddy integrated into docker-compose orchestration
- Automatic restart on system reboot via `restart: unless-stopped`
- Dependency declaration ensures Caddy starts after backend and frontend
- Named volumes for persistent certificate storage across reboots
- Single source of truth for deployment configuration

## Prevention

1. **Always define all services in docker-compose.yml** — Ensures Docker Compose is the single orchestration source
2. **Use `restart: unless-stopped`** — Guarantees services recover after system reboot or daemon restart
3. **Version control Caddy configuration** — Caddyfile is already in version control; ensure docker-compose matches this pattern
4. **Test reboot recovery** — After VPS maintenance or updates, verify all services start automatically with `docker ps` check
5. **Document deployment topology** — Make explicit in CLAUDE.md or deployment docs which services are part of the managed stack

## References

- Docker restart policies: https://docs.docker.com/config/containers/start-containers-automatically/
- Caddy Docker docs: https://hub.docker.com/_/caddy
- CruxMD deployment: `/Users/jneumann/Code/CruxMD/docker-compose.yml`
- CruxMD Caddyfile: `/Users/jneumann/Code/CruxMD/Caddyfile`

## Related Issues

- See: Problem 2 (PNG optimization causing OOM during Docker build) — related to VPS deployment constraints

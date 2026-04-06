# Net-OS Guide

Your home network runs as a unified system across three machines. This guide covers everything — Telegram bot commands, the orch CLI, direct API calls, browser access, and what to do when things break. Written so you can pick this up cold after months away.

---

## Architecture Overview

```
                        ┌─────────────────────────────────────┐
                        │           YOU (Telegram/Browser)     │
                        └────────────┬───────────┬────────────┘
                                     │           │
                              Telegram Bot    Browser (LAN/Tailscale)
                                     │           │
                        ┌────────────▼───────────▼────────────┐
                        │        OpenClaw Gateway             │
                        │        KianPuter :18799             │
                        │   (AI agent, reads workspace/)      │
                        └────────────────┬────────────────────┘
                                         │
                        ┌────────────────▼────────────────────┐
                        │          net-os-api :8080           │
                        │   Central orchestration API         │
                        │   Deploys, execs, schedules, logs   │
                        └────────┬───────────────┬────────────┘
                                 │               │
               ┌─────────────────▼──┐     ┌──────▼──────────────────┐
               │  Node Agent        │     │  Node Agent              │
               │  Pi :7700          │     │  Laptop :7700            │
               │  192.168.0.209     │     │  192.168.0.49            │
               │  [robot-tank]      │     │  [orch.ps1]              │
               └────────────────────┘     └──────────────────────────┘

               PC also runs:
               - Portainer :9000    (Docker UI)
               - Dashboard :80      (reverse proxy)
               - All PC projects    (archon, assistant2, chemcode, ai-kernel)

               All nodes reachable via:
               - LAN (192.168.0.x)
               - Tailscale (100.x.x.x)
               - SSH aliases (ssh pc / ssh pi / ssh laptop)
```

---

## Quick Reference

| Task | Telegram | orch CLI | Direct API | Browser |
|---|---|---|---|---|
| Check status | `/status` | `orch status` | `GET /status` | Portainer |
| Node health | `/nodes` | `orch nodes` | `GET /nodes` | — |
| Deploy project | `/deploy robot-tank` | `orch deploy robot-tank` | `POST /deploy` | Portainer |
| Run command | `/exec pi uptime` | `orch exec pi uptime` | `POST /exec` | — |
| View logs | `/logs net-os-api` | `orch logs net-os-api` | `GET /logs/SERVICE` | Portainer |
| List schedules | `/sched` | `orch sched list` | `GET /jobs` | — |
| Add schedule | (natural language) | `orch sched add ...` | `POST /jobs` | — |
| Docker UI | — | — | — | :9000 |
| Dashboard | — | — | — | :80 |

---

## Telegram Bot Commands

The bot understands both slash commands and plain natural language. Both work equally well.

### /status

Shows all nodes and running containers.

```
Network Status

PC (KianPuter) — online
  CPU: 8%  |  RAM: 4.1 / 16 GB
  Running: archon, assistant2, net-os-api (3 containers)

Pi (KianPotPi) — online
  CPU: 22%  |  RAM: 891 MB / 4 GB  |  Temp: 52°C
  Running: robot-tank (1 container)

Laptop (MSI) — offline
  Last seen: 2h ago

Scheduled jobs: 2 active
```

### /nodes

Node health with resource usage.

```
Node Health

pc — online
  Host: KianPuter (192.168.0.27)
  CPU: 8%  |  RAM: 4.1 / 16 GB  |  Uptime: 3d 14h

pi — online
  Host: KianPotPi (192.168.0.209)
  CPU: 22%  |  RAM: 891 MB / 4 GB  |  Temp: 52°C  |  Uptime: 12d 6h

laptop — offline
  Last seen: 2026-04-01 18:32
```

### /deploy `<project>`

Deploys (or restarts) a project. Valid projects: `robot-tank`, `archon`, `assistant2`, `chemcode`, `ai-kernel`.

```
/deploy robot-tank
→ Deploying robot-tank on Pi...
→ robot-tank is up and running. (Verified via /status)

/deploy archon
→ Deploying archon on PC...
→ archon is up and running.
```

### /exec `<node>` `<command>`

Runs a shell command on a node and returns output.

```
/exec pi uptime
→  14:32:01 up 12 days, 6:14,  1 user,  load average: 0.22, 0.18, 0.15

/exec pc df -h
→ Filesystem      Size  Used Avail Use% Mounted on
  /dev/sda1       931G  412G  472G  47% /

/exec laptop free -h
→        total  used  free
  Mem:    15G   8.2G  6.8G
```

### /logs `<service>`

Tails the last 50 lines of logs for a service.

```
/logs net-os-api
/logs archon
/logs robot-tank
```

### /sched

Lists all scheduled jobs.

```
Scheduled Jobs

nightly-backup
  Node: PC | Schedule: 0 2 * * * (every day at 2am)
  Command: bash /home/kian/backup.sh

robot-tank-watchdog
  Node: Pi | Schedule: */30 * * * * (every 30 minutes)
  Command: docker inspect robot-tank | grep Running
```

### /help

Shows all available commands (the list above, formatted).

---

### Natural Language — What Works

You don't need slash commands. Just describe what you want:

```
"how are my nodes"
"is the pi online"
"deploy the robot tank"
"start archon on the server"
"run df -h on the pi"
"what's the temperature on the raspberry pi"
"show me the logs for net-os-api"
"schedule a backup every night at 2am on the PC"
"what jobs are scheduled"
"restart archon"
"show me what's running"
"is chemcode up"
"what machines do I have"
"deploy everything"
```

The agent reads your message, figures out the intent, calls the appropriate API, and replies. It falls back to SSH if the API is down.

---

## orch CLI Reference

The orch CLI is a PowerShell script at `C:\AI\orchestrator\scripts\orch.ps1` on the **laptop**. Run it from PowerShell on the laptop, or via SSH from anywhere: `ssh laptop 'powershell -File C:/AI/orchestrator/scripts/orch.ps1 COMMAND'`.

### Status and Nodes

```powershell
orch status              # Full network status (all nodes + containers)
orch nodes               # Node list with health metrics
orch nodes --watch       # Auto-refresh every 5s
```

### Deployment

```powershell
orch deploy robot-tank           # Deploy to default node (pi)
orch deploy archon               # Deploy to default node (pc)
orch deploy assistant2
orch deploy chemcode
orch deploy ai-kernel
orch deploy robot-tank --node pi # Explicit node
```

### Remote Execution

```powershell
orch exec pi uptime
orch exec pc "docker ps"
orch exec laptop "df -h"
orch exec pi "vcgencmd measure_temp"
orch exec pc "docker logs --tail 50 archon"
```

### Natural Language (Intent)

```powershell
orch intent "check if robot-tank is still running"
orch intent "restart archon if it's down"
orch intent "show me disk usage on all nodes"
```

### Logs

```powershell
orch logs net-os-api
orch logs archon
orch logs robot-tank
orch logs robot-tank --node pi --tail 100
```

### Scheduling

```powershell
orch sched list                                    # List all jobs
orch sched add nightly-backup "0 2 * * *" pc "bash /home/kian/backup.sh"
orch sched add tank-check "*/30 * * * *" pi "docker inspect robot-tank"
orch sched remove nightly-backup                   # Delete by name
orch sched run nightly-backup                      # Trigger immediately
```

### Node Management

```powershell
orch nodes add lenovo 192.168.0.X 7700            # Register new node
orch nodes remove lenovo                           # Deregister
orch nodes ping                                    # Ping all nodes
```

---

## Browser Access

All of these work on LAN. For phone or off-network, replace the LAN IP with the Tailscale IP (see table below).

| URL | What it is |
|---|---|
| `http://192.168.0.27:9000` | Portainer — Docker management UI |
| `http://192.168.0.27:80` | Dashboard / reverse proxy |
| `http://192.168.0.27:8080` | net-os-api (raw, for curl/testing) |
| `http://192.168.0.27:18799` | OpenClaw gateway |

### Tailscale IPs (phone/remote access)

| Node | Tailscale IP |
|---|---|
| Pi (KianPotPi) | 100.73.208.99 |
| Laptop (MSI) | 100.123.23.84 |
| PC (KianPuter) | 100.99.89.118 |

So from your phone: `http://100.99.89.118:9000` (Portainer on PC).

### Add to Home Screen as PWA

On Android/iOS with Tailscale active:
1. Open the Portainer URL in Chrome/Safari.
2. Tap the Share button (iOS) or three-dot menu (Android).
3. Select "Add to Home Screen".
4. Name it "Portainer" or "Net-OS".

---

## Direct API Reference

Base URL: `http://192.168.0.27:8080`  
Auth header: `Authorization: Bearer netosmasterkey`

### Get full status
```bash
curl -s http://192.168.0.27:8080/status \
  -H "Authorization: Bearer netosmasterkey" | python3 -m json.tool
```

### List nodes
```bash
curl -s http://192.168.0.27:8080/nodes \
  -H "Authorization: Bearer netosmasterkey"
```

### Deploy a project
```bash
curl -s -X POST http://192.168.0.27:8080/deploy \
  -H "Authorization: Bearer netosmasterkey" \
  -H "Content-Type: application/json" \
  -d '{"project":"robot-tank","node":"pi"}'
```

### Run a command on any node
```bash
# On Pi
curl -s -X POST http://192.168.0.27:8080/exec \
  -H "Authorization: Bearer netosmasterkey" \
  -H "Content-Type: application/json" \
  -d '{"node":"pi","command":"vcgencmd measure_temp"}'

# On PC
curl -s -X POST http://192.168.0.27:8080/exec \
  -H "Authorization: Bearer netosmasterkey" \
  -H "Content-Type: application/json" \
  -d '{"node":"pc","command":"df -h"}'

# On Laptop
curl -s -X POST http://192.168.0.27:8080/exec \
  -H "Authorization: Bearer netosmasterkey" \
  -H "Content-Type: application/json" \
  -d '{"node":"laptop","command":"uptime"}'
```

### Schedule a recurring task
```bash
curl -s -X POST http://192.168.0.27:8080/jobs \
  -H "Authorization: Bearer netosmasterkey" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nightly-backup",
    "schedule": "0 2 * * *",
    "node": "pc",
    "command": "bash /home/kian/backup.sh"
  }'
```

### List scheduled jobs
```bash
curl -s http://192.168.0.27:8080/jobs \
  -H "Authorization: Bearer netosmasterkey"
```

### Delete a scheduled job
```bash
curl -s -X DELETE http://192.168.0.27:8080/jobs/JOB_ID \
  -H "Authorization: Bearer netosmasterkey"
```

### Tail logs
```bash
curl -s http://192.168.0.27:8080/logs/net-os-api \
  -H "Authorization: Bearer netosmasterkey"
```

### Register a new node
```bash
curl -s -X POST http://192.168.0.27:8080/nodes \
  -H "Authorization: Bearer netosmasterkey" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "lenovo",
    "host": "192.168.0.X",
    "port": 7700,
    "token": "netoskeylocal"
  }'
```

---

## Adding New Devices

When you get a new machine (Lenovo, another Pi, etc.):

1. **Install the node agent on the new machine.**
   ```bash
   # On the new machine (Linux/Pi):
   git clone https://github.com/your-repo/node-agent /opt/node-agent
   cd /opt/node-agent
   TOKEN=netoskeylocal PORT=7700 python3 main.py
   
   # Or via Docker:
   docker run -d \
     -e TOKEN=netoskeylocal \
     -p 7700:7700 \
     --restart always \
     --name node-agent \
     your-registry/node-agent
   ```

2. **Verify the agent is responding:**
   ```bash
   curl -s http://NEW_MACHINE_IP:7700/health \
     -H "Authorization: Bearer netoskeylocal"
   ```
   Should return JSON with `status: ok`.

3. **Register the node with net-os-api:**
   ```bash
   curl -s -X POST http://192.168.0.27:8080/nodes \
     -H "Authorization: Bearer netosmasterkey" \
     -H "Content-Type: application/json" \
     -d '{"name":"lenovo","host":"NEW_MACHINE_IP","port":7700,"token":"netoskeylocal"}'
   ```

4. **Add SSH alias on PC.** In `~/.ssh/config`:
   ```
   Host lenovo
       HostName NEW_MACHINE_IP
       User kian
       IdentityFile ~/.ssh/id_rsa
   ```

5. **Install Tailscale on the new machine** (optional but recommended):
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```
   Then add its Tailscale IP to this guide.

6. **Update workspace files.** Add the new node to `NET_OS.md` node reference table and `BOOT.md` session state.

7. **Test via Telegram:** Send `/nodes` — the new machine should appear.

---

## Phone (Tailscale) Access

With Tailscale installed on your phone:

| Service | URL |
|---|---|
| Portainer | `http://100.99.89.118:9000` |
| Dashboard | `http://100.99.89.118:80` |
| OpenClaw | `http://100.99.89.118:18799` |
| net-os-api | `http://100.99.89.118:8080` |
| Pi node agent | `http://100.73.208.99:7700/health` |
| Laptop agent | `http://100.123.23.84:7700/health` |

PC Tailscale IP: `100.99.89.118`. To verify: `ssh pc 'tailscale ip'`.

The Telegram bot works from anywhere without Tailscale (it goes through Telegram's servers). Tailscale is only needed for direct browser/curl access.

---

## Troubleshooting

### net-os-api not responding

Symptoms: curl times out, Telegram bot says API unreachable.

```bash
# Check if the container is running
ssh pc "docker ps | grep net-os-api"

# If not running, start it
ssh pc "cd /home/kian/net-os && docker compose up -d net-os-api"

# Check logs for startup errors
ssh pc "docker logs --tail 50 net-os-api"

# Test directly on PC (no network hop)
ssh pc "curl -s http://localhost:8080/status -H 'Authorization: Bearer netosmasterkey'"
```

### Node shows offline

Symptoms: `/status` or `/nodes` shows a node as offline.

```bash
# 1. Try pinging the node
ping 192.168.0.209    # Pi
ping 192.168.0.49     # Laptop

# 2. Try SSH
ssh pi uptime
ssh laptop uptime

# 3. If reachable via SSH, check the node agent
ssh pi "docker ps | grep node-agent"
ssh pi "docker logs --tail 30 node-agent"
ssh pi "curl -s http://localhost:7700/health -H 'Authorization: Bearer netoskeylocal'"

# 4. Restart the node agent if needed
ssh pi "docker restart node-agent"
```

If the machine is physically off, just note it. It'll come back when it boots.

### Telegram bot not responding

Symptoms: messages to bot get no reply, or it's slow.

```bash
# Check OpenClaw gateway
ssh pc "docker ps | grep openclaw"
ssh pc "docker logs --tail 50 openclaw-gateway"

# Restart OpenClaw
ssh pc "cd /home/kian/openclaw && docker compose restart"
# Or if running directly:
ssh pc "pm2 restart openclaw"
```

Also check: is your bot token still valid? Test with:
```bash
BOT_TOKEN="your_token"
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe"
```
Should return `{"ok":true,"result":{...}}`.

### Docker credential error on deploy

Symptoms: deploy fails with `unauthorized: authentication required` or `Error response from daemon: pull access denied`.

This happens when the PC can't pull private images directly (no Docker credentials stored).

**Fix:** Pull on the laptop (which is logged in) and transfer the image:
```bash
# On laptop, pull and export
docker pull ghcr.io/your-org/your-image:tag
docker save ghcr.io/your-org/your-image:tag | ssh pc docker load

# Then deploy normally — it'll use the local image
curl -s -X POST http://192.168.0.27:8080/deploy \
  -H "Authorization: Bearer netosmasterkey" \
  -H "Content-Type: application/json" \
  -d '{"project":"PROJECT","node":"pc"}'
```

Or run `docker login` on PC directly before deploying:
```bash
ssh pc "echo TOKEN | docker login ghcr.io -u USERNAME --password-stdin"
```

### OpenClaw gateway restart

```bash
ssh pc "docker restart openclaw-gateway"
# Or
ssh pc "cd /home/kian/openclaw && docker compose restart gateway"
# Or find the process and restart it
ssh pc "pm2 list"
ssh pc "pm2 restart openclaw"
```

### orch.ps1 not found or errors on laptop

```bash
ssh laptop "ls C:/AI/orchestrator/scripts/"
# If missing, check alternate path
ssh laptop "ls C:/AI/orchestrator/"
```

If orch.ps1 was moved, update references in `NET_OS.md` and this guide.

### Portainer login forgotten

Default Portainer credentials are set on first run. If locked out:
```bash
ssh pc "docker exec portainer /bin/sh -c 'rm /data/portainer.db && exit'"
ssh pc "docker restart portainer"
# Then visit :9000 and set up a new admin account
```

---

## Reference — Tokens and Ports

| Service | Port | Token/Auth |
|---|---|---|
| net-os-api | 8080 | `netosmasterkey` |
| Node agent (Pi, Laptop) | 7700 | `netoskeylocal` |
| OpenClaw gateway | 18799 | (configured in openclaw.json) |
| Portainer | 9000 | Web UI credentials |
| Dashboard | 80 | None (internal) |

All tokens are in plaintext in this guide because this is a home network. Do not expose these ports to the public internet without adding TLS and stronger auth.

"""
net-os central API — runs on PC (in Docker).
Port 8080. Auth: Authorization: Bearer <NET_OS_API_TOKEN>

Node execution notes:
- For node="pc": since this runs in Docker, we SSH to the host via `ssh pc <cmd>`.
  The Docker container must have an SSH key mounted and ~/.ssh/config with `Host pc`.
- For other nodes: we call the node-agent HTTP API at their IP:7700.
"""

import asyncio
import json
import logging
import os
import re
import sqlite3
import subprocess
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
import redis.asyncio as redis
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_TOKEN = os.environ.get("NET_OS_API_TOKEN", "netosmasterkey")
NODE_TOKEN = os.environ.get("NODE_TOKEN", "netoskeylocal")
PORT = int(os.environ.get("PORT", "8080"))
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

CONFIGS_DIR = Path(os.environ.get("CONFIGS_DIR", "/configs"))
PROJECTS_FILE = CONFIGS_DIR / "projects.json"
NODES_FILE = CONFIGS_DIR / "nodes.json"
DB_PATH = Path(os.environ.get("DB_PATH", "/data/nodes.db"))

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                name TEXT PRIMARY KEY,
                display TEXT,
                ip TEXT,
                tailscale_ip TEXT,
                port INTEGER DEFAULT 7700,
                os TEXT,
                role TEXT,
                token TEXT,
                registered_at TEXT,
                last_seen TEXT,
                last_health TEXT
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                name TEXT,
                cmd TEXT,
                node TEXT,
                cron TEXT,
                interval_seconds INTEGER,
                created_at TEXT,
                last_run TEXT,
                last_result TEXT
            );

            CREATE TABLE IF NOT EXISTS command_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT,
                node TEXT,
                cmd TEXT,
                returncode INTEGER,
                source TEXT
            );
        """)


# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------

_nodes: dict[str, dict] = {}
_projects: dict[str, dict] = {}
_scheduler = AsyncIOScheduler()
_recent_commands: list[dict] = []
_ws_nodes: dict[str, WebSocket] = {}
_ws_meta: dict[str, dict] = {}
_pending: dict[str, asyncio.Future] = {}
_redis: Optional[redis.Redis] = None
logger = logging.getLogger("net-os-api")


def load_seed_data() -> None:
    global _nodes, _projects

    if PROJECTS_FILE.exists():
        _projects = json.loads(PROJECTS_FILE.read_text())
    else:
        _projects = {}

    if NODES_FILE.exists():
        seed = json.loads(NODES_FILE.read_text())
        for name, data in seed.items():
            _nodes[name] = data

    # Sync seed nodes to DB
    with get_db() as conn:
        # Load existing DB nodes first
        rows = conn.execute("SELECT * FROM nodes").fetchall()
        for row in rows:
            _nodes[row["name"]] = dict(row)

        # Upsert seed nodes
        for name, data in _nodes.items():
            conn.execute("""
                INSERT INTO nodes (name, display, ip, tailscale_ip, port, os, role, token, registered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    display=excluded.display,
                    ip=excluded.ip,
                    tailscale_ip=excluded.tailscale_ip,
                    port=excluded.port,
                    os=excluded.os,
                    role=excluded.role,
                    token=excluded.token
            """, (
                name,
                data.get("display", name),
                data.get("ip", ""),
                data.get("tailscale_ip"),
                data.get("port", 7700),
                data.get("os", "linux"),
                data.get("role", "node"),
                data.get("token", NODE_TOKEN),
                datetime.utcnow().isoformat(),
            ))


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis
    init_db()
    load_seed_data()
    _redis = redis.from_url(REDIS_URL, decode_responses=True)
    _scheduler.start()
    # Background health poller
    _scheduler.add_job(poll_all_health, "interval", seconds=30, id="__health_poll__", replace_existing=True)
    yield
    _scheduler.shutdown(wait=False)
    if _redis is not None:
        await _redis.aclose()
        _redis = None


app = FastAPI(title="net-os central API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def verify_token(request: Request) -> None:
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token:
        token = request.headers.get("X-Api-Token", "")
    if token != API_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")


def verify_ws_token(websocket: WebSocket) -> bool:
    token = websocket.query_params.get("token") or websocket.headers.get("X-Node-Token", "")
    return token == NODE_TOKEN


# ---------------------------------------------------------------------------
# Node agent client
# ---------------------------------------------------------------------------

def node_agent_url(node: dict) -> str:
    ip = node.get("tailscale_ip") or node.get("ip")
    port = node.get("port", 7700)
    return f"http://{ip}:{port}"


async def agent_get(node: dict, path: str, timeout: int = 10) -> dict:
    url = f"{node_agent_url(node)}{path}"
    token = node.get("token", NODE_TOKEN)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, headers={"X-Node-Token": token})
        resp.raise_for_status()
        return resp.json()


async def agent_post(node: dict, path: str, body: dict, timeout: int = 60) -> dict:
    url = f"{node_agent_url(node)}{path}"
    token = node.get("token", NODE_TOKEN)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=body, headers={"X-Node-Token": token})
        resp.raise_for_status()
        return resp.json()


async def queue_for_node(node_id: str, message_dict: dict) -> None:
    if _redis is None:
        return
    queue_key = f"node:queue:{node_id}"
    await _redis.rpush(queue_key, json.dumps(message_dict))
    await _redis.expire(queue_key, 24 * 60 * 60)


async def drain_node_queue(node_id: str, ws: WebSocket) -> None:
    if _redis is None:
        return
    queue_key = f"node:queue:{node_id}"
    queued_messages = await _redis.lrange(queue_key, 0, -1)
    if not queued_messages:
        return
    await _redis.delete(queue_key)
    for raw_message in queued_messages:
        await ws.send_text(raw_message)


# ---------------------------------------------------------------------------
# PC-local exec (via SSH since we're in Docker)
# ---------------------------------------------------------------------------

def exec_on_pc(cmd: str, cwd: Optional[str] = None, timeout: int = 60) -> dict:
    """
    Run a command on the PC host.
    Since net-os-api runs in Docker, we can't run Windows commands directly.
    We SSH to 'pc' using the mounted SSH key.
    Requires: SSH key at /root/.ssh/id_rsa, Host 'pc' in /root/.ssh/config.
    """
    if cwd:
        full_cmd = f"ssh pc \"cd /d {cwd} && {cmd}\""
    else:
        full_cmd = f"ssh pc \"{cmd}\""

    try:
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "cmd": cmd,
            "via": "ssh-pc",
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Timed out", "returncode": -1, "cmd": cmd, "via": "ssh-pc"}
    except Exception as exc:
        return {"stdout": "", "stderr": str(exc), "returncode": -1, "cmd": cmd, "via": "ssh-pc"}


# ---------------------------------------------------------------------------
# Docker info (via docker CLI in container with /var/run/docker.sock)
# ---------------------------------------------------------------------------

def get_docker_containers() -> list[dict]:
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", '{"id":"{{.ID}}","name":"{{.Names}}","image":"{{.Image}}","status":"{{.Status}}","ports":"{{.Ports}}"}'],
            capture_output=True, text=True, timeout=10
        )
        containers = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if line:
                try:
                    containers.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return containers
    except Exception as exc:
        return [{"error": str(exc)}]


# ---------------------------------------------------------------------------
# Health polling
# ---------------------------------------------------------------------------

async def poll_node_health(name: str, node: dict) -> dict:
    if node.get("role") == "gateway" or name == "pc":
        # PC is local — check docker socket availability as proxy for health
        containers = get_docker_containers()
        health = {
            "name": name,
            "status": "online",
            "cpu_percent": 0,
            "ram_percent": 0,
            "disk_percent": 0,
            "containers": len(containers),
            "note": "PC self-health via docker socket",
        }
    else:
        try:
            health = await agent_get(node, "/health", timeout=8)
            health["status"] = "online"
        except Exception as exc:
            health = {"name": name, "status": "offline", "error": str(exc)}

    health["polled_at"] = datetime.utcnow().isoformat()
    node["last_health"] = health
    node["last_seen"] = health["polled_at"] if health.get("status") == "online" else node.get("last_seen")

    with get_db() as conn:
        conn.execute(
            "UPDATE nodes SET last_seen=?, last_health=? WHERE name=?",
            (node.get("last_seen"), json.dumps(health), name)
        )

    return health


async def poll_all_health() -> None:
    tasks = [poll_node_health(name, node) for name, node in _nodes.items()]
    await asyncio.gather(*tasks, return_exceptions=True)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class NodeRegister(BaseModel):
    name: str
    ip: str
    tailscale_ip: Optional[str] = None
    port: int = 7700
    token: str = "netoskeylocal"
    display: Optional[str] = None
    os: Optional[str] = None
    role: str = "node"


class ExecRequest(BaseModel):
    node: str
    cmd: str
    cwd: Optional[str] = None
    timeout: Optional[int] = 60


class DeployRequest(BaseModel):
    project: str
    node: Optional[str] = None


class IntentRequest(BaseModel):
    text: str
    source: Optional[str] = "api"


class ScheduleRequest(BaseModel):
    name: str
    cmd: str
    node: str
    cron: Optional[str] = None
    interval_seconds: Optional[int] = None


def _message_payload(message: dict) -> dict:
    payload = message.get("data")
    if isinstance(payload, dict):
        return payload
    return message


# ---------------------------------------------------------------------------
# Routes — Root dashboard
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root_dashboard():
    nodes_html = "".join(
        f'<div class="node"><b>{n}</b> — {d.get("display","")}'
        f' ({d.get("ip","")})'
        f' [{"&#x1F7E2;" if d.get("last_health",{}).get("status")=="online" else "&#x1F534;"}]</div>'
        for n, d in _nodes.items()
    )
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>net-os API</title>
<style>body{{font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:2em}}
.node{{margin:.5em 0;padding:.5em;background:#1a1a1a;border-radius:4px}}
a{{color:#4af}}</style></head>
<body>
<h1>net-os central API</h1>
<p>Status: <b style="color:#4f4">ONLINE</b></p>
<h2>Nodes</h2>{nodes_html}
<h2>Quick Links</h2>
<ul>
  <li><a href="/docs">API Docs (Swagger)</a></li>
  <li><a href="/status">/status (JSON)</a></li>
  <li><a href="/nodes">/nodes (JSON)</a></li>
  <li><a href="/schedule">/schedule (JSON)</a></li>
</ul>
<p><small>net-os v1.0.0</small></p>
</body></html>""")


# ---------------------------------------------------------------------------
# Routes — Status
# ---------------------------------------------------------------------------

@app.get("/status")
async def get_status(request: Request):
    verify_token(request)
    await poll_all_health()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "nodes": {
            name: {**node, "last_health": node.get("last_health", {})}
            for name, node in _nodes.items()
        },
        "docker_containers": get_docker_containers(),
        "scheduled_jobs": _list_jobs(),
        "recent_commands": _recent_commands[-20:],
    }


# ---------------------------------------------------------------------------
# Routes — Nodes
# ---------------------------------------------------------------------------

@app.get("/nodes")
async def list_nodes(request: Request):
    verify_token(request)
    ws_online_ids = set(_ws_nodes.keys())
    return {
        "nodes": {
            name: {
                **node,
                "ws_online": name.lower() in ws_online_ids,
            }
            for name, node in _nodes.items()
        }
    }


@app.post("/nodes/register", status_code=201)
async def register_node(body: NodeRegister, request: Request):
    verify_token(request)
    data = body.model_dump()
    data["registered_at"] = datetime.utcnow().isoformat()
    data["display"] = data.get("display") or body.name.capitalize()
    _nodes[body.name] = data

    with get_db() as conn:
        conn.execute("""
            INSERT INTO nodes (name, display, ip, tailscale_ip, port, os, role, token, registered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                display=excluded.display, ip=excluded.ip,
                tailscale_ip=excluded.tailscale_ip, port=excluded.port,
                os=excluded.os, role=excluded.role, token=excluded.token
        """, (
            body.name, data["display"], body.ip, body.tailscale_ip,
            body.port, body.os, body.role, body.token, data["registered_at"]
        ))

    return {"ok": True, "node": data}


@app.get("/nodes/{name}/health")
async def node_health(name: str, request: Request):
    verify_token(request)
    if name not in _nodes:
        raise HTTPException(404, f"Node '{name}' not found")
    health = await poll_node_health(name, _nodes[name])
    return health


# ---------------------------------------------------------------------------
# Routes — Exec
# ---------------------------------------------------------------------------

@app.post("/exec")
async def exec_remote(body: ExecRequest, request: Request):
    verify_token(request)

    if body.node not in _nodes:
        raise HTTPException(404, f"Node '{body.node}' not found")

    node = _nodes[body.node]

    if body.node == "pc" or node.get("role") == "gateway":
        result = exec_on_pc(body.cmd, body.cwd, body.timeout or 60)
    else:
        try:
            result = await agent_post(
                node, "/exec",
                {"cmd": body.cmd, "cwd": body.cwd, "timeout": body.timeout},
                timeout=body.timeout or 60,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"Node agent error: {exc}")

    _log_command(body.node, body.cmd, result.get("returncode", -1))
    return result


@app.post("/ws/exec/{node_id}")
async def exec_over_ws(node_id: str, body: ExecRequest, request: Request):
    verify_token(request)

    normalized_node_id = node_id.lower()
    websocket = _ws_nodes.get(normalized_node_id)
    if websocket is None:
        raise HTTPException(404, "Node not connected")

    req_id = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    _pending[req_id] = future

    try:
        await websocket.send_json({
            "type": "exec",
            "id": req_id,
            "cmd": body.cmd,
            "cwd": body.cwd,
            "timeout": body.timeout,
        })
        result = await asyncio.wait_for(future, timeout=body.timeout or 60)
    finally:
        _pending.pop(req_id, None)

    _log_command(normalized_node_id, body.cmd, result.get("returncode", -1), source="ws")
    return result


@app.get("/ws/nodes")
async def list_ws_nodes(request: Request):
    verify_token(request)
    return {
        "nodes": [
            {
                "id": node_id,
                "meta": _ws_meta.get(node_id, {}),
                "online": True,
            }
            for node_id in sorted(_ws_nodes.keys())
        ]
    }


@app.websocket("/ws/node/{node_id}")
async def node_websocket(websocket: WebSocket, node_id: str):
    normalized_node_id = node_id.lower()
    await websocket.accept()
    if not verify_ws_token(websocket):
        await websocket.close(code=4001)
        return

    _ws_nodes[normalized_node_id] = websocket
    logger.info("WebSocket node connected: %s", normalized_node_id)

    try:
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")
            payload = _message_payload(message)

            if message_type == "register":
                meta = payload.get("meta", {})
                existing_meta = _ws_meta.get(normalized_node_id, {})
                existing_meta.update(meta)
                _ws_meta[normalized_node_id] = existing_meta
                await websocket.send_json({"type": "ack"})
                await drain_node_queue(normalized_node_id, websocket)
            elif message_type == "heartbeat":
                metrics = payload.get("metrics", {})
                node_meta = _ws_meta.setdefault(normalized_node_id, {})
                node_meta.update(metrics)
            elif message_type == "result":
                req_id = payload.get("id")
                future = _pending.get(req_id)
                if future is not None and not future.done():
                    future.set_result(payload)
            elif message_type == "pong":
                continue
    except WebSocketDisconnect:
        logger.info("WebSocket node disconnected: %s", normalized_node_id)
    except Exception:
        logger.exception("WebSocket node error: %s", normalized_node_id)
    finally:
        _ws_nodes.pop(normalized_node_id, None)


# ---------------------------------------------------------------------------
# Routes — Deploy
# ---------------------------------------------------------------------------

@app.post("/deploy")
async def deploy_project(body: DeployRequest, request: Request):
    verify_token(request)

    if body.project not in _projects:
        raise HTTPException(404, f"Project '{body.project}' not found. Known: {list(_projects.keys())}")

    project = _projects[body.project]
    target_node = body.node or project.get("node", "pc")
    cmd = project["cmd"]

    if target_node not in _nodes:
        raise HTTPException(404, f"Target node '{target_node}' not found")

    node = _nodes[target_node]

    async def stream_deploy():
        yield f"[net-os] Deploying '{body.project}' to node '{target_node}'...\n"
        yield f"[net-os] CMD: {cmd}\n"
        yield "-" * 60 + "\n"

        if target_node == "pc":
            result = exec_on_pc(cmd)
            yield result.get("stdout", "") or ""
            if result.get("stderr"):
                yield f"\n[stderr] {result['stderr']}"
            yield f"\n[net-os] Exited with code {result.get('returncode', '?')}\n"
        else:
            token = node.get("token", NODE_TOKEN)
            url = f"{node_agent_url(node)}/deploy/{body.project}"
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream("POST", url, headers={"X-Node-Token": token}) as resp:
                    async for chunk in resp.aiter_text():
                        yield chunk

        _log_command(target_node, f"deploy:{body.project}", 0)

    return StreamingResponse(stream_deploy(), media_type="text/plain")


# ---------------------------------------------------------------------------
# Routes — Intent (NL dispatch, rule-based)
# ---------------------------------------------------------------------------

INTENT_PATTERNS: list[tuple[str, str, Any]] = [
    (r"deploy (.+)", "deploy", lambda m: {"project": m.group(1).strip()}),
    (r"status|how.*(nodes|network|system)", "status", lambda m: {}),
    (r"(restart|reboot) (.+)", "exec", lambda m: {"node": m.group(2).strip(), "cmd": "reboot"}),
    (r"run (.+) on (.+)", "exec", lambda m: {"cmd": m.group(1).strip(), "node": m.group(2).strip()}),
    (r"exec(?:ute)? (.+) on (.+)", "exec", lambda m: {"cmd": m.group(1).strip(), "node": m.group(2).strip()}),
    (r"(list|show) (nodes|machines)", "nodes", lambda m: {}),
    (r"(list|show) (jobs|schedule)", "schedule", lambda m: {}),
    (r"logs? (?:from|for|on) (.+)", "logs", lambda m: {"node": m.group(1).strip()}),
]


@app.post("/intent")
async def handle_intent(body: IntentRequest, request: Request):
    verify_token(request)

    text = body.text.lower().strip()

    for pattern, action, extractor in INTENT_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            params = extractor(m)
            result = await _dispatch_intent(action, params)
            return {
                "intent": action,
                "params": params,
                "result": result,
                "matched_pattern": pattern,
                "source": body.source,
            }

    return {
        "intent": "unknown",
        "result": "Could not understand the command. Try: 'deploy robot-tank', 'status', 'run uptime on pi'",
        "text": body.text,
    }


async def _dispatch_intent(action: str, params: dict) -> Any:
    if action == "deploy":
        project = params.get("project", "")
        if project not in _projects:
            return f"Unknown project: {project}. Known: {list(_projects.keys())}"
        proj = _projects[project]
        node_name = proj.get("node", "pc")
        node = _nodes.get(node_name)
        if not node:
            return f"Target node '{node_name}' not found"
        if node_name == "pc":
            return exec_on_pc(proj["cmd"])
        return await agent_post(node, f"/deploy/{project}", {})

    elif action == "status":
        await poll_all_health()
        return {n: d.get("last_health", {"status": "unknown"}) for n, d in _nodes.items()}

    elif action == "nodes":
        return list(_nodes.keys())

    elif action == "schedule":
        return _list_jobs()

    elif action == "exec":
        node_name = params.get("node", "pc")
        cmd = params.get("cmd", "echo ok")
        node = _nodes.get(node_name)
        if not node:
            return f"Node '{node_name}' not found"
        if node_name == "pc":
            return exec_on_pc(cmd)
        return await agent_post(node, "/exec", {"cmd": cmd})

    elif action == "logs":
        node_name = params.get("node", "pc")
        node = _nodes.get(node_name)
        if not node:
            return f"Node '{node_name}' not found"
        log_cmd = "journalctl -n 50 --no-pager" if node.get("os") != "windows" else "Get-EventLog -Newest 50 Application"
        if node_name == "pc":
            return exec_on_pc(log_cmd)
        return await agent_post(node, "/exec", {"cmd": log_cmd})

    return f"No handler for action: {action}"


# ---------------------------------------------------------------------------
# Routes — Schedule
# ---------------------------------------------------------------------------

def _list_jobs() -> list[dict]:
    jobs = []
    for job in _scheduler.get_jobs():
        if job.id.startswith("__"):
            continue
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return jobs


@app.get("/schedule")
async def list_schedule(request: Request):
    verify_token(request)
    return {"jobs": _list_jobs()}


@app.post("/schedule", status_code=201)
async def add_schedule(body: ScheduleRequest, request: Request):
    verify_token(request)

    if body.node not in _nodes:
        raise HTTPException(404, f"Node '{body.node}' not found")

    node = _nodes[body.node]
    job_id = f"job_{body.name}_{int(time.time())}"

    async def run_scheduled():
        if body.node == "pc":
            result = exec_on_pc(body.cmd)
        else:
            result = await agent_post(node, "/exec", {"cmd": body.cmd})
        _log_command(body.node, body.cmd, result.get("returncode", -1))
        with get_db() as conn:
            conn.execute(
                "UPDATE jobs SET last_run=?, last_result=? WHERE id=?",
                (datetime.utcnow().isoformat(), json.dumps(result), job_id)
            )

    if body.cron:
        trigger = CronTrigger.from_crontab(body.cron)
    elif body.interval_seconds:
        trigger = IntervalTrigger(seconds=body.interval_seconds)
    else:
        raise HTTPException(400, "Must provide 'cron' or 'interval_seconds'")

    _scheduler.add_job(run_scheduled, trigger=trigger, id=job_id, name=body.name, replace_existing=True)

    with get_db() as conn:
        conn.execute("""
            INSERT INTO jobs (id, name, cmd, node, cron, interval_seconds, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
        """, (job_id, body.name, body.cmd, body.node, body.cron, body.interval_seconds, datetime.utcnow().isoformat()))

    return {"ok": True, "job_id": job_id, "trigger": str(trigger)}


@app.delete("/schedule/{job_id}")
async def delete_schedule(job_id: str, request: Request):
    verify_token(request)
    try:
        _scheduler.remove_job(job_id)
    except Exception:
        raise HTTPException(404, f"Job '{job_id}' not found")
    with get_db() as conn:
        conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    return {"ok": True, "deleted": job_id}


# ---------------------------------------------------------------------------
# Routes — Logs
# ---------------------------------------------------------------------------

@app.get("/logs/{node}")
async def get_logs(node: str, request: Request, lines: int = 50):
    verify_token(request)
    if node not in _nodes:
        raise HTTPException(404, f"Node '{node}' not found")

    node_data = _nodes[node]
    os_type = node_data.get("os", "linux")

    if os_type == "linux":
        cmd = f"journalctl -n {lines} --no-pager"
    else:
        cmd = f"powershell -Command \"Get-EventLog -LogName Application -Newest {lines} | Format-List\""

    if node == "pc":
        result = exec_on_pc(cmd)
    else:
        try:
            result = await agent_post(node_data, "/exec", {"cmd": cmd}, timeout=30)
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"Node agent error: {exc}")

    return {"node": node, "lines": lines, "output": result.get("stdout", ""), "stderr": result.get("stderr", "")}


# ---------------------------------------------------------------------------
# Bootstrap endpoints (for onboard-node.sh)
# ---------------------------------------------------------------------------

@app.get("/bootstrap/node-agent.py")
async def serve_agent_py():
    """Serve the node agent script for new node bootstrapping."""
    agent_candidates = [
        Path("/app/node-agent/agent.py"),
        Path("/configs/../node-agent/agent.py"),
        Path(__file__).parent.parent / "node-agent" / "agent.py",
    ]
    for candidate in agent_candidates:
        if candidate.exists():
            return HTMLResponse(candidate.read_text(), media_type="text/plain")
    raise HTTPException(404, "node-agent.py not found on server")


@app.post("/onboard/ssh-key")
async def receive_ssh_key(request: Request):
    """Receive a new node's SSH public key and add to authorized_keys."""
    verify_token(request)
    body = await request.json()
    pubkey = body.get("pubkey", "").strip()
    node_name = body.get("name", "unknown")
    if not pubkey:
        raise HTTPException(400, "Missing pubkey")

    auth_keys = Path.home() / ".ssh" / "authorized_keys"
    auth_keys.parent.mkdir(exist_ok=True, mode=0o700)
    existing = auth_keys.read_text() if auth_keys.exists() else ""
    if pubkey not in existing:
        with auth_keys.open("a") as f:
            f.write(f"\n# net-os: {node_name}\n{pubkey}\n")

    return {"ok": True, "message": f"SSH key for '{node_name}' added"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_command(node: str, cmd: str, returncode: int, source: str = "api") -> None:
    entry = {
        "ts": datetime.utcnow().isoformat(),
        "node": node,
        "cmd": cmd,
        "returncode": returncode,
        "source": source,
    }
    _recent_commands.append(entry)
    if len(_recent_commands) > 200:
        _recent_commands.pop(0)

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO command_log (ts, node, cmd, returncode, source) VALUES (?, ?, ?, ?, ?)",
                (entry["ts"], node, cmd[:500], returncode, source)
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")

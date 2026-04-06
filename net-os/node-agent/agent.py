"""
net-os node-agent
Runs on every non-PC node (laptop, Pi).
Port 7700, auth via X-Node-Token header.
"""

import asyncio
import inspect
import json
import logging
import os
import platform
import subprocess
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Optional

import psutil
import uvicorn
import websockets
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
PROJECTS_FILE = BASE_DIR / "projects.json"

NODE_TOKEN = os.environ.get("NODE_TOKEN", "netoskeylocal")
PORT = int(os.environ.get("NODE_PORT", "7700"))

_config: dict = {}
_projects: dict = {}
_hub_task: Optional[asyncio.Task] = None

BOOT_TIME = time.time()
logger = logging.getLogger("net-os-agent")


def load_config() -> None:
    global _config, _projects
    if CONFIG_FILE.exists():
        _config = json.loads(CONFIG_FILE.read_text())
    else:
        _config = {
            "name": platform.node(),
            "pc_ip": "192.168.0.27",
            "port": PORT,
            "hub_ws_url": "ws://100.99.89.118:8080",
        }

    if PROJECTS_FILE.exists():
        _projects = json.loads(PROJECTS_FILE.read_text())
    else:
        _projects = {}


load_config()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _hub_task
    load_config()
    _hub_task = asyncio.create_task(hub_connect())
    try:
        yield
    finally:
        if _hub_task is not None:
            _hub_task.cancel()
            with suppress(asyncio.CancelledError):
                await _hub_task
            _hub_task = None


app = FastAPI(title="net-os node-agent", version="1.0.0", lifespan=lifespan)

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
    token = request.headers.get("X-Node-Token") or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if token != NODE_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Node-Token",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_tailscale_ip() -> Optional[str]:
    """Attempt to read Tailscale IP from the OS."""
    try:
        result = subprocess.run(
            ["tailscale", "ip", "--4"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_local_ip() -> str:
    """Return primary LAN IP."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def get_node_id() -> str:
    return _config.get("name", platform.node()).lower().replace(" ", "-")


def _run_command(cmd: str, cwd: Optional[str], timeout: int) -> dict:
    run_kwargs = {
        "args": cmd,
        "shell": True,
        "capture_output": True,
        "text": True,
        "timeout": timeout,
        "env": os.environ.copy(),
    }
    if cwd:
        run_kwargs["cwd"] = cwd

    try:
        result = subprocess.run(**run_kwargs)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Command timed out", "returncode": -1}
    except Exception as exc:
        return {"stdout": "", "stderr": str(exc), "returncode": -1}


async def handle_hub_message(ws, msg: dict) -> None:
    message_type = msg.get("type")

    if message_type == "exec":
        timeout = msg.get("timeout") or 60
        result = await asyncio.to_thread(_run_command, msg.get("cmd", ""), msg.get("cwd"), timeout)
        await ws.send(json.dumps({
            "type": "result",
            "id": msg.get("id"),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "returncode": result.get("returncode", -1),
        }))
    elif message_type == "ack":
        logger.info("registered with hub")
    elif message_type == "ping":
        await ws.send(json.dumps({"type": "pong"}))


def _ws_connect_kwargs(url: str) -> dict:
    connect_kwargs = {
        "uri": url,
        "ping_interval": 20,
        "ping_timeout": 10,
        "close_timeout": 5,
    }
    header_key = "additional_headers" if "additional_headers" in inspect.signature(websockets.connect).parameters else "extra_headers"
    connect_kwargs[header_key] = {"X-Node-Token": NODE_TOKEN}
    return connect_kwargs


async def hub_connect():
    node_id = get_node_id()
    hub = _config.get("hub_ws_url", "ws://100.99.89.118:8080").rstrip("/")
    url = f"{hub}/ws/node/{node_id}?token={NODE_TOKEN}"
    backoff = 1

    while True:
        try:
            async with websockets.connect(**_ws_connect_kwargs(url)) as ws:
                backoff = 1
                logger.info("Connected to hub at %s", hub)

                await ws.send(json.dumps({
                    "type": "register",
                    "meta": {
                        "name": _config.get("name", platform.node()),
                        "os": platform.system(),
                        "ip": get_local_ip(),
                        "tailscale_ip": get_tailscale_ip(),
                        "python": platform.python_version(),
                    },
                }))

                async def heartbeat():
                    while True:
                        await asyncio.sleep(30)
                        try:
                            disk = psutil.disk_usage("/")
                            await ws.send(json.dumps({
                                "type": "heartbeat",
                                "metrics": {
                                    "cpu_percent": psutil.cpu_percent(interval=0.1),
                                    "ram_percent": psutil.virtual_memory().percent,
                                    "disk_percent": disk.percent,
                                    "uptime_seconds": int(time.time() - psutil.boot_time()),
                                },
                            }))
                        except Exception:
                            break

                hb = asyncio.create_task(heartbeat())
                try:
                    async for raw in ws:
                        msg = json.loads(raw)
                        await handle_hub_message(ws, msg)
                finally:
                    hb.cancel()
                    with suppress(asyncio.CancelledError):
                        await hb
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Hub disconnected: %s. Retry in %ss", exc, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ExecRequest(BaseModel):
    cmd: str
    cwd: Optional[str] = None
    timeout: Optional[int] = 60


class DeployRequest(BaseModel):
    env: Optional[dict] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health(request: Request):
    verify_token(request)
    disk = psutil.disk_usage("/")
    return {
        "name": _config.get("name", platform.node()),
        "os": platform.system(),
        "os_version": platform.version(),
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "ram_percent": psutil.virtual_memory().percent,
        "disk_percent": disk.percent,
        "uptime_seconds": int(time.time() - psutil.boot_time()),
        "agent_uptime_seconds": int(time.time() - BOOT_TIME),
        "ip": get_local_ip(),
        "tailscale_ip": get_tailscale_ip(),
        "python": platform.python_version(),
    }


@app.post("/exec")
async def exec_cmd(body: ExecRequest, request: Request):
    verify_token(request)
    result = await asyncio.to_thread(_run_command, body.cmd, body.cwd, body.timeout or 60)
    result["cmd"] = body.cmd
    return result


@app.post("/deploy/{project_name}")
async def deploy_project(project_name: str, request: Request):
    verify_token(request)

    if project_name not in _projects:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_name}' not found. Known: {list(_projects.keys())}",
        )

    project = _projects[project_name]
    cmd = project.get("cmd", "")
    cwd = project.get("cwd")

    async def stream_output():
        yield f"[net-os] Deploying {project_name}...\n"
        yield f"[net-os] CMD: {cmd}\n"
        yield "-" * 60 + "\n"

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )

        async for line in proc.stdout:
            yield line.decode(errors="replace")

        await proc.wait()
        yield f"\n[net-os] Exited with code {proc.returncode}\n"

    return StreamingResponse(stream_output(), media_type="text/plain")


@app.get("/projects")
async def list_projects(request: Request):
    verify_token(request)
    return {
        "projects": {
            name: {
                "description": info.get("description", ""),
                "cmd": info.get("cmd", ""),
                "node": info.get("node", "local"),
            }
            for name, info in _projects.items()
        }
    }


@app.get("/ping")
async def ping():
    """Unauthenticated ping for basic connectivity checks."""
    return {"pong": True, "name": _config.get("name", platform.node())}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"[net-os agent] Starting on port {PORT}")
    print(f"[net-os agent] Node: {_config.get('name', platform.node())}")
    print(f"[net-os agent] Projects: {list(_projects.keys())}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

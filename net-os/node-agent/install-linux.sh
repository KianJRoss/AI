#!/usr/bin/env bash
# net-os node-agent installer for Linux (Pi / Debian)
# Run as root: sudo bash install-linux.sh
set -e

INSTALL_DIR="/opt/net-os-agent"
SERVICE_NAME="net-os-agent"
NODE_TOKEN="${NODE_TOKEN:-netoskeylocal}"
PC_IP="${PC_IP:-192.168.0.27}"
NODE_NAME="${NODE_NAME:-KianPotPi}"
PORT="${PORT:-7700}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== net-os node-agent installer (Linux) ==="
echo "Install dir : $INSTALL_DIR"
echo "Node name   : $NODE_NAME"
echo "PC IP       : $PC_IP"
echo "Port        : $PORT"
echo ""

# ---------------------------------------------------------------------------
# 1. Ensure Python 3 + pip
# ---------------------------------------------------------------------------
if ! command -v python3 &>/dev/null; then
    echo "[+] Installing python3..."
    apt-get update -qq && apt-get install -y -qq python3 python3-pip python3-venv
else
    echo "[ok] python3 found: $(python3 --version)"
fi

if ! command -v pip3 &>/dev/null; then
    echo "[+] Installing pip3..."
    apt-get install -y -qq python3-pip
fi

# ---------------------------------------------------------------------------
# 2. Ensure uv
# ---------------------------------------------------------------------------
if ! command -v uv &>/dev/null; then
    echo "[+] Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
    # Also symlink for system-wide use
    UV_BIN="$(command -v uv 2>/dev/null || echo $HOME/.local/bin/uv)"
    ln -sf "$UV_BIN" /usr/local/bin/uv 2>/dev/null || true
else
    echo "[ok] uv found: $(uv --version)"
fi

# ---------------------------------------------------------------------------
# 3. Create install directory
# ---------------------------------------------------------------------------
echo "[+] Creating $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# ---------------------------------------------------------------------------
# 4. Copy agent.py
# ---------------------------------------------------------------------------
if [[ -f "$SCRIPT_DIR/agent.py" ]]; then
    cp "$SCRIPT_DIR/agent.py" "$INSTALL_DIR/agent.py"
    echo "[ok] agent.py copied from $SCRIPT_DIR"
elif [[ -f "$(dirname "$0")/agent.py" ]]; then
    cp "$(dirname "$0")/agent.py" "$INSTALL_DIR/agent.py"
    echo "[ok] agent.py copied"
else
    echo "[!!] agent.py not found next to installer. Attempting download from PC..."
    curl -fsSL "http://$PC_IP:8080/bootstrap/node-agent.py" -o "$INSTALL_DIR/agent.py" || {
        echo "[!!] Could not download agent.py. Place it at $INSTALL_DIR/agent.py manually."
        exit 1
    }
fi

# ---------------------------------------------------------------------------
# 5. Create config.json
# ---------------------------------------------------------------------------
cat > "$INSTALL_DIR/config.json" <<EOF
{
  "name": "$NODE_NAME",
  "pc_ip": "$PC_IP",
  "port": $PORT,
  "hub_ws_url": "ws://100.99.89.118:8080"
}
EOF
echo "[ok] config.json written"

# ---------------------------------------------------------------------------
# 6. Create projects.json
# ---------------------------------------------------------------------------
cat > "$INSTALL_DIR/projects.json" <<'EOF'
{
  "robot-tank": {
    "node": "pi",
    "cmd": "cd ~/robot-tank && git pull && python3 tools/deploy_rp2040.py",
    "cwd": null,
    "description": "Deploy robot-tank firmware to RP2040"
  }
}
EOF
echo "[ok] projects.json written"

# ---------------------------------------------------------------------------
# 7. Create .env
# ---------------------------------------------------------------------------
cat > "$INSTALL_DIR/.env" <<EOF
NODE_TOKEN=$NODE_TOKEN
NODE_PORT=$PORT
EOF
chmod 600 "$INSTALL_DIR/.env"
echo "[ok] .env written (token: $NODE_TOKEN)"

# ---------------------------------------------------------------------------
# 8. Install Python dependencies via uv venv
# ---------------------------------------------------------------------------
echo "[+] Creating Python venv and installing dependencies..."
uv venv "$INSTALL_DIR/.venv" --python python3 2>/dev/null || python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --quiet fastapi "uvicorn[standard]" psutil pydantic websockets 2>&1 | tail -5
echo "[ok] Python deps installed"

# ---------------------------------------------------------------------------
# 9. Create systemd service
# ---------------------------------------------------------------------------
PYTHON_BIN="$INSTALL_DIR/.venv/bin/python3"
UVICORN_BIN="$INSTALL_DIR/.venv/bin/uvicorn"

cat > "/etc/systemd/system/$SERVICE_NAME.service" <<EOF
[Unit]
Description=net-os Node Agent
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$UVICORN_BIN agent:app --host 0.0.0.0 --port $PORT
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=net-os-agent

[Install]
WantedBy=multi-user.target
EOF

echo "[ok] systemd service written"

# ---------------------------------------------------------------------------
# 10. Enable and start
# ---------------------------------------------------------------------------
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
echo "[ok] Service enabled and started"

# ---------------------------------------------------------------------------
# 11. Verify
# ---------------------------------------------------------------------------
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo ""
    echo "=== INSTALLATION COMPLETE ==="
    echo "Node agent is RUNNING on port $PORT"
    echo "Health check: curl -H 'X-Node-Token: $NODE_TOKEN' http://localhost:$PORT/health"
    echo "Ping (no auth): curl http://localhost:$PORT/ping"
    echo ""
    echo "Logs: journalctl -u $SERVICE_NAME -f"
else
    echo "[!!] Service failed to start. Check: journalctl -u $SERVICE_NAME -e"
    exit 1
fi

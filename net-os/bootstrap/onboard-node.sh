#!/usr/bin/env bash
# net-os universal node onboarding script
# Usage: curl http://192.168.0.27:8080/bootstrap/onboard.sh | bash -s -- --name lenovo --pc-ip 192.168.0.27
#
# Or with custom token and port:
#   curl ... | bash -s -- --name mynode --pc-ip 192.168.0.27 --token mytoken --port 7700

set -e

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

NODE_NAME=""
PC_IP="192.168.0.27"
PC_PORT="8080"
NODE_PORT="7700"
NODE_TOKEN="${NODE_TOKEN:-netoskeylocal}"
API_TOKEN="${NET_OS_API_TOKEN:-netosmasterkey}"
INSTALL_DIR="/opt/net-os-agent"
SKIP_TAILSCALE=0
TAILSCALE_AUTHKEY="${TAILSCALE_AUTHKEY:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)        NODE_NAME="$2";      shift 2 ;;
        --pc-ip)       PC_IP="$2";          shift 2 ;;
        --pc-port)     PC_PORT="$2";        shift 2 ;;
        --port)        NODE_PORT="$2";      shift 2 ;;
        --token)       NODE_TOKEN="$2";     shift 2 ;;
        --api-token)   API_TOKEN="$2";      shift 2 ;;
        --no-tailscale) SKIP_TAILSCALE=1;   shift ;;
        --ts-authkey)  TAILSCALE_AUTHKEY="$2"; shift 2 ;;
        *) echo "[!!] Unknown arg: $1"; exit 1 ;;
    esac
done

if [[ -z "$NODE_NAME" ]]; then
    NODE_NAME="$(hostname -s)"
    echo "[warn] --name not provided, using hostname: $NODE_NAME"
fi

API_BASE="http://$PC_IP:$PC_PORT"

echo ""
echo "============================================="
echo "  net-os Node Onboarding"
echo "============================================="
echo "  Node name : $NODE_NAME"
echo "  PC API    : $API_BASE"
echo "  Agent port: $NODE_PORT"
echo "  Install   : $INSTALL_DIR"
echo "============================================="
echo ""

# Check root
if [[ $EUID -ne 0 ]]; then
    echo "[!!] This script must be run as root (use sudo)"
    exit 1
fi

# ---------------------------------------------------------------------------
# Helper: detect package manager
# ---------------------------------------------------------------------------
install_pkg() {
    if command -v apt-get &>/dev/null; then
        apt-get install -y -qq "$@"
    elif command -v yum &>/dev/null; then
        yum install -y -q "$@"
    elif command -v dnf &>/dev/null; then
        dnf install -y -q "$@"
    elif command -v pacman &>/dev/null; then
        pacman -Sy --noconfirm "$@"
    else
        echo "[!!] Unknown package manager — install $* manually"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Step 1: Install Tailscale
# ---------------------------------------------------------------------------
if [[ $SKIP_TAILSCALE -eq 0 ]]; then
    echo "[1/6] Tailscale..."
    if ! command -v tailscale &>/dev/null; then
        echo "  Installing Tailscale..."
        curl -fsSL https://tailscale.com/install.sh | sh
    else
        echo "  Tailscale already installed: $(tailscale --version | head -1)"
    fi

    # Check if connected
    TS_STATUS=$(tailscale status --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('BackendState',''))" 2>/dev/null || echo "")

    if [[ "$TS_STATUS" != "Running" ]]; then
        echo ""
        echo "  [!] Tailscale not connected. Starting..."
        if [[ -n "$TAILSCALE_AUTHKEY" ]]; then
            tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="net-os-$NODE_NAME" --accept-routes
            echo "  [ok] Tailscale connected with authkey"
        else
            tailscale up --hostname="net-os-$NODE_NAME" --accept-routes &
            TS_PID=$!
            echo ""
            echo "  ============================================"
            echo "  ACTION REQUIRED: Open the URL above in a browser"
            echo "  to authenticate this node with Tailscale."
            echo "  Waiting up to 120 seconds..."
            echo "  ============================================"
            for i in $(seq 1 24); do
                sleep 5
                TS_STATUS=$(tailscale status --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('BackendState',''))" 2>/dev/null || echo "")
                if [[ "$TS_STATUS" == "Running" ]]; then
                    echo "  [ok] Tailscale connected!"
                    break
                fi
                echo "  Waiting... ($((i*5))s)"
            done
        fi
    else
        echo "  [ok] Tailscale already running"
    fi

    TAILSCALE_IP=$(tailscale ip --4 2>/dev/null || echo "")
    echo "  Tailscale IP: ${TAILSCALE_IP:-unavailable}"
else
    echo "[1/6] Tailscale — SKIPPED (--no-tailscale)"
    TAILSCALE_IP=""
fi

# ---------------------------------------------------------------------------
# Step 2: Generate SSH keypair for this node
# ---------------------------------------------------------------------------
echo ""
echo "[2/6] SSH key generation..."

SSH_DIR="/root/.ssh"
KEY_FILE="$SSH_DIR/net-os-node"

mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

if [[ ! -f "$KEY_FILE" ]]; then
    ssh-keygen -t ed25519 -f "$KEY_FILE" -N "" -C "net-os-$NODE_NAME@$(hostname)" -q
    echo "  [ok] SSH keypair generated at $KEY_FILE"
else
    echo "  [ok] SSH keypair already exists at $KEY_FILE"
fi

PUBKEY="$(cat "$KEY_FILE.pub")"
echo "  Public key: ${PUBKEY:0:50}..."

# POST public key to PC API
echo "  Sending public key to PC API..."
RESPONSE=$(curl -sfS -X POST "$API_BASE/onboard/ssh-key" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$NODE_NAME\", \"pubkey\": \"$PUBKEY\"}" 2>&1) && {
    echo "  [ok] Public key registered on PC"
} || {
    echo "  [warn] Could not register SSH key on PC: $RESPONSE"
    echo "  [warn] You may need to add it manually: cat $KEY_FILE.pub >> ~/.ssh/authorized_keys (on PC)"
}

# ---------------------------------------------------------------------------
# Step 3: Install Python + uv + download node-agent
# ---------------------------------------------------------------------------
echo ""
echo "[3/6] Installing agent..."

# Python 3
if ! command -v python3 &>/dev/null; then
    echo "  Installing python3..."
    apt-get update -qq
    install_pkg python3 python3-pip python3-venv
fi
echo "  Python: $(python3 --version)"

# uv
if ! command -v uv &>/dev/null; then
    echo "  Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
    ln -sf "$(command -v uv 2>/dev/null || echo $HOME/.local/bin/uv)" /usr/local/bin/uv 2>/dev/null || true
fi

mkdir -p "$INSTALL_DIR"

# Download agent.py from PC
echo "  Downloading agent from PC ($API_BASE/bootstrap/node-agent.py)..."
if curl -fsSL "$API_BASE/bootstrap/node-agent.py" -o "$INSTALL_DIR/agent.py" 2>/dev/null; then
    echo "  [ok] agent.py downloaded"
else
    echo "  [warn] Could not download from PC API. Checking if agent.py is already present..."
    if [[ ! -f "$INSTALL_DIR/agent.py" ]]; then
        echo "  [!!] agent.py not found. Cannot proceed."
        echo "  Place agent.py at $INSTALL_DIR/agent.py manually and re-run."
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Step 4: Configure and install as systemd service
# ---------------------------------------------------------------------------
echo ""
echo "[4/6] Installing systemd service..."

# config.json
cat > "$INSTALL_DIR/config.json" <<EOF
{
  "name": "$NODE_NAME",
  "pc_ip": "$PC_IP",
  "port": $NODE_PORT
}
EOF

# projects.json (empty by default — user can populate)
if [[ ! -f "$INSTALL_DIR/projects.json" ]]; then
    echo '{}' > "$INSTALL_DIR/projects.json"
fi

# .env
cat > "$INSTALL_DIR/.env" <<EOF
NODE_TOKEN=$NODE_TOKEN
NODE_PORT=$NODE_PORT
EOF
chmod 600 "$INSTALL_DIR/.env"

# Python venv
uv venv "$INSTALL_DIR/.venv" --python python3 2>/dev/null || python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --quiet fastapi "uvicorn[standard]" psutil pydantic

UVICORN="$INSTALL_DIR/.venv/bin/uvicorn"

cat > "/etc/systemd/system/net-os-agent.service" <<EOF
[Unit]
Description=net-os Node Agent ($NODE_NAME)
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$UVICORN agent:app --host 0.0.0.0 --port $NODE_PORT
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=net-os-agent

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable net-os-agent
systemctl restart net-os-agent
echo "  [ok] systemd service enabled and started"

sleep 2
if ! systemctl is-active --quiet net-os-agent; then
    echo "  [!!] Service failed to start. Check: journalctl -u net-os-agent -e"
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 5: Register node with PC API
# ---------------------------------------------------------------------------
echo ""
echo "[5/6] Registering node with PC API..."

LOCAL_IP=$(python3 -c "import socket; s=socket.socket(); s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()" 2>/dev/null || hostname -I | awk '{print $1}')
OS_TYPE="linux"

REG_RESPONSE=$(curl -sfS -X POST "$API_BASE/nodes/register" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"$NODE_NAME\",
        \"ip\": \"$LOCAL_IP\",
        \"tailscale_ip\": \"${TAILSCALE_IP:-null}\",
        \"port\": $NODE_PORT,
        \"token\": \"$NODE_TOKEN\",
        \"os\": \"$OS_TYPE\",
        \"role\": \"node\",
        \"display\": \"$NODE_NAME\"
    }" 2>&1) && {
    echo "  [ok] Node registered with PC"
} || {
    echo "  [warn] Could not auto-register: $REG_RESPONSE"
    echo "  [warn] You can register manually:"
    echo "    curl -X POST $API_BASE/nodes/register -H 'Authorization: Bearer $API_TOKEN' \\"
    echo "      -H 'Content-Type: application/json' \\"
    echo "      -d '{\"name\":\"$NODE_NAME\",\"ip\":\"$LOCAL_IP\",\"port\":$NODE_PORT,\"token\":\"$NODE_TOKEN\"}'"
}

# ---------------------------------------------------------------------------
# Step 6: Verify
# ---------------------------------------------------------------------------
echo ""
echo "[6/6] Verifying..."

sleep 1
HEALTH_RESP=$(curl -sfS -H "X-Node-Token: $NODE_TOKEN" "http://localhost:$NODE_PORT/health" 2>/dev/null || echo "FAILED")
if echo "$HEALTH_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  CPU:', d.get('cpu_percent'), '% | RAM:', d.get('ram_percent'), '%')" 2>/dev/null; then
    echo "  [ok] Agent health check passed"
else
    echo "  [warn] Health check response: $HEALTH_RESP"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "============================================="
echo "  Node '$NODE_NAME' ONBOARDED SUCCESSFULLY"
echo "============================================="
echo "  Local IP    : $LOCAL_IP"
echo "  Tailscale IP: ${TAILSCALE_IP:-not connected}"
echo "  Agent URL   : http://$LOCAL_IP:$NODE_PORT"
echo "  Health      : curl -H 'X-Node-Token: $NODE_TOKEN' http://$LOCAL_IP:$NODE_PORT/health"
echo "  Logs        : journalctl -u net-os-agent -f"
echo ""
echo "  PC can now reach this node at:"
echo "  http://$LOCAL_IP:$NODE_PORT"
echo "============================================="

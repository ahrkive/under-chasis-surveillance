#!/usr/bin/env bash
# ============================================================================
# Raspberry Pi Edge Device — Setup Script
# ============================================================================
# This script installs all dependencies and configures the inspection bot
# as a systemd service on Raspberry Pi OS (64-bit Bookworm).
#
# Usage:
#   chmod +x install.sh
#   sudo ./install.sh
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="inspection-bot"
VENV_DIR="${SCRIPT_DIR}/venv"
USER_NAME="${SUDO_USER:-pi}"

echo "=============================================="
echo "  Vehicle Undercarriage Inspection Bot Setup"
echo "=============================================="
echo ""

# ── 1. System packages ──────────────────────────────────────────────────────
echo "[1/6] Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    python3-venv \
    python3-pip \
    python3-dev \
    python3-picamera2 \
    python3-libcamera \
    libcamera-dev \
    libcap-dev \
    libatlas-base-dev \
    libjpeg-dev \
    libopenjp2-7 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev

echo "  ✓ System packages installed."

# ── 2. Python virtual environment ───────────────────────────────────────────
echo "[2/6] Creating Python virtual environment..."
if [ -d "${VENV_DIR}" ]; then
    echo "  Virtual environment already exists. Updating..."
else
    python3 -m venv "${VENV_DIR}" --system-site-packages
    echo "  ✓ Virtual environment created at ${VENV_DIR}"
fi

# Activate and install Python deps
source "${VENV_DIR}/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "${SCRIPT_DIR}/requirements.txt"
echo "  ✓ Python dependencies installed."

# ── 3. Enable camera interface ──────────────────────────────────────────────
echo "[3/6] Ensuring camera interface is enabled..."
if ! grep -q "^start_x=1" /boot/config.txt 2>/dev/null; then
    # For newer Pi OS with libcamera, camera is enabled by default
    # but we ensure the GPU memory is sufficient
    if grep -q "^gpu_mem=" /boot/config.txt; then
        sed -i 's/^gpu_mem=.*/gpu_mem=128/' /boot/config.txt
    else
        echo "gpu_mem=128" >> /boot/config.txt
    fi
fi
echo "  ✓ Camera interface configured."

# ── 4. Create buffer directory ──────────────────────────────────────────────
echo "[4/6] Creating buffer directory..."
BUFFER_DIR="${SCRIPT_DIR}/buffer"
mkdir -p "${BUFFER_DIR}"
chown -R "${USER_NAME}:${USER_NAME}" "${BUFFER_DIR}"
echo "  ✓ Buffer directory created at ${BUFFER_DIR}"

# ── 5. Create .env from template ────────────────────────────────────────────
echo "[5/6] Setting up environment configuration..."
ENV_FILE="${SCRIPT_DIR}/.env"
if [ ! -f "${ENV_FILE}" ]; then
    if [ -f "${SCRIPT_DIR}/../.env.example" ]; then
        # Extract edge-relevant vars from root .env.example
        grep -E "^(EDGE_|LOG_LEVEL)" "${SCRIPT_DIR}/../.env.example" > "${ENV_FILE}" || true
        echo "  ✓ Created .env from template. EDIT THIS FILE with your server URL and API key!"
    else
        cat > "${ENV_FILE}" << 'EOF'
EDGE_BOT_ID=bot-001
EDGE_SERVER_URL=ws://YOUR_SERVER_IP:8000/ws/edge/bot-001
EDGE_API_KEY=change-me-to-a-secure-key
EDGE_CAPTURE_INTERVAL_SEC=2
EDGE_IMAGE_QUALITY=85
EDGE_IMAGE_WIDTH=640
EDGE_IMAGE_HEIGHT=480
EDGE_BUFFER_DIR=./buffer
EDGE_MAX_BUFFER_SIZE_MB=500
EDGE_HTTP_FALLBACK_URL=http://YOUR_SERVER_IP:8000/api/inspections/upload
LOG_LEVEL=INFO
EOF
        echo "  ✓ Created default .env. EDIT THIS FILE with your server URL and API key!"
    fi
else
    echo "  .env already exists. Skipping."
fi
chown "${USER_NAME}:${USER_NAME}" "${ENV_FILE}"

# ── 6. Create systemd service ───────────────────────────────────────────────
echo "[6/6] Installing systemd service..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Vehicle Undercarriage Inspection Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USER_NAME}
Group=${USER_NAME}
WorkingDirectory=${SCRIPT_DIR}
EnvironmentFile=${SCRIPT_DIR}/.env
ExecStart=${VENV_DIR}/bin/python ${SCRIPT_DIR}/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

# Hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
echo "  ✓ Systemd service installed and enabled."

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "=============================================="
echo "  Setup Complete!"
echo "=============================================="
echo ""
echo "  IMPORTANT: Edit ${ENV_FILE}"
echo "  Set EDGE_SERVER_URL and EDGE_API_KEY to your backend server values."
echo ""
echo "  To start the bot:"
echo "    sudo systemctl start ${SERVICE_NAME}"
echo ""
echo "  To view logs:"
echo "    journalctl -u ${SERVICE_NAME} -f"
echo ""
echo "  To check status:"
echo "    sudo systemctl status ${SERVICE_NAME}"
echo ""
echo "  A reboot is recommended to ensure camera is fully available:"
echo "    sudo reboot"
echo ""

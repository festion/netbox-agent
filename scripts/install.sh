#!/bin/bash
set -e

INSTALL_DIR="/opt/netbox-agent"
SERVICE_USER="netboxagent"
SERVICE_NAME="netbox-agent"

echo "Installing NetBox Agent..."

# Create service user
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "Creating service user: $SERVICE_USER"
    sudo useradd -r -s /bin/false -d "$INSTALL_DIR" "$SERVICE_USER"
fi

# Create installation directory
sudo mkdir -p "$INSTALL_DIR"
sudo chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# Copy application files
echo "Copying application files..."
sudo cp -r src/ config/ scripts/ requirements.txt "$INSTALL_DIR/"
sudo mkdir -p "$INSTALL_DIR"/{logs,cache}
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# Create Python virtual environment
echo "Creating Python virtual environment..."
sudo -u "$SERVICE_USER" python3 -m venv "$INSTALL_DIR/venv"
sudo -u "$SERVICE_USER" "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Install systemd service
echo "Installing systemd service..."
sudo cp scripts/netbox-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

# Setup log rotation
sudo tee /etc/logrotate.d/netbox-agent > /dev/null << 'EOF'
/opt/netbox-agent/logs/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    create 644 netboxagent netboxagent
}
EOF

echo "Installation complete!"
echo "Next steps:"
echo "1. Configure: sudo -u $SERVICE_USER nano $INSTALL_DIR/config/netbox-agent.json"
echo "2. Set environment: sudo -u $SERVICE_USER nano $INSTALL_DIR/.env"
echo "3. Start service: sudo systemctl start $SERVICE_NAME"
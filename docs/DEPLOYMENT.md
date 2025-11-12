# NetBox Agent Deployment Guide

## Prerequisites

### System Requirements
- Python 3.8 or higher
- Network access to NetBox instance
- Network access to data sources (Home Assistant, network ranges, etc.)
- Minimum 1GB RAM, 2GB recommended
- 10GB disk space for logs and cache

### Dependencies
- NetBox 3.0 or higher with API enabled
- Home Assistant (if using HA integration)
- Network scanning permissions (if using network scanner)

## Installation

### Quick Start (Development/Testing)

For quick development or testing setup, use the quick-start script:

```bash
git clone https://github.com/festion/netbox-agent.git
cd netbox-agent
./scripts/quick-start.sh
```

This automated script will:
- Create Python virtual environment
- Install all dependencies
- Create example configuration files
- Set up necessary directories

After running quick-start, follow the prompts to:
1. Edit `config/netbox-agent.json` with your NetBox details
2. Edit `.env` with your environment variables
3. Validate configuration: `python scripts/validate-config.py`
4. Run the agent: `python src/netbox_agent.py`

### Manual Installation

For more control over the installation process:

#### 1. Clone Repository
```bash
git clone https://github.com/festion/netbox-agent.git
cd netbox-agent
```

#### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configuration

#### Environment Variables
Create `.env` file:
```bash
NETBOX_URL=https://your-netbox.com
NETBOX_TOKEN=your-api-token
HA_URL=http://your-homeassistant:8123
HA_TOKEN=your-ha-token
```

#### Main Configuration
Edit `config/netbox-agent.json`:
- Update NetBox URL and token
- Configure data sources
- Set sync intervals
- Configure logging

### 4. Initial Setup
```bash
# Validate configuration
./scripts/validate-config.sh

# Test connections
python src/netbox_agent.py --test-connections

# Run initial sync (dry run)
python src/netbox_agent.py --sync --dry-run
```

## Production Deployment

### Systemd Service
Create `/etc/systemd/system/netbox-agent.service`:
```ini
[Unit]
Description=NetBox Agent
After=network.target

[Service]
Type=simple
User=netbox-agent
WorkingDirectory=/opt/netbox-agent
ExecStart=/opt/netbox-agent/venv/bin/python src/netbox_agent.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable netbox-agent
sudo systemctl start netbox-agent
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "src/netbox_agent.py"]
```

Docker Compose:
```yaml
version: '3.8'
services:
  netbox-agent:
    build: .
    environment:
      - NETBOX_URL=https://netbox.local
      - NETBOX_TOKEN=${NETBOX_TOKEN}
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    restart: unless-stopped
```

## Monitoring

### Health Checks
- HTTP endpoint: `http://localhost:8080/health` (if enabled)
- Log monitoring for error patterns
- NetBox API connectivity checks

### Metrics
- Sync success/failure rates
- Device discovery counts by source
- API response times
- Memory and CPU usage

### Alerting
Configure alerts for:
- Sync failures
- Connection timeouts
- High error rates
- Resource exhaustion

## Maintenance

### Log Rotation
Configure log rotation in `/etc/logrotate.d/netbox-agent`:
```
/opt/netbox-agent/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    postrotate
        systemctl reload netbox-agent
    endscript
}
```

### Backup
- Configuration files
- Custom mappings
- SSL certificates
- Database (if using local database)

### Updates
```bash
# Stop service
sudo systemctl stop netbox-agent

# Update code
git pull origin main

# Update dependencies  
pip install -r requirements.txt

# Test configuration
./scripts/validate-config.sh

# Restart service
sudo systemctl start netbox-agent
```
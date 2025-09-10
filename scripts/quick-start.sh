#!/bin/bash
set -e

echo "🚀 NetBox Agent Quick Start"
echo "=========================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs cache config

# Copy example configuration if config doesn't exist
if [ ! -f "config/netbox-agent.json" ]; then
    echo "📝 Creating example configuration..."
    cat > config/netbox-agent.json << 'EOF'
{
  "netbox": {
    "url": "http://localhost:8000",
    "token": "your-netbox-api-token-here",
    "verify_ssl": true
  },
  "logging": {
    "level": "INFO",
    "file": "logs/netbox-agent.log",
    "max_size": "10MB",
    "backup_count": 5
  },
  "sync": {
    "interval": 300,
    "batch_size": 100
  },
  "error_handling": {
    "retry": {
      "max_attempts": 3,
      "base_delay": 1,
      "max_delay": 60
    }
  }
}
EOF
fi

# Create example environment file
if [ ! -f ".env" ]; then
    echo "🔧 Creating example environment file..."
    cat > .env << 'EOF'
# NetBox Configuration
NETBOX_URL=http://localhost:8000
NETBOX_TOKEN=your-netbox-api-token-here

# Logging
LOG_LEVEL=INFO

# Optional: Health server port
HEALTH_SERVER_PORT=8080
EOF
fi

echo ""
echo "✅ Quick start setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config/netbox-agent.json with your NetBox details"
echo "2. Edit .env with your environment variables"
echo "3. Validate configuration: python scripts/validate-config.py"
echo "4. Run the agent: python src/netbox_agent.py"
echo ""
echo "For production deployment:"
echo "- Systemd: sudo ./scripts/install.sh"
echo "- Docker: docker-compose up -d"
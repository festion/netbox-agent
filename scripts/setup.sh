#!/bin/bash

# NetBox Agent Setup Script
# This script initializes the NetBox Agent project

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/template-config.json"
MCP_CONFIG_FILE="$PROJECT_ROOT/.mcp.json"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3.8+ and try again."
        exit 1
    fi
    
    local python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
    if [[ "$(printf '%s\n' "3.8" "$python_version" | sort -V | head -n1)" != "3.8" ]]; then
        log_error "Python version $python_version is too old. Please install Python 3.8+ and try again."
        exit 1
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is not installed. Please install pip3 and try again."
        exit 1
    fi
    
    # Check Git
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed. Please install Git and try again."
        exit 1
    fi
    
    # Check if jq is available for JSON processing
    if ! command -v jq &> /dev/null; then
        log_warning "jq is not installed. Some features may not work properly."
        log_info "Install jq for better JSON processing: sudo apt-get install jq"
    fi
    
    log_success "Prerequisites check passed"
}

# Load configuration
load_config() {
    log_info "Loading configuration..."
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    # Validate JSON syntax
    if command -v jq &> /dev/null; then
        if ! jq empty "$CONFIG_FILE" 2>/dev/null; then
            log_error "Invalid JSON in configuration file: $CONFIG_FILE"
            exit 1
        fi
    else
        # Basic validation without jq
        if ! python3 -m json.tool "$CONFIG_FILE" > /dev/null 2>&1; then
            log_error "Invalid JSON in configuration file: $CONFIG_FILE"
            exit 1
        fi
    fi
    
    log_success "Configuration loaded successfully"
}

# Get configuration value with default
get_config() {
    local key="$1"
    local default="$2"
    
    if command -v jq &> /dev/null; then
        local value=$(jq -r "$key // \"$default\"" "$CONFIG_FILE")
        echo "$value"
    else
        # Fallback without jq - return default
        echo "$default"
    fi
}

# Process project structure
setup_project_structure() {
    log_info "Setting up project structure..."
    
    local project_type=$(get_config ".project.type" "automation")
    log_info "Project type: $project_type"
    
    # Create Python project structure
    mkdir -p {src,config,logs,tests,docs}
    
    # Create Python package structure
    touch src/__init__.py
    touch tests/__init__.py
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv venv
        log_success "Virtual environment created"
    fi
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        log_info "Installing Python dependencies..."
        source venv/bin/activate
        pip install -r requirements.txt
        deactivate
        log_success "Dependencies installed"
    fi
    
    log_success "Project structure created"
}

# Create API template files
create_api_template() {
    local framework=$(get_config ".structure.api.framework" "express")
    local language=$(get_config ".structure.api.language" "javascript")
    
    # Create package.json template
    cat > api/package.json.template << 'EOF'
{
  "name": "{{PROJECT_NAME}}-api",
  "version": "1.0.0",
  "description": "{{PROJECT_DESCRIPTION}} - API",
  "main": "src/server.js",
  "scripts": {
    "start": "node src/server.js",
    "dev": "nodemon src/server.js",
    "test": "jest",
    "lint": "eslint src/"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1"
  },
  "devDependencies": {
    "nodemon": "^3.0.1",
    "jest": "^29.6.2",
    "eslint": "^8.45.0"
  }
}
EOF
    
    # Create basic server template
    cat > api/src/server.js.template << 'EOF'
const express = require('express');
const cors = require('cors');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.get('/', (req, res) => {
  res.json({ 
    message: 'Welcome to {{PROJECT_NAME}} API',
    version: '1.0.0',
    status: 'running'
  });
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

module.exports = app;
EOF
}

# Create dashboard template files
create_dashboard_template() {
    local framework=$(get_config ".structure.dashboard.framework" "react")
    
    # Create package.json template
    cat > dashboard/package.json.template << 'EOF'
{
  "name": "{{PROJECT_NAME}}-dashboard",
  "version": "1.0.0",
  "description": "{{PROJECT_DESCRIPTION}} - Dashboard",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "jest",
    "lint": "eslint src/"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.14.2"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.0.3",
    "vite": "^4.4.5",
    "eslint": "^8.45.0"
  }
}
EOF
    
    # Create basic React app template
    cat > dashboard/src/App.jsx.template << 'EOF'
import React from 'react';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>{{PROJECT_NAME}}</h1>
        <p>{{PROJECT_DESCRIPTION}}</p>
        <p>Welcome to your homelab project dashboard!</p>
      </header>
    </div>
  );
}

export default App;
EOF
}

# Setup MCP configuration
setup_mcp_config() {
    log_info "Setting up MCP configuration..."
    
    local mcp_servers=$(get_config ".mcp.servers" "all")
    local github_enabled=$(get_config ".mcp.configuration.github.enabled" "true")
    local filesystem_enabled=$(get_config ".mcp.configuration.filesystem.enabled" "true")
    local ha_enabled=$(get_config ".mcp.configuration.homeAssistant.enabled" "false")
    
    # Create MCP configuration
    cat > "$MCP_CONFIG_FILE" << 'EOF'
{
  "mcpServers": {
EOF
    
    # Add filesystem server if enabled
    if [ "$filesystem_enabled" = "true" ]; then
        cat >> "$MCP_CONFIG_FILE" << 'EOF'
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
      "env": {}
    },
EOF
    fi
    
    # Add GitHub server if enabled
    if [ "$github_enabled" = "true" ]; then
        cat >> "$MCP_CONFIG_FILE" << 'EOF'
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
EOF
    fi
    
    # Add Home Assistant server if enabled
    if [ "$ha_enabled" = "true" ]; then
        cat >> "$MCP_CONFIG_FILE" << 'EOF'
    "home-assistant": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-home-assistant"],
      "env": {
        "HA_URL": "${HA_URL}",
        "HA_TOKEN": "${HA_TOKEN}"
      }
    },
EOF
    fi
    
    # Remove trailing comma and close
    sed -i '$ s/,$//' "$MCP_CONFIG_FILE"
    cat >> "$MCP_CONFIG_FILE" << 'EOF'
  }
}
EOF
    
    log_success "MCP configuration created"
}

# Process template variables
process_templates() {
    log_info "Processing template variables..."
    
    local project_name=$(get_config ".project.name" "my-project")
    local project_description=$(get_config ".project.description" "A homelab project")
    local project_author=$(get_config ".project.author" "")
    
    # Process template files
    find "$PROJECT_ROOT" -name "*.template" -type f | while read -r template_file; do
        local output_file="${template_file%.template}"
        log_info "Processing template: $template_file -> $output_file"
        
        # Replace template variables
        sed "s/{{PROJECT_NAME}}/$project_name/g; s/{{PROJECT_DESCRIPTION}}/$project_description/g; s/{{PROJECT_AUTHOR}}/$project_author/g" "$template_file" > "$output_file"
        
        # Remove template file
        rm "$template_file"
    done
    
    log_success "Template processing completed"
}

# Create environment file
create_env_file() {
    log_info "Creating environment file..."
    
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        cat > "$PROJECT_ROOT/.env" << 'EOF'
# NetBox Agent Environment Configuration
ENVIRONMENT=development

# NetBox Configuration
NETBOX_URL=https://netbox.example.com
NETBOX_TOKEN=your_netbox_api_token_here
NETBOX_VERIFY_SSL=true

# GitHub Configuration
GITHUB_TOKEN=your_github_token_here

# Home Assistant Configuration
HA_URL=http://192.168.1.10:8123
HA_TOKEN=your_ha_token_here

# Network Scanning Configuration
NETWORK_RANGES=192.168.1.0/24,10.0.0.0/24

# Proxmox Configuration (optional)
PROXMOX_URL=https://proxmox.example.com:8006
PROXMOX_USERNAME=api@pve
PROXMOX_TOKEN=your_proxmox_token_here

# TrueNAS Configuration (optional)
TRUENAS_URL=https://truenas.example.com
TRUENAS_API_KEY=your_truenas_api_key_here

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/home/dev/workspace/netbox-agent/logs/netbox-agent.log
EOF
        log_success "Environment file created at .env"
        log_warning "Please update .env with your actual configuration values"
    else
        log_info "Environment file already exists, skipping creation"
    fi
}

# Initialize git repository
init_git_repo() {
    log_info "Initializing git repository..."
    
    if [ ! -d "$PROJECT_ROOT/.git" ]; then
        cd "$PROJECT_ROOT"
        git init
        git add .
        git commit -m "Initial commit from homelab-project-template"
        log_success "Git repository initialized"
    else
        log_info "Git repository already exists, skipping initialization"
    fi
}

# Create GitHub workflow files
setup_github_workflows() {
    local github_enabled=$(get_config ".github.useTemplates" "true")
    
    if [ "$github_enabled" = "true" ]; then
        log_info "Setting up GitHub workflows..."
        
        mkdir -p .github/workflows
        
        # Create CI workflow
        cat > .github/workflows/ci.yml << 'EOF'
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        node-version: [16, 18, 20]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Use Node.js ${{ matrix.node-version }}
      uses: actions/setup-node@v3
      with:
        node-version: ${{ matrix.node-version }}
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Run linter
      run: npm run lint --if-present
    
    - name: Run tests
      run: npm test --if-present
    
    - name: Build project
      run: npm run build --if-present
EOF
        
        log_success "GitHub workflows created"
    fi
}

# Print next steps
print_next_steps() {
    log_success "Setup completed successfully!"
    echo
    log_info "Next steps:"
    echo "1. Update .env file with your actual configuration values"
    echo "2. Customize template-config.json for your specific needs"
    echo "3. Install project dependencies (if using Node.js):"
    echo "   - cd api && npm install (if API enabled)"
    echo "   - cd dashboard && npm install (if dashboard enabled)"
    echo "4. Set up your GitHub repository:"
    echo "   - git remote add origin https://github.com/username/repo.git"
    echo "   - git push -u origin main"
    echo "5. Configure MCP servers for AI assistance (see docs/MCP_CONFIGURATION.md)"
    echo
    log_info "For detailed setup instructions, see docs/SETUP.md"
    log_info "For troubleshooting help, see docs/TROUBLESHOOTING.md"
}

# Main execution
main() {
    log_info "Starting Homelab Project Template setup..."
    echo
    
    check_prerequisites
    load_config
    setup_project_structure
    setup_mcp_config
    process_templates
    create_env_file
    setup_github_workflows
    init_git_repo
    
    echo
    print_next_steps
}

# Run main function
main "$@"
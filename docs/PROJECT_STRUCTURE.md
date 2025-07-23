# NetBox Agent Project Structure

This document provides a comprehensive overview of the NetBox Agent project structure, including directory organization, file purposes, and development workflows.

## Project Directory Structure

```
netbox-agent/
├── src/                          # Source code directory
│   ├── __init__.py              # Package initialization
│   ├── netbox_agent.py          # Main agent implementation
│   ├── data_sources/            # Data source implementations
│   │   ├── __init__.py
│   │   ├── home_assistant.py    # Home Assistant integration
│   │   ├── network_scanner.py   # Network discovery
│   │   ├── filesystem.py        # File system monitoring
│   │   ├── proxmox.py          # Proxmox integration
│   │   └── truenas.py          # TrueNAS integration
│   ├── netbox/                  # NetBox API integration
│   │   ├── __init__.py
│   │   ├── client.py           # NetBox API client
│   │   ├── models.py           # NetBox data models
│   │   └── sync.py             # Synchronization logic
│   ├── utils/                   # Utility modules
│   │   ├── __init__.py
│   │   ├── logging.py          # Logging configuration
│   │   ├── config.py           # Configuration management
│   │   └── helpers.py          # Helper functions
│   └── mcp/                     # MCP server integrations
│       ├── __init__.py
│       ├── base.py             # Base MCP client
│       ├── home_assistant.py   # HA MCP integration
│       ├── filesystem.py       # Filesystem MCP integration
│       └── proxmox.py          # Proxmox MCP integration
├── config/                      # Configuration directory
│   ├── netbox-agent.json       # Main agent configuration
│   ├── data-sources.json       # Data source configurations
│   ├── logging.yaml            # Logging configuration
│   └── netbox-mappings.json    # NetBox field mappings
├── tests/                       # Test directory
│   ├── __init__.py
│   ├── test_netbox_agent.py    # Main agent tests
│   ├── test_data_sources/      # Data source tests
│   │   ├── __init__.py
│   │   ├── test_home_assistant.py
│   │   ├── test_network_scanner.py
│   │   └── test_filesystem.py
│   ├── test_netbox/            # NetBox integration tests
│   │   ├── __init__.py
│   │   ├── test_client.py
│   │   └── test_sync.py
│   └── fixtures/               # Test fixtures and data
│       ├── home_assistant_entities.json
│       ├── network_scan_results.json
│       └── netbox_responses.json
├── logs/                        # Log directory
│   ├── netbox-agent.log        # Main application log
│   ├── sync.log                # Synchronization logs
│   └── debug.log               # Debug logs
├── docs/                        # Documentation directory
│   ├── SETUP.md                # Setup instructions
│   ├── CUSTOMIZATION.md        # Customization guide
│   ├── MCP_CONFIGURATION.md    # MCP server configuration
│   ├── TROUBLESHOOTING.md      # Troubleshooting guide
│   ├── MCP_SERVER_CAPABILITIES.md # MCP server documentation
│   ├── PROJECT_STRUCTURE.md    # This file
│   └── API_REFERENCE.md        # API documentation
├── scripts/                     # Utility scripts
│   ├── setup.sh                # Project setup script
│   ├── validate-config.sh      # Configuration validation
│   ├── run-tests.sh            # Test runner script
│   └── deploy.sh               # Deployment script
├── examples/                    # Example configurations
│   ├── basic-project/          # Basic setup example
│   └── advanced-project/       # Advanced setup example
├── api/                         # Optional API server
│   └── (API files if enabled)
├── dashboard/                   # Optional dashboard
│   └── (Dashboard files if enabled)
├── .github/                     # GitHub workflows and templates
│   ├── workflows/
│   │   ├── ci.yml              # Continuous integration
│   │   ├── tests.yml           # Test automation
│   │   └── deploy.yml          # Deployment workflow
│   ├── ISSUE_TEMPLATE/         # Issue templates
│   └── PULL_REQUEST_TEMPLATE.md # PR template
├── requirements.txt             # Python dependencies
├── requirements-dev.txt         # Development dependencies
├── setup.py                     # Package setup configuration
├── pytest.ini                  # Pytest configuration
├── .env                        # Environment variables
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
├── .pre-commit-config.yaml     # Pre-commit hooks
├── template-config.json        # Template configuration
├── README.md                   # Project overview
├── LICENSE                     # License file
└── CHANGELOG.md                # Change log
```

## Core Components

### 1. Source Code (`src/`)

#### Main Agent (`netbox_agent.py`)
- **Purpose**: Main application entry point and orchestration
- **Responsibilities**:
  - Configuration loading and validation
  - Data source coordination
  - Synchronization scheduling
  - Error handling and logging
  - MCP server orchestration

#### Data Sources (`src/data_sources/`)
- **Purpose**: Individual data source implementations
- **Components**:
  - `home_assistant.py`: IoT device discovery via Home Assistant
  - `network_scanner.py`: Network scanning and device discovery
  - `filesystem.py`: Configuration file parsing and monitoring
  - `proxmox.py`: Virtualization infrastructure discovery
  - `truenas.py`: Storage system discovery

#### NetBox Integration (`src/netbox/`)
- **Purpose**: NetBox API interaction and data synchronization
- **Components**:
  - `client.py`: NetBox REST API client
  - `models.py`: Pydantic models for NetBox objects
  - `sync.py`: Data synchronization and conflict resolution

#### MCP Integrations (`src/mcp/`)
- **Purpose**: MCP server client implementations
- **Components**:
  - `base.py`: Base MCP client with common functionality
  - Individual MCP server clients for each integrated server
  - Error handling and retry logic

#### Utilities (`src/utils/`)
- **Purpose**: Common utility functions and helpers
- **Components**:
  - `logging.py`: Structured logging configuration
  - `config.py`: Configuration management and validation
  - `helpers.py`: Common helper functions

### 2. Configuration (`config/`)

#### Main Configuration (`netbox-agent.json`)
```json
{
  "netbox": {
    "url": "https://netbox.example.com",
    "token": "api-token",
    "verify_ssl": true
  },
  "sources": {
    "homeassistant": {...},
    "network_scan": {...},
    "filesystem": {...}
  },
  "sync": {
    "interval": 3600,
    "dry_run": false
  }
}
```

#### Data Source Configuration (`data-sources.json`)
- Individual configuration for each data source
- Connection parameters and sync settings
- Field mappings and filtering rules

#### NetBox Mappings (`netbox-mappings.json`)
- Field mappings between data sources and NetBox
- Device type mappings and role assignments
- Custom field definitions

### 3. Testing (`tests/`)

#### Test Structure
- Unit tests for individual components
- Integration tests for data source interactions
- End-to-end tests for complete workflows
- Mock data and fixtures for reliable testing

#### Test Categories
- **Unit Tests**: Individual function and class testing
- **Integration Tests**: MCP server and NetBox API integration
- **Functional Tests**: Complete workflow testing
- **Performance Tests**: Sync performance and scalability

### 4. Documentation (`docs/`)

#### Documentation Types
- **Setup Documentation**: Installation and configuration
- **User Documentation**: Usage guides and examples
- **Developer Documentation**: API reference and architecture
- **Troubleshooting**: Common issues and solutions

### 5. Scripts (`scripts/`)

#### Utility Scripts
- `setup.sh`: Automated project initialization
- `validate-config.sh`: Configuration validation
- `run-tests.sh`: Test execution with coverage
- `deploy.sh`: Production deployment automation

## Development Workflow

### 1. Initial Setup
```bash
# Clone and setup project
git clone <repository-url>
cd netbox-agent
./scripts/setup.sh

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
vim config/netbox-agent.json
vim .env
```

### 3. Development
```bash
# Run agent in development mode
python src/netbox_agent.py

# Run tests
./scripts/run-tests.sh

# Validate configuration
./scripts/validate-config.sh
```

### 4. Testing
```bash
# Run all tests
pytest

# Run specific test category
pytest tests/test_data_sources/

# Run with coverage
pytest --cov=src tests/
```

## Configuration Management

### Environment Variables
- Used for sensitive information (API tokens, passwords)
- Environment-specific settings (URLs, timeouts)
- Runtime configuration overrides

### Configuration Files
- Static configuration that doesn't change between environments
- Data source configurations and mappings
- Logging and monitoring settings

### Configuration Validation
- JSON schema validation for configuration files
- Environment variable presence checks
- API connectivity validation

## Logging and Monitoring

### Log Categories
- **Application Logs**: Main agent operations and status
- **Sync Logs**: Data synchronization activities
- **Debug Logs**: Detailed debugging information
- **Error Logs**: Error conditions and exceptions

### Log Formats
- Structured JSON logging for machine processing
- Human-readable formats for development
- Configurable log levels and rotation

## Security Considerations

### API Token Management
- Environment variable storage for tokens
- Secure token rotation procedures
- Least-privilege access principles

### Data Protection
- Encryption for sensitive configuration data
- Secure communication with all APIs
- Audit trails for all data modifications

### Access Control
- Role-based access for NetBox operations
- MCP server authentication and authorization
- Secure defaults for all configurations

## Deployment Patterns

### Development Deployment
- Local development environment
- Docker Compose for dependencies
- Hot-reload for rapid iteration

### Production Deployment
- Containerized deployment with Docker
- Kubernetes deployment manifests
- High availability and scaling considerations

### CI/CD Integration
- GitHub Actions for automated testing
- Automated deployment on successful tests
- Environment-specific configuration management

## Future Enhancements

### Planned Features
- Real-time synchronization via WebSockets
- Multi-tenant NetBox support
- Advanced conflict resolution
- Plugin architecture for custom data sources

### Architecture Improvements
- Microservices architecture for scaling
- Event-driven synchronization
- Caching layer for performance
- Metrics and observability improvements
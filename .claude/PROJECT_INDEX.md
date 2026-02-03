# netbox-agent Project Index

Generated: 2026-02-03

## Purpose

NetBox Agent is an intelligent Python service that automates the discovery and population of network infrastructure data into NetBox DCIM/IPAM. It leverages MCP (Model Context Protocol) servers to collect data from multiple sources including Home Assistant IoT devices, Proxmox virtualization, TrueNAS storage systems, network scanning, and filesystem inventories, then synchronizes this data with a NetBox instance using configurable mapping rules and conflict resolution strategies.

## Directory Structure

```
netbox-agent/
├── src/                      # Main source code
│   ├── netbox_agent.py       # Main agent entry point and orchestrator
│   ├── data_sources/         # Data source implementations
│   │   ├── base.py           # Abstract base class for data sources
│   │   ├── manager.py        # Data source lifecycle management
│   │   ├── home_assistant.py # Home Assistant integration
│   │   ├── network_scanner.py# Network device discovery
│   │   ├── filesystem.py     # Filesystem-based inventory
│   │   ├── proxmox.py        # Proxmox VM/container discovery
│   │   └── truenas.py        # TrueNAS storage integration
│   ├── netbox/               # NetBox API integration
│   │   ├── client.py         # NetBox REST API client
│   │   ├── sync.py           # Advanced sync engine with conflict resolution
│   │   ├── mappings.py       # Data mapping rules engine
│   │   └── models.py         # Pydantic models for NetBox objects
│   ├── mcp/                  # MCP server integrations
│   │   ├── base.py           # Base MCP client
│   │   ├── manager.py        # MCP server connection manager
│   │   ├── filesystem.py     # Filesystem MCP client
│   │   ├── home_assistant.py # Home Assistant MCP client
│   │   ├── proxmox.py        # Proxmox MCP client
│   │   └── truenas.py        # TrueNAS MCP client
│   ├── scheduler/            # Job scheduling
│   │   └── scheduler.py      # Advanced scheduler with priorities
│   ├── monitoring/           # Health and metrics
│   ├── cli/                  # CLI interface
│   └── utils/                # Shared utilities
├── config/                   # Configuration files
│   ├── netbox-agent.json     # Main agent configuration
│   ├── data-mappings.json    # Source-to-NetBox field mappings
│   ├── alerts.json           # Alerting configuration
│   └── mcp-servers.json      # MCP server definitions
├── tests/                    # Test suite
│   ├── conftest.py           # Pytest fixtures
│   ├── test_netbox_agent.py  # Main agent tests
│   ├── test_data_sources/    # Data source tests
│   ├── test_mcp/             # MCP integration tests
│   ├── test_netbox/          # NetBox client tests
│   ├── integration/          # Integration tests
│   └── performance/          # Performance benchmarks
├── scripts/                  # Operational scripts
│   ├── setup.sh              # Project initialization
│   ├── run-agent.sh          # Run the agent
│   ├── health_check.py       # Health check endpoint
│   ├── health_server.py      # Health HTTP server
│   ├── validate-config.py    # Configuration validator
│   └── validate-deployment.sh# Deployment validation
├── docs/                     # Documentation
│   ├── API_REFERENCE.md      # API documentation
│   ├── CONFIGURATION_REFERENCE.md
│   ├── RUNBOOK.md            # Operational runbook
│   └── TROUBLESHOOTING.md    # Common issues
├── dashboard/                # Web dashboard
├── cache/                    # Local cache storage
├── logs/                     # Log files
└── examples/                 # Usage examples
```

## Key Files

| File | Description |
|------|-------------|
| `src/netbox_agent.py` | Main entry point; orchestrates data collection and sync |
| `src/data_sources/manager.py` | Manages data source lifecycle and concurrent collection |
| `src/netbox/client.py` | Async NetBox REST API client with connection pooling |
| `src/netbox/sync.py` | Advanced sync engine with diff detection and conflict resolution |
| `src/netbox/mappings.py` | Configurable data mapping rules engine |
| `config/netbox-agent.json` | Main configuration (NetBox URL, sources, sync settings) |
| `config/data-mappings.json` | Field mapping rules from sources to NetBox objects |
| `scripts/setup.sh` | Initial project setup script |
| `deploy-to-remote.sh` | Remote deployment script |
| `Dockerfile` | Container build definition |

## Architecture Patterns

- **Data Source Abstraction**: All sources implement `BaseDataSource` abstract class
- **Async Operations**: Uses `asyncio` and `aiohttp` for concurrent API calls
- **Pydantic Models**: All configs and data objects use Pydantic for validation
- **Conflict Resolution**: Configurable strategies for sync conflicts (prefer_source, prefer_newer, etc.)
- **Rate Limiting**: Built-in rate limiting per data source
- **Connection Pooling**: Shared HTTP session pools for efficiency
- **MCP Integration**: Uses Model Context Protocol for external system access
- **Scheduler**: Priority-based job scheduling with concurrency control

## Entry Points

```bash
# Run the agent directly
python src/netbox_agent.py

# Run with custom config
python src/netbox_agent.py --config /path/to/config.json

# Run via script
./scripts/run-agent.sh

# Quick start (setup + run)
./scripts/quick-start.sh

# Run tests
pytest tests/
```

## Dependencies

**Core:**
- `requests` / `aiohttp` - HTTP clients
- `pydantic` - Data validation
- `pynetbox` - NetBox Python API
- `schedule` - Job scheduling
- `backoff` - Retry logic

**Data Sources:**
- `homeassistant-api` - Home Assistant integration
- `python-nmap` - Network scanning
- `psutil` - System monitoring

**Development:**
- `pytest` / `pytest-asyncio` - Testing
- `black` / `flake8` - Formatting/linting
- `mypy` - Type checking

## Common Tasks

**Setup:**
```bash
./scripts/setup.sh
cp config/template-netbox-agent.json config/netbox-agent.json
# Edit config with NetBox URL and token
```

**Run Agent:**
```bash
python src/netbox_agent.py
# Or for dry-run mode (no changes to NetBox)
# Set "dry_run": true in config
```

**Test:**
```bash
pytest tests/ -v
pytest tests/integration/ -v  # Integration tests
pytest tests/performance/     # Performance benchmarks
```

**Deploy:**
```bash
./deploy-to-remote.sh <target-host>
./scripts/validate-deployment.sh
```

**Health Check:**
```bash
python scripts/health_check.py
```

## Configuration

Main config at `config/netbox-agent.json`:
- `netbox.url` / `netbox.token` - NetBox connection
- `data_sources.*` - Enable/configure each source
- `sync.dry_run` - Test mode without changes
- `sync.conflict_resolution` - How to handle conflicts
- `scheduler.*` - Job concurrency and rate limits

## Notes for AI Assistants

- The agent uses async/await patterns extensively in sync operations
- Data source configs are passed through Pydantic models for validation
- The sync engine tracks changes via hash comparison for efficiency
- MCP servers provide authenticated access to external systems
- Tests use extensive mocking; see `tests/conftest.py` for fixtures

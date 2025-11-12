# NetBox Agent API Reference

**Version**: 1.0.0
**Last Updated**: 2025-11-12

---

## Table of Contents

- [Core Classes](#core-classes)
- [Data Sources](#data-sources)
- [Data Models](#data-models)
- [Sync Engine](#sync-engine)
- [Monitoring](#monitoring)
- [Utilities](#utilities)
- [Custom Development](#custom-development)

---

## Core Classes

### NetBoxAgent

Main orchestration class that manages the agent lifecycle.

**Location**: `src/netbox_agent.py`

#### Constructor

```python
def __init__(self, config_path: str = "config/netbox-agent.json")
```

**Parameters**:
- `config_path` (str): Path to configuration file

**Raises**:
- `ConfigError`: If configuration is invalid
- `FileNotFoundError`: If config file doesn't exist

**Example**:
```python
from src.netbox_agent import NetBoxAgent

agent = NetBoxAgent("config/netbox-agent.json")
```

#### Methods

##### `run()`

Start the agent main loop with scheduled sync operations.

```python
async def run() -> None
```

**Behavior**:
- Initializes all data sources
- Starts health check server
- Runs sync operations on schedule
- Handles graceful shutdown

**Example**:
```python
import asyncio

async def main():
    agent = NetBoxAgent()
    await agent.run()

asyncio.run(main())
```

##### `perform_full_sync()`

Execute a full synchronization from all enabled data sources.

```python
async def perform_full_sync() -> Dict[str, Any]
```

**Returns**:
- `Dict`: Sync results with statistics

**Example**:
```python
results = await agent.perform_full_sync()
print(f"Synced {results['total_synced']} devices")
```

##### `perform_incremental_sync()`

Execute incremental synchronization (only changed devices).

```python
async def perform_incremental_sync() -> Dict[str, Any]
```

**Returns**:
- `Dict`: Sync results with statistics

##### `test_connections()`

Test connectivity to NetBox and all enabled data sources.

```python
async def test_connections() -> Dict[str, bool]
```

**Returns**:
- `Dict`: Connection test results per source

**Example**:
```python
results = await agent.test_connections()
if not all(results.values()):
    print("Some connections failed:", results)
```

---

## Data Sources

All data sources inherit from the `DataSource` base class.

### Base Class: DataSource

**Location**: `src/data_sources/base.py`

#### Abstract Methods

```python
class DataSource(ABC):
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to data source"""
        pass

    @abstractmethod
    async def discover(self) -> List[Device]:
        """Discover devices from this source"""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if source is reachable"""
        pass
```

---

### HomeAssistantDataSource

Discovers devices from Home Assistant via REST API.

**Location**: `src/data_sources/home_assistant.py`

#### Constructor

```python
def __init__(self, config: Dict[str, Any])
```

**Configuration**:
```python
{
    "enabled": True,
    "url": "http://homeassistant:8123",
    "token_path": "/config/ha_token",
    "sync_interval": 3600,
    "include_entities": ["sensor", "switch", "light"]
}
```

#### Methods

##### `discover()`

```python
async def discover() -> List[Device]
```

Discovers network-relevant devices from Home Assistant entities.

**Returns**: List of discovered devices

**Device Types Discovered**:
- Network devices (routers, switches)
- Smart home devices with network connectivity
- Devices with MAC addresses or IP addresses

##### `test_connection()`

```python
async def test_connection() -> bool
```

Tests connection to Home Assistant API.

**Example**:
```python
ha_source = HomeAssistantDataSource(config)
if await ha_source.test_connection():
    devices = await ha_source.discover()
```

---

### NetworkScannerDataSource

Discovers devices through network scanning (ICMP, port scanning).

**Location**: `src/data_sources/network_scanner.py`

#### Constructor

```python
def __init__(self, config: Dict[str, Any])
```

**Configuration**:
```python
{
    "enabled": True,
    "networks": ["192.168.1.0/24", "10.0.0.0/24"],
    "scan_ports": [22, 80, 443, 161, 8080],
    "timeout": 5,
    "max_concurrent": 50
}
```

#### Methods

##### `discover()`

```python
async def discover() -> List[Device]
```

Scans configured networks and discovers active devices.

**Returns**: List of discovered devices with:
- IP addresses
- Open ports
- Detected services
- Hostnames (if resolvable)

##### `scan_network(network: str)`

```python
async def scan_network(network: str) -> List[Device]
```

Scans a specific network.

**Parameters**:
- `network` (str): CIDR network (e.g., "192.168.1.0/24")

**Example**:
```python
scanner = NetworkScannerDataSource(config)
devices = await scanner.scan_network("192.168.1.0/24")
```

---

### FilesystemDataSource

Discovers devices from configuration files.

**Location**: `src/data_sources/filesystem.py`

#### Constructor

```python
def __init__(self, config: Dict[str, Any])
```

**Configuration**:
```python
{
    "enabled": True,
    "config_paths": ["/etc/ansible/hosts", "/opt/configs"],
    "watch_interval": 300,
    "recursive": True
}
```

#### Methods

##### `discover()`

```python
async def discover() -> List[Device]
```

Parses configuration files and extracts device information.

**Supported Formats**:
- Ansible inventory files
- Network configuration files
- CSV/JSON device lists

---

### ProxmoxDataSource

Discovers virtual machines and containers from Proxmox VE.

**Location**: `src/data_sources/proxmox.py`

#### Constructor

```python
def __init__(self, config: Dict[str, Any])
```

**Configuration**:
```python
{
    "enabled": True,
    "url": "https://proxmox:8006",
    "username": "root@pam",
    "token": "api-token",
    "verify_ssl": False,
    "include_stopped": True,
    "include_containers": True,
    "include_vms": True
}
```

#### Methods

##### `discover()`

```python
async def discover() -> List[Device]
```

Discovers VMs, containers, and cluster nodes.

**Returns**: List of devices including:
- QEMU virtual machines
- LXC containers
- Proxmox nodes (if configured)

**Device Attributes**:
- VM ID
- Status (running/stopped)
- CPU/Memory configuration
- Network interfaces
- Node location

**Example**:
```python
proxmox = ProxmoxDataSource(config)
devices = await proxmox.discover()
for device in devices:
    print(f"{device.name}: {device.device_type.model} on {device.site.name}")
```

---

### TrueNASDataSource

Discovers storage systems from TrueNAS.

**Location**: `src/data_sources/truenas.py`

#### Constructor

```python
def __init__(self, config: Dict[str, Any])
```

**Configuration**:
```python
{
    "enabled": True,
    "url": "https://truenas:443",
    "api_key": "truenas-api-key",
    "verify_ssl": True,
    "include_pools": True,
    "include_datasets": True,
    "include_shares": True
}
```

#### Methods

##### `discover()`

```python
async def discover() -> List[Device]
```

Discovers TrueNAS system, storage pools, and shares.

**Returns**: List including:
- TrueNAS system (as device)
- Storage pools (as custom fields)
- Datasets (as custom fields)
- Network shares (NFS/SMB/iSCSI)

**Example**:
```python
truenas = TrueNASDataSource(config)
devices = await truenas.discover()
```

---

## Data Models

### Device

Primary data model representing a network device.

**Location**: `src/models/device.py`

```python
@dataclass
class Device:
    name: str
    device_type: DeviceType
    device_role: DeviceRole
    site: Site
    serial: Optional[str] = None
    asset_tag: Optional[str] = None
    status: str = "active"
    primary_ip4: Optional[str] = None
    primary_ip6: Optional[str] = None
    comments: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
```

**Attributes**:
- `name`: Device hostname/name
- `device_type`: Device type (model/manufacturer)
- `device_role`: Device role (router/switch/server)
- `site`: Physical location
- `serial`: Serial number
- `primary_ip4`: Primary IPv4 address
- `custom_fields`: Additional metadata

---

### DeviceType

Represents device model and manufacturer.

```python
@dataclass
class DeviceType:
    manufacturer: str
    model: str
    slug: str
    u_height: float = 1.0
    is_full_depth: bool = True
```

---

### DeviceRole

Represents device functional role.

```python
@dataclass
class DeviceRole:
    name: str
    slug: str
    color: str
    vm_role: bool = False
```

---

### Site

Represents physical location.

```python
@dataclass
class Site:
    name: str
    slug: str
    status: str = "active"
    facility: Optional[str] = None
    description: Optional[str] = None
```

---

### SyncResult

Result of a synchronization operation.

```python
@dataclass
class SyncResult:
    device_name: str
    action: str  # "created", "updated", "skipped", "failed"
    success: bool
    message: str
    netbox_id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

---

## Sync Engine

### AdvancedSyncEngine

Handles synchronization between discovered devices and NetBox.

**Location**: `src/netbox/sync.py`

#### Constructor

```python
def __init__(self, netbox_client: NetBoxClient, config: Dict[str, Any])
```

#### Methods

##### `sync_devices_batch()`

```python
async def sync_devices_batch(
    devices: List[Device],
    source: str,
    dry_run: bool = False
) -> List[SyncResult]
```

Synchronizes a batch of devices to NetBox.

**Parameters**:
- `devices`: List of devices to sync
- `source`: Data source name
- `dry_run`: If True, preview changes without applying

**Returns**: List of sync results

**Example**:
```python
sync_engine = AdvancedSyncEngine(netbox_client, config)
results = await sync_engine.sync_devices_batch(
    devices=discovered_devices,
    source="homeassistant",
    dry_run=True
)

for result in results:
    print(f"{result.device_name}: {result.action} - {result.message}")
```

##### `build_caches()`

```python
async def build_caches() -> None
```

Builds performance caches for faster lookups.

**Caches Built**:
- Existing devices
- Device types
- Device roles
- Sites

##### `get_sync_statistics()`

```python
def get_sync_statistics() -> Dict[str, Any]
```

Returns synchronization statistics.

**Returns**:
```python
{
    "total_synced": 150,
    "created": 10,
    "updated": 135,
    "skipped": 3,
    "failed": 2,
    "duration_seconds": 12.5
}
```

---

## Monitoring

### HealthMonitor

System health monitoring.

**Location**: `src/monitoring/health.py`

#### Methods

##### `run_all_checks()`

```python
async def run_all_checks() -> Dict[str, HealthCheck]
```

Runs all health checks.

**Returns**: Dictionary of health check results

**Checks**:
- System resources (CPU, memory)
- NetBox API connectivity
- Disk space
- Memory usage

**Example**:
```python
from src.monitoring.health import HealthMonitor

monitor = HealthMonitor(config)
results = await monitor.run_all_checks()

if results["netbox_api"].status == HealthStatus.CRITICAL:
    print("NetBox is unreachable!")
```

---

### SimpleMetrics

Metrics collection without external dependencies.

**Location**: `src/monitoring/metrics.py`

#### Methods

##### `increment_counter()`

```python
def increment_counter(name: str, value: int = 1, labels: Dict = None)
```

Increments a counter metric.

**Example**:
```python
metrics.increment_counter("discovery_runs", labels={"source": "proxmox"})
```

##### `record_histogram()`

```python
def record_histogram(name: str, value: float, labels: Dict = None)
```

Records a histogram value.

**Example**:
```python
metrics.record_histogram("sync_duration", duration, labels={"source": "truenas"})
```

##### `set_gauge()`

```python
def set_gauge(name: str, value: float, labels: Dict = None)
```

Sets a gauge value.

**Example**:
```python
metrics.set_gauge("cached_devices", len(cache))
```

##### `get_metrics()`

```python
def get_metrics() -> Dict[str, Any]
```

Returns all collected metrics.

---

## Utilities

### DataSourceManager

Manages multiple data sources.

**Location**: `src/data_sources/manager.py`

#### Methods

##### `discover_all_devices()`

```python
async def discover_all_devices() -> Dict[str, DataSourceResult]
```

Discovers devices from all enabled sources.

**Returns**: Dictionary of results per source

**Example**:
```python
from src.data_sources.manager import DataSourceManager

manager = DataSourceManager(config)
results = await manager.discover_all_devices()

total_devices = sum(len(r.devices) for r in results.values())
print(f"Discovered {total_devices} devices total")
```

---

## Custom Development

### Creating a Custom Data Source

To create a custom data source, inherit from `DataSource`:

```python
from src.data_sources.base import DataSource
from src.models.device import Device
from typing import List, Dict, Any

class CustomDataSource(DataSource):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = config["url"]
        self.api_key = config["api_key"]

    async def connect(self) -> None:
        """Establish connection"""
        # Initialize API client
        pass

    async def discover(self) -> List[Device]:
        """Discover devices"""
        devices = []
        # Fetch from your API
        # Transform to Device objects
        return devices

    async def test_connection(self) -> bool:
        """Test connectivity"""
        try:
            # Test API connection
            return True
        except Exception:
            return False
```

**Register in configuration**:
```json
{
  "data_sources": {
    "custom": {
      "enabled": true,
      "class": "src.data_sources.custom.CustomDataSource",
      "url": "https://api.example.com",
      "api_key": "your-key"
    }
  }
}
```

See [Custom Data Sources Guide](CUSTOM_DATA_SOURCES.md) for complete tutorial.

---

## Error Handling

### Exception Types

```python
class ConfigError(Exception):
    """Configuration related errors"""
    pass

class MCPError(Exception):
    """MCP server communication errors"""
    pass

class SyncError(Exception):
    """Synchronization errors"""
    pass

class DataSourceError(Exception):
    """Data source errors"""
    pass
```

### Example Error Handling

```python
from src.netbox_agent import NetBoxAgent
from src.exceptions import ConfigError, SyncError

try:
    agent = NetBoxAgent("config/netbox-agent.json")
    await agent.run()
except ConfigError as e:
    print(f"Configuration error: {e}")
except SyncError as e:
    print(f"Sync error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Logging

The agent uses Python's standard logging module.

### Log Levels

- `DEBUG`: Detailed debugging information
- `INFO`: General operational information
- `WARNING`: Warning conditions
- `ERROR`: Error conditions
- `CRITICAL`: Critical errors

### Example

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Starting device discovery")
logger.info("Discovered 50 devices")
logger.warning("Device has no IP address")
logger.error("Failed to connect to NetBox")
logger.critical("Agent crashed")
```

---

## Command Line Interface

### Basic Usage

```bash
# Start agent
python src/netbox_agent.py

# Test connections
python src/netbox_agent.py --test-connections

# Dry run sync
python src/netbox_agent.py --sync --dry-run

# Discovery only
python src/netbox_agent.py --discover-only
```

### Options

| Option | Description |
|--------|-------------|
| `--config PATH` | Path to configuration file |
| `--test-connections` | Test all connections and exit |
| `--sync` | Run synchronization once and exit |
| `--dry-run` | Preview changes without applying |
| `--discover-only` | Run discovery without sync |
| `--log-level LEVEL` | Override log level (DEBUG/INFO/WARNING/ERROR) |

---

## Performance Benchmarks

Performance characteristics from testing:

| Operation | Scale | Performance |
|-----------|-------|-------------|
| Discovery | 1000 devices | < 1 second |
| Discovery | 5000 devices | < 1 second |
| Sync | 1000 devices | ~0.3 seconds |
| Sync | 5000 devices | ~1.5 seconds |
| Memory Usage | 5000 devices | < 250MB |

See [Performance Benchmarks](PERFORMANCE_BENCHMARKS.md) for detailed results.

---

## Reference Links

- [Configuration Reference](CONFIGURATION_REFERENCE.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Monitoring Guide](MONITORING.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Operational Runbook](RUNBOOK.md)

## Configuration Reference

### Main Configuration (`config/netbox-agent.json`)

```json
{
  "netbox": {
    "url": "https://netbox.example.com",
    "token": "your-api-token",
    "verify_ssl": true
  },
  "sources": {
    "homeassistant": {
      "enabled": true,
      "url": "http://homeassistant:8123",
      "token_path": "/config/ha_token"
    },
    "network_scan": {
      "enabled": true,
      "networks": ["192.168.1.0/24"]
    },
    "filesystem": {
      "enabled": true,
      "config_paths": ["/etc/ansible/hosts"]
    }
  },
  "sync": {
    "dry_run": false,
    "full_sync_interval": 86400,
    "incremental_sync_interval": 3600,
    "batch_size": 50
  },
  "logging": {
    "level": "INFO",
    "file": "/var/log/netbox-agent.log"
  }
}
```

### Data Mappings (`config/data-mappings.json`)

```json
{
  "homeassistant": {
    "device_name": {
      "source_field": "name",
      "target_field": "name", 
      "mapping_type": "transform",
      "transform_function": "clean_device_name"
    },
    "manufacturer": {
      "source_field": "manufacturer",
      "target_field": "device_type.manufacturer",
      "mapping_type": "lookup",
      "transform_function": "manufacturer_aliases"
    }
  }
}
```

## Error Handling

### Exception Types
- `ConfigError` - Configuration related errors
- `MCPError` - MCP server communication errors  
- `SyncError` - Synchronization errors

### Logging
The agent uses structured logging with the following levels:
- DEBUG - Detailed debugging information
- INFO - General operational information
- WARNING - Warning conditions
- ERROR - Error conditions
- CRITICAL - Critical errors that may stop the agent
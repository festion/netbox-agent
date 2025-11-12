import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from src.netbox.client import NetBoxClient
from src.netbox.sync import AdvancedSyncEngine
from src.data_sources.home_assistant import HomeAssistantDataSource
from src.data_sources.network_scanner import NetworkScannerDataSource
from src.data_sources.filesystem import FilesystemDataSource
from src.data_sources.proxmox import ProxmoxDataSource
from src.data_sources.truenas import TrueNASDataSource
from src.scheduler.scheduler import AdvancedScheduler
from src.utils.config import ConfigManager

# Test configuration
TEST_CONFIG = {
    "netbox": {
        "url": "http://test.netbox.local",
        "token": "test-token-123",
        "verify_ssl": False
    },
    "sources": {
        "homeassistant": {
            "enabled": True,
            "url": "http://test.ha.local:8123",
            "token_path": "/tmp/test_ha_token"
        },
        "network_scan": {
            "enabled": True,
            "networks": ["192.168.1.0/24"]
        },
        "filesystem": {
            "enabled": True,
            "config_paths": ["/tmp/test_configs"]
        },
        "proxmox": {
            "enabled": True,
            "url": "https://test-proxmox.local:8006",
            "username": "root@pam",
            "token": "test-token",
            "mcp_port": 8126,
            "verify_ssl": False
        },
        "truenas": {
            "enabled": True,
            "url": "https://test-truenas.local",
            "api_key": "test-api-key",
            "verify_ssl": False
        }
    },
    "sync": {
        "dry_run": True,
        "full_sync_interval": 3600,
        "batch_size": 10
    }
}

@pytest.fixture
def test_config():
    """Provide test configuration"""
    return TEST_CONFIG

@pytest.fixture
def mock_netbox_client():
    """Mock NetBox client"""
    client = Mock(spec=NetBoxClient)
    client.api = Mock()
    client.test_connection = AsyncMock(return_value=True)
    
    # Mock API responses
    client.api.dcim.devices.all = Mock(return_value=[])
    client.api.dcim.device_types.all = Mock(return_value=[])
    client.api.dcim.device_roles.all = Mock(return_value=[])
    client.api.dcim.sites.all = Mock(return_value=[])
    client.api.ipam.ip_addresses.all = Mock(return_value=[])
    
    return client

@pytest.fixture
def test_data_fixtures():
    """Load test data fixtures"""
    fixtures_dir = Path(__file__).parent / "fixtures"
    
    fixtures = {}
    
    # Load JSON fixtures
    for json_file in fixtures_dir.glob("*.json"):
        with open(json_file, 'r') as f:
            fixtures[json_file.stem] = json.load(f)
    
    return fixtures

@pytest.fixture
def mock_home_assistant_data():
    """Mock Home Assistant test data"""
    return [
        {
            "id": "device1",
            "name": "Test Router",
            "manufacturer": "Ubiquiti",
            "model": "Dream Machine",
            "device_class": "router",
            "area_id": "network_room",
            "sw_version": "1.12.33"
        },
        {
            "id": "device2", 
            "name": "Smart Switch",
            "manufacturer": "TP-Link",
            "model": "TL-SG108",
            "device_class": "switch"
        }
    ]

@pytest.fixture
def mock_network_scan_data():
    """Mock network scan test data"""
    return [
        {
            "ip": "192.168.1.1",
            "alive": True,
            "hostname": "router.local",
            "open_ports": [22, 80, 443],
            "services": {80: {"name": "HTTP", "server": "nginx"}},
            "os_guess": "Linux",
            "mac_address": "AA:BB:CC:DD:EE:FF"
        },
        {
            "ip": "192.168.1.10", 
            "alive": True,
            "hostname": "switch.local",
            "open_ports": [80, 161],
            "services": {161: {"name": "SNMP"}},
            "os_guess": "Network Device"
        }
    ]

@pytest.fixture
async def sync_engine(mock_netbox_client, test_config):
    """Create sync engine with mocked dependencies"""
    engine = AdvancedSyncEngine(mock_netbox_client, test_config)
    # Pre-populate caches to avoid API calls
    engine.device_cache = {}
    engine.device_type_cache = {}
    engine.device_role_cache = {}
    engine.site_cache = {}
    return engine

@pytest.fixture
def temp_config_files(tmp_path):
    """Create temporary config files for testing"""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    # Create test YAML file
    yaml_file = config_dir / "inventory.yaml"
    yaml_content = """
devices:
  - name: test-server-01
    ip_address: 192.168.1.100
    type: server
    group: servers
  - name: test-switch-01
    ip_address: 192.168.1.10
    type: switch
    group: network
"""
    yaml_file.write_text(yaml_content)
    
    # Create test JSON file
    json_file = config_dir / "devices.json"
    json_content = {
        "hosts": [
            {"name": "database-01", "ip": "192.168.1.200", "role": "database"},
            {"name": "web-01", "ip": "192.168.1.201", "role": "web"}
        ]
    }
    with open(json_file, 'w') as f:
        json.dump(json_content, f)
    
    return str(config_dir)

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Test utilities
def assert_device_valid(device):
    """Assert that a device object is valid"""
    assert device.name is not None
    assert len(device.name) > 0
    assert device.device_type is not None
    assert device.device_role is not None
    assert device.site is not None

def create_mock_device(name="test-device", ip="192.168.1.100",
                      manufacturer="Test Manufacturer", model="Test Model"):
    """Create a mock device for testing"""
    from src.netbox.models import Device, DeviceType, DeviceRole, Site

    # Generate slug from manufacturer and model
    slug = f"{manufacturer.lower().replace(' ', '-')}-{model.lower().replace(' ', '-')}"

    return Device(
        name=name,
        device_type=DeviceType(
            manufacturer=manufacturer,
            model=model,
            slug=slug
        ),
        device_role=DeviceRole(
            name="Test Role",
            slug="test-role",
            color="ff0000"
        ),
        site=Site(
            name="Test Site",
            slug="test-site"
        ),
        primary_ip4=ip
    )

@pytest.fixture
def mock_proxmox_data():
    """Mock Proxmox test data"""
    return {
        "system_info": {
            "version": "7.4-3",
            "hostname": "pve-test"
        },
        "vms": [
            {
                "vmid": "100",
                "name": "test-vm-1",
                "status": "running",
                "node": "pve-node1",
                "cpus": 2,
                "memory": 4096
            }
        ],
        "containers": [
            {
                "vmid": "200",
                "name": "test-ct-1",
                "status": "running",
                "node": "pve-node1",
                "cpus": 1,
                "memory": 512
            }
        ]
    }

@pytest.fixture
def mock_truenas_data():
    """Mock TrueNAS test data"""
    return {
        "system_info": {
            "hostname": "truenas.local",
            "version": "TrueNAS-13.0-U6.7",
            "system_manufacturer": "Supermicro",
            "system_product": "X11SPL-F"
        },
        "pools": [
            {
                "name": "tank",
                "status": "ONLINE",
                "size": 10995116277760,
                "allocated": 5497558138880,
                "free": 5497558138880
            }
        ],
        "datasets": [
            {
                "name": "tank/data",
                "type": "FILESYSTEM",
                "used": {"parsed": 1099511627776}
            }
        ],
        "nfs_shares": [
            {
                "path": "/mnt/tank/data",
                "enabled": True
            }
        ],
        "smb_shares": [
            {
                "name": "media",
                "path": "/mnt/tank/media",
                "enabled": True
            }
        ]
    }
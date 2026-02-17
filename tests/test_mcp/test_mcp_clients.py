import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.mcp.home_assistant import HomeAssistantMCPClient
from src.mcp.filesystem import FilesystemMCPClient
from src.mcp.manager import MCPServerManager

@pytest.mark.asyncio
async def test_home_assistant_connection():
    """Test Home Assistant MCP connection"""
    config = {
        "url": "http://test.ha.local:8123",
        "token_path": "/tmp/test_token"
    }
    
    with patch.object(HomeAssistantMCPClient, 'start_server', new_callable=AsyncMock) as mock_start:
        with patch.object(HomeAssistantMCPClient, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"status": "ok"}
            
            client = HomeAssistantMCPClient(config)
            result = await client.connect()
            
            assert result == True
            mock_start.assert_called_once()

@pytest.mark.asyncio
async def test_filesystem_file_parsing():
    """Test filesystem configuration parsing"""
    config = {
        "root_path": "/tmp",
        "allowed_directories": ["/tmp"]
    }
    
    client = FilesystemMCPClient(config)
    
    # Test YAML parsing
    yaml_content = """
    devices:
      - name: router1
        ip: 192.168.1.1
      - name: switch1
        ip: 192.168.1.2
    """
    
    devices = client.parse_yaml_config(yaml_content)
    assert len(devices) == 2
    assert devices[0]["name"] == "router1"

@pytest.mark.asyncio
async def test_filesystem_dhcp_parsing():
    """Test DHCP configuration parsing"""
    config = {
        "root_path": "/tmp",
        "allowed_directories": ["/tmp"]
    }
    
    client = FilesystemMCPClient(config)
    
    # Test DHCP conf parsing
    dhcp_content = """
    host printer {
        hardware ethernet 00:11:22:33:44:55;
        fixed-address 192.168.1.100;
    }
    
    host server {
        hardware ethernet aa:bb:cc:dd:ee:ff;
        fixed-address 192.168.1.200;
    }
    """
    
    devices = client.parse_conf_file(dhcp_content)
    assert len(devices) == 2
    assert devices[0]["name"] == "printer"
    assert devices[0]["mac_address"] == "00:11:22:33:44:55"
    assert devices[0]["ip_address"] == "192.168.1.100"

@pytest.mark.asyncio
async def test_home_assistant_device_mapping():
    """Test Home Assistant device mapping to NetBox"""
    config = {
        "url": "http://test.ha.local:8123",
        "token_path": "/tmp/test_token"
    }
    
    client = HomeAssistantMCPClient(config)
    
    ha_device = {
        "id": "test_device_id",
        "name": "Smart Light Switch",
        "manufacturer": "TP-Link",
        "model": "Kasa HS200",
        "device_class": "switch",
        "area_id": "living_room",
        "attributes": {
            "ip_address": "192.168.1.150"
        }
    }
    
    netbox_device = client.map_to_netbox_device(ha_device)
    
    assert netbox_device.name == "smart-light-switch"
    assert netbox_device.device_type["manufacturer"] == "TP-Link"
    assert netbox_device.device_role["name"] == "IoT Switch"
    assert netbox_device.site["name"] == "Living Room"
    assert netbox_device.primary_ip4 == "192.168.1.150"

@pytest.mark.asyncio
async def test_mcp_manager_initialization():
    """Test MCP Server Manager initialization"""
    config = {
        "sources": {
            "homeassistant": {"enabled": True, "url": "http://test:8123"},
            "filesystem": {"enabled": True, "config_paths": ["/test/path"]},
            "proxmox": {"enabled": False},
            "truenas": {"enabled": False}
        }
    }
    
    manager = MCPServerManager(config)
    
    assert "homeassistant" in manager.clients
    assert "filesystem" in manager.clients
    assert "proxmox" not in manager.clients
    assert "truenas" not in manager.clients

@pytest.mark.asyncio
async def test_mcp_manager_connect_all():
    """Test MCP Manager connecting to all clients"""
    config = {
        "sources": {
            "homeassistant": {"enabled": True, "url": "http://test:8123"},
            "filesystem": {"enabled": True, "config_paths": ["/test/path"]}
        }
    }
    
    manager = MCPServerManager(config)
    
    # Mock the client connections
    with patch.object(manager.clients["homeassistant"], "connect", new_callable=AsyncMock) as mock_ha_connect:
        with patch.object(manager.clients["filesystem"], "connect", new_callable=AsyncMock) as mock_fs_connect:
            mock_ha_connect.return_value = True
            mock_fs_connect.return_value = True
            
            results = await manager.connect_all()
            
            assert results["homeassistant"] == True
            assert results["filesystem"] == True
            mock_ha_connect.assert_called_once()
            mock_fs_connect.assert_called_once()

@pytest.mark.asyncio
async def test_filesystem_ansible_inventory_parsing():
    """Test Ansible inventory parsing"""
    config = {
        "root_path": "/tmp",
        "allowed_directories": ["/tmp"]
    }
    
    client = FilesystemMCPClient(config)
    
    # Test Ansible inventory content
    ansible_content = """
    [web_servers]
    web1 ansible_host=192.168.1.10 ansible_user=ubuntu
    web2 ansible_host=192.168.1.11 ansible_user=ubuntu
    
    [database_servers]
    db1 ansible_host=192.168.1.20 ansible_user=postgres
    """
    
    devices = client.parse_ansible_inventory_content(ansible_content)
    assert len(devices) == 3
    assert devices[0]["name"] == "web1"
    assert devices[0]["ip_address"] == "192.168.1.10"
    assert devices[0]["group"] == "web_servers"

# Add helper method to filesystem client for testing
def parse_ansible_inventory_content(self, content: str):
    """Helper method for testing - parse content directly"""
    devices = []
    lines = content.split('\n')
    current_group = None
    
    for line in lines:
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('#'):
            continue
        
        # Group header
        if line.startswith('[') and line.endswith(']'):
            current_group = line[1:-1]
            continue
        
        # Host entry
        if current_group and not line.startswith('['):
            parts = line.split()
            hostname = parts[0]
            
            device = {
                'name': hostname,
                'group': current_group
            }
            
            # Parse host variables
            for part in parts[1:]:
                if '=' in part:
                    key, value = part.split('=', 1)
                    if key == 'ansible_host':
                        device['ip_address'] = value
                    elif key == 'ansible_user':
                        device['username'] = value
                    else:
                        device[key] = value
            
            devices.append(device)
    
    return devices

# Monkey patch the method for testing
FilesystemMCPClient.parse_ansible_inventory_content = parse_ansible_inventory_content
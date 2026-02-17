import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.netbox_agent import NetBoxAgent
from src.mcp.manager import MCPServerManager

@pytest.mark.asyncio
async def test_agent_mcp_integration():
    """Test NetBox Agent MCP integration"""
    
    # Mock config
    mock_config = {
        "netbox": {
            "url": "http://netbox.test",
            "token": "test_token",
            "verify_ssl": True
        },
        "sources": {
            "homeassistant": {
                "enabled": True,
                "url": "http://ha.test:8123",
                "token_path": "/tmp/test_token"
            },
            "filesystem": {
                "enabled": True,
                "config_paths": ["/tmp/test.conf"]
            }
        },
        "logging": {
            "level": "INFO",
            "file": "/tmp/test.log",
            "max_size": "10MB",
            "backup_count": 5
        },
        "sync": {
            "dry_run": True,
            "full_sync_interval": 3600,
            "incremental_sync_interval": 1800
        }
    }
    
    with patch('src.netbox_agent.AgentConfig') as mock_agent_config:
        with patch('builtins.open', mock_open(read_data='{"test": "config"}')):
            with patch('json.load', return_value=mock_config):
                with patch('pathlib.Path.mkdir'):
                    with patch('logging.basicConfig'):
                        agent = NetBoxAgent("/tmp/test_config.json")
                        
                        # Mock MCP manager
                        with patch.object(agent.mcp_manager, 'connect_all', new_callable=AsyncMock) as mock_connect:
                            with patch.object(agent.mcp_manager, 'get_client') as mock_get_client:
                                with patch.object(agent, 'test_netbox_connection', new_callable=AsyncMock) as mock_netbox_test:
                                    
                                    mock_connect.return_value = {"homeassistant": True, "filesystem": True}
                                    mock_netbox_test.return_value = True
                                    
                                    # Mock HA client
                                    mock_ha_client = Mock()
                                    mock_ha_client.get_devices = AsyncMock(return_value=[
                                        {
                                            "id": "test1",
                                            "name": "Test Device 1",
                                            "manufacturer": "Test Corp",
                                            "model": "Test Model"
                                        }
                                    ])
                                    mock_ha_client.map_to_netbox_device = Mock(return_value={
                                        "name": "test-device-1",
                                        "device_type": {"manufacturer": "Test Corp", "model": "Test Model"}
                                    })
                                    
                                    # Mock FS client
                                    mock_fs_client = Mock()
                                    mock_fs_client.parse_network_config = AsyncMock(return_value=[
                                        {"name": "server1", "ip_address": "192.168.1.10"}
                                    ])
                                    
                                    def get_client_side_effect(client_name):
                                        if client_name == "homeassistant":
                                            return mock_ha_client
                                        elif client_name == "filesystem":
                                            return mock_fs_client
                                        return None
                                    
                                    mock_get_client.side_effect = get_client_side_effect
                                    
                                    with patch.object(agent, '_sync_device_to_netbox', new_callable=AsyncMock) as mock_sync:
                                        # Test sync methods
                                        await agent.sync_home_assistant()
                                        await agent.sync_filesystem()
                                        
                                        # Verify calls
                                        mock_ha_client.get_devices.assert_called_once()
                                        mock_ha_client.map_to_netbox_device.assert_called_once()
                                        mock_fs_client.parse_network_config.assert_called_once_with("/tmp/test.conf")
                                        
                                        # Should sync 2 devices (1 from HA, 1 from filesystem)
                                        assert mock_sync.call_count == 2

@pytest.mark.asyncio
async def test_mcp_health_check():
    """Test MCP health check functionality"""
    config = {
        "sources": {
            "homeassistant": {"enabled": True},
            "filesystem": {"enabled": True}
        }
    }
    
    manager = MCPServerManager(config)
    
    # Mock clients
    mock_ha_client = Mock()
    mock_ha_client.list_tools = AsyncMock(return_value=["tool1", "tool2"])
    
    mock_fs_client = Mock()
    mock_fs_client.list_tools = AsyncMock(return_value=["tool3", "tool4"])
    
    manager.clients["homeassistant"] = mock_ha_client
    manager.clients["filesystem"] = mock_fs_client
    
    health_status = await manager.health_check()
    
    assert health_status["homeassistant"] == True
    assert health_status["filesystem"] == True

@pytest.mark.asyncio
async def test_mcp_collect_all_devices():
    """Test collecting devices from all MCP sources"""
    config = {
        "sources": {
            "homeassistant": {"enabled": True},
            "filesystem": {"enabled": True, "config_paths": ["/test/path"]}
        }
    }
    
    manager = MCPServerManager(config)
    
    # Mock HA client
    mock_ha_client = Mock()
    mock_ha_client.get_devices = AsyncMock(return_value=[
        {"id": "ha1", "name": "HA Device 1"},
        {"id": "ha2", "name": "HA Device 2"}
    ])
    mock_ha_client.map_to_netbox_device = Mock(side_effect=lambda x: {
        "name": x["name"].lower().replace(" ", "-"),
        "source": "homeassistant"
    })
    
    # Mock FS client
    mock_fs_client = Mock()
    mock_fs_client.parse_network_config = AsyncMock(return_value=[
        {"name": "server1", "ip": "192.168.1.10"},
        {"name": "server2", "ip": "192.168.1.11"}
    ])
    
    manager.clients["homeassistant"] = mock_ha_client
    manager.clients["filesystem"] = mock_fs_client
    
    all_devices = await manager.collect_all_devices()
    
    assert "homeassistant" in all_devices
    assert "filesystem" in all_devices
    assert len(all_devices["homeassistant"]) == 2
    assert len(all_devices["filesystem"]) == 2

def mock_open(read_data):
    """Helper function to create mock open"""
    from unittest.mock import mock_open as mock_open_func
    return mock_open_func(read_data=read_data)
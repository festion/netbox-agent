#!/usr/bin/env python3
"""
Tests for NetBox Agent
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.netbox_agent import NetBoxAgent, AgentConfig, NetBoxConfig


@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        "netbox": {
            "url": "https://test-netbox.example.com",
            "token": "test-token",
            "verify_ssl": True
        },
        "sources": {
            "homeassistant": {
                "enabled": True,
                "url": "http://192.168.1.10:8123",
                "token_path": "/tmp/ha_token",
                "sync_interval": 3600
            },
            "network_scan": {
                "enabled": True,
                "networks": ["192.168.1.0/24"],
                "scan_interval": 3600
            },
            "filesystem": {
                "enabled": True,
                "config_paths": ["/tmp/configs"],
                "watch_interval": 300
            }
        },
        "logging": {
            "level": "INFO",
            "file": "/tmp/netbox-agent.log",
            "max_size": "10MB",
            "backup_count": 5
        },
        "sync": {
            "dry_run": True,
            "full_sync_interval": 86400,
            "incremental_sync_interval": 3600
        }
    }


@pytest.fixture
def config_file(sample_config):
    """Create temporary config file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_config, f)
        config_path = f.name
    
    yield config_path
    
    # Cleanup
    Path(config_path).unlink()


class TestNetBoxAgent:
    """Test cases for NetBoxAgent"""
    
    def test_config_loading(self, config_file):
        """Test configuration loading"""
        agent = NetBoxAgent(config_file)
        assert agent.config.netbox.url == "https://test-netbox.example.com"
        assert agent.config.netbox.token == "test-token"
        assert agent.config.sync.dry_run is True
    
    @patch('requests.Session.get')
    @pytest.mark.asyncio
    async def test_netbox_connection_success(self, mock_get, config_file):
        """Test successful NetBox connection"""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        agent = NetBoxAgent(config_file)
        result = await agent.test_netbox_connection()
        
        assert result is True
        mock_get.assert_called_once()
    
    @patch('requests.Session.get')
    @pytest.mark.asyncio
    async def test_netbox_connection_failure(self, mock_get, config_file):
        """Test failed NetBox connection"""
        # Mock failed response
        mock_get.side_effect = Exception("Connection failed")
        
        agent = NetBoxAgent(config_file)
        result = await agent.test_netbox_connection()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_sync_home_assistant_disabled(self, config_file, sample_config):
        """Test Home Assistant sync when disabled"""
        # Disable Home Assistant in config
        sample_config["sources"]["homeassistant"]["enabled"] = False
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_config, f)
            disabled_config_path = f.name
        
        try:
            agent = NetBoxAgent(disabled_config_path)
            # Should complete without error when disabled
            await agent.sync_home_assistant()
        finally:
            Path(disabled_config_path).unlink()
    
    @pytest.mark.asyncio
    async def test_sync_home_assistant_enabled(self, config_file):
        """Test Home Assistant sync when enabled"""
        agent = NetBoxAgent(config_file)
        
        # Should complete without error (currently just logs)
        await agent.sync_home_assistant()
    
    @pytest.mark.asyncio
    async def test_sync_network_scan(self, config_file):
        """Test network scan sync"""
        agent = NetBoxAgent(config_file)
        
        # Should complete without error (currently just logs)
        await agent.sync_network_scan()
    
    @pytest.mark.asyncio
    async def test_sync_filesystem(self, config_file):
        """Test filesystem sync"""
        agent = NetBoxAgent(config_file)
        
        # Should complete without error (currently just logs)
        await agent.sync_filesystem()
    
    @patch.object(NetBoxAgent, 'test_netbox_connection')
    @pytest.mark.asyncio
    async def test_full_sync_connection_failure(self, mock_connection, config_file):
        """Test full sync when NetBox connection fails"""
        mock_connection.return_value = False
        
        agent = NetBoxAgent(config_file)
        await agent.perform_full_sync()
        
        mock_connection.assert_called_once()
    
    @patch.object(NetBoxAgent, 'test_netbox_connection')
    @patch.object(NetBoxAgent, 'sync_home_assistant')
    @patch.object(NetBoxAgent, 'sync_network_scan')  
    @patch.object(NetBoxAgent, 'sync_filesystem')
    @pytest.mark.asyncio
    async def test_full_sync_success(self, mock_fs, mock_net, mock_ha, mock_connection, config_file):
        """Test successful full sync"""
        mock_connection.return_value = True
        mock_ha.return_value = None
        mock_net.return_value = None
        mock_fs.return_value = None
        
        agent = NetBoxAgent(config_file)
        await agent.perform_full_sync()
        
        mock_connection.assert_called_once()
        mock_ha.assert_called_once()
        mock_net.assert_called_once()
        mock_fs.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
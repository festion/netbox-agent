import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.data_sources.home_assistant import HomeAssistantDataSource
from src.netbox.models import Device

class TestHomeAssistantDataSource:
    """Test Home Assistant data source"""
    
    @pytest.fixture
    def ha_source(self, test_config):
        """Create Home Assistant data source"""
        return HomeAssistantDataSource(test_config["sources"]["homeassistant"])
    
    @pytest.mark.asyncio
    async def test_discover_devices(self, ha_source, mock_home_assistant_data):
        """Test device discovery from Home Assistant"""
        
        # Mock MCP client
        ha_source.mcp_client.connect = AsyncMock(return_value=True)
        ha_source.mcp_client.get_devices = AsyncMock(return_value=mock_home_assistant_data)
        ha_source.mcp_client.get_network_devices = AsyncMock(return_value=[])
        ha_source.mcp_client.disconnect = AsyncMock()
        
        devices = await ha_source.discover()
        
        assert len(devices) == 2
        assert all(isinstance(d, Device) for d in devices)
        assert any(d.name.startswith("test-router") for d in devices)
    
    @pytest.mark.asyncio
    async def test_connection_test(self, ha_source):
        """Test connection testing"""
        ha_source.mcp_client.connect = AsyncMock(return_value=True)
        ha_source.mcp_client.disconnect = AsyncMock()
        
        result = await ha_source.test_connection()
        
        assert result == True
    
    def test_is_network_relevant_router(self, ha_source):
        """Test network relevance detection for router"""
        device_data = {
            "device_class": "router",
            "manufacturer": "Ubiquiti"
        }
        
        result = ha_source.is_network_relevant(device_data, {})
        
        assert result == True
    
    def test_is_network_relevant_irrelevant(self, ha_source):
        """Test network relevance detection for non-network device"""
        device_data = {
            "device_class": "light",
            "manufacturer": "Philips"
        }
        
        result = ha_source.is_network_relevant(device_data, {})
        
        assert result == False
    
    def test_device_type_determination(self, ha_source):
        """Test device type determination"""
        device_data = {
            "manufacturer": "Ubiquiti",
            "model": "Dream Machine",
            "device_class": "router"
        }
        
        device_type = ha_source.determine_device_type_from_config(device_data, {})
        
        assert device_type.manufacturer == "Ubiquiti"
        assert device_type.model == "Dream Machine"
    
    def test_device_name_sanitization(self, ha_source):
        """Test device name sanitization"""
        names = [
            "Device Name with Spaces",
            "device-with-hyphens",
            "Device_with_underscores",
            "Device@#$%Special!Characters"
        ]
        
        expected = [
            "device-name-with-spaces",
            "device-with-hyphens",
            "device-with-underscores",
            "devicespecialcharacters"
        ]
        
        for name, expected_result in zip(names, expected):
            result = ha_source.sanitize_device_name(name)
            assert result == expected_result
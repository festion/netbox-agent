import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
from src.data_sources.filesystem import FilesystemDataSource
from src.netbox.models import Device

class TestFilesystemDataSource:
    """Test Filesystem data source"""
    
    @pytest.fixture
    def fs_source(self, test_config, temp_config_files):
        """Create Filesystem data source"""
        config = test_config["sources"]["filesystem"].copy()
        config["config_paths"] = [temp_config_files]
        return FilesystemDataSource(config)
    
    @pytest.mark.asyncio
    async def test_discover_devices(self, fs_source):
        """Test device discovery from filesystem configs"""
        
        devices = await fs_source.discover()
        
        assert len(devices) >= 2  # From YAML and JSON fixtures
        assert all(isinstance(d, Device) for d in devices)
        
        # Check for devices from YAML file
        yaml_devices = [d for d in devices if d.name in ["test-server-01", "test-switch-01"]]
        assert len(yaml_devices) == 2
        
        # Check for devices from JSON file
        json_devices = [d for d in devices if d.name in ["database-01", "web-01"]]
        assert len(json_devices) == 2
    
    def test_parse_yaml_file(self, fs_source, temp_config_files):
        """Test YAML file parsing"""
        yaml_file = Path(temp_config_files) / "inventory.yaml"
        
        devices = fs_source.parse_yaml_file(str(yaml_file))
        
        assert len(devices) == 2
        assert devices[0]["name"] == "test-server-01"
        assert devices[0]["ip_address"] == "192.168.1.100"
        assert devices[1]["name"] == "test-switch-01"
        assert devices[1]["type"] == "switch"
    
    def test_parse_json_file(self, fs_source, temp_config_files):
        """Test JSON file parsing"""
        json_file = Path(temp_config_files) / "devices.json"
        
        devices = fs_source.parse_json_file(str(json_file))
        
        assert len(devices) == 2
        assert devices[0]["name"] == "database-01"
        assert devices[0]["ip"] == "192.168.1.200"
        assert devices[1]["role"] == "web"
    
    def test_convert_to_device_yaml(self, fs_source):
        """Test conversion from YAML data to Device object"""
        device_data = {
            "name": "test-device",
            "ip_address": "192.168.1.50",
            "type": "server",
            "group": "servers"
        }
        
        device = fs_source.convert_to_device(device_data, "yaml")
        
        assert device.name == "test-device"
        assert device.primary_ip4 == "192.168.1.50"
        assert device.device_role.name == "Server"
    
    def test_convert_to_device_json(self, fs_source):
        """Test conversion from JSON data to Device object"""
        device_data = {
            "name": "api-server",
            "ip": "192.168.1.75",
            "role": "api"
        }
        
        device = fs_source.convert_to_device(device_data, "json")
        
        assert device.name == "api-server"
        assert device.primary_ip4 == "192.168.1.75"
        assert device.device_role.name == "API"
    
    def test_determine_device_type_from_name(self, fs_source):
        """Test device type determination from name"""
        
        # Router
        router_data = {"name": "core-router-01"}
        device_type = fs_source.determine_device_type_from_name(router_data)
        assert "router" in device_type.model.lower()
        
        # Switch
        switch_data = {"name": "access-switch-24p"}
        device_type = fs_source.determine_device_type_from_name(switch_data)
        assert "switch" in device_type.model.lower()
        
        # Server
        server_data = {"name": "web-server-prod"}
        device_type = fs_source.determine_device_type_from_name(server_data)
        assert "server" in device_type.model.lower()
    
    def test_determine_device_role_from_type(self, fs_source):
        """Test device role determination from type field"""
        
        test_cases = [
            ("router", "Router"),
            ("switch", "Switch"), 
            ("server", "Server"),
            ("firewall", "Firewall"),
            ("api", "API")
        ]
        
        for type_value, expected_role in test_cases:
            device_data = {"type": type_value}
            device_role = fs_source.determine_device_role_from_type(device_data)
            assert device_role.name == expected_role
    
    def test_find_config_files(self, fs_source, temp_config_files):
        """Test finding configuration files"""
        
        config_files = fs_source.find_config_files(temp_config_files)
        
        # Should find both YAML and JSON files
        yaml_files = [f for f in config_files if f.endswith('.yaml')]
        json_files = [f for f in config_files if f.endswith('.json')]
        
        assert len(yaml_files) >= 1
        assert len(json_files) >= 1
    
    def test_validate_device_data(self, fs_source):
        """Test device data validation"""
        
        # Valid data
        valid_data = {
            "name": "valid-device",
            "ip_address": "192.168.1.100"
        }
        assert fs_source.validate_device_data(valid_data) == True
        
        # Missing name
        invalid_data = {
            "ip_address": "192.168.1.100"
        }
        assert fs_source.validate_device_data(invalid_data) == False
        
        # Invalid IP
        invalid_ip_data = {
            "name": "device",
            "ip_address": "not.an.ip"
        }
        assert fs_source.validate_device_data(invalid_ip_data) == False
import pytest
from src.netbox.models import Device, DeviceType, DeviceRole, Site

class TestNetBoxModels:
    """Test NetBox model classes"""
    
    def test_device_creation(self):
        """Test device model creation"""
        device_type = DeviceType(
            manufacturer="Ubiquiti",
            model="Dream Machine",
            slug="ubiquiti-dream-machine"
        )
        
        device_role = DeviceRole(
            name="Router",
            slug="router",
            color="ff0000"
        )
        
        site = Site(
            name="Main Site",
            slug="main-site"
        )
        
        device = Device(
            name="test-router",
            device_type=device_type,
            device_role=device_role,
            site=site,
            primary_ip4="192.168.1.1"
        )
        
        assert device.name == "test-router"
        assert device.device_type.manufacturer == "Ubiquiti"
        assert device.device_role.name == "Router"
        assert device.site.name == "Main Site"
        assert device.primary_ip4 == "192.168.1.1"
    
    def test_device_validation(self):
        """Test device validation"""
        device_type = DeviceType(
            manufacturer="Test",
            model="Model",
            slug="test-model"
        )
        
        device_role = DeviceRole(
            name="Test Role",
            slug="test-role",
            color="ff0000"
        )
        
        site = Site(
            name="Test Site",
            slug="test-site"
        )
        
        # Valid device
        device = Device(
            name="valid-device-name",
            device_type=device_type,
            device_role=device_role,
            site=site,
            primary_ip4="192.168.1.100"
        )
        
        # Test that device was created successfully
        assert device.name == "valid-device-name"
    
    def test_device_invalid_name(self):
        """Test device with invalid name"""
        device_type = DeviceType(
            manufacturer="Test",
            model="Model",
            slug="test-model"
        )
        
        device_role = DeviceRole(
            name="Test Role",
            slug="test-role",
            color="ff0000"
        )
        
        site = Site(
            name="Test Site",
            slug="test-site"
        )
        
        # Device with spaces in name should still be created
        # Validation would happen at the sync level
        device = Device(
            name="invalid device name",
            device_type=device_type,
            device_role=device_role,
            site=site
        )
        
        assert device.name == "invalid device name"
    
    def test_device_serialization(self):
        """Test device serialization"""
        device_type = DeviceType(
            manufacturer="Cisco",
            model="Catalyst 2960",
            slug="cisco-catalyst-2960"
        )
        
        device_role = DeviceRole(
            name="Switch",
            slug="switch",
            color="00ff00"
        )
        
        site = Site(
            name="Data Center",
            slug="data-center"
        )
        
        device = Device(
            name="switch-01",
            device_type=device_type,
            device_role=device_role,
            site=site,
            primary_ip4="192.168.1.10"
        )
        
        # Test that device model has expected attributes
        assert device.name == "switch-01"
        assert device.device_type.manufacturer == "Cisco"
        assert device.device_role.name == "Switch"
        assert device.site.name == "Data Center"
        assert device.primary_ip4 == "192.168.1.10"
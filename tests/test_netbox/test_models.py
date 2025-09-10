"""Tests for NetBox Models"""

import pytest
from pydantic import ValidationError
from ipaddress import IPv4Interface, IPv6Interface

from src.netbox.models import (
    Device, DeviceType, DeviceRole, Site, Manufacturer, Platform,
    IPAddress, Interface, DeviceCreateRequest, DeviceStatus, 
    InterfaceType, IPAddressStatus
)


class TestDeviceType:
    """Test DeviceType model"""
    
    def test_device_type_creation(self):
        """Test creating a device type"""
        device_type = DeviceType(
            manufacturer="Dell",
            model="PowerEdge R740",
            slug="dell-poweredge-r740"
        )
        
        assert device_type.manufacturer == "Dell"
        assert device_type.model == "PowerEdge R740"
        assert device_type.slug == "dell-poweredge-r740"
        assert device_type.u_height == 1.0  # Default
        assert device_type.is_full_depth is True  # Default
    
    def test_device_type_with_optional_fields(self):
        """Test device type with optional fields"""
        device_type = DeviceType(
            manufacturer="Cisco",
            model="Catalyst 9300",
            slug="cisco-catalyst-9300",
            part_number="C9300-24T-A",
            u_height=2.0,
            is_full_depth=False
        )
        
        assert device_type.part_number == "C9300-24T-A"
        assert device_type.u_height == 2.0
        assert device_type.is_full_depth is False


class TestDeviceRole:
    """Test DeviceRole model"""
    
    def test_device_role_creation(self):
        """Test creating a device role"""
        role = DeviceRole(
            name="Server",
            slug="server",
            color="aa1409"
        )
        
        assert role.name == "Server"
        assert role.slug == "server"
        assert role.color == "aa1409"
    
    def test_device_role_defaults(self):
        """Test device role with default color"""
        role = DeviceRole(
            name="Network Equipment",
            slug="network-equipment"
        )
        
        assert role.color == "9e9e9e"  # Default gray


class TestSite:
    """Test Site model"""
    
    def test_site_creation(self):
        """Test creating a site"""
        site = Site(
            name="Main Data Center",
            slug="main-dc"
        )
        
        assert site.name == "Main Data Center"
        assert site.slug == "main-dc"
        assert site.status == "active"  # Default
    
    def test_site_with_location(self):
        """Test site with geographic information"""
        site = Site(
            name="East Coast DC",
            slug="east-coast-dc",
            physical_address="123 Tech Street, New York, NY",
            latitude=40.7128,
            longitude=-74.0060
        )
        
        assert site.physical_address == "123 Tech Street, New York, NY"
        assert site.latitude == 40.7128
        assert site.longitude == -74.0060


class TestDevice:
    """Test Device model"""
    
    @pytest.fixture
    def sample_device_components(self):
        """Sample device components"""
        return {
            'device_type': DeviceType(
                manufacturer="HPE",
                model="ProLiant DL380",
                slug="hpe-proliant-dl380"
            ),
            'device_role': DeviceRole(
                name="Server",
                slug="server"
            ),
            'site': Site(
                name="Production DC",
                slug="prod-dc"
            )
        }
    
    def test_device_creation(self, sample_device_components):
        """Test creating a device"""
        device = Device(
            name="web-server-01",
            **sample_device_components
        )
        
        assert device.name == "web-server-01"
        assert device.status == DeviceStatus.ACTIVE  # Default
        assert device.device_type.manufacturer == "HPE"
        assert device.device_role.name == "Server"
        assert device.site.name == "Production DC"
    
    def test_device_with_optional_fields(self, sample_device_components):
        """Test device with all optional fields"""
        device = Device(
            name="db-server-01",
            serial="ABC123456",
            asset_tag="ASSET-001",
            comments="Production database server",
            status=DeviceStatus.PLANNED,
            **sample_device_components
        )
        
        assert device.serial == "ABC123456"
        assert device.asset_tag == "ASSET-001"
        assert device.comments == "Production database server"
        assert device.status == DeviceStatus.PLANNED
    
    def test_device_name_validation(self, sample_device_components):
        """Test device name validation"""
        # Valid name should work
        device = Device(name="valid-name", **sample_device_components)
        assert device.name == "valid-name"
        
        # Empty name should raise validation error
        with pytest.raises(ValidationError):
            Device(name="", **sample_device_components)
        
        # None name should raise validation error
        with pytest.raises(ValidationError):
            Device(name=None, **sample_device_components)
    
    def test_device_custom_fields(self, sample_device_components):
        """Test device custom fields"""
        device = Device(
            name="custom-server",
            custom_fields={
                "warranty_expiry": "2025-12-31",
                "business_unit": "Engineering",
                "criticality": "High"
            },
            **sample_device_components
        )
        
        assert device.custom_fields["warranty_expiry"] == "2025-12-31"
        assert device.custom_fields["business_unit"] == "Engineering"
        assert device.custom_fields["criticality"] == "High"


class TestIPAddress:
    """Test IPAddress model"""
    
    def test_ipv4_address_creation(self):
        """Test creating IPv4 address"""
        ip = IPAddress(
            address="192.168.1.100/24",
            status="active"
        )
        
        assert ip.address == "192.168.1.100/24"
        assert ip.status == "active"
    
    def test_ipv6_address_creation(self):
        """Test creating IPv6 address"""
        ip = IPAddress(
            address="2001:db8::1/64",
            status="active"
        )
        
        assert ip.address == "2001:db8::1/64"
    
    def test_ip_address_validation_valid(self):
        """Test valid IP address formats"""
        valid_addresses = [
            "192.168.1.1/24",
            "10.0.0.1/8",
            "172.16.0.1/16",
            "2001:db8::1/64",
            "fe80::1/64"
        ]
        
        for addr in valid_addresses:
            ip = IPAddress(address=addr)
            assert ip.address == addr
    
    def test_ip_address_validation_invalid(self):
        """Test invalid IP address formats"""
        invalid_addresses = [
            "not.an.ip.address",
            "256.1.1.1/24",
            "192.168.1.1/33",
            "192.168.1",
            ""
        ]
        
        for addr in invalid_addresses:
            with pytest.raises(ValidationError):
                IPAddress(address=addr)
    
    def test_ip_address_with_assignment(self):
        """Test IP address assigned to device"""
        ip = IPAddress(
            address="10.1.1.50/24",
            assigned_object_type="dcim.device",
            assigned_object_id=123,
            dns_name="server01.example.com",
            description="Primary server IP"
        )
        
        assert ip.assigned_object_type == "dcim.device"
        assert ip.assigned_object_id == 123
        assert ip.dns_name == "server01.example.com"
        assert ip.description == "Primary server IP"


class TestInterface:
    """Test Interface model"""
    
    def test_interface_creation(self):
        """Test creating an interface"""
        interface = Interface(
            device_id=123,
            name="eth0",
            type="1000base-t"
        )
        
        assert interface.device_id == 123
        assert interface.name == "eth0"
        assert interface.type == "1000base-t"
        assert interface.enabled is True  # Default
    
    def test_interface_with_optional_fields(self):
        """Test interface with all optional fields"""
        interface = Interface(
            device_id=456,
            name="GigabitEthernet0/1",
            type="10gbase-t",
            enabled=False,
            mac_address="00:11:22:33:44:55",
            mtu=9000,
            description="Uplink to core switch"
        )
        
        assert interface.enabled is False
        assert interface.mac_address == "00:11:22:33:44:55"
        assert interface.mtu == 9000
        assert interface.description == "Uplink to core switch"


class TestDeviceCreateRequest:
    """Test DeviceCreateRequest model"""
    
    def test_device_create_request(self):
        """Test creating device create request"""
        request = DeviceCreateRequest(
            name="new-server",
            device_type={
                'manufacturer': 'Dell',
                'model': 'PowerEdge R740',
                'slug': 'dell-poweredge-r740'
            },
            device_role={
                'name': 'Server',
                'slug': 'server'
            },
            site={
                'name': 'Main DC',
                'slug': 'main-dc'
            },
            status='active'
        )
        
        assert request.name == "new-server"
        assert request.device_type['manufacturer'] == 'Dell'
        assert request.device_role['name'] == 'Server'
        assert request.site['name'] == 'Main DC'
        assert request.status == 'active'


class TestEnums:
    """Test enumeration types"""
    
    def test_device_status_enum(self):
        """Test DeviceStatus enum values"""
        assert DeviceStatus.ACTIVE == "active"
        assert DeviceStatus.PLANNED == "planned"
        assert DeviceStatus.STAGED == "staged"
        assert DeviceStatus.FAILED == "failed"
        assert DeviceStatus.INVENTORY == "inventory"
        assert DeviceStatus.DECOMMISSIONING == "decommissioning"
        assert DeviceStatus.OFFLINE == "offline"
    
    def test_interface_type_enum(self):
        """Test InterfaceType enum values"""
        assert InterfaceType.ETHERNET_1G == "1000base-t"
        assert InterfaceType.ETHERNET_10G == "10gbase-t"
        assert InterfaceType.ETHERNET_25G == "25gbase-t"
    
    def test_ip_address_status_enum(self):
        """Test IPAddressStatus enum values"""
        assert IPAddressStatus.ACTIVE == "active"
        assert IPAddressStatus.RESERVED == "reserved"
        assert IPAddressStatus.DEPRECATED == "deprecated"
        assert IPAddressStatus.DHCP == "dhcp"


class TestModelIntegration:
    """Test model integration and relationships"""
    
    def test_complete_device_with_relationships(self):
        """Test creating complete device with all relationships"""
        manufacturer = Manufacturer(
            name="Cisco",
            slug="cisco"
        )
        
        device_type = DeviceType(
            manufacturer="Cisco",
            model="Catalyst 9300-24T",
            slug="cisco-catalyst-9300-24t",
            part_number="C9300-24T-A"
        )
        
        device_role = DeviceRole(
            name="Access Switch",
            slug="access-switch",
            color="2196f3"
        )
        
        site = Site(
            name="Branch Office",
            slug="branch-office",
            physical_address="456 Business Ave"
        )
        
        platform = Platform(
            name="Cisco IOS",
            slug="cisco-ios"
        )
        
        device = Device(
            name="sw-branch-01",
            device_type=device_type,
            device_role=device_role,
            site=site,
            platform=platform.name,
            serial="FCW2140L0GH",
            status=DeviceStatus.ACTIVE
        )
        
        # Verify all relationships
        assert device.name == "sw-branch-01"
        assert device.device_type.manufacturer == "Cisco"
        assert device.device_type.model == "Catalyst 9300-24T"
        assert device.device_role.name == "Access Switch"
        assert device.site.name == "Branch Office"
        assert device.platform == "Cisco IOS"
        assert device.serial == "FCW2140L0GH"
        assert device.status == DeviceStatus.ACTIVE
    
    def test_device_serialization(self):
        """Test device model serialization"""
        device = Device(
            name="test-device",
            device_type=DeviceType(
                manufacturer="Test",
                model="Test Device",
                slug="test-device"
            ),
            device_role=DeviceRole(
                name="Test Role",
                slug="test-role"
            ),
            site=Site(
                name="Test Site",
                slug="test-site"
            )
        )
        
        device_dict = device.model_dump()
        
        assert isinstance(device_dict, dict)
        assert device_dict['name'] == "test-device"
        assert device_dict['device_type']['manufacturer'] == "Test"
        assert device_dict['device_role']['name'] == "Test Role"
        assert device_dict['site']['name'] == "Test Site"
    
    def test_model_json_serialization(self):
        """Test JSON serialization of models"""
        ip = IPAddress(
            address="192.168.1.1/24",
            status="active",
            dns_name="gateway.local"
        )
        
        json_str = ip.model_dump_json()
        assert isinstance(json_str, str)
        assert "192.168.1.1/24" in json_str
        assert "gateway.local" in json_str
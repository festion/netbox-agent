"""Tests for NetBox API Client"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import ConnectionError, HTTPError

from src.netbox.client import NetBoxClient
from src.netbox.models import DeviceCreateRequest, Device, DeviceType, DeviceRole, Site


@pytest.fixture
def mock_api():
    """Mock pynetbox API object"""
    with patch('pynetbox.api') as mock:
        api_instance = Mock()
        mock.return_value = api_instance
        
        # Mock API endpoints
        api_instance.dcim = Mock()
        api_instance.dcim.devices = Mock()
        api_instance.dcim.device_types = Mock()
        api_instance.dcim.device_roles = Mock()
        api_instance.dcim.sites = Mock()
        api_instance.dcim.manufacturers = Mock()
        
        api_instance.ipam = Mock()
        api_instance.ipam.ip_addresses = Mock()
        
        api_instance.status = Mock(return_value={'netbox-version': '3.6.0'})
        
        yield api_instance


@pytest.fixture
def netbox_client(mock_api):
    """NetBox client fixture"""
    client = NetBoxClient(
        url="http://test.netbox.com",
        token="test-token-123",
        verify_ssl=False
    )
    return client


@pytest.fixture
def sample_device_data():
    """Sample device data for testing"""
    return DeviceCreateRequest(
        name="test-device-01",
        device_type={
            'manufacturer': 'Generic',
            'model': 'Test Device',
            'slug': 'generic-test-device'
        },
        device_role={
            'name': 'Server',
            'slug': 'server'
        },
        site={
            'name': 'Main Site',
            'slug': 'main-site'
        },
        status='active'
    )


class TestNetBoxClient:
    """Test NetBox client functionality"""
    
    def test_client_initialization(self, mock_api):
        """Test client initialization"""
        client = NetBoxClient(
            url="http://test.netbox.com/",  # Test URL normalization
            token="test-token",
            verify_ssl=True
        )
        
        assert client.url == "http://test.netbox.com"
        assert client.token == "test-token"
        assert client.verify_ssl is True
        assert client.api is not None
    
    def test_ssl_verification_disabled(self, mock_api):
        """Test SSL verification can be disabled"""
        with patch('urllib3.disable_warnings') as mock_disable_warnings:
            client = NetBoxClient(
                url="http://test.netbox.com",
                token="test-token",
                verify_ssl=False
            )
            
            mock_disable_warnings.assert_called_once()
            assert client.api.http_session.verify is False
    
    def test_connection_success(self, netbox_client, mock_api):
        """Test successful connection to NetBox"""
        mock_api.status.return_value = {'netbox-version': '3.6.0'}
        
        result = netbox_client.test_connection()
        
        assert result is True
        mock_api.status.assert_called_once()
    
    def test_connection_failure(self, netbox_client, mock_api):
        """Test connection failure handling"""
        mock_api.status.side_effect = ConnectionError("Connection failed")
        
        result = netbox_client.test_connection()
        
        assert result is False
    
    def test_connection_retry_logic(self, netbox_client, mock_api):
        """Test connection retry logic with backoff"""
        # First two calls fail, third succeeds
        mock_api.status.side_effect = [
            ConnectionError("Failed"),
            ConnectionError("Failed"),
            {'netbox-version': '3.6.0'}
        ]
        
        result = netbox_client.test_connection()
        
        assert result is True
        assert mock_api.status.call_count == 3
    
    def test_create_device_success(self, netbox_client, mock_api, sample_device_data):
        """Test successful device creation"""
        mock_device = Mock()
        mock_device.id = 123
        mock_device.name = "test-device-01"
        mock_api.dcim.devices.create.return_value = mock_device
        
        result = netbox_client.create_device(sample_device_data)
        
        assert result is not None
        assert result.id == 123
        mock_api.dcim.devices.create.assert_called_once()
    
    def test_create_device_failure(self, netbox_client, mock_api, sample_device_data):
        """Test device creation failure"""
        mock_api.dcim.devices.create.side_effect = HTTPError("400 Bad Request")
        
        result = netbox_client.create_device(sample_device_data)
        
        assert result is None
    
    def test_get_device_by_name_found(self, netbox_client, mock_api):
        """Test getting device by name when it exists"""
        mock_device = Mock()
        mock_device.id = 123
        mock_device.name = "test-device"
        mock_api.dcim.devices.get.return_value = mock_device
        
        result = netbox_client.get_device_by_name("test-device")
        
        assert result is not None
        assert result.id == 123
        mock_api.dcim.devices.get.assert_called_once_with(name="test-device")
    
    def test_get_device_by_name_not_found(self, netbox_client, mock_api):
        """Test getting device by name when it doesn't exist"""
        mock_api.dcim.devices.get.return_value = None
        
        result = netbox_client.get_device_by_name("nonexistent-device")
        
        assert result is None
    
    def test_update_device_success(self, netbox_client, mock_api):
        """Test successful device update"""
        mock_device = Mock()
        mock_device.save.return_value = True
        mock_api.dcim.devices.get.return_value = mock_device
        
        update_data = {"description": "Updated description"}
        result = netbox_client.update_device(123, update_data)
        
        assert result is not None
        assert mock_device.description == "Updated description"
        mock_device.save.assert_called_once()
    
    def test_update_device_not_found(self, netbox_client, mock_api):
        """Test updating non-existent device"""
        mock_api.dcim.devices.get.return_value = None
        
        result = netbox_client.update_device(999, {"description": "test"})
        
        assert result is None
    
    def test_delete_device_success(self, netbox_client, mock_api):
        """Test successful device deletion"""
        mock_device = Mock()
        mock_device.delete.return_value = True
        mock_api.dcim.devices.get.return_value = mock_device
        
        result = netbox_client.delete_device(123)
        
        assert result is True
        mock_device.delete.assert_called_once()
    
    def test_delete_device_not_found(self, netbox_client, mock_api):
        """Test deleting non-existent device"""
        mock_api.dcim.devices.get.return_value = None
        
        result = netbox_client.delete_device(999)
        
        assert result is False
    
    def test_get_all_devices(self, netbox_client, mock_api):
        """Test getting all devices"""
        mock_devices = [Mock(id=1), Mock(id=2), Mock(id=3)]
        mock_api.dcim.devices.all.return_value = mock_devices
        
        result = netbox_client.get_all_devices()
        
        assert len(result) == 3
        assert all(hasattr(device, 'id') for device in result)
    
    def test_create_ip_address_success(self, netbox_client, mock_api):
        """Test successful IP address creation"""
        mock_ip = Mock()
        mock_ip.id = 456
        mock_ip.address = "192.168.1.100/24"
        mock_api.ipam.ip_addresses.create.return_value = mock_ip
        
        ip_data = {
            'address': '192.168.1.100/24',
            'status': 'active'
        }
        result = netbox_client.create_ip_address(ip_data)
        
        assert result is not None
        assert result.id == 456
    
    def test_get_ip_address_found(self, netbox_client, mock_api):
        """Test getting IP address when it exists"""
        mock_ip = Mock()
        mock_ip.id = 456
        mock_ip.address = "192.168.1.100/24"
        mock_api.ipam.ip_addresses.get.return_value = mock_ip
        
        result = netbox_client.get_ip_address("192.168.1.100/24")
        
        assert result is not None
        assert result.address == "192.168.1.100/24"
    
    def test_get_ip_address_not_found(self, netbox_client, mock_api):
        """Test getting IP address when it doesn't exist"""
        mock_api.ipam.ip_addresses.get.return_value = None
        
        result = netbox_client.get_ip_address("192.168.1.200/24")
        
        assert result is None
    
    def test_get_all_ip_addresses(self, netbox_client, mock_api):
        """Test getting all IP addresses"""
        mock_ips = [Mock(id=1), Mock(id=2)]
        mock_api.ipam.ip_addresses.all.return_value = mock_ips
        
        result = netbox_client.get_all_ip_addresses()
        
        assert len(result) == 2
    
    def test_get_or_create_device_type_existing(self, netbox_client, mock_api):
        """Test getting existing device type"""
        mock_device_type = Mock()
        mock_device_type.id = 789
        mock_api.dcim.device_types.get.return_value = mock_device_type
        
        result = netbox_client.get_or_create_device_type("Generic", "Test Device")
        
        assert result is not None
        assert result.id == 789
        mock_api.dcim.device_types.get.assert_called_once()
        mock_api.dcim.device_types.create.assert_not_called()
    
    def test_get_or_create_device_type_new(self, netbox_client, mock_api):
        """Test creating new device type"""
        mock_api.dcim.device_types.get.return_value = None
        
        mock_manufacturer = Mock()
        mock_manufacturer.id = 1
        mock_api.dcim.manufacturers.get.return_value = mock_manufacturer
        
        mock_new_device_type = Mock()
        mock_new_device_type.id = 790
        mock_api.dcim.device_types.create.return_value = mock_new_device_type
        
        result = netbox_client.get_or_create_device_type("Generic", "New Device")
        
        assert result is not None
        assert result.id == 790
        mock_api.dcim.device_types.create.assert_called_once()
    
    def test_bulk_create_devices(self, netbox_client, mock_api):
        """Test bulk device creation"""
        devices_data = [
            {"name": "device1", "device_type": 1},
            {"name": "device2", "device_type": 1}
        ]
        
        mock_created = [Mock(id=1), Mock(id=2)]
        mock_api.dcim.devices.create.return_value = mock_created
        
        result = netbox_client.bulk_create_devices(devices_data)
        
        assert len(result) == 2
        mock_api.dcim.devices.create.assert_called_once_with(devices_data)


class TestNetBoxClientIntegration:
    """Integration-style tests for NetBox client"""
    
    @pytest.mark.skipif(True, reason="Requires actual NetBox instance")
    def test_real_connection(self):
        """Test connection to real NetBox instance"""
        # This would require environment variables for real testing
        pass
    
    def test_error_handling_chain(self, netbox_client, mock_api):
        """Test error handling through the entire chain"""
        # Simulate various error conditions
        mock_api.dcim.devices.create.side_effect = [
            ConnectionError("Network error"),
            HTTPError("HTTP 500"),
            Exception("Unknown error")
        ]
        
        device_data = DeviceCreateRequest(
            name="test-device",
            device_type={'manufacturer': 'Test', 'model': 'Test'},
            device_role={'name': 'Test', 'slug': 'test'},
            site={'name': 'Test', 'slug': 'test'}
        )
        
        # All three attempts should fail gracefully
        for _ in range(3):
            result = netbox_client.create_device(device_data)
            assert result is None
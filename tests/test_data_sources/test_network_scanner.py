import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.data_sources.network_scanner import NetworkScannerDataSource
from src.netbox.models import Device

class TestNetworkScannerDataSource:
    """Test Network Scanner data source"""
    
    @pytest.fixture
    def scanner_source(self, test_config):
        """Create Network Scanner data source"""
        return NetworkScannerDataSource(test_config["sources"]["network_scan"])
    
    @pytest.mark.asyncio
    async def test_discover_devices(self, scanner_source, mock_network_scan_data):
        """Test device discovery from network scanning"""
        
        with patch('src.data_sources.network_scanner.nmap.PortScanner') as mock_scanner:
            # Mock nmap scanner
            mock_nm = Mock()
            mock_nm.scan.return_value = None
            mock_nm.all_hosts.return_value = ["192.168.1.1", "192.168.1.10"]
            
            # Mock host data
            mock_nm.__getitem__.side_effect = lambda host: {
                "hostnames": [{"name": f"{host.split('.')[-1]}.local"}],
                "status": {"state": "up"},
                "tcp": {22: {"state": "open"}, 80: {"state": "open"}},
                "addresses": {"mac": "AA:BB:CC:DD:EE:FF"}
            }
            
            mock_scanner.return_value = mock_nm
            
            devices = await scanner_source.discover()
            
            assert len(devices) >= 1
            assert all(isinstance(d, Device) for d in devices)
    
    @pytest.mark.asyncio
    async def test_scan_single_network(self, scanner_source):
        """Test scanning a single network"""
        
        with patch('src.data_sources.network_scanner.nmap.PortScanner') as mock_scanner:
            mock_nm = Mock()
            mock_nm.scan.return_value = None
            mock_nm.all_hosts.return_value = ["192.168.1.1"]
            mock_nm.__getitem__.return_value = {
                "hostnames": [{"name": "router.local"}],
                "status": {"state": "up"},
                "tcp": {22: {"state": "open"}},
                "addresses": {"mac": "AA:BB:CC:DD:EE:FF"}
            }
            mock_scanner.return_value = mock_nm
            
            devices = await scanner_source.scan_network("192.168.1.0/24")
            
            assert len(devices) == 1
            assert devices[0].name == "router-local"
    
    def test_determine_device_type_from_ports(self, scanner_source):
        """Test device type determination from open ports"""
        
        # Router-like device
        host_info = {
            "tcp": {22: {"state": "open"}, 80: {"state": "open"}, 443: {"state": "open"}},
            "hostnames": [{"name": "router.local"}]
        }
        
        device_type = scanner_source.determine_device_type_from_ports(host_info)
        
        assert "router" in device_type.model.lower()
    
    def test_determine_device_type_from_snmp(self, scanner_source):
        """Test device type determination from SNMP"""
        
        # Switch-like device
        host_info = {
            "tcp": {161: {"state": "open"}},
            "hostnames": [{"name": "switch.local"}]
        }
        
        device_type = scanner_source.determine_device_type_from_ports(host_info)
        
        assert "switch" in device_type.model.lower() or "network" in device_type.model.lower()
    
    def test_sanitize_hostname(self, scanner_source):
        """Test hostname sanitization"""
        hostnames = [
            "router.local",
            "switch-01.domain.com",
            "device_with_underscores",
            "UPPERCASE-DEVICE"
        ]
        
        expected = [
            "router-local",
            "switch-01-domain-com", 
            "device-with-underscores",
            "uppercase-device"
        ]
        
        for hostname, expected_result in zip(hostnames, expected):
            result = scanner_source.sanitize_hostname(hostname)
            assert result == expected_result
    
    def test_is_network_device(self, scanner_source):
        """Test network device detection"""
        
        # Network device with management ports
        network_host = {
            "tcp": {22: {"state": "open"}, 80: {"state": "open"}, 161: {"state": "open"}},
            "hostnames": [{"name": "switch.local"}]
        }
        
        assert scanner_source.is_network_device(network_host) == True
        
        # Regular server
        server_host = {
            "tcp": {22: {"state": "open"}, 3306: {"state": "open"}},
            "hostnames": [{"name": "database.local"}]
        }
        
        assert scanner_source.is_network_device(server_host) == False
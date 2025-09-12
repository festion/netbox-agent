import asyncio
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
import json
import configparser
from src.data_sources.base import FileBasedDataSource, DataSourceType, DiscoveryResult, DataSourceConfig
from src.netbox.models import Device, DeviceType, DeviceRole, Site
from src.mcp.filesystem import FilesystemMCPClient

class FilesystemDataSourceConfig(DataSourceConfig):
    """Configuration for Filesystem data source"""
    config_paths: List[str]
    watch_interval: int = 300  # 5 minutes
    supported_formats: List[str] = ['.yaml', '.yml', '.json', '.conf', '.cfg', '.ini']
    file_type_mappings: Dict[str, str] = {
        'dhcp': 'dhcp_config',
        'ansible': 'ansible_inventory',
        'hosts': 'hosts_file',
        'network': 'network_config'
    }

class FilesystemDataSource(FileBasedDataSource):
    """Data source for filesystem-based configuration files"""
    
    def __init__(self, config: FilesystemDataSourceConfig):
        super().__init__(config, DataSourceType.FILESYSTEM)
        self.fs_config = config
        self.mcp_client = FilesystemMCPClient(config.dict())
        
    async def discover(self) -> DiscoveryResult:
        """Discover devices from configuration files"""
        result = DiscoveryResult(
            source_type=self.source_type,
            source_id=self.source_id
        )
        
        total_files_processed = 0
        
        try:
            # Connect to filesystem MCP server
            if not await self.mcp_client.connect():
                result.add_error("Failed to connect to Filesystem MCP")
                return result
            
            # Process each configured path
            for config_path in self.fs_config.config_paths:
                try:
                    path_devices, files_processed = await self._process_config_path(config_path)
                    result.devices.extend(path_devices)
                    total_files_processed += files_processed
                    self.logger.info("Processed config path", 
                                   path=config_path, 
                                   devices_found=len(path_devices),
                                   files_processed=files_processed)
                except Exception as e:
                    result.add_error(f"Failed to process {config_path}: {str(e)}")
                    
        except Exception as e:
            result.add_error(f"Discovery failed: {str(e)}")
        finally:
            await self.mcp_client.disconnect()
        
        result.metadata = {
            "config_paths_processed": len(self.fs_config.config_paths),
            "total_files_processed": total_files_processed,
            "devices_discovered": len(result.devices)
        }
        
        return result
    
    async def _process_config_path(self, config_path: str) -> tuple[List[Device], int]:
        """Process a configuration path (file or directory)"""
        devices = []
        files_processed = 0
        
        try:
            # Check if path is file or directory
            path_info = await self.mcp_client.call_tool("get_file_info", {"path": config_path})
            
            if path_info.get("type") == "file":
                # Single file
                if self._is_supported_format(config_path):
                    file_devices = await self._parse_config_file(config_path)
                    devices.extend(file_devices)
                    files_processed = 1
            elif path_info.get("type") == "directory":
                # Directory - find all supported files
                files = await self.mcp_client.list_directory(config_path)
                for file_name in files:
                    if self._is_supported_format(file_name):
                        file_path = os.path.join(config_path, file_name)
                        file_devices = await self._parse_config_file(file_path)
                        devices.extend(file_devices)
                        files_processed += 1
                        
        except Exception as e:
            self.logger.error("Error processing path", path=config_path, error=str(e))
            raise
        
        return devices, files_processed
    
    def _is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported"""
        return any(file_path.lower().endswith(ext) for ext in self.fs_config.supported_formats)
    
    async def _parse_config_file(self, file_path: str) -> List[Device]:
        """Parse a configuration file and extract device information"""
        devices = []
        
        try:
            self.logger.info("Parsing config file", file_path=file_path)
            
            # Read file content
            content = await self.mcp_client.read_file(file_path)
            
            # Parse based on file type
            if file_path.endswith(('.yaml', '.yml')):
                parsed_data = await self._parse_yaml_file(content, file_path)
            elif file_path.endswith('.json'):
                parsed_data = await self._parse_json_file(content, file_path)
            elif file_path.endswith(('.conf', '.cfg')):
                parsed_data = await self._parse_conf_file(content, file_path)
            elif file_path.endswith('.ini'):
                parsed_data = await self._parse_ini_file(content, file_path)
            else:
                parsed_data = await self._parse_generic_file(content, file_path)
            
            # Convert parsed data to NetBox devices
            for device_data in parsed_data:
                device = await self._create_device_from_config(device_data, file_path)
                if device:
                    devices.append(device)
                    
        except Exception as e:
            self.logger.error("Failed to parse config file", file_path=file_path, error=str(e))
            raise
        
        return devices
    
    async def _parse_yaml_file(self, content: str, file_path: str) -> List[Dict]:
        """Parse YAML configuration file"""
        try:
            data = yaml.safe_load(content)
            
            # Handle different YAML structures
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Common YAML structures
                if 'inventory' in data:
                    return self._extract_ansible_inventory(data)
                elif 'hosts' in data:
                    return data['hosts']
                elif 'devices' in data:
                    return data['devices']
                elif 'networks' in data:
                    return self._extract_network_config(data)
                else:
                    # Try to find device-like objects
                    return self._extract_devices_from_dict(data)
            
            return []
            
        except yaml.YAMLError as e:
            self.logger.error("YAML parsing error", file_path=file_path, error=str(e))
            return []
    
    def _extract_ansible_inventory(self, data: Dict) -> List[Dict]:
        """Extract devices from Ansible inventory YAML"""
        devices = []
        
        inventory = data.get('inventory', {})
        
        # Process groups
        for group_name, group_data in inventory.items():
            if group_name == '_meta':
                continue
            
            hosts = group_data.get('hosts', {})
            for hostname, host_vars in hosts.items():
                device = {
                    'name': hostname,
                    'group': group_name,
                    'source_file': 'ansible_inventory'
                }
                
                # Add host variables
                if isinstance(host_vars, dict):
                    device.update(host_vars)
                    
                    # Map common Ansible variables
                    if 'ansible_host' in host_vars:
                        device['ip_address'] = host_vars['ansible_host']
                    if 'ansible_user' in host_vars:
                        device['username'] = host_vars['ansible_user']
                    if 'ansible_port' in host_vars:
                        device['ssh_port'] = host_vars['ansible_port']
                
                devices.append(device)
        
        return devices
    
    def _extract_network_config(self, data: Dict) -> List[Dict]:
        """Extract devices from network configuration"""
        devices = []
        
        networks = data.get('networks', {})
        for network_name, network_config in networks.items():
            # Extract devices from network configuration
            if 'devices' in network_config:
                for device in network_config['devices']:
                    device['network'] = network_name
                    devices.append(device)
            
            # Extract DHCP reservations
            if 'dhcp' in network_config and 'reservations' in network_config['dhcp']:
                for reservation in network_config['dhcp']['reservations']:
                    devices.append({
                        'name': reservation.get('name', 'unknown'),
                        'ip_address': reservation.get('ip'),
                        'mac_address': reservation.get('mac'),
                        'network': network_name,
                        'type': 'dhcp_reservation'
                    })
        
        return devices
    
    def _extract_devices_from_dict(self, data: Dict) -> List[Dict]:
        """Extract device-like objects from arbitrary dictionary"""
        devices = []
        
        # Look for common device indicators
        for key, value in data.items():
            if isinstance(value, dict):
                # Check if this looks like a device
                if any(field in value for field in ['ip', 'ip_address', 'hostname', 'host']):
                    device = value.copy()
                    if 'name' not in device:
                        device['name'] = key
                    devices.append(device)
                elif isinstance(value, dict):
                    # Recursive search
                    nested_devices = self._extract_devices_from_dict(value)
                    devices.extend(nested_devices)
        
        return devices
    
    async def _parse_json_file(self, content: str, file_path: str) -> List[Dict]:
        """Parse JSON configuration file"""
        try:
            data = json.loads(content)
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Similar logic to YAML
                if 'hosts' in data:
                    return data['hosts']
                elif 'devices' in data:
                    return data['devices']
                elif 'inventory' in data:
                    return data['inventory']
                else:
                    return self._extract_devices_from_dict(data)
            
            return []
            
        except json.JSONDecodeError as e:
            self.logger.error("JSON parsing error", file_path=file_path, error=str(e))
            return []
    
    async def _parse_conf_file(self, content: str, file_path: str) -> List[Dict]:
        """Parse .conf configuration files (like dhcpd.conf)"""
        devices = []
        
        # Different parsing strategies based on filename
        if 'dhcp' in file_path.lower():
            devices = self._parse_dhcp_conf(content)
        elif 'host' in file_path.lower():
            devices = self._parse_hosts_file(content)
        else:
            devices = self._parse_generic_conf(content)
        
        return devices
    
    def _parse_dhcp_conf(self, content: str) -> List[Dict]:
        """Parse DHCP configuration file"""
        devices = []
        lines = content.split('\n')
        
        current_host = None
        brace_count = 0
        
        for line in lines:
            line = line.strip()
            
            if not line or line.startswith('#'):
                continue
            
            # Host declaration
            if line.startswith('host ') and '{' in line:
                if current_host:
                    devices.append(current_host)
                
                host_name = line.split('host ')[1].split(' ')[0].strip()
                current_host = {
                    'name': host_name,
                    'type': 'dhcp_host'
                }
                brace_count = line.count('{') - line.count('}')
                
            elif current_host:
                brace_count += line.count('{') - line.count('}')
                
                # Extract host parameters
                if 'hardware ethernet' in line:
                    mac = line.split('hardware ethernet')[1].strip(';').strip()
                    current_host['mac_address'] = mac
                elif 'fixed-address' in line:
                    ip = line.split('fixed-address')[1].strip(';').strip()
                    current_host['ip_address'] = ip
                elif 'option host-name' in line:
                    hostname = line.split('option host-name')[1].strip('";').strip()
                    current_host['hostname'] = hostname
                
                # End of host block
                if brace_count == 0:
                    devices.append(current_host)
                    current_host = None
        
        # Add last host if exists
        if current_host:
            devices.append(current_host)
        
        return devices
    
    def _parse_hosts_file(self, content: str) -> List[Dict]:
        """Parse /etc/hosts style files"""
        devices = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if len(parts) >= 2:
                ip_address = parts[0]
                hostnames = parts[1:]
                
                for hostname in hostnames:
                    devices.append({
                        'name': hostname,
                        'ip_address': ip_address,
                        'type': 'hosts_file'
                    })
        
        return devices
    
    def _parse_generic_conf(self, content: str) -> List[Dict]:
        """Parse generic configuration file"""
        devices = []
        
        # Look for IP addresses and associated information
        import re
        
        # Pattern for IP address with optional hostname
        ip_pattern = r'(\d+\.\d+\.\d+\.\d+)\s+([a-zA-Z0-9.-]+)'
        matches = re.findall(ip_pattern, content)
        
        for ip, hostname in matches:
            devices.append({
                'name': hostname,
                'ip_address': ip,
                'type': 'config_file'
            })
        
        return devices
    
    async def _parse_ini_file(self, content: str, file_path: str) -> List[Dict]:
        """Parse INI configuration files"""
        devices = []
        
        config = configparser.ConfigParser()
        
        try:
            config.read_string(content)
            
            for section_name in config.sections():
                section = config[section_name]
                
                # Check if section looks like a device
                if any(key in section for key in ['ip', 'host', 'address']):
                    device = {'name': section_name}
                    
                    for key, value in section.items():
                        if key in ['ip', 'host', 'address']:
                            device['ip_address'] = value
                        elif key == 'mac':
                            device['mac_address'] = value
                        else:
                            device[key] = value
                    
                    devices.append(device)
                    
        except configparser.Error as e:
            self.logger.error("INI parsing error", file_path=file_path, error=str(e))
        
        return devices
    
    async def _parse_generic_file(self, content: str, file_path: str) -> List[Dict]:
        """Parse generic text files looking for device information"""
        devices = []
        
        # Use regex to find IP addresses and hostnames
        import re
        
        # Various patterns for device information
        patterns = [
            r'(\w+)\s+(\d+\.\d+\.\d+\.\d+)',  # hostname ip
            r'(\d+\.\d+\.\d+\.\d+)\s+(\w+)',  # ip hostname
            r'([a-f0-9:]{17})\s+(\d+\.\d+\.\d+\.\d+)\s+(\w+)',  # mac ip hostname
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                device = {'type': 'text_file'}
                
                if len(match) == 2:
                    if re.match(r'\d+\.\d+\.\d+\.\d+', match[0]):
                        device['ip_address'] = match[0]
                        device['name'] = match[1]
                    else:
                        device['name'] = match[0]
                        device['ip_address'] = match[1]
                elif len(match) == 3:
                    device['mac_address'] = match[0]
                    device['ip_address'] = match[1]
                    device['name'] = match[2]
                
                if device.get('name'):
                    devices.append(device)
        
        return devices
    
    async def _create_device_from_config(self, device_data: Dict, source_file: str) -> Optional[Device]:
        """Create NetBox device from configuration data"""
        
        # Extract basic information
        name = device_data.get('name')
        if not name:
            return None
        
        ip_address = device_data.get('ip_address') or device_data.get('ip') or device_data.get('host')
        mac_address = device_data.get('mac_address') or device_data.get('mac')
        
        # Determine device type and role
        device_type = self._determine_device_type_from_config(device_data, source_file)
        device_role = self._determine_device_role_from_config(device_data, source_file)
        site = self._determine_site_from_config(device_data, source_file)
        
        # Create device
        device = Device(
            name=self._sanitize_device_name(name),
            device_type=device_type,
            device_role=device_role,
            site=site,
            primary_ip4=ip_address,
            status="active",
            custom_fields={
                "config_source_file": source_file,
                "config_type": device_data.get('type', 'config_file'),
                "config_group": device_data.get('group'),
                "mac_address": mac_address,
                "username": device_data.get('username'),
                "ssh_port": device_data.get('ssh_port', device_data.get('port')),
                "network": device_data.get('network'),
                "discovery_source": "filesystem",
                "last_discovered": self.last_incremental_sync.isoformat() if self.last_incremental_sync else None
            }
        )
        
        return device
    
    def _determine_device_type_from_config(self, device_data: Dict, source_file: str) -> DeviceType:
        """Determine device type from configuration data"""
        
        # Default values
        manufacturer = "Generic"
        model = "Config Device"
        
        # Infer from various sources
        device_type = device_data.get('type', '').lower()
        name = device_data.get('name', '').lower()
        group = device_data.get('group', '').lower()
        
        # Type-based inference
        if 'router' in device_type or 'router' in name or 'gw' in name:
            manufacturer = "Generic"
            model = "Router"
        elif 'switch' in device_type or 'switch' in name or 'sw' in name:
            manufacturer = "Generic"
            model = "Switch"
        elif 'ap' in device_type or 'access' in device_type or 'ap' in name:
            manufacturer = "Generic"
            model = "Access Point"
        elif 'server' in device_type or 'server' in name or 'srv' in name:
            manufacturer = "Generic"
            model = "Server"
        elif 'camera' in device_type or 'camera' in name or 'cam' in name:
            manufacturer = "Generic"
            model = "IP Camera"
        elif 'dhcp' in device_type:
            manufacturer = "Generic"
            model = "DHCP Client"
        
        # Group-based inference
        elif group:
            if 'router' in group:
                model = "Router"
            elif 'switch' in group:
                model = "Switch"
            elif 'server' in group:
                model = "Server"
            elif 'network' in group:
                model = "Network Device"
        
        # Source file-based inference
        filename = os.path.basename(source_file).lower()
        if 'dhcp' in filename:
            model = "DHCP Client"
        elif 'ansible' in filename or 'inventory' in filename:
            model = "Managed Host"
        elif 'network' in filename:
            model = "Network Device"
        
        return DeviceType(
            manufacturer=manufacturer,
            model=model,
            slug=f"{manufacturer.lower()}-{model.lower()}".replace(" ", "-"),
            u_height=1.0 if model in ["Router", "Switch", "Server"] else 0.0
        )
    
    def _determine_device_role_from_config(self, device_data: Dict, source_file: str) -> DeviceRole:
        """Determine device role from configuration data"""
        
        device_type = device_data.get('type', '').lower()
        name = device_data.get('name', '').lower()
        group = device_data.get('group', '').lower()
        
        # Role mapping
        if 'router' in device_type or 'router' in name or 'gw' in name:
            return DeviceRole(name="Router", slug="router", color="ff5722")
        elif 'switch' in device_type or 'switch' in name:
            return DeviceRole(name="Switch", slug="switch", color="2196f3")
        elif 'server' in device_type or 'server' in name or group == 'servers':
            return DeviceRole(name="Server", slug="server", color="795548")
        elif 'access' in device_type or 'ap' in name:
            return DeviceRole(name="Access Point", slug="access-point", color="4caf50")
        elif 'camera' in device_type or 'camera' in name:
            return DeviceRole(name="Security Camera", slug="security-camera", color="9c27b0")
        elif device_type == 'dhcp_host' or device_type == 'dhcp_reservation':
            return DeviceRole(name="DHCP Client", slug="dhcp-client", color="ff9800")
        else:
            return DeviceRole(name="Configured Device", slug="configured-device", color="607d8b")
    
    def _determine_site_from_config(self, device_data: Dict, source_file: str) -> Site:
        """Determine site from configuration data"""
        
        # Check for explicit site information
        site_name = device_data.get('site') or device_data.get('location')
        if site_name:
            return Site(
                name=site_name.title(),
                slug=site_name.lower().replace(" ", "-")
            )
        
        # Infer from group or network
        group = device_data.get('group', '').lower()
        network = device_data.get('network', '').lower()
        
        site_mappings = {
            'dmz': {"name": "DMZ", "slug": "dmz"},
            'internal': {"name": "Internal Network", "slug": "internal"},
            'guest': {"name": "Guest Network", "slug": "guest"},
            'iot': {"name": "IoT Network", "slug": "iot"},
            'management': {"name": "Management Network", "slug": "management"},
            'servers': {"name": "Server Room", "slug": "server-room"},
            'network': {"name": "Network Infrastructure", "slug": "network"}
        }
        
        for key, site_info in site_mappings.items():
            if key in group or key in network:
                return Site(name=site_info["name"], slug=site_info["slug"])
        
        # Default based on source file
        filename = os.path.basename(source_file).lower()
        if 'prod' in filename or 'production' in filename:
            return Site(name="Production", slug="production")
        elif 'test' in filename or 'staging' in filename:
            return Site(name="Test Environment", slug="test")
        elif 'home' in filename:
            return Site(name="Home", slug="home")
        
        return Site(name="Configuration", slug="configuration")
    
    def _sanitize_device_name(self, name: str) -> str:
        """Sanitize device name for NetBox"""
        import re
        # Remove special characters except hyphens and underscores
        name = re.sub(r'[^\w\s-]', '', name)
        # Replace spaces and multiple hyphens/underscores with single hyphen
        name = re.sub(r'[-\s_]+', '-', name)
        # Remove leading/trailing hyphens
        return name.lower().strip('-')
    
    async def monitor_file_changes(self) -> Dict[str, Any]:
        """Monitor configuration files for changes"""
        changes = {}
        
        try:
            if not await self.mcp_client.connect():
                return changes
            
            for config_path in self.fs_config.config_paths:
                try:
                    path_changes = await self.mcp_client.monitor_config_changes([config_path])
                    changes.update(path_changes)
                except Exception as e:
                    self.logger.error("Failed to monitor config path", path=config_path, error=str(e))
            
        finally:
            await self.mcp_client.disconnect()
        
        return changes
    
    async def connect(self) -> bool:
        """Connect to filesystem data source"""
        try:
            result = await self.mcp_client.connect()
            return result
        except Exception as e:
            self.logger.error("Connection failed", error=str(e))
            return False
    
    async def test_connection(self) -> bool:
        """Test filesystem access"""
        try:
            result = await self.mcp_client.connect()
            await self.mcp_client.disconnect()
            return result
        except Exception as e:
            self.logger.error("Connection test failed", error=str(e))
            return False
    
    def get_required_config_fields(self) -> List[str]:
        """Return required configuration fields"""
        return ["config_paths", "enabled"]
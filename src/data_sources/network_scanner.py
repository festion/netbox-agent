import asyncio
import socket
from typing import List, Dict, Any, Optional
import ipaddress
import subprocess
from concurrent.futures import ThreadPoolExecutor
from src.data_sources.base import NetworkDataSource, DataSourceType, DiscoveryResult, DataSourceConfig
from src.netbox.models import Device, IPAddress, DeviceType, DeviceRole, Site

class NetworkScannerConfig(DataSourceConfig):
    """Configuration for Network Scanner data source"""
    networks: List[str]
    scan_ports: List[int] = [22, 23, 53, 80, 161, 443, 8080, 8443]
    timeout: int = 5
    max_workers: int = 50
    ping_timeout: int = 3
    use_nmap: bool = False
    nmap_options: str = "-sS -O"
    skip_ping_test: bool = False
    subnet_site_mapping: Dict[str, str] = {}

class NetworkScannerDataSource(NetworkDataSource):
    """Data source for network scanning and device discovery"""
    
    def __init__(self, config: NetworkScannerConfig):
        super().__init__(config, DataSourceType.NETWORK_SCAN)
        self.scan_config = config
        
    async def discover(self) -> DiscoveryResult:
        """Discover devices through network scanning"""
        result = DiscoveryResult(
            source_type=self.source_type,
            source_id=self.source_id
        )
        
        total_hosts_scanned = 0
        
        for network in self.scan_config.networks:
            try:
                self.logger.info("Starting network scan", network=network)
                network_devices, hosts_scanned = await self._scan_network(network)
                result.devices.extend(network_devices)
                total_hosts_scanned += hosts_scanned
                
                # Extract IP addresses
                for device in network_devices:
                    if device.primary_ip4:
                        ip_addr = IPAddress(
                            address=device.primary_ip4,
                            status="active",
                            dns_name=device.custom_fields.get("hostname"),
                            description=f"Discovered by network scan"
                        )
                        result.ip_addresses.append(ip_addr)
                
                self.logger.info("Network scan completed", 
                               network=network, 
                               devices_found=len(network_devices),
                               hosts_scanned=hosts_scanned)
                               
            except Exception as e:
                result.add_error(f"Failed to scan network {network}: {str(e)}")
        
        result.metadata = {
            "networks_scanned": len(self.scan_config.networks),
            "total_hosts_scanned": total_hosts_scanned,
            "devices_discovered": len(result.devices),
            "discovery_rate": f"{len(result.devices) / max(1, total_hosts_scanned) * 100:.1f}%"
        }
        
        return result
    
    async def _scan_network(self, network: str) -> tuple[List[Device], int]:
        """Scan a specific network for devices"""
        devices = []
        
        try:
            # Parse network
            net = ipaddress.ip_network(network, strict=False)
            total_hosts = net.num_addresses
            
            # For large networks, sample every 10th IP to avoid overwhelming
            if total_hosts > 1000:
                host_ips = [str(ip) for ip in net.hosts() if int(str(ip).split('.')[-1]) % 10 == 0]
                self.logger.info("Large network detected, sampling every 10th IP", 
                               network=network, 
                               total_hosts=total_hosts,
                               sampled_hosts=len(host_ips))
            else:
                host_ips = [str(ip) for ip in net.hosts()]
            
            # Create tasks for parallel scanning
            with ThreadPoolExecutor(max_workers=self.scan_config.max_workers) as executor:
                loop = asyncio.get_event_loop()
                
                # Scan all hosts in network
                tasks = [
                    loop.run_in_executor(executor, self._scan_host, ip)
                    for ip in host_ips
                ]
                
                # Wait for all scans to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in results:
                    if isinstance(result, dict) and result.get("alive"):
                        device = await self._create_device_from_scan(result)
                        if device:
                            devices.append(device)
                    elif isinstance(result, Exception):
                        self.logger.debug("Scan task failed", error=str(result))
                            
        except Exception as e:
            self.logger.error("Network scan failed", network=network, error=str(e))
            raise
        
        return devices, len(host_ips)
    
    def _scan_host(self, ip: str) -> Dict[str, Any]:
        """Scan a single host for services and information"""
        result = {
            "ip": ip,
            "alive": False,
            "hostname": None,
            "mac_address": None,
            "open_ports": [],
            "services": {},
            "os_guess": None,
            "vendor": None,
            "response_time": None
        }
        
        try:
            # Skip ping test if configured
            if not self.scan_config.skip_ping_test:
                if not self._ping_host(ip):
                    return result
            
            result["alive"] = True
            
            # Get hostname
            try:
                hostname = socket.gethostbyaddr(ip)[0]
                result["hostname"] = hostname
            except (socket.herror, socket.gaierror):
                pass
            
            # Port scanning
            if self.scan_config.use_nmap and self._is_nmap_available():
                result.update(self._nmap_scan(ip))
            else:
                result["open_ports"] = self._scan_ports_tcp(ip)
            
            # Service detection
            for port in result["open_ports"]:
                service = self._detect_service(ip, port)
                if service:
                    result["services"][port] = service
            
            # OS fingerprinting (basic)
            result["os_guess"] = self._guess_os(result["open_ports"], result["services"])
            
            # Get MAC address (if on same subnet)
            result["mac_address"] = self._get_mac_address(ip)
            
            # Vendor lookup based on MAC
            if result["mac_address"]:
                result["vendor"] = self._lookup_vendor(result["mac_address"])
                
        except Exception as e:
            self.logger.debug("Error scanning host", ip=ip, error=str(e))
        
        return result
    
    def _ping_host(self, ip: str) -> bool:
        """Ping a host to check if it's alive"""
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", str(self.scan_config.ping_timeout), ip],
                capture_output=True,
                timeout=self.scan_config.ping_timeout + 1
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False
    
    def _is_nmap_available(self) -> bool:
        """Check if nmap is available on the system"""
        try:
            subprocess.run(["nmap", "--version"], 
                         capture_output=True, 
                         timeout=5)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _nmap_scan(self, ip: str) -> Dict[str, Any]:
        """Use nmap for more advanced scanning"""
        result = {"open_ports": [], "os_guess": None, "services": {}}
        
        try:
            # Basic nmap scan
            cmd = ["nmap"] + self.scan_config.nmap_options.split() + [ip]
            nmap_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if nmap_result.returncode == 0:
                output = nmap_result.stdout
                
                # Parse open ports
                for line in output.split('\n'):
                    if '/tcp' in line and 'open' in line:
                        port_str = line.split('/')[0].strip()
                        try:
                            port = int(port_str)
                            result["open_ports"].append(port)
                        except ValueError:
                            pass
                
                # Parse OS information
                if "OS details:" in output:
                    for line in output.split('\n'):
                        if "OS details:" in line:
                            result["os_guess"] = line.split("OS details:")[1].strip()
                            break
                        
        except subprocess.TimeoutExpired:
            self.logger.debug("Nmap scan timed out", ip=ip)
        except Exception as e:
            self.logger.debug("Nmap scan failed", ip=ip, error=str(e))
        
        return result
    
    def _scan_ports_tcp(self, ip: str) -> List[int]:
        """Scan TCP ports on a host"""
        open_ports = []
        
        for port in self.scan_config.scan_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.scan_config.timeout)
                result = sock.connect_ex((ip, port))
                sock.close()
                
                if result == 0:
                    open_ports.append(port)
                    
            except socket.error:
                pass
        
        return open_ports
    
    def _detect_service(self, ip: str, port: int) -> Optional[Dict]:
        """Detect service running on a port"""
        service_map = {
            22: {"name": "SSH", "protocol": "ssh"},
            23: {"name": "Telnet", "protocol": "telnet"},
            53: {"name": "DNS", "protocol": "dns"},
            80: {"name": "HTTP", "protocol": "http"},
            161: {"name": "SNMP", "protocol": "snmp"},
            443: {"name": "HTTPS", "protocol": "https"},
            8080: {"name": "HTTP Alt", "protocol": "http"},
            8443: {"name": "HTTPS Alt", "protocol": "https"},
            3389: {"name": "RDP", "protocol": "rdp"},
            21: {"name": "FTP", "protocol": "ftp"},
            25: {"name": "SMTP", "protocol": "smtp"},
            110: {"name": "POP3", "protocol": "pop3"},
            143: {"name": "IMAP", "protocol": "imap"},
            993: {"name": "IMAPS", "protocol": "imaps"},
            995: {"name": "POP3S", "protocol": "pop3s"}
        }
        
        base_service = service_map.get(port, {"name": f"Port {port}", "protocol": "unknown"})
        
        # Try to get more detailed information
        try:
            if port in [80, 8080]:
                return self._probe_http(ip, port, base_service)
            elif port in [443, 8443]:
                return self._probe_https(ip, port, base_service)
            elif port == 161:
                return self._probe_snmp(ip, port, base_service)
            else:
                return base_service
        except Exception:
            return base_service
    
    def _probe_http(self, ip: str, port: int, base_service: Dict) -> Dict:
        """Probe HTTP service for more details"""
        try:
            import requests
            response = requests.get(
                f"http://{ip}:{port}/",
                timeout=self.scan_config.timeout,
                verify=False
            )
            
            service = base_service.copy()
            service["headers"] = dict(response.headers)
            service["status_code"] = response.status_code
            
            # Try to identify device type from headers
            server_header = response.headers.get("Server", "").lower()
            if "nginx" in server_header:
                service["server"] = "nginx"
            elif "apache" in server_header:
                service["server"] = "apache"
            elif "ubiquiti" in server_header:
                service["device_type"] = "ubiquiti"
            elif "mikrotik" in server_header:
                service["device_type"] = "mikrotik"
            
            # Check for common device web interfaces
            if response.text:
                content_lower = response.text.lower()
                if "unifi" in content_lower:
                    service["device_type"] = "unifi"
                elif "dd-wrt" in content_lower:
                    service["device_type"] = "dd-wrt"
                elif "openwrt" in content_lower:
                    service["device_type"] = "openwrt"
            
            return service
            
        except Exception:
            return base_service
    
    def _probe_https(self, ip: str, port: int, base_service: Dict) -> Dict:
        """Probe HTTPS service for more details"""
        try:
            import ssl
            import requests
            
            response = requests.get(
                f"https://{ip}:{port}/",
                timeout=self.scan_config.timeout,
                verify=False
            )
            
            service = base_service.copy()
            service["headers"] = dict(response.headers)
            service["status_code"] = response.status_code
            
            # Get SSL certificate info
            try:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                
                with socket.create_connection((ip, port), timeout=self.scan_config.timeout) as sock:
                    with context.wrap_socket(sock, server_hostname=ip) as ssock:
                        cert = ssock.getpeercert()
                        if cert:
                            service["ssl_cert"] = {
                                "subject": dict(x[0] for x in cert.get("subject", [])),
                                "issuer": dict(x[0] for x in cert.get("issuer", [])),
                                "version": cert.get("version"),
                                "serial_number": cert.get("serialNumber")
                            }
            except Exception:
                pass
            
            return service
            
        except Exception:
            return base_service
    
    def _probe_snmp(self, ip: str, port: int, base_service: Dict) -> Dict:
        """Probe SNMP for device information"""
        service = base_service.copy()
        service["snmp_capable"] = True
        
        # TODO: Implement SNMP probing with pysnmp if available
        # This would allow getting system description, vendor info, etc.
        
        return service
    
    def _guess_os(self, open_ports: List[int], services: Dict) -> Optional[str]:
        """Make educated guess about OS based on ports and services"""
        
        # Windows-specific ports
        if 3389 in open_ports or 135 in open_ports or 445 in open_ports:
            return "Windows"
        
        # Unix/Linux patterns
        if 22 in open_ports:
            # Check for typical Linux/Unix services
            if any(port in open_ports for port in [80, 443, 53, 25]):
                return "Linux"
        
        # Network device patterns
        if 161 in open_ports:
            # SNMP usually indicates network equipment
            return "Network Device"
        
        # Check HTTP headers for clues
        for port, service in services.items():
            if isinstance(service, dict):
                headers = service.get("headers", {})
                server = headers.get("server", "").lower()
                device_type = service.get("device_type", "").lower()
                
                if device_type:
                    if device_type == "ubiquiti" or "unifi" in device_type:
                        return "UniFi OS"
                    elif device_type == "dd-wrt":
                        return "DD-WRT"
                    elif device_type == "openwrt":
                        return "OpenWrt"
                    elif device_type == "mikrotik":
                        return "RouterOS"
                
                if "ubiquiti" in server or "unifi" in server:
                    return "UniFi OS"
                elif "dd-wrt" in server:
                    return "DD-WRT"
                elif "openwrt" in server:
                    return "OpenWrt"
                elif "mikrotik" in server:
                    return "RouterOS"
        
        return None
    
    def _get_mac_address(self, ip: str) -> Optional[str]:
        """Get MAC address from ARP table"""
        try:
            # Try to get from system ARP table
            result = subprocess.run(
                ["arp", "-n", ip],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if ip in line:
                        parts = line.split()
                        for part in parts:
                            if ':' in part and len(part) == 17:  # MAC format
                                return part.upper()
                                
        except Exception:
            pass
        
        return None
    
    def _lookup_vendor(self, mac_address: str) -> Optional[str]:
        """Lookup vendor from MAC address OUI"""
        oui = mac_address[:8].upper()  # First 3 octets
        
        vendor_map = {
            "00:50:56": "VMware",
            "08:00:27": "VirtualBox",
            "00:15:5D": "Microsoft",
            "00:0C:29": "VMware",
            "24:5E:BE": "Ubiquiti",
            "04:18:D6": "Ubiquiti",
            "78:8A:20": "Ubiquiti",
            "DC:9F:DB": "Ubiquiti",
            "B4:FB:E4": "Ubiquiti",
            "68:D7:9A": "Ubiquiti",
            "04:DA:D2": "Ubiquiti",
            "E4:8D:8C": "Ubiquiti",
            "4C:5E:0C": "TP-Link",
            "14:CC:20": "TP-Link",
            "00:1B:21": "Intel",
            "00:1F:3C": "Belkin",
            "00:21:29": "Dell",
            "00:23:EB": "Cisco"
        }
        
        return vendor_map.get(oui)
    
    async def _create_device_from_scan(self, scan_result: Dict) -> Optional[Device]:
        """Create NetBox device from scan results"""
        
        ip = scan_result["ip"]
        hostname = scan_result.get("hostname")
        vendor = scan_result.get("vendor")
        os_guess = scan_result.get("os_guess")
        open_ports = scan_result.get("open_ports", [])
        services = scan_result.get("services", {})
        
        # Generate device name
        if hostname:
            device_name = hostname.split('.')[0]  # Remove domain
        else:
            device_name = f"host-{ip.replace('.', '-')}"
        
        # Determine device type and role
        device_type = self._determine_device_type(scan_result)
        device_role = self._determine_device_role(scan_result)
        
        # Determine site based on IP subnet
        site = self._determine_site_from_ip(ip)
        
        device = Device(
            name=device_name,
            device_type=device_type,
            device_role=device_role,
            site=site,
            primary_ip4=ip,
            platform=os_guess,
            status="active",
            custom_fields={
                "scan_timestamp": self.last_incremental_sync.isoformat() if self.last_incremental_sync else None,
                "open_ports": open_ports,
                "mac_address": scan_result.get("mac_address"),
                "vendor": vendor,
                "hostname": hostname,
                "services": [f"{port}:{service.get('name', 'unknown')}" 
                           for port, service in services.items() if isinstance(service, dict)],
                "discovery_source": "network_scan",
                "response_time": scan_result.get("response_time")
            }
        )
        
        return device
    
    def _determine_device_type(self, scan_result: Dict) -> DeviceType:
        """Determine device type from scan results"""
        vendor = scan_result.get("vendor", "Generic")
        open_ports = scan_result.get("open_ports", [])
        services = scan_result.get("services", {})
        os_guess = scan_result.get("os_guess")
        
        # Default values
        manufacturer = "Generic"
        model = "Network Device"
        
        # Vendor-specific logic
        if vendor:
            manufacturer = vendor
        
        # Service-based detection
        if 161 in open_ports:  # SNMP
            model = "Managed Switch"
        elif 3389 in open_ports:  # RDP
            manufacturer = "Microsoft"
            model = "Windows Server"
        elif 22 in open_ports and 80 in open_ports:
            model = "Linux Server"
        elif 80 in open_ports or 443 in open_ports:
            # Check for specific device types
            for port, service in services.items():
                if isinstance(service, dict):
                    device_type = service.get("device_type", "")
                    if device_type == "ubiquiti" or device_type == "unifi":
                        manufacturer = "Ubiquiti"
                        model = "UniFi Device"
                    elif device_type == "mikrotik":
                        manufacturer = "MikroTik"
                        model = "RouterBoard"
                    elif device_type == "dd-wrt":
                        model = "DD-WRT Router"
                    elif device_type == "openwrt":
                        model = "OpenWrt Router"
                    elif "router" in str(service).lower():
                        model = "Router"
                    elif "switch" in str(service).lower():
                        model = "Switch"
        
        # OS-based detection
        if os_guess:
            if "unifi" in os_guess.lower():
                manufacturer = "Ubiquiti"
                model = "UniFi Device"
            elif "routeros" in os_guess.lower():
                manufacturer = "MikroTik"
                model = "RouterBoard"
            elif "windows" in os_guess.lower():
                manufacturer = "Microsoft"
                model = "Windows Device"
            elif "linux" in os_guess.lower():
                model = "Linux Device"
        
        return DeviceType(
            manufacturer=manufacturer,
            model=model,
            slug=f"{manufacturer.lower()}-{model.lower()}".replace(" ", "-"),
            u_height=1.0 if any(keyword in model.lower() for keyword in ["switch", "router", "server"]) else 0.0
        )
    
    def _determine_device_role(self, scan_result: Dict) -> DeviceRole:
        """Determine device role from scan results"""
        open_ports = scan_result.get("open_ports", [])
        services = scan_result.get("services", {})
        os_guess = scan_result.get("os_guess", "")
        
        # Default
        role_name = "Unknown Device"
        role_slug = "unknown-device"
        color = "9e9e9e"
        
        # SNMP usually indicates network equipment
        if 161 in open_ports:
            role_name = "Network Switch"
            role_slug = "network-switch"
            color = "2196f3"
        # RDP suggests Windows server
        elif 3389 in open_ports:
            role_name = "Windows Server"
            role_slug = "windows-server"
            color = "03a9f4"
        # SSH + web suggests Linux server/appliance
        elif 22 in open_ports and (80 in open_ports or 443 in open_ports):
            # Check for specific device types
            device_identified = False
            for port, service in services.items():
                if isinstance(service, dict):
                    device_type = service.get("device_type", "").lower()
                    if "unifi" in device_type or "ubiquiti" in str(service).lower():
                        role_name = "Access Point"
                        role_slug = "access-point"
                        color = "4caf50"
                        device_identified = True
                        break
                    elif "router" in str(service).lower() or "mikrotik" in device_type:
                        role_name = "Router"
                        role_slug = "router"
                        color = "ff5722"
                        device_identified = True
                        break
            
            if not device_identified:
                role_name = "Linux Server"
                role_slug = "linux-server"
                color = "795548"
        # Web interface suggests management device
        elif 80 in open_ports or 443 in open_ports:
            role_name = "Network Device"
            role_slug = "network-device"
            color = "607d8b"
        # SSH only suggests server/appliance
        elif 22 in open_ports:
            role_name = "Server"
            role_slug = "server"
            color = "795548"
        # DNS server
        elif 53 in open_ports:
            role_name = "DNS Server"
            role_slug = "dns-server"
            color = "9c27b0"
        
        return DeviceRole(
            name=role_name,
            slug=role_slug,
            color=color,
            description=f"Network discovered device with ports: {', '.join(map(str, open_ports))}"
        )
    
    def _determine_site_from_ip(self, ip: str) -> Site:
        """Determine site based on IP subnet"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            # Check custom subnet mappings first
            subnet_key = '.'.join(ip.split('.')[:3])
            if subnet_key in self.scan_config.subnet_site_mapping:
                site_name = self.scan_config.subnet_site_mapping[subnet_key]
                return Site(
                    name=site_name,
                    slug=site_name.lower().replace(" ", "-")
                )
            
            # Common subnet to site mappings
            subnet_sites = {
                "192.168.1": {"name": "Main Network", "slug": "main"},
                "192.168.10": {"name": "IoT Network", "slug": "iot"},
                "192.168.20": {"name": "Guest Network", "slug": "guest"},
                "10.0.0": {"name": "Internal Network", "slug": "internal"},
                "10.0.10": {"name": "Management Network", "slug": "management"},
                "172.16.0": {"name": "DMZ Network", "slug": "dmz"}
            }
            
            if subnet_key in subnet_sites:
                site_info = subnet_sites[subnet_key]
            else:
                # Default site based on private/public
                if ip_obj.is_private:
                    site_info = {"name": f"Subnet {subnet_key}", "slug": f"subnet-{subnet_key.replace('.', '-')}"}
                else:
                    site_info = {"name": "External", "slug": "external"}
            
            return Site(
                name=site_info["name"],
                slug=site_info["slug"],
                description=f"Auto-discovered from network scan of {subnet_key}.0/24"
            )
            
        except Exception:
            return Site(name="Unknown", slug="unknown")
    
    async def connect(self) -> bool:
        """Connect to network scanner (no persistent connection needed)"""
        try:
            # Network scanner doesn't maintain persistent connections
            # Just verify scanning capability is available
            result = await self.test_connection()
            if result:
                self.logger.info("Network scanner ready")
            else:
                self.logger.error("Network scanner initialization failed")
            return result
        except Exception as e:
            self.logger.error("Connection failed", error=str(e))
            return False
    
    async def test_connection(self) -> bool:
        """Test network scanning capability"""
        try:
            # Test by scanning localhost
            result = self._scan_host("127.0.0.1")
            return result.get("alive", False)
        except Exception as e:
            self.logger.error("Connection test failed", error=str(e))
            return False
    
    def get_required_config_fields(self) -> List[str]:
        """Return required configuration fields"""
        return ["networks", "enabled"]
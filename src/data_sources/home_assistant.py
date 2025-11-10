import asyncio
from typing import List, Dict, Any, Optional
from src.data_sources.base import APIBasedDataSource, DataSourceType, DiscoveryResult, DataSourceConfig
from src.netbox.models import Device, IPAddress, DeviceType, DeviceRole, Site
from src.mcp.home_assistant import HomeAssistantMCPClient

class HomeAssistantDataSourceConfig(DataSourceConfig):
    """Configuration for Home Assistant data source"""
    url: str
    token_path: str
    include_entity_types: List[str] = ["device_tracker", "sensor", "switch", "camera", "media_player"]
    area_site_mapping: Dict[str, str] = {}
    manufacturer_normalization: Dict[str, str] = {
        "ubnt": "Ubiquiti",
        "ui": "Ubiquiti", 
        "tplink": "TP-Link",
        "dlink": "D-Link"
    }

class HomeAssistantDataSource(APIBasedDataSource):
    """Data source for Home Assistant integration"""
    
    def __init__(self, config: HomeAssistantDataSourceConfig):
        super().__init__(config, DataSourceType.HOME_ASSISTANT)
        self.ha_config = config
        self.mcp_client = HomeAssistantMCPClient(config.dict())
        self.device_type_cache = {}
        self.device_role_cache = {}
        
    async def discover(self) -> DiscoveryResult:
        """Discover devices from Home Assistant"""
        result = DiscoveryResult(
            source_type=self.source_type,
            source_id=self.source_id
        )
        
        try:
            # Connect to MCP server
            if not await self.mcp_client.connect():
                result.add_error("Failed to connect to Home Assistant MCP")
                return result
            
            # Get all HA devices
            ha_devices = await self.mcp_client.get_devices()
            self.logger.info("Retrieved devices from Home Assistant", count=len(ha_devices))
            
            # Get network entities for IP mapping
            network_entities = await self.mcp_client.get_network_devices()
            self.logger.info("Retrieved network entities", count=len(network_entities))
            
            # Create device mapping
            entity_to_device_map = self._map_entities_to_devices(network_entities, ha_devices)
            
            # Convert to NetBox devices
            for ha_device in ha_devices:
                try:
                    netbox_device = await self._convert_to_netbox_device(
                        ha_device, entity_to_device_map
                    )
                    if netbox_device:
                        result.devices.append(netbox_device)
                        
                        # Extract IP addresses
                        ip_addresses = self._extract_ip_addresses(ha_device, entity_to_device_map)
                        result.ip_addresses.extend(ip_addresses)
                        
                except Exception as e:
                    result.add_error(f"Failed to convert device {ha_device.get('name')}: {str(e)}")
                    
        except Exception as e:
            result.add_error(f"Discovery failed: {str(e)}")
        finally:
            await self.mcp_client.disconnect()
        
        result.metadata = {
            "total_ha_devices": len(ha_devices) if 'ha_devices' in locals() else 0,
            "network_entities": len(network_entities) if 'network_entities' in locals() else 0,
            "conversion_success_rate": f"{len(result.devices) / max(1, len(ha_devices)) * 100:.1f}%" if 'ha_devices' in locals() else "0%"
        }
        
        return result
    
    def _map_entities_to_devices(self, entities: List[Dict], devices: List[Dict]) -> Dict:
        """Map entities to their parent devices"""
        mapping = {}
        
        for entity in entities:
            device_id = entity.get("device_id")
            if device_id:
                if device_id not in mapping:
                    mapping[device_id] = []
                mapping[device_id].append(entity)
        
        return mapping
    
    async def _convert_to_netbox_device(self, ha_device: Dict, entity_map: Dict) -> Optional[Device]:
        """Convert Home Assistant device to NetBox device"""
        
        # Skip devices without useful network information
        if not self._is_network_relevant(ha_device, entity_map):
            return None
        
        device_name = self._generate_device_name(ha_device)
        device_type = await self._determine_device_type(ha_device, entity_map)
        device_role = await self._determine_device_role(ha_device, entity_map)
        site = self._determine_site(ha_device)
        
        # Extract primary IP address
        primary_ip4 = self._get_primary_ip(ha_device, entity_map)
        
        # Create device
        device = Device(
            name=device_name,
            device_type=device_type,
            device_role=device_role,
            site=site,
            primary_ip4=primary_ip4,
            platform=self._determine_platform(ha_device),
            serial=ha_device.get("serial_number"),
            status="active",
            custom_fields={
                "ha_device_id": ha_device.get("id"),
                "ha_manufacturer": ha_device.get("manufacturer"),
                "ha_model": ha_device.get("model"),
                "ha_sw_version": ha_device.get("sw_version"),
                "ha_integration": ha_device.get("via_device_id"),
                "ha_area_id": ha_device.get("area_id"),
                "ha_config_entries": ha_device.get("config_entries", []),
                "discovery_source": "home_assistant",
                "last_discovered": self.last_incremental_sync.isoformat() if self.last_incremental_sync else None
            }
        )
        
        return device
    
    def _is_network_relevant(self, device: Dict, entity_map: Dict) -> bool:
        """Check if device is network-relevant for NetBox"""
        device_id = device.get("id")
        
        # Check device class
        device_class = device.get("device_class", "").lower()
        network_classes = [
            "router", "switch", "access_point", "gateway", "modem",
            "hub", "bridge", "repeater", "firewall", "camera"
        ]
        
        if device_class in network_classes:
            return True
        
        # Check if device has network entities
        entities = entity_map.get(device_id, [])
        for entity in entities:
            attributes = entity.get("attributes", {})
            if any(attr in attributes for attr in ["ip_address", "mac_address", "host_name"]):
                return True
            
            # Check entity domains
            entity_id = entity.get("entity_id", "")
            if any(domain in entity_id for domain in self.ha_config.include_entity_types):
                return True
        
        # Check manufacturer for known network brands
        manufacturer = device.get("manufacturer", "").lower()
        network_brands = [
            "ubiquiti", "cisco", "netgear", "linksys", "asus", "tp-link",
            "d-link", "fortinet", "pfsense", "mikrotik", "unifi"
        ]
        
        if any(brand in manufacturer for brand in network_brands):
            return True
        
        # Check model names
        model = device.get("model", "").lower()
        if any(keyword in model for keyword in ["router", "switch", "ap", "gateway", "camera"]):
            return True
        
        return False
    
    def _generate_device_name(self, device: Dict) -> str:
        """Generate a valid NetBox device name"""
        name = device.get("name") or device.get("name_by_user") or "unknown"
        
        # Sanitize name
        import re
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[-\s]+', '-', name)
        name = name.lower().strip('-')
        
        # Ensure uniqueness with device ID
        device_id = device.get("id", "")[:8]  # First 8 chars of ID
        
        return f"{name}-{device_id}" if device_id else name
    
    async def _determine_device_type(self, device: Dict, entity_map: Dict) -> DeviceType:
        """Determine NetBox device type"""
        manufacturer = device.get("manufacturer", "Generic")
        model = device.get("model", "Unknown")
        
        # Check cache first
        cache_key = f"{manufacturer}-{model}"
        if cache_key in self.device_type_cache:
            return self.device_type_cache[cache_key]
        
        # Clean up manufacturer and model
        manufacturer = self._normalize_manufacturer(manufacturer)
        model = self._normalize_model(model, device, entity_map)
        
        device_type = DeviceType(
            manufacturer=manufacturer,
            model=model,
            slug=f"{manufacturer.lower()}-{model.lower()}".replace(" ", "-"),
            part_number=device.get("hw_version"),
            u_height=self._estimate_u_height(device, entity_map)
        )
        
        # Cache the result
        self.device_type_cache[cache_key] = device_type
        return device_type
    
    def _normalize_manufacturer(self, manufacturer: str) -> str:
        """Normalize manufacturer name"""
        manufacturer_lower = manufacturer.lower()
        return self.ha_config.manufacturer_normalization.get(manufacturer_lower, manufacturer.title())
    
    def _normalize_model(self, model: str, device: Dict, entity_map: Dict) -> str:
        """Normalize and enhance model name"""
        if not model or model.lower() == "unknown":
            # Try to infer from device class or entities
            device_class = device.get("device_class", "")
            if device_class:
                return device_class.title()
            
            # Check entities for clues
            entities = entity_map.get(device.get("id"), [])
            for entity in entities:
                entity_id = entity.get("entity_id", "")
                if "router" in entity_id:
                    return "Router"
                elif "switch" in entity_id:
                    return "Switch"
                elif "camera" in entity_id:
                    return "IP Camera"
        
        return model
    
    def _estimate_u_height(self, device: Dict, entity_map: Dict) -> float:
        """Estimate rack unit height"""
        device_class = device.get("device_class", "").lower()
        
        rack_devices = ["switch", "router", "firewall", "server"]
        if any(dev_type in device_class for dev_type in rack_devices):
            return 1.0
        
        return 0.0  # Desktop/wall-mount devices
    
    async def _determine_device_role(self, device: Dict, entity_map: Dict) -> DeviceRole:
        """Determine NetBox device role"""
        device_class = device.get("device_class", "").lower()
        manufacturer = device.get("manufacturer", "").lower()
        model = device.get("model", "").lower()
        
        # Role mapping based on device characteristics
        if device_class in ["router", "gateway"] or "router" in model:
            role_name = "Router"
            role_slug = "router"
            color = "ff5722"  # Deep Orange
        elif device_class == "switch" or "switch" in model:
            role_name = "Switch"
            role_slug = "switch"
            color = "2196f3"  # Blue
        elif device_class in ["access_point", "ap"] or "access" in model:
            role_name = "Access Point"
            role_slug = "access-point"
            color = "4caf50"  # Green
        elif "camera" in model or self._has_camera_entities(entity_map.get(device.get("id"), [])):
            role_name = "Security Camera"
            role_slug = "security-camera"
            color = "9c27b0"  # Purple
        elif "sensor" in device_class or self._has_sensor_entities(entity_map.get(device.get("id"), [])):
            role_name = "IoT Sensor"
            role_slug = "iot-sensor"
            color = "ff9800"  # Orange
        elif device_class in ["smart_plug", "switch"] or self._has_switch_entities(entity_map.get(device.get("id"), [])):
            role_name = "Smart Switch"
            role_slug = "smart-switch"
            color = "607d8b"  # Blue Grey
        elif "media_player" in str(entity_map.get(device.get("id"), [])):
            role_name = "Media Device"
            role_slug = "media-device"
            color = "e91e63"  # Pink
        else:
            role_name = "IoT Device"
            role_slug = "iot-device"
            color = "9e9e9e"  # Grey
        
        return DeviceRole(
            name=role_name,
            slug=role_slug,
            color=color,
            description=f"Discovered from Home Assistant ({device_class})"
        )
    
    def _has_camera_entities(self, entities: List[Dict]) -> bool:
        """Check if device has camera entities"""
        return any("camera" in entity.get("entity_id", "") for entity in entities)
    
    def _has_sensor_entities(self, entities: List[Dict]) -> bool:
        """Check if device has sensor entities"""
        return any("sensor" in entity.get("entity_id", "") for entity in entities)
    
    def _has_switch_entities(self, entities: List[Dict]) -> bool:
        """Check if device has switch entities"""
        return any("switch" in entity.get("entity_id", "") for entity in entities)
    
    def _determine_site(self, device: Dict) -> Site:
        """Determine site based on HA area"""
        area_id = device.get("area_id")
        
        if area_id:
            # Check custom area mappings first
            if area_id in self.ha_config.area_site_mapping:
                site_name = self.ha_config.area_site_mapping[area_id]
                return Site(
                    name=site_name,
                    slug=site_name.lower().replace(" ", "-")
                )
            
            # Default area to site mapping
            area_site_map = {
                "living_room": {"name": "Living Room", "slug": "living-room"},
                "bedroom": {"name": "Bedroom", "slug": "bedroom"},
                "kitchen": {"name": "Kitchen", "slug": "kitchen"},
                "office": {"name": "Office", "slug": "office"},
                "basement": {"name": "Basement", "slug": "basement"},
                "garage": {"name": "Garage", "slug": "garage"},
                "outdoor": {"name": "Outdoor", "slug": "outdoor"},
                "network_closet": {"name": "Network Closet", "slug": "network-closet"}
            }
            
            site_info = area_site_map.get(area_id.lower(), {
                "name": area_id.replace("_", " ").title(),
                "slug": area_id.lower()
            })
        else:
            site_info = {"name": "Home", "slug": "home"}
        
        return Site(
            name=site_info["name"],
            slug=site_info["slug"],
            description=f"Home Assistant area: {area_id}" if area_id else "Default home site"
        )
    
    def _determine_platform(self, device: Dict) -> Optional[str]:
        """Determine device platform/OS"""
        platform_hints = [
            device.get("sw_version", ""),
            device.get("model", ""),
            device.get("manufacturer", "")
        ]
        
        for hint in platform_hints:
            hint_lower = hint.lower()
            if "openwrt" in hint_lower:
                return "OpenWrt"
            elif "dd-wrt" in hint_lower:
                return "DD-WRT"
            elif "unifi" in hint_lower:
                return "UniFi OS"
            elif "ios" in hint_lower and "cisco" in device.get("manufacturer", "").lower():
                return "Cisco IOS"
            elif "android" in hint_lower:
                return "Android"
            elif "linux" in hint_lower:
                return "Linux"
        
        return None
    
    def _get_primary_ip(self, device: Dict, entity_map: Dict) -> Optional[str]:
        """Get primary IP address for device"""
        # Check device attributes
        device_ip = device.get("primary_config_entry", {}).get("data", {}).get("host")
        if device_ip and self._is_valid_ip(device_ip):
            return device_ip
        
        # Check entities for IP addresses
        entities = entity_map.get(device.get("id"), [])
        for entity in entities:
            attributes = entity.get("attributes", {})
            
            # Check various IP attributes
            for ip_attr in ["ip_address", "host", "ip"]:
                ip_val = attributes.get(ip_attr)
                if ip_val and self._is_valid_ip(ip_val):
                    return ip_val
        
        return None
    
    def _extract_ip_addresses(self, device: Dict, entity_map: Dict) -> List[IPAddress]:
        """Extract all IP addresses associated with device"""
        ip_addresses = []
        
        primary_ip = self._get_primary_ip(device, entity_map)
        if primary_ip:
            ip_addresses.append(IPAddress(
                address=primary_ip,
                status="active",
                dns_name=device.get("name"),
                description=f"Primary IP for {device.get('name')} (Home Assistant)"
            ))
        
        # Extract additional IPs from entities
        entities = entity_map.get(device.get("id"), [])
        for entity in entities:
            attributes = entity.get("attributes", {})
            
            for ip_attr in ["ip_address", "host", "ip"]:
                ip_val = attributes.get(ip_attr)
                if ip_val and self._is_valid_ip(ip_val) and ip_val != primary_ip:
                    ip_addresses.append(IPAddress(
                        address=ip_val,
                        status="active",
                        description=f"Secondary IP for {device.get('name')} from entity {entity.get('entity_id')}"
                    ))
        
        return ip_addresses
    
    def _is_valid_ip(self, ip_str: str) -> bool:
        """Check if string is a valid IP address"""
        import ipaddress
        try:
            ipaddress.ip_address(ip_str)
            return True
        except ValueError:
            return False
    
    async def connect(self) -> bool:
        """Connect to Home Assistant MCP server"""
        try:
            result = await self.mcp_client.connect()
            if result:
                self.logger.info("Connected to Home Assistant MCP server")
            else:
                self.logger.error("Failed to connect to Home Assistant MCP server")
            return result
        except Exception as e:
            self.logger.error("Connection failed", error=str(e))
            return False
    
    async def test_connection(self) -> bool:
        """Test connection to Home Assistant"""
        try:
            result = await self.mcp_client.connect()
            await self.mcp_client.disconnect()
            return result
        except Exception as e:
            self.logger.error("Connection test failed", error=str(e))
            return False
    
    def get_required_config_fields(self) -> List[str]:
        """Return required configuration fields"""
        return ["url", "token_path", "enabled"]
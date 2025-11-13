"""NetBox API Client Implementation"""

import pynetbox
from typing import Optional, List, Dict, Any, Union
import backoff
import structlog
from urllib3.exceptions import InsecureRequestWarning
import urllib3


class NetBoxClient:
    """NetBox API client with pynetbox integration"""
    
    def __init__(self, url: str, token: str, verify_ssl: bool = True):
        self.url = url.rstrip('/')
        self.token = token
        self.verify_ssl = verify_ssl
        self.api = None
        self.logger = structlog.get_logger(__name__)
        
        if not verify_ssl:
            urllib3.disable_warnings(InsecureRequestWarning)
        
        self.connect()
    
    def connect(self):
        """Establish connection to NetBox API"""
        try:
            self.api = pynetbox.api(
                self.url,
                token=self.token,
                threading=True
            )
            
            if not self.verify_ssl:
                self.api.http_session.verify = False
                
            self.logger.info("NetBox API client initialized", url=self.url)
            
        except Exception as e:
            self.logger.error("Failed to initialize NetBox API client", error=str(e))
            raise
    
    @backoff.on_exception(
        backoff.expo,
        (Exception,),
        max_tries=3,
        max_time=30
    )
    def test_connection(self) -> bool:
        """Test NetBox API connectivity with retry logic"""
        try:
            status = self.api.status()
            self.logger.info("NetBox connection test successful", 
                           netbox_version=status.get('netbox-version', 'unknown'))
            return True
        except Exception as e:
            self.logger.error("NetBox connection test failed", error=str(e))
            raise
    
    # DCIM Methods
    def get_sites(self, **filters) -> List:
        """Get all sites from NetBox with optional filtering"""
        try:
            if filters:
                return list(self.api.dcim.sites.filter(**filters))
            return list(self.api.dcim.sites.all())
        except Exception as e:
            self.logger.error("Failed to get sites", error=str(e), filters=filters)
            raise
    
    def get_site(self, name: str = None, slug: str = None) -> Optional[Any]:
        """Get a site by name or slug"""
        try:
            if name:
                return self.api.dcim.sites.get(name=name)
            elif slug:
                return self.api.dcim.sites.get(slug=slug)
            else:
                raise ValueError("Either name or slug must be provided")
        except Exception as e:
            self.logger.error("Failed to get site", error=str(e), name=name, slug=slug)
            return None
    
    def create_site(self, site_data: Dict) -> Any:
        """Create a new site in NetBox"""
        try:
            site = self.api.dcim.sites.create(site_data)
            self.logger.info("Site created successfully", site_name=site_data.get('name'))
            return site
        except Exception as e:
            self.logger.error("Failed to create site", error=str(e), site_data=site_data)
            raise
    
    def get_device_types(self, **filters) -> List:
        """Get device types with optional filtering"""
        try:
            if filters:
                return list(self.api.dcim.device_types.filter(**filters))
            return list(self.api.dcim.device_types.all())
        except Exception as e:
            self.logger.error("Failed to get device types", error=str(e), filters=filters)
            raise
    
    def get_or_create_device_type(self, manufacturer: str, model: str, **kwargs) -> Any:
        """Get or create device type"""
        try:
            # Try to get existing device type
            device_type = self.api.dcim.device_types.get(
                manufacturer__name=manufacturer,
                model=model
            )
            
            if device_type:
                self.logger.debug("Device type found", manufacturer=manufacturer, model=model)
                return device_type
            
            # Get or create manufacturer
            manufacturer_obj = self.get_or_create_manufacturer(manufacturer)
            
            # Create device type
            device_type_data = {
                'manufacturer': manufacturer_obj.id,
                'model': model,
                'slug': f"{manufacturer.lower().replace(' ', '-')}-{model.lower().replace(' ', '-')}",
                **kwargs
            }
            
            device_type = self.api.dcim.device_types.create(device_type_data)
            self.logger.info("Device type created", manufacturer=manufacturer, model=model)
            return device_type
            
        except Exception as e:
            self.logger.error("Failed to get or create device type", 
                            error=str(e), manufacturer=manufacturer, model=model)
            raise
    
    def get_or_create_manufacturer(self, name: str) -> Any:
        """Get or create manufacturer"""
        try:
            manufacturer = self.api.dcim.manufacturers.get(name=name)
            
            if manufacturer:
                return manufacturer
            
            manufacturer_data = {
                'name': name,
                'slug': name.lower().replace(' ', '-')
            }
            
            manufacturer = self.api.dcim.manufacturers.create(manufacturer_data)
            self.logger.info("Manufacturer created", name=name)
            return manufacturer
            
        except Exception as e:
            self.logger.error("Failed to get or create manufacturer", error=str(e), name=name)
            raise
    
    def get_device_roles(self, **filters) -> List:
        """Get device roles with optional filtering"""
        try:
            if filters:
                return list(self.api.dcim.device_roles.filter(**filters))
            return list(self.api.dcim.device_roles.all())
        except Exception as e:
            self.logger.error("Failed to get device roles", error=str(e), filters=filters)
            raise
    
    def get_or_create_device_role(self, name: str, color: str = "9e9e9e", **kwargs) -> Any:
        """Get or create device role"""
        try:
            role = self.api.dcim.device_roles.get(name=name)
            
            if role:
                return role
            
            role_data = {
                'name': name,
                'slug': name.lower().replace(' ', '-'),
                'color': color,
                **kwargs
            }
            
            role = self.api.dcim.device_roles.create(role_data)
            self.logger.info("Device role created", name=name)
            return role
            
        except Exception as e:
            self.logger.error("Failed to get or create device role", error=str(e), name=name)
            raise
    
    def get_devices(self, **filters) -> List:
        """Get devices with optional filtering"""
        try:
            if filters:
                return list(self.api.dcim.devices.filter(**filters))
            return list(self.api.dcim.devices.all())
        except Exception as e:
            self.logger.error("Failed to get devices", error=str(e), filters=filters)
            raise

    def get_all_devices(self, limit: int = None, offset: int = 0) -> List:
        """
        Get all devices from NetBox with pagination support

        Args:
            limit: Maximum number of devices to return (None for all)
            offset: Number of devices to skip

        Returns:
            List of device objects
        """
        try:
            devices = []
            page_size = 100  # NetBox default page size
            current_offset = offset

            self.logger.debug("Fetching all devices from NetBox", limit=limit, offset=offset)

            while True:
                # Fetch page of devices
                if limit and len(devices) >= limit:
                    # We've reached the limit
                    devices = devices[:limit]
                    break

                # Calculate how many to fetch in this page
                if limit:
                    remaining = limit - len(devices)
                    fetch_limit = min(page_size, remaining)
                else:
                    fetch_limit = page_size

                # Fetch devices with pagination
                page = list(self.api.dcim.devices.filter(
                    limit=fetch_limit,
                    offset=current_offset
                ))

                if not page:
                    # No more devices
                    break

                devices.extend(page)

                # If we got fewer devices than requested, we've reached the end
                if len(page) < fetch_limit:
                    break

                current_offset += len(page)

            self.logger.info("Fetched all devices from NetBox",
                           total_devices=len(devices),
                           limit=limit,
                           offset=offset)
            return devices

        except Exception as e:
            self.logger.error("Failed to get all devices", error=str(e), limit=limit, offset=offset)
            raise

    def get_device(self, name: str) -> Optional[Any]:
        """Get a device by name"""
        try:
            return self.api.dcim.devices.get(name=name)
        except Exception as e:
            self.logger.error("Failed to get device", error=str(e), name=name)
            return None
    
    def create_device(self, device_data: Dict) -> Any:
        """Create a new device in NetBox"""
        try:
            device = self.api.dcim.devices.create(device_data)
            self.logger.info("Device created successfully", device_name=device_data.get('name'))
            return device
        except Exception as e:
            self.logger.error("Failed to create device", error=str(e), device_data=device_data)
            raise
    
    def update_device(self, device_id: int, device_data: Dict) -> Any:
        """Update existing device"""
        try:
            device = self.api.dcim.devices.get(device_id)
            if not device:
                raise ValueError(f"Device with ID {device_id} not found")
            
            # Update device fields
            for key, value in device_data.items():
                setattr(device, key, value)
            
            device.save()
            self.logger.info("Device updated successfully", device_id=device_id)
            return device
            
        except Exception as e:
            self.logger.error("Failed to update device", error=str(e), 
                            device_id=device_id, device_data=device_data)
            raise
    
    def get_all_sites(self, limit: int = None) -> List:
        """
        Get all sites from NetBox with pagination support

        Args:
            limit: Maximum number of sites to return (None for all)

        Returns:
            List of site objects
        """
        try:
            if limit:
                return list(self.api.dcim.sites.filter(limit=limit))
            return list(self.api.dcim.sites.all())
        except Exception as e:
            self.logger.error("Failed to get all sites", error=str(e))
            raise

    def get_all_device_types(self, limit: int = None) -> List:
        """
        Get all device types from NetBox

        Args:
            limit: Maximum number to return (None for all)

        Returns:
            List of device type objects
        """
        try:
            if limit:
                return list(self.api.dcim.device_types.filter(limit=limit))
            return list(self.api.dcim.device_types.all())
        except Exception as e:
            self.logger.error("Failed to get all device types", error=str(e))
            raise

    def get_all_device_roles(self, limit: int = None) -> List:
        """
        Get all device roles from NetBox

        Args:
            limit: Maximum number to return (None for all)

        Returns:
            List of device role objects
        """
        try:
            if limit:
                return list(self.api.dcim.device_roles.filter(limit=limit))
            return list(self.api.dcim.device_roles.all())
        except Exception as e:
            self.logger.error("Failed to get all device roles", error=str(e))
            raise

    # IPAM Methods
    def get_ip_addresses(self, **filters) -> List:
        """Get IP addresses with optional filtering"""
        try:
            if filters:
                return list(self.api.ipam.ip_addresses.filter(**filters))
            return list(self.api.ipam.ip_addresses.all())
        except Exception as e:
            self.logger.error("Failed to get IP addresses", error=str(e), filters=filters)
            raise

    def get_all_ip_addresses(self, limit: int = None) -> List:
        """
        Get all IP addresses from NetBox with pagination support

        Args:
            limit: Maximum number to return (None for all)

        Returns:
            List of IP address objects
        """
        try:
            addresses = []
            page_size = 100
            current_offset = 0

            self.logger.debug("Fetching all IP addresses from NetBox", limit=limit)

            while True:
                if limit and len(addresses) >= limit:
                    addresses = addresses[:limit]
                    break

                fetch_limit = min(page_size, limit - len(addresses)) if limit else page_size

                page = list(self.api.ipam.ip_addresses.filter(
                    limit=fetch_limit,
                    offset=current_offset
                ))

                if not page:
                    break

                addresses.extend(page)

                if len(page) < fetch_limit:
                    break

                current_offset += len(page)

            self.logger.info("Fetched all IP addresses from NetBox", total=len(addresses))
            return addresses

        except Exception as e:
            self.logger.error("Failed to get all IP addresses", error=str(e))
            raise
    
    def get_ip_address(self, address: str) -> Optional[Any]:
        """Get an IP address by address string"""
        try:
            return self.api.ipam.ip_addresses.get(address=address)
        except Exception as e:
            self.logger.error("Failed to get IP address", error=str(e), address=address)
            return None
    
    def create_ip_address(self, ip_data: Dict) -> Any:
        """Create IP address in NetBox"""
        try:
            ip = self.api.ipam.ip_addresses.create(ip_data)
            self.logger.info("IP address created successfully", address=ip_data.get('address'))
            return ip
        except Exception as e:
            self.logger.error("Failed to create IP address", error=str(e), ip_data=ip_data)
            raise
    
    def assign_ip_to_device(self, ip_address: str, device_id: int, interface_name: str = None) -> bool:
        """Assign IP address to device interface"""
        try:
            # Get IP address object
            ip = self.get_ip_address(ip_address)
            if not ip:
                self.logger.error("IP address not found", address=ip_address)
                return False
            
            # Get device
            device = self.api.dcim.devices.get(device_id)
            if not device:
                self.logger.error("Device not found", device_id=device_id)
                return False
            
            # Get or create interface if specified
            if interface_name:
                interface = self.get_or_create_interface(device_id, interface_name)
                if interface:
                    ip.assigned_object_type = 'dcim.interface'
                    ip.assigned_object_id = interface.id
            
            ip.save()
            self.logger.info("IP address assigned to device", 
                           address=ip_address, device_id=device_id, interface=interface_name)
            return True
            
        except Exception as e:
            self.logger.error("Failed to assign IP to device", 
                            error=str(e), address=ip_address, device_id=device_id)
            return False
    
    def get_or_create_interface(self, device_id: int, name: str, interface_type: str = "1000base-t") -> Any:
        """Get or create device interface"""
        try:
            # Try to get existing interface
            interface = self.api.dcim.interfaces.get(device_id=device_id, name=name)
            
            if interface:
                return interface
            
            # Create interface
            interface_data = {
                'device': device_id,
                'name': name,
                'type': interface_type,
                'enabled': True
            }
            
            interface = self.api.dcim.interfaces.create(interface_data)
            self.logger.info("Interface created", device_id=device_id, name=name)
            return interface
            
        except Exception as e:
            self.logger.error("Failed to get or create interface", 
                            error=str(e), device_id=device_id, name=name)
            raise
    
    # Bulk Operations
    def bulk_create_devices(self, devices: List[Dict]) -> List:
        """Bulk create devices for better performance"""
        try:
            created_devices = []
            batch_size = 50  # NetBox recommended batch size
            
            for i in range(0, len(devices), batch_size):
                batch = devices[i:i + batch_size]
                batch_result = self.api.dcim.devices.create(batch)
                
                # Handle single item vs list response
                if isinstance(batch_result, list):
                    created_devices.extend(batch_result)
                else:
                    created_devices.append(batch_result)
                
                self.logger.info("Device batch created", 
                               batch_size=len(batch), total_created=len(created_devices))
            
            return created_devices
            
        except Exception as e:
            self.logger.error("Failed to bulk create devices", error=str(e), device_count=len(devices))
            raise
    
    def bulk_update_devices(self, updates: List[Dict]) -> List:
        """Bulk update devices"""
        try:
            updated_devices = []
            
            for update_data in updates:
                device_id = update_data.pop('id', None)
                if not device_id:
                    self.logger.warning("Device update data missing ID", data=update_data)
                    continue
                
                try:
                    device = self.update_device(device_id, update_data)
                    updated_devices.append(device)
                except Exception as e:
                    self.logger.error("Failed to update device in bulk", 
                                    error=str(e), device_id=device_id)
                    continue
            
            self.logger.info("Bulk device update completed", 
                           total_updated=len(updated_devices), total_attempted=len(updates))
            return updated_devices
            
        except Exception as e:
            self.logger.error("Failed to bulk update devices", error=str(e))
            raise
    
    # Utility Methods
    def get_object_by_id(self, object_type: str, object_id: int) -> Optional[Any]:
        """Generic method to get any NetBox object by type and ID"""
        try:
            # Map common object types to API endpoints
            type_mapping = {
                'site': self.api.dcim.sites,
                'device': self.api.dcim.devices,
                'device_type': self.api.dcim.device_types,
                'device_role': self.api.dcim.device_roles,
                'manufacturer': self.api.dcim.manufacturers,
                'ip_address': self.api.ipam.ip_addresses,
                'interface': self.api.dcim.interfaces,
            }
            
            if object_type not in type_mapping:
                raise ValueError(f"Unsupported object type: {object_type}")
            
            return type_mapping[object_type].get(object_id)
            
        except Exception as e:
            self.logger.error("Failed to get object by ID", 
                            error=str(e), object_type=object_type, object_id=object_id)
            return None
    
    def search(self, query: str, object_types: List[str] = None) -> Dict[str, List]:
        """Search across NetBox objects"""
        results = {}
        
        # Default object types to search if none specified
        if not object_types:
            object_types = ['devices', 'sites', 'ip_addresses']
        
        for obj_type in object_types:
            try:
                if obj_type == 'devices':
                    results[obj_type] = list(self.api.dcim.devices.filter(q=query))
                elif obj_type == 'sites':
                    results[obj_type] = list(self.api.dcim.sites.filter(q=query))
                elif obj_type == 'ip_addresses':
                    results[obj_type] = list(self.api.ipam.ip_addresses.filter(q=query))
                # Add more object types as needed
                    
            except Exception as e:
                self.logger.error("Search failed for object type", 
                                error=str(e), object_type=obj_type, query=query)
                results[obj_type] = []
        
        return results
    
    def close(self):
        """Clean up resources"""
        if self.api and hasattr(self.api, 'http_session'):
            self.api.http_session.close()
        self.logger.info("NetBox client connection closed")
"""NetBox Data Models with Pydantic v2 Validation"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
import ipaddress
import re


class DeviceStatus(str, Enum):
    """NetBox device status choices"""
    ACTIVE = "active"
    PLANNED = "planned"
    STAGED = "staged"
    FAILED = "failed"
    INVENTORY = "inventory"
    DECOMMISSIONING = "decommissioning"
    OFFLINE = "offline"


class IPAddressStatus(str, Enum):
    """NetBox IP address status choices"""
    ACTIVE = "active"
    RESERVED = "reserved"
    DEPRECATED = "deprecated"
    DHCP = "dhcp"
    SLAAC = "slaac"


class InterfaceType(str, Enum):
    """Common NetBox interface types"""
    ETHERNET_1G = "1000base-t"
    ETHERNET_100M = "100base-tx"
    ETHERNET_10G = "10gbase-t"
    ETHERNET_25G = "25gbase-t"
    WIFI = "ieee802.11ac"
    BRIDGE = "bridge"
    LAG = "lag"
    VIRTUAL = "virtual"


class BaseNetBoxModel(BaseModel):
    """Base model for NetBox objects"""
    model_config = ConfigDict(
        extra='allow',
        validate_assignment=True,
        use_enum_values=True
    )
    
    id: Optional[int] = None
    url: Optional[str] = None
    display: Optional[str] = None
    created: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class Manufacturer(BaseNetBoxModel):
    """NetBox manufacturer model"""
    name: str
    slug: str
    description: Optional[str] = None
    
    @field_validator('slug', mode='before')
    @classmethod
    def generate_slug(cls, v, info):
        if not v and info.data.get('name'):
            return info.data['name'].lower().replace(' ', '-').replace('_', '-')
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Manufacturer name cannot be empty')
        return v.strip()


class DeviceRole(BaseNetBoxModel):
    """NetBox device role model"""
    name: str
    slug: str
    color: str = "9e9e9e"
    vm_role: bool = False
    description: Optional[str] = None
    
    @field_validator('slug', mode='before')
    @classmethod
    def generate_slug(cls, v, info):
        if not v and info.data.get('name'):
            return info.data['name'].lower().replace(' ', '-').replace('_', '-')
        return v
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v):
        if not re.match(r'^[0-9a-fA-F]{6}$', v):
            raise ValueError('Color must be a valid hex color (6 characters)')
        return v.lower()
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Role name cannot be empty')
        return v.strip()


class Site(BaseNetBoxModel):
    """NetBox site model"""
    name: str
    slug: str
    status: str = "active"
    region_id: Optional[int] = None
    group_id: Optional[int] = None
    tenant_id: Optional[int] = None
    facility: Optional[str] = None
    time_zone: Optional[str] = None
    description: Optional[str] = None
    physical_address: Optional[str] = None
    shipping_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    comments: Optional[str] = None
    
    @field_validator('slug', mode='before')
    @classmethod
    def generate_slug(cls, v, info):
        if not v and info.data.get('name'):
            return info.data['name'].lower().replace(' ', '-').replace('_', '-')
        return v


class Platform(BaseNetBoxModel):
    """NetBox platform model"""
    name: str
    slug: str
    manufacturer_id: Optional[int] = None
    napalm_driver: Optional[str] = None
    napalm_args: Optional[Dict[str, Any]] = Field(default_factory=dict)
    description: Optional[str] = None


class DeviceType(BaseNetBoxModel):
    """NetBox device type model"""
    manufacturer: Union[str, int, Dict]  # Can be name, ID, or nested object
    model: str
    slug: str
    part_number: Optional[str] = None
    u_height: float = 1.0
    is_full_depth: bool = True
    subdevice_role: Optional[str] = None
    airflow: Optional[str] = None
    weight: Optional[float] = None
    weight_unit: str = "kg"
    description: Optional[str] = None
    comments: Optional[str] = None
    front_image: Optional[str] = None
    rear_image: Optional[str] = None


class VirtualChassis(BaseNetBoxModel):
    """NetBox virtual chassis model"""
    name: str
    domain: Optional[str] = None
    master_id: Optional[int] = None
    description: Optional[str] = None
    comments: Optional[str] = None


class Cluster(BaseNetBoxModel):
    """NetBox cluster model"""
    name: str
    type_id: int
    group_id: Optional[int] = None
    tenant_id: Optional[int] = None
    site_id: Optional[int] = None
    description: Optional[str] = None
    comments: Optional[str] = None


class Device(BaseNetBoxModel):
    """NetBox device model"""
    name: str
    device_type: Union[int, Dict, DeviceType]
    device_role: Union[int, Dict, DeviceRole] 
    tenant_id: Optional[int] = None
    platform: Optional[Union[str, int, Dict]] = None
    serial: Optional[str] = None
    asset_tag: Optional[str] = None
    site: Union[int, Dict, Site]
    location_id: Optional[int] = None
    rack_id: Optional[int] = None
    position: Optional[int] = None
    face: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: DeviceStatus = DeviceStatus.ACTIVE
    airflow: Optional[str] = None
    primary_ip4_id: Optional[int] = None
    primary_ip6_id: Optional[int] = None
    oob_ip_id: Optional[int] = None
    cluster_id: Optional[int] = None
    virtual_chassis_id: Optional[int] = None
    vc_position: Optional[int] = None
    vc_priority: Optional[int] = None
    description: Optional[str] = None
    comments: Optional[str] = None
    config_context: Dict[str, Any] = Field(default_factory=dict)
    local_context_data: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Device name cannot be empty')
        return v.strip()
    
    @field_validator('vc_priority')
    @classmethod
    def validate_vc_priority(cls, v):
        if v is not None and (v < 0 or v > 255):
            raise ValueError('VC priority must be between 0 and 255')
        return v


class Interface(BaseNetBoxModel):
    """NetBox interface model"""
    device_id: int
    name: str
    label: Optional[str] = None
    type: InterfaceType = InterfaceType.ETHERNET_1G
    enabled: bool = True
    parent_id: Optional[int] = None
    bridge_id: Optional[int] = None
    lag_id: Optional[int] = None
    mtu: Optional[int] = None
    mac_address: Optional[str] = None
    speed: Optional[int] = None
    duplex: Optional[str] = None
    wwn: Optional[str] = None
    mgmt_only: bool = False
    description: Optional[str] = None
    mode: Optional[str] = None
    rf_role: Optional[str] = None
    rf_type: Optional[str] = None
    rf_channel: Optional[str] = None
    poe_mode: Optional[str] = None
    poe_type: Optional[str] = None
    wireless_lans: List[int] = Field(default_factory=list)
    untagged_vlan_id: Optional[int] = None
    tagged_vlans: List[int] = Field(default_factory=list)
    mark_connected: bool = False
    cable_id: Optional[int] = None
    cable_peer_id: Optional[int] = None
    cable_peer_type: Optional[str] = None
    wireless_link_id: Optional[int] = None
    link_peers: List[int] = Field(default_factory=list)
    link_peers_type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Interface name cannot be empty')
        return v.strip()
    
    @field_validator('mtu')
    @classmethod
    def validate_mtu(cls, v):
        if v is not None and (v < 68 or v > 65536):
            raise ValueError('MTU must be between 68 and 65536')
        return v
    
    @field_validator('mac_address')
    @classmethod
    def validate_mac_address(cls, v):
        if v and not re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', v):
            raise ValueError('Invalid MAC address format')
        return v.lower() if v else v
    
    @field_validator('speed')
    @classmethod
    def validate_speed(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Interface speed must be positive')
        return v


class IPAddress(BaseNetBoxModel):
    """NetBox IP address model"""
    address: str
    vrf_id: Optional[int] = None
    tenant_id: Optional[int] = None
    status: IPAddressStatus = IPAddressStatus.ACTIVE
    role: Optional[str] = None
    assigned_object_type: Optional[str] = None
    assigned_object_id: Optional[int] = None
    nat_inside_id: Optional[int] = None
    dns_name: Optional[str] = None
    description: Optional[str] = None
    comments: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    @field_validator('address')
    @classmethod
    def validate_address(cls, v):
        try:
            ipaddress.ip_interface(v)
            return v
        except ValueError:
            raise ValueError(f'Invalid IP address format: {v}')
    
    @field_validator('dns_name')
    @classmethod
    def validate_dns_name(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', v):
            raise ValueError('Invalid DNS name format')
        return v


class DeviceCreateRequest(BaseModel):
    """Simplified model for creating devices via API"""
    model_config = ConfigDict(extra='allow')
    
    name: str
    device_type: Union[int, Dict]
    device_role: Union[int, Dict]
    site: Union[int, Dict]
    tenant: Optional[Union[int, Dict]] = None
    platform: Optional[Union[int, Dict]] = None
    serial: Optional[str] = None
    asset_tag: Optional[str] = None
    status: str = 'active'
    rack: Optional[Union[int, Dict]] = None
    position: Optional[int] = None
    face: Optional[str] = None
    primary_ip4: Optional[Union[int, Dict]] = None
    primary_ip6: Optional[Union[int, Dict]] = None
    cluster: Optional[Union[int, Dict]] = None
    virtual_chassis: Optional[Union[int, Dict]] = None
    vc_position: Optional[int] = None
    vc_priority: Optional[int] = None
    description: Optional[str] = None
    comments: Optional[str] = None
    tags: List[Union[str, Dict]] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class IPAddressCreateRequest(BaseModel):
    """Simplified model for creating IP addresses"""
    model_config = ConfigDict(extra='allow')
    
    address: str
    status: IPAddressStatus = IPAddressStatus.ACTIVE
    vrf: Optional[Union[int, Dict]] = None
    tenant: Optional[Union[int, Dict]] = None
    assigned_object_type: Optional[str] = None
    assigned_object_id: Optional[int] = None
    dns_name: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    tags: List[Union[str, Dict]] = Field(default_factory=list)


class BulkOperationResult(BaseModel):
    """Result model for bulk operations"""
    created: int = 0
    updated: int = 0
    failed: int = 0
    skipped: int = 0
    errors: List[str] = Field(default_factory=list)
    total_processed: int = 0
    
    @model_validator(mode='after')
    def calculate_total(self):
        self.total_processed = (
            self.created + self.updated + self.failed + self.skipped
        )
        return self
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total_processed == 0:
            return 0.0
        return ((self.created + self.updated) / self.total_processed) * 100


class SyncStatistics(BaseModel):
    """Statistics for synchronization operations"""
    source: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    devices_discovered: int = 0
    devices_created: int = 0
    devices_updated: int = 0
    devices_failed: int = 0
    ip_addresses_created: int = 0
    ip_addresses_updated: int = 0
    interfaces_created: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    @model_validator(mode='after') 
    def calculate_duration(self):
        if self.end_time and self.start_time:
            duration = self.end_time - self.start_time
            self.duration_seconds = duration.total_seconds()
        return self
    
    @property
    def total_objects_processed(self) -> int:
        """Total number of objects processed"""
        return (
            self.devices_created + self.devices_updated + self.devices_failed +
            self.ip_addresses_created + self.ip_addresses_updated +
            self.interfaces_created
        )
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        total = self.total_objects_processed
        if total == 0:
            return 100.0
        
        successful = (
            self.devices_created + self.devices_updated +
            self.ip_addresses_created + self.ip_addresses_updated +
            self.interfaces_created
        )
        return (successful / total) * 100


# Update forward references for self-referential models
Device.model_rebuild()
Interface.model_rebuild()
IPAddress.model_rebuild()
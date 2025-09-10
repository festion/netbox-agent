"""Base classes for data sources"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set, AsyncGenerator
from datetime import datetime, timedelta
import asyncio
import hashlib
import json
from enum import Enum
from pydantic import BaseModel, Field

import structlog

from ..netbox.models import Device, IPAddress, Interface, DeviceCreateRequest, SyncStatistics


class DataSourceType(str, Enum):
    """Types of data sources"""
    HOME_ASSISTANT = "home_assistant"
    NETWORK_SCAN = "network_scan"
    FILESYSTEM = "filesystem"
    PROXMOX = "proxmox"
    TRUENAS = "truenas"
    MCP_SERVER = "mcp_server"


class SyncMode(str, Enum):
    """Synchronization modes"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DRY_RUN = "dry_run"


class DiscoveryResult(BaseModel):
    """Result of device discovery from a data source"""
    source_type: DataSourceType
    source_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    devices: List[Device] = Field(default_factory=list)
    ip_addresses: List[IPAddress] = Field(default_factory=list)
    interfaces: List[Interface] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    @property
    def total_objects(self) -> int:
        """Total number of discovered objects"""
        return len(self.devices) + len(self.ip_addresses) + len(self.interfaces)
    
    @property
    def has_errors(self) -> bool:
        """Check if discovery had errors"""
        return len(self.errors) > 0
    
    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(f"[{datetime.now().isoformat()}] {error}")
    
    def add_warning(self, warning: str):
        """Add a warning message"""
        self.warnings.append(f"[{datetime.now().isoformat()}] {warning}")


class DataSourceConfig(BaseModel):
    """Base configuration for data sources"""
    enabled: bool = False
    sync_interval: int = 3600  # seconds
    full_sync_interval: int = 86400  # seconds
    timeout: int = 300  # seconds
    retry_attempts: int = 3
    retry_delay: int = 5  # seconds
    batch_size: int = 50
    dry_run: bool = False
    
    # Discovery settings
    discover_devices: bool = True
    discover_ip_addresses: bool = True
    discover_interfaces: bool = True
    
    # Filtering
    include_patterns: List[str] = Field(default_factory=list)
    exclude_patterns: List[str] = Field(default_factory=list)
    
    # NetBox mapping
    default_site: str = "Main"
    default_device_role: str = "Server"
    device_type_mappings: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    
    # Custom fields and tags
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class DataSource(ABC):
    """Abstract base class for all data sources"""
    
    def __init__(self, config: DataSourceConfig, source_type: DataSourceType):
        self.config = config
        self.source_type = source_type
        self.source_id = f"{source_type.value}_{id(self)}"
        self.logger = structlog.get_logger(f"datasource.{source_type.value}")
        
        # State tracking
        self.last_full_sync: Optional[datetime] = None
        self.last_incremental_sync: Optional[datetime] = None
        self.sync_in_progress: bool = False
        self.discovered_objects_cache: Dict[str, str] = {}  # object_id -> hash
        
        # Statistics
        self.total_discoveries = 0
        self.total_sync_time = 0.0
        self.error_count = 0
    
    @abstractmethod
    async def discover(self) -> DiscoveryResult:
        """
        Discover devices and infrastructure from this data source
        
        Returns:
            DiscoveryResult containing discovered objects
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test connection to the data source
        
        Returns:
            True if connection is successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_required_config_fields(self) -> List[str]:
        """
        Get list of required configuration fields for this data source
        
        Returns:
            List of required field names
        """
        pass
    
    async def sync(self, mode: SyncMode = SyncMode.INCREMENTAL) -> SyncStatistics:
        """
        Execute synchronization for this data source
        
        Args:
            mode: Synchronization mode (full, incremental, dry_run)
            
        Returns:
            SyncStatistics with results of the sync operation
        """
        if not self.config.enabled:
            self.logger.info("Data source is disabled", source=self.source_type.value)
            return self._create_disabled_stats()
        
        if self.sync_in_progress:
            self.logger.warning("Sync already in progress", source=self.source_type.value)
            return self._create_in_progress_stats()
        
        self.sync_in_progress = True
        stats = SyncStatistics(
            source=self.source_type.value,
            start_time=datetime.now()
        )
        
        try:
            self.logger.info("Starting sync", source=self.source_type.value, mode=mode.value)
            
            # Test connection first
            if not await self.test_connection():
                stats.errors.append("Connection test failed")
                return stats
            
            # Determine if we should do full or incremental sync
            should_full_sync = (
                mode == SyncMode.FULL or
                self.last_full_sync is None or
                self._should_perform_full_sync()
            )
            
            if should_full_sync:
                await self._perform_full_sync(stats, mode)
            else:
                await self._perform_incremental_sync(stats, mode)
            
            # Update sync timestamps
            now = datetime.now()
            if should_full_sync:
                self.last_full_sync = now
            self.last_incremental_sync = now
            
            stats.end_time = now
            self.total_discoveries += 1
            self.total_sync_time += stats.duration_seconds or 0
            
            self.logger.info("Sync completed", 
                           source=self.source_type.value,
                           mode=mode.value,
                           duration=stats.duration_seconds,
                           devices_discovered=stats.devices_discovered,
                           success_rate=f"{stats.success_rate:.1f}%")
            
        except Exception as e:
            self.error_count += 1
            stats.errors.append(f"Sync failed: {str(e)}")
            self.logger.error("Sync failed", source=self.source_type.value, error=str(e))
        
        finally:
            self.sync_in_progress = False
        
        return stats
    
    async def _perform_full_sync(self, stats: SyncStatistics, mode: SyncMode):
        """Perform full synchronization"""
        self.logger.debug("Performing full sync", source=self.source_type.value)
        
        try:
            # Clear cache for full sync
            self.discovered_objects_cache.clear()
            
            # Discover all objects
            discovery_result = await self.discover()
            
            stats.devices_discovered = len(discovery_result.devices)
            stats.errors.extend(discovery_result.errors)
            stats.warnings.extend(discovery_result.warnings)
            
            if mode != SyncMode.DRY_RUN:
                # Process discovered objects (would be implemented by sync engine)
                self.logger.info("Full sync discovery completed",
                               devices=len(discovery_result.devices),
                               ip_addresses=len(discovery_result.ip_addresses),
                               interfaces=len(discovery_result.interfaces))
            else:
                self.logger.info("DRY RUN: Full sync discovery completed",
                               devices=len(discovery_result.devices),
                               ip_addresses=len(discovery_result.ip_addresses),
                               interfaces=len(discovery_result.interfaces))
            
            # Update cache
            await self._update_object_cache(discovery_result)
            
        except Exception as e:
            stats.errors.append(f"Full sync failed: {str(e)}")
            raise
    
    async def _perform_incremental_sync(self, stats: SyncStatistics, mode: SyncMode):
        """Perform incremental synchronization"""
        self.logger.debug("Performing incremental sync", source=self.source_type.value)
        
        try:
            # Discover objects
            discovery_result = await self.discover()
            
            stats.devices_discovered = len(discovery_result.devices)
            stats.errors.extend(discovery_result.errors)
            stats.warnings.extend(discovery_result.warnings)
            
            # Filter for changed objects only
            changed_objects = await self._filter_changed_objects(discovery_result)
            
            if mode != SyncMode.DRY_RUN:
                # Process only changed objects
                self.logger.info("Incremental sync discovery completed",
                               total_devices=len(discovery_result.devices),
                               changed_devices=len(changed_objects.devices))
            else:
                self.logger.info("DRY RUN: Incremental sync discovery completed",
                               total_devices=len(discovery_result.devices),
                               changed_devices=len(changed_objects.devices))
            
            # Update cache
            await self._update_object_cache(discovery_result)
            
        except Exception as e:
            stats.errors.append(f"Incremental sync failed: {str(e)}")
            raise
    
    async def _filter_changed_objects(self, discovery_result: DiscoveryResult) -> DiscoveryResult:
        """Filter discovery result to only include changed objects"""
        changed_result = DiscoveryResult(
            source_type=self.source_type,
            source_id=self.source_id,
            metadata=discovery_result.metadata
        )
        
        # Check devices for changes
        for device in discovery_result.devices:
            device_hash = self._calculate_object_hash(device.dict())
            cached_hash = self.discovered_objects_cache.get(f"device_{device.name}")
            
            if cached_hash != device_hash:
                changed_result.devices.append(device)
        
        # Check IP addresses for changes
        for ip in discovery_result.ip_addresses:
            ip_hash = self._calculate_object_hash(ip.dict())
            cached_hash = self.discovered_objects_cache.get(f"ip_{ip.address}")
            
            if cached_hash != ip_hash:
                changed_result.ip_addresses.append(ip)
        
        # Check interfaces for changes
        for interface in discovery_result.interfaces:
            interface_hash = self._calculate_object_hash(interface.dict())
            cached_hash = self.discovered_objects_cache.get(f"interface_{interface.device}_{interface.name}")
            
            if cached_hash != interface_hash:
                changed_result.interfaces.append(interface)
        
        return changed_result
    
    async def _update_object_cache(self, discovery_result: DiscoveryResult):
        """Update the object cache with current discovery results"""
        # Cache devices
        for device in discovery_result.devices:
            device_hash = self._calculate_object_hash(device.dict())
            self.discovered_objects_cache[f"device_{device.name}"] = device_hash
        
        # Cache IP addresses
        for ip in discovery_result.ip_addresses:
            ip_hash = self._calculate_object_hash(ip.dict())
            self.discovered_objects_cache[f"ip_{ip.address}"] = ip_hash
        
        # Cache interfaces
        for interface in discovery_result.interfaces:
            interface_hash = self._calculate_object_hash(interface.dict())
            self.discovered_objects_cache[f"interface_{interface.device}_{interface.name}"] = interface_hash
    
    def _calculate_object_hash(self, obj_dict: Dict) -> str:
        """Calculate SHA256 hash of object for change detection"""
        # Remove timestamps and IDs that change frequently
        filtered_dict = {k: v for k, v in obj_dict.items() 
                        if k not in ['id', 'created', 'last_updated', 'url', 'display']}
        
        obj_str = json.dumps(filtered_dict, sort_keys=True, default=str)
        return hashlib.sha256(obj_str.encode()).hexdigest()
    
    def _should_perform_full_sync(self) -> bool:
        """Determine if a full sync should be performed"""
        if not self.last_full_sync:
            return True
        
        time_since_full_sync = datetime.now() - self.last_full_sync
        return time_since_full_sync.total_seconds() >= self.config.full_sync_interval
    
    def should_sync(self) -> bool:
        """Check if sync should run based on interval"""
        if not self.config.enabled:
            return False
        
        if not self.last_incremental_sync:
            return True
        
        time_since_sync = datetime.now() - self.last_incremental_sync
        return time_since_sync.total_seconds() >= self.config.sync_interval
    
    def validate_config(self) -> bool:
        """Validate data source configuration"""
        try:
            # Check required fields
            required_fields = self.get_required_config_fields()
            for field in required_fields:
                if not hasattr(self.config, field):
                    self.logger.error("Missing required config field", field=field)
                    return False
                
                value = getattr(self.config, field)
                if value is None or (isinstance(value, str) and not value.strip()):
                    self.logger.error("Required config field is empty", field=field)
                    return False
            
            # Validate intervals
            if self.config.sync_interval <= 0:
                self.logger.error("Sync interval must be positive")
                return False
            
            if self.config.full_sync_interval < self.config.sync_interval:
                self.logger.error("Full sync interval must be >= sync interval")
                return False
            
            # Validate timeout and retry settings
            if self.config.timeout <= 0:
                self.logger.error("Timeout must be positive")
                return False
            
            if self.config.retry_attempts < 0:
                self.logger.error("Retry attempts must be non-negative")
                return False
            
            if self.config.batch_size <= 0:
                self.logger.error("Batch size must be positive")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("Config validation failed", error=str(e))
            return False
    
    def normalize_device_data(self, raw_data: Dict) -> Device:
        """
        Normalize raw device data to NetBox Device model
        
        Override in subclasses for source-specific normalization logic
        """
        # Default normalization - override in subclasses
        return Device(
            name=raw_data.get('name', 'unknown-device'),
            device_type=self._get_default_device_type(),
            device_role=self._get_default_device_role(),
            site=self._get_default_site(),
            status='active'
        )
    
    def map_device_type(self, raw_data: Dict) -> Dict[str, Any]:
        """Map raw device data to NetBox device type"""
        # Check for custom mappings first
        device_identifier = self._get_device_identifier(raw_data)
        
        if device_identifier in self.config.device_type_mappings:
            return self.config.device_type_mappings[device_identifier]
        
        # Default mapping
        return {
            'manufacturer': 'Generic',
            'model': raw_data.get('model', 'Unknown'),
            'slug': f"generic-{raw_data.get('model', 'unknown').lower().replace(' ', '-')}"
        }
    
    def map_device_role(self, raw_data: Dict) -> Dict[str, Any]:
        """Map raw device data to NetBox device role"""
        # Try to infer role from device data
        device_type = raw_data.get('type', '').lower()
        name = raw_data.get('name', '').lower()
        
        if any(keyword in device_type or keyword in name for keyword in ['router', 'gateway']):
            return {'name': 'Router', 'slug': 'router', 'color': 'ff9800'}
        elif any(keyword in device_type or keyword in name for keyword in ['switch', 'port']):
            return {'name': 'Switch', 'slug': 'switch', 'color': '2196f3'}
        elif any(keyword in device_type or keyword in name for keyword in ['server', 'host']):
            return {'name': 'Server', 'slug': 'server', 'color': '4caf50'}
        elif any(keyword in device_type or keyword in name for keyword in ['sensor', 'iot']):
            return {'name': 'IoT Device', 'slug': 'iot-device', 'color': 'purple'}
        else:
            return {'name': self.config.default_device_role, 'slug': 'unknown', 'color': '9e9e9e'}
    
    def get_default_site(self) -> Dict[str, Any]:
        """Get default site for devices"""
        return {
            'name': self.config.default_site,
            'slug': self.config.default_site.lower().replace(' ', '-')
        }
    
    def _get_default_device_type(self) -> Dict[str, Any]:
        """Get default device type"""
        return {
            'manufacturer': 'Generic',
            'model': 'Unknown',
            'slug': 'generic-unknown'
        }
    
    def _get_default_device_role(self) -> Dict[str, Any]:
        """Get default device role"""
        return {
            'name': self.config.default_device_role,
            'slug': self.config.default_device_role.lower().replace(' ', '-'),
            'color': '9e9e9e'
        }
    
    def _get_default_site(self) -> Dict[str, Any]:
        """Get default site"""
        return self.get_default_site()
    
    def _get_device_identifier(self, raw_data: Dict) -> str:
        """Get unique identifier for device type mapping"""
        manufacturer = raw_data.get('manufacturer', 'unknown').lower()
        model = raw_data.get('model', 'unknown').lower()
        return f"{manufacturer}:{model}"
    
    def _create_disabled_stats(self) -> SyncStatistics:
        """Create stats for disabled data source"""
        return SyncStatistics(
            source=self.source_type.value,
            start_time=datetime.now(),
            end_time=datetime.now(),
            warnings=["Data source is disabled"]
        )
    
    def _create_in_progress_stats(self) -> SyncStatistics:
        """Create stats for sync already in progress"""
        return SyncStatistics(
            source=self.source_type.value,
            start_time=datetime.now(),
            end_time=datetime.now(),
            warnings=["Sync already in progress"]
        )
    
    # Context manager support for resource cleanup
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup"""
        await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources - override in subclasses if needed"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get data source statistics"""
        return {
            'source_type': self.source_type.value,
            'source_id': self.source_id,
            'enabled': self.config.enabled,
            'last_full_sync': self.last_full_sync.isoformat() if self.last_full_sync else None,
            'last_incremental_sync': self.last_incremental_sync.isoformat() if self.last_incremental_sync else None,
            'sync_in_progress': self.sync_in_progress,
            'total_discoveries': self.total_discoveries,
            'total_sync_time': self.total_sync_time,
            'error_count': self.error_count,
            'average_sync_time': self.total_sync_time / max(1, self.total_discoveries),
            'cached_objects': len(self.discovered_objects_cache)
        }


class NetworkDataSource(DataSource):
    """Base class for network-based data sources"""
    
    def __init__(self, config: DataSourceConfig, source_type: DataSourceType):
        super().__init__(config, source_type)
        self.connection_pool = None
    
    async def cleanup(self):
        """Cleanup network connections"""
        if self.connection_pool:
            await self.connection_pool.close()
        await super().cleanup()


class FileBasedDataSource(DataSource):
    """Base class for file-based data sources"""
    
    def __init__(self, config: DataSourceConfig, source_type: DataSourceType):
        super().__init__(config, source_type)
        self.watched_files: Set[str] = set()
        self.file_hashes: Dict[str, str] = {}
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate hash of file content"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _has_file_changed(self, file_path: str) -> bool:
        """Check if file has changed since last check"""
        current_hash = self._calculate_file_hash(file_path)
        previous_hash = self.file_hashes.get(file_path, "")
        
        if current_hash != previous_hash:
            self.file_hashes[file_path] = current_hash
            return True
        
        return False


class APIBasedDataSource(NetworkDataSource):
    """Base class for API-based data sources"""
    
    def __init__(self, config: DataSourceConfig, source_type: DataSourceType):
        super().__init__(config, source_type)
        self.session = None
        self.rate_limiter = None
    
    async def _make_api_request(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make rate-limited API request"""
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        
        # Implementation would go here - override in subclasses
        raise NotImplementedError("Subclasses must implement _make_api_request")
    
    async def cleanup(self):
        """Cleanup API connections"""
        if self.session:
            await self.session.close()
        await super().cleanup()
"""NetBox Synchronization Engine"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
import structlog
from concurrent.futures import ThreadPoolExecutor, as_completed

from .client import NetBoxClient
from .models import Device, IPAddress, DeviceCreateRequest, BulkOperationResult


class SyncMode(Enum):
    """Synchronization modes"""
    FULL = "full"
    INCREMENTAL = "incremental" 
    DRY_RUN = "dry_run"


class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    SKIP = "skip"
    OVERWRITE = "overwrite"
    MERGE = "merge"
    MANUAL = "manual"


class ConflictType(Enum):
    """Types of synchronization conflicts"""
    FIELD_MISMATCH = "field_mismatch"
    DUPLICATE_NAME = "duplicate_name"
    DUPLICATE_IP = "duplicate_ip"
    MISSING_DEPENDENCY = "missing_dependency"
    TYPE_MISMATCH = "type_mismatch"
    ROLE_MISMATCH = "role_mismatch"


class SyncAction(Enum):
    """Synchronization actions"""
    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"
    DELETE = "delete"
    MERGE = "merge"


@dataclass
class SyncConflict:
    """Represents a synchronization conflict"""
    conflict_type: ConflictType
    source_data: Dict[str, Any]
    netbox_data: Optional[Dict[str, Any]]
    device_name: str
    field_name: Optional[str] = None
    resolution: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class SyncResult:
    """Results of a synchronization operation"""
    action: SyncAction
    device_name: str
    success: bool
    error: Optional[str] = None
    conflicts: List[SyncConflict] = None
    metadata: Dict[str, Any] = None


class SyncStatistics:
    """Synchronization statistics tracking"""
    
    def __init__(self):
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.devices_processed = 0
        self.devices_created = 0
        self.devices_updated = 0
        self.devices_skipped = 0
        self.devices_failed = 0
        self.ip_addresses_processed = 0
        self.ip_addresses_created = 0
        self.ip_addresses_updated = 0
        self.errors: List[str] = []
        
    @property
    def duration(self) -> float:
        """Get sync duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def to_dict(self) -> Dict:
        """Convert statistics to dictionary"""
        return {
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
            'devices': {
                'processed': self.devices_processed,
                'created': self.devices_created,
                'updated': self.devices_updated,
                'skipped': self.devices_skipped,
                'failed': self.devices_failed
            },
            'ip_addresses': {
                'processed': self.ip_addresses_processed,
                'created': self.ip_addresses_created,
                'updated': self.ip_addresses_updated
            },
            'errors': self.errors
        }


class SyncEngine:
    """NetBox synchronization engine with change detection and conflict resolution"""
    
    def __init__(self, netbox_client: NetBoxClient, config: Dict):
        self.netbox = netbox_client
        self.config = config
        self.logger = structlog.get_logger(__name__)
        self.sync_cache: Dict[str, Dict] = {}
        self.conflict_queue: List[Dict] = []
        self.stats = SyncStatistics()
        self.max_workers = config.get('sync', {}).get('max_workers', 5)
        
    def calculate_hash(self, obj: Dict) -> str:
        """Calculate SHA256 hash of object for change detection"""
        # Remove volatile fields before hashing
        obj_clean = {k: v for k, v in obj.items() 
                    if k not in ['id', 'created', 'last_updated', 'url', 'display']}
        obj_str = json.dumps(obj_clean, sort_keys=True)
        return hashlib.sha256(obj_str.encode()).hexdigest()
    
    def detect_changes(self, source_data: Dict, netbox_data: Dict) -> bool:
        """Detect if source data differs from NetBox data"""
        source_hash = self.calculate_hash(source_data)
        netbox_hash = self.calculate_hash(netbox_data)
        return source_hash != netbox_hash
    
    def resolve_conflict(self, 
                        source_data: Dict, 
                        netbox_data: Dict,
                        resolution: ConflictResolution) -> Dict:
        """Resolve conflicts between source and NetBox data"""
        if resolution == ConflictResolution.SKIP:
            self.logger.info("Conflict resolved: SKIP", device=source_data.get('name'))
            return netbox_data
        elif resolution == ConflictResolution.OVERWRITE:
            self.logger.info("Conflict resolved: OVERWRITE", device=source_data.get('name'))
            return source_data
        elif resolution == ConflictResolution.MERGE:
            # Merge logic - prefer source for conflicts
            merged = netbox_data.copy()
            merged.update(source_data)
            self.logger.info("Conflict resolved: MERGE", device=source_data.get('name'))
            return merged
        else:
            # Queue for manual resolution
            self.conflict_queue.append({
                'source': source_data,
                'netbox': netbox_data,
                'timestamp': datetime.now()
            })
            self.logger.warning("Conflict queued for manual resolution", device=source_data.get('name'))
            return netbox_data
    
    async def sync_device(self, device_data: Device, mode: SyncMode) -> bool:
        """Sync a single device to NetBox"""
        try:
            self.stats.devices_processed += 1
            
            # Check if device exists
            existing = None
            try:
                existing = self.netbox.get_device_by_name(device_data.name)
            except Exception as e:
                self.logger.debug("Device lookup failed", device=device_data.name, error=str(e))
            
            if existing:
                # Convert existing device to comparable format
                existing_dict = existing.serialize() if hasattr(existing, 'serialize') else dict(existing)
                device_dict = device_data.dict(exclude_unset=True)
                
                if self.detect_changes(device_dict, existing_dict):
                    if mode != SyncMode.DRY_RUN:
                        # Update existing device
                        updated = self.netbox.update_device(existing.id, device_dict)
                        if updated:
                            self.stats.devices_updated += 1
                            self.logger.info("Device updated", device=device_data.name, id=existing.id)
                        else:
                            self.stats.devices_failed += 1
                            self.logger.error("Device update failed", device=device_data.name)
                            return False
                    else:
                        self.stats.devices_updated += 1
                        self.logger.info("[DRY RUN] Would update device", device=device_data.name)
                else:
                    self.stats.devices_skipped += 1
                    self.logger.debug("Device unchanged, skipping", device=device_data.name)
                return True
            else:
                if mode != SyncMode.DRY_RUN:
                    # Create new device
                    created = self.netbox.create_device(DeviceCreateRequest(**device_data.dict(exclude_unset=True)))
                    if created:
                        self.stats.devices_created += 1
                        self.logger.info("Device created", device=device_data.name, id=created.id)
                    else:
                        self.stats.devices_failed += 1
                        self.logger.error("Device creation failed", device=device_data.name)
                        return False
                else:
                    self.stats.devices_created += 1
                    self.logger.info("[DRY RUN] Would create device", device=device_data.name)
                return True
                
        except Exception as e:
            self.stats.devices_failed += 1
            error_msg = f"Failed to sync device {device_data.name}: {str(e)}"
            self.stats.errors.append(error_msg)
            self.logger.error("Device sync failed", device=device_data.name, error=str(e))
            return False
    
    async def sync_ip_address(self, ip_data: IPAddress, mode: SyncMode) -> bool:
        """Sync a single IP address to NetBox"""
        try:
            self.stats.ip_addresses_processed += 1
            
            # Check if IP address exists
            existing = None
            try:
                existing = self.netbox.get_ip_address(ip_data.address)
            except Exception:
                pass
            
            if existing:
                existing_dict = existing.serialize() if hasattr(existing, 'serialize') else dict(existing)
                ip_dict = ip_data.dict(exclude_unset=True)
                
                if self.detect_changes(ip_dict, existing_dict):
                    if mode != SyncMode.DRY_RUN:
                        updated = self.netbox.update_ip_address(existing.id, ip_dict)
                        if updated:
                            self.stats.ip_addresses_updated += 1
                            self.logger.info("IP address updated", address=ip_data.address)
                        return updated is not None
                    else:
                        self.stats.ip_addresses_updated += 1
                        self.logger.info("[DRY RUN] Would update IP address", address=ip_data.address)
                return True
            else:
                if mode != SyncMode.DRY_RUN:
                    created = self.netbox.create_ip_address(ip_dict)
                    if created:
                        self.stats.ip_addresses_created += 1
                        self.logger.info("IP address created", address=ip_data.address)
                    return created is not None
                else:
                    self.stats.ip_addresses_created += 1
                    self.logger.info("[DRY RUN] Would create IP address", address=ip_data.address)
                return True
                
        except Exception as e:
            error_msg = f"Failed to sync IP address {ip_data.address}: {str(e)}"
            self.stats.errors.append(error_msg)
            self.logger.error("IP address sync failed", address=ip_data.address, error=str(e))
            return False
    
    async def sync_batch(self, 
                        devices: List[Device], 
                        mode: SyncMode = SyncMode.FULL,
                        conflict_resolution: ConflictResolution = ConflictResolution.MERGE) -> SyncStatistics:
        """Sync batch of devices with performance optimization"""
        self.stats = SyncStatistics()
        self.stats.start_time = datetime.now()
        
        self.logger.info("Starting batch sync", 
                        device_count=len(devices), 
                        mode=mode.value,
                        conflict_resolution=conflict_resolution.value)
        
        # Build sync cache for performance
        if mode != SyncMode.DRY_RUN:
            await self.build_sync_cache()
        
        # Process devices concurrently
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def sync_with_semaphore(device: Device):
            async with semaphore:
                return await self.sync_device(device, mode)
        
        # Execute sync tasks
        tasks = [sync_with_semaphore(device) for device in devices]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                self.stats.devices_failed += 1
                error_msg = f"Sync task failed: {str(result)}"
                self.stats.errors.append(error_msg)
                self.logger.error("Sync task exception", error=str(result))
        
        self.stats.end_time = datetime.now()
        
        self.logger.info("Batch sync completed", 
                        duration=self.stats.duration,
                        created=self.stats.devices_created,
                        updated=self.stats.devices_updated,
                        skipped=self.stats.devices_skipped,
                        failed=self.stats.devices_failed)
        
        return self.stats
    
    async def build_sync_cache(self):
        """Build cache of existing NetBox objects for performance"""
        self.logger.info("Building sync cache...")
        try:
            # Cache devices
            devices = self.netbox.get_all_devices()
            for device in devices:
                device_dict = device.serialize() if hasattr(device, 'serialize') else dict(device)
                self.sync_cache[f"device_{device_dict['name']}"] = device_dict
            
            # Cache IP addresses
            ip_addresses = self.netbox.get_all_ip_addresses()
            for ip in ip_addresses:
                ip_dict = ip.serialize() if hasattr(ip, 'serialize') else dict(ip)
                self.sync_cache[f"ip_{ip_dict['address']}"] = ip_dict
            
            self.logger.info("Sync cache built", 
                           devices=len([k for k in self.sync_cache.keys() if k.startswith('device_')]),
                           ip_addresses=len([k for k in self.sync_cache.keys() if k.startswith('ip_')]))
        except Exception as e:
            self.logger.error("Failed to build sync cache", error=str(e))
            # Continue without cache
    
    def get_sync_statistics(self) -> Dict:
        """Get current synchronization statistics"""
        return self.stats.to_dict()
    
    def get_conflict_queue(self) -> List[Dict]:
        """Get pending conflicts for manual resolution"""
        return self.conflict_queue.copy()
    
    def resolve_pending_conflict(self, conflict_index: int, resolution: ConflictResolution) -> bool:
        """Resolve a pending conflict by index"""
        try:
            if 0 <= conflict_index < len(self.conflict_queue):
                conflict = self.conflict_queue.pop(conflict_index)
                resolved_data = self.resolve_conflict(
                    conflict['source'], 
                    conflict['netbox'], 
                    resolution
                )
                self.logger.info("Manual conflict resolution applied", 
                               device=conflict['source'].get('name'),
                               resolution=resolution.value)
                return True
            return False
        except Exception as e:
            self.logger.error("Failed to resolve conflict", error=str(e))
            return False
    
    async def cleanup_orphaned_objects(self, source_devices: Set[str], mode: SyncMode = SyncMode.DRY_RUN) -> Dict:
        """Remove objects from NetBox that are no longer in source data"""
        cleanup_stats = {
            'devices_removed': 0,
            'ip_addresses_removed': 0,
            'errors': []
        }
        
        try:
            # Get all NetBox devices
            netbox_devices = self.netbox.get_all_devices()
            
            for device in netbox_devices:
                device_dict = device.serialize() if hasattr(device, 'serialize') else dict(device)
                device_name = device_dict.get('name')
                
                if device_name and device_name not in source_devices:
                    if mode != SyncMode.DRY_RUN:
                        try:
                            self.netbox.delete_device(device_dict['id'])
                            cleanup_stats['devices_removed'] += 1
                            self.logger.info("Orphaned device removed", device=device_name)
                        except Exception as e:
                            error_msg = f"Failed to remove device {device_name}: {str(e)}"
                            cleanup_stats['errors'].append(error_msg)
                            self.logger.error("Device removal failed", device=device_name, error=str(e))
                    else:
                        cleanup_stats['devices_removed'] += 1
                        self.logger.info("[DRY RUN] Would remove orphaned device", device=device_name)
        
        except Exception as e:
            error_msg = f"Cleanup operation failed: {str(e)}"
            cleanup_stats['errors'].append(error_msg)
            self.logger.error("Cleanup failed", error=str(e))
        
        return cleanup_stats


class AdvancedSyncEngine:
    """Enhanced synchronization engine with conflict resolution"""
    
    def __init__(self, netbox_client: NetBoxClient, config: Dict):
        self.netbox = netbox_client
        self.config = config
        self.logger = structlog.get_logger(__name__)
        
        # Caches for performance
        self.device_cache = {}
        self.device_type_cache = {}
        self.device_role_cache = {}
        self.site_cache = {}
        self.ip_cache = {}
        
        # Conflict tracking
        self.conflicts = []
        self.conflict_resolution_rules = self.load_conflict_rules()
        
        # Sync statistics
        self.stats = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'conflicts': 0
        }
    
    def load_conflict_rules(self) -> Dict:
        """Load conflict resolution rules from configuration"""
        default_rules = {
            ConflictType.FIELD_MISMATCH: "prefer_source",
            ConflictType.DUPLICATE_NAME: "append_suffix",
            ConflictType.DUPLICATE_IP: "prefer_newer",
            ConflictType.MISSING_DEPENDENCY: "create_dependency",
            ConflictType.TYPE_MISMATCH: "prefer_existing",
            ConflictType.ROLE_MISMATCH: "prefer_source"
        }
        
        # Override with config if available
        config_rules = self.config.get("sync", {}).get("conflict_resolution", {})
        default_rules.update(config_rules)
        
        return default_rules
    
    async def build_caches(self):
        """Build caches of existing NetBox objects for performance"""
        self.logger.info("Building sync caches...")
        
        try:
            # Cache devices
            devices = list(self.netbox.get_all_devices())
            for device in devices:
                device_dict = device.serialize() if hasattr(device, 'serialize') else dict(device)
                self.device_cache[device_dict['name']] = device_dict
            self.logger.info(f"Cached {len(self.device_cache)} devices")
            
            # Cache IP addresses  
            ip_addresses = list(self.netbox.get_all_ip_addresses())
            for ip in ip_addresses:
                ip_dict = ip.serialize() if hasattr(ip, 'serialize') else dict(ip)
                self.ip_cache[ip_dict['address']] = ip_dict
            self.logger.info(f"Cached {len(self.ip_cache)} IP addresses")
            
        except Exception as e:
            self.logger.error(f"Failed to build caches: {e}")
            raise
    
    async def sync_devices_batch(self, 
                               source_devices: List[Device], 
                               source_name: str,
                               dry_run: bool = False) -> List[SyncResult]:
        """Sync a batch of devices from a single source"""
        
        self.logger.info(f"Starting batch sync of {len(source_devices)} devices from {source_name}")
        
        # Build caches if needed
        if not self.device_cache:
            await self.build_caches()
        
        # Process devices
        results = []
        
        # Phase 1: Validate and prepare devices
        validated_devices = []
        for device in source_devices:
            try:
                validation_result = await self.validate_device(device, source_name)
                if validation_result.success:
                    validated_devices.append(device)
                    results.append(validation_result)
                else:
                    results.append(validation_result)
                    
            except Exception as e:
                self.logger.error(f"Validation failed for {device.name}: {e}")
                results.append(SyncResult(
                    action=SyncAction.SKIP,
                    device_name=device.name,
                    success=False,
                    error=str(e)
                ))
        
        # Phase 2: Detect conflicts and plan actions
        sync_plan = await self.create_sync_plan(validated_devices, source_name)
        
        # Phase 3: Execute sync plan
        if not dry_run:
            execution_results = await self.execute_sync_plan(sync_plan, validated_devices)
            results.extend(execution_results)
        else:
            self.logger.info(f"DRY RUN: Would sync {len(sync_plan)} devices")
            for device_name, action in sync_plan.items():
                results.append(SyncResult(
                    action=action,
                    device_name=device_name,
                    success=True,
                    metadata={"dry_run": True}
                ))
        
        # Update statistics
        self.update_stats(results)
        
        return results
    
    async def validate_device(self, device: Device, source_name: str) -> SyncResult:
        """Validate a device before synchronization"""
        
        # Check required fields
        if not device.name:
            return SyncResult(
                action=SyncAction.SKIP,
                device_name="unnamed",
                success=False,
                error="Device name is required"
            )
        
        # Validate device name format
        if not self.is_valid_device_name(device.name):
            return SyncResult(
                action=SyncAction.SKIP,
                device_name=device.name,
                success=False,
                error=f"Invalid device name format: {device.name}"
            )
        
        # Check for IP address format
        if hasattr(device, 'primary_ip4') and device.primary_ip4 and not self.is_valid_ip(device.primary_ip4):
            return SyncResult(
                action=SyncAction.SKIP,
                device_name=device.name,
                success=False,
                error=f"Invalid IP address: {device.primary_ip4}"
            )
        
        return SyncResult(
            action=SyncAction.CREATE,  # Will be determined later
            device_name=device.name,
            success=True
        )
    
    def is_valid_device_name(self, name: str) -> bool:
        """Check if device name is valid for NetBox"""
        import re
        # NetBox device name requirements: alphanumeric, hyphens, underscores
        pattern = r'^[a-zA-Z0-9._-]+$'
        return bool(re.match(pattern, name)) and len(name) <= 64
    
    def is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    async def create_sync_plan(self, devices: List[Device], source_name: str) -> Dict[str, SyncAction]:
        """Create synchronization plan with conflict detection"""
        
        sync_plan = {}
        
        for device in devices:
            action = await self.determine_sync_action(device, source_name)
            sync_plan[device.name] = action
        
        return sync_plan
    
    async def determine_sync_action(self, device: Device, source_name: str) -> SyncAction:
        """Determine what action to take for a device"""
        
        existing_device = self.device_cache.get(device.name)
        
        if not existing_device:
            # Check for conflicts with IP address
            if hasattr(device, 'primary_ip4') and device.primary_ip4 and device.primary_ip4 in self.ip_cache:
                conflict = SyncConflict(
                    conflict_type=ConflictType.DUPLICATE_IP,
                    source_data=device.dict(),
                    netbox_data=self.ip_cache[device.primary_ip4],
                    device_name=device.name
                )
                
                resolution = await self.resolve_conflict(conflict)
                if resolution == "skip":
                    return SyncAction.SKIP
                elif resolution == "create_with_suffix":
                    # Modify device name
                    device.name = f"{device.name}-{source_name}"
            
            return SyncAction.CREATE
        
        else:
            # Device exists - check if update is needed
            changes = self.detect_changes(device, existing_device)
            
            if changes:
                # Check for conflicts
                conflicts = self.detect_conflicts(device, existing_device, changes)
                
                if conflicts:
                    # Resolve conflicts
                    for conflict in conflicts:
                        resolution = await self.resolve_conflict(conflict)
                        if resolution == "skip":
                            return SyncAction.SKIP
                
                return SyncAction.UPDATE
            else:
                return SyncAction.SKIP
    
    def detect_changes(self, source_device: Device, existing_device: Dict) -> List[str]:
        """Detect changes between source and existing device"""
        changes = []
        
        source_dict = source_device.dict()
        
        # Compare key fields
        comparable_fields = [
            'device_type', 'device_role', 'site', 'platform',
            'primary_ip4', 'serial', 'custom_fields'
        ]
        
        for field in comparable_fields:
            source_value = source_dict.get(field)
            existing_value = existing_device.get(field)
            
            # Handle nested objects (device_type, device_role, site)
            if isinstance(source_value, dict) and isinstance(existing_value, dict):
                if not self.compare_nested_objects(source_value, existing_value):
                    changes.append(field)
            elif source_value != existing_value:
                changes.append(field)
        
        return changes
    
    def compare_nested_objects(self, source_obj: Dict, existing_obj: Dict) -> bool:
        """Compare nested objects like device_type, device_role"""
        
        # Compare by name or slug if available
        for key in ['name', 'slug', 'model']:
            if key in source_obj and key in existing_obj:
                if source_obj[key] != existing_obj[key]:
                    return False
        
        return True
    
    def detect_conflicts(self, source_device: Device, existing_device: Dict, changes: List[str]) -> List[SyncConflict]:
        """Detect conflicts in changed fields"""
        conflicts = []
        
        source_dict = source_device.dict()
        
        for field in changes:
            # Determine conflict type
            conflict_type = ConflictType.FIELD_MISMATCH
            
            if field == 'device_type':
                conflict_type = ConflictType.TYPE_MISMATCH
            elif field == 'device_role':
                conflict_type = ConflictType.ROLE_MISMATCH
            elif field == 'primary_ip4':
                conflict_type = ConflictType.DUPLICATE_IP
            
            conflict = SyncConflict(
                conflict_type=conflict_type,
                source_data=source_dict,
                netbox_data=existing_device,
                device_name=source_device.name,
                field_name=field
            )
            
            conflicts.append(conflict)
        
        return conflicts
    
    async def resolve_conflict(self, conflict: SyncConflict) -> str:
        """Resolve a synchronization conflict"""
        
        rule = self.conflict_resolution_rules.get(conflict.conflict_type, "prefer_existing")
        
        if rule == "prefer_source":
            return "update"
        elif rule == "prefer_existing":
            return "skip"
        elif rule == "prefer_newer":
            # Compare discovery timestamps if available
            source_timestamp = conflict.source_data.get("custom_fields", {}).get("discovery_timestamp")
            netbox_timestamp = conflict.netbox_data.get("last_updated")
            
            if source_timestamp and netbox_timestamp:
                if source_timestamp > netbox_timestamp:
                    return "update"
            return "skip"
        elif rule == "append_suffix":
            return "create_with_suffix"
        elif rule == "create_dependency":
            # Create missing dependencies (device types, roles, sites)
            await self.create_dependencies(conflict.source_data)
            return "update"
        elif rule == "manual":
            # Add to manual review queue
            self.conflicts.append(conflict)
            return "skip"
        
        return "skip"
    
    async def create_dependencies(self, device_data: Dict):
        """Create missing dependencies like device types, roles, sites"""
        
        # Create device type if needed
        device_type = device_data.get("device_type", {})
        if device_type:
            await self.ensure_device_type(device_type)
        
        # Create device role if needed
        device_role = device_data.get("device_role", {})
        if device_role:
            await self.ensure_device_role(device_role)
        
        # Create site if needed
        site = device_data.get("site", {})
        if site:
            await self.ensure_site(site)
    
    async def ensure_device_type(self, device_type_data: Dict):
        """Ensure device type exists in NetBox"""
        manufacturer = device_type_data.get("manufacturer")
        model = device_type_data.get("model")
        
        if not manufacturer or not model:
            return
        
        key = f"{manufacturer}-{model}"
        
        if key not in self.device_type_cache:
            try:
                # For now, just log - would need NetBox client methods
                self.logger.info(f"Would create device type: {manufacturer} {model}")
                
            except Exception as e:
                self.logger.error(f"Failed to create device type {key}: {e}")
    
    async def ensure_device_role(self, device_role_data: Dict):
        """Ensure device role exists in NetBox"""
        name = device_role_data.get("name")
        
        if not name:
            return
        
        if name not in self.device_role_cache:
            try:
                # For now, just log - would need NetBox client methods
                self.logger.info(f"Would create device role: {name}")
                
            except Exception as e:
                self.logger.error(f"Failed to create device role {name}: {e}")
    
    async def ensure_site(self, site_data: Dict):
        """Ensure site exists in NetBox"""
        name = site_data.get("name")

        if not name:
            return

        if name not in self.site_cache:
            try:
                # For now, just log - would need NetBox client methods
                self.logger.info(f"Would create site: {name}")

            except Exception as e:
                self.logger.error(f"Failed to create site {name}: {e}")

    async def ensure_site_exists(self, site_data: Dict) -> int:
        """Ensure site exists in NetBox and return its ID"""
        slug = site_data.get("slug")
        name = site_data.get("name")

        # Sanitize slug - replace dots and other invalid chars with hyphens
        slug = slug.replace(".", "-").replace("_", "-")
        # Ensure slug only contains valid characters
        slug = "".join(c if c.isalnum() or c == "-" else "-" for c in slug)

        # Try to find existing site by slug
        existing_site = self.netbox.get_site(slug=slug)
        if existing_site:
            self.logger.debug(f"Found existing site: {name} (ID: {existing_site.id})")
            return existing_site.id

        # Create new site
        site_payload = {
            "name": name,
            "slug": slug,
            "description": site_data.get("description", "")
        }

        created_site = self.netbox.create_site(site_payload)
        if created_site and hasattr(created_site, 'id'):
            self.logger.info(f"Created site: {name} (ID: {created_site.id})")
            return created_site.id

        raise Exception(f"Failed to create or find site: {name}")

    async def ensure_device_role_exists(self, role_data: Dict) -> int:
        """Ensure device role exists in NetBox and return its ID"""
        name = role_data.get("name")
        color = role_data.get("color", "9e9e9e")

        # Use NetBoxClient's get_or_create_device_role method
        existing_role = self.netbox.get_or_create_device_role(
            name=name,
            color=color,
            vm_role=role_data.get("vm_role", False),
            description=role_data.get("description", "")
        )

        if existing_role and hasattr(existing_role, 'id'):
            self.logger.debug(f"Device role ready: {name} (ID: {existing_role.id})")
            return existing_role.id

        raise Exception(f"Failed to create or find device role: {name}")

    async def ensure_device_type_exists(self, type_data: Dict) -> int:
        """Ensure device type exists in NetBox and return its ID"""
        model = type_data.get("model")
        manufacturer_name = type_data.get("manufacturer", "Generic")

        # Use NetBoxClient's get_or_create_device_type method
        device_type = self.netbox.get_or_create_device_type(
            manufacturer=manufacturer_name,
            model=model,
            u_height=type_data.get("u_height", 1.0),
            is_full_depth=type_data.get("is_full_depth", True)
        )

        if device_type and hasattr(device_type, 'id'):
            self.logger.debug(f"Device type ready: {model} (ID: {device_type.id})")
            return device_type.id

        raise Exception(f"Failed to create or find device type: {model}")

    async def ensure_manufacturer_exists(self, manufacturer_name: str) -> int:
        """Ensure manufacturer exists in NetBox and return its ID"""
        if not manufacturer_name:
            manufacturer_name = "Generic"

        # Use NetBoxClient's get_or_create_manufacturer method
        manufacturer = self.netbox.get_or_create_manufacturer(manufacturer_name)

        if manufacturer and hasattr(manufacturer, 'id'):
            self.logger.debug(f"Manufacturer ready: {manufacturer_name} (ID: {manufacturer.id})")
            return manufacturer.id

        raise Exception(f"Failed to create or find manufacturer: {manufacturer_name}")

    async def execute_sync_plan(self, sync_plan: Dict[str, SyncAction], devices: List[Device]) -> List[SyncResult]:
        """Execute the synchronization plan"""
        
        results = []
        device_dict = {device.name: device for device in devices}
        
        for device_name, action in sync_plan.items():
            device = device_dict.get(device_name)
            if not device:
                continue
                
            try:
                if action == SyncAction.CREATE:
                    result = await self.create_single_device(device)
                    results.append(result)
                elif action == SyncAction.UPDATE:
                    result = await self.update_single_device(device)
                    results.append(result)
                elif action == SyncAction.SKIP:
                    results.append(SyncResult(
                        action=SyncAction.SKIP,
                        device_name=device_name,
                        success=True
                    ))
                    
            except Exception as e:
                results.append(SyncResult(
                    action=action,
                    device_name=device_name,
                    success=False,
                    error=str(e)
                ))
        
        return results
    
    async def create_single_device(self, device: Device) -> SyncResult:
        """Create a single device"""
        try:
            device_dict = device.dict(exclude_unset=True)

            # Log what we're trying to create
            self.logger.info(f"Attempting to create device: {device.name}",
                           device_type=device_dict.get('device_type'),
                           site=device_dict.get('site'),
                           role=device_dict.get('device_role'),
                           device_data=device_dict)

            # Step 1: Ensure dependencies exist and get their IDs
            # Handle site
            site_data = device_dict.get('site')
            if isinstance(site_data, dict):
                site_id = await self.ensure_site_exists(site_data)
                device_dict['site'] = site_id
            elif not site_data:
                # Use default site if none provided
                device_dict['site'] = await self.ensure_site_exists({"name": "Default", "slug": "default"})

            # Handle device_role
            role_data = device_dict.get('device_role')
            if isinstance(role_data, dict):
                role_id = await self.ensure_device_role_exists(role_data)
                device_dict['device_role'] = role_id
            elif not role_data:
                # Use default role if none provided
                device_dict['device_role'] = await self.ensure_device_role_exists({"name": "Server", "slug": "server"})

            # Handle device_type (which includes manufacturer)
            type_data = device_dict.get('device_type')
            if isinstance(type_data, dict):
                type_id = await self.ensure_device_type_exists(type_data)
                device_dict['device_type'] = type_id
            elif not type_data:
                # Use default device type if none provided
                device_dict['device_type'] = await self.ensure_device_type_exists({
                    "manufacturer": "Generic",
                    "model": "Generic Device",
                    "slug": "generic-device"
                })

            # Handle platform - convert string to None (or look up later if needed)
            if isinstance(device_dict.get('platform'), str):
                # For now, remove platform strings - they need to be platform IDs
                device_dict.pop('platform', None)

            # Step 2: Rename device_role to role for NetBox API
            if 'device_role' in device_dict:
                device_dict['role'] = device_dict.pop('device_role')

            # Step 2.5: Remove custom_fields for now (they need to be defined in NetBox first)
            device_dict.pop('custom_fields', None)

            # Step 3: Create device in NetBox with resolved IDs
            self.logger.info(f"Creating device with resolved IDs: {device.name}",
                           device_type_id=device_dict.get('device_type'),
                           site_id=device_dict.get('site'),
                           role_id=device_dict.get('role'))

            # NetBoxClient.create_device() expects a dict, not a Pydantic model
            created_device = self.netbox.create_device(device_dict)

            if created_device:
                self.logger.info(f"Created device: {device.name}", device_id=created_device.id)
                return SyncResult(
                    action=SyncAction.CREATE,
                    device_name=device.name,
                    success=True,
                    metadata={"device_id": created_device.id}
                )
            else:
                self.logger.error(f"NetBox API returned None for device: {device.name}", device_data=device_dict)
                return SyncResult(
                    action=SyncAction.CREATE,
                    device_name=device.name,
                    success=False,
                    error="Failed to create device in NetBox - API returned None"
                )

        except Exception as e:
            self.logger.error(f"Exception creating device: {device.name}", error=str(e), error_type=type(e).__name__)
            return SyncResult(
                action=SyncAction.CREATE,
                device_name=device.name,
                success=False,
                error=str(e)
            )
    
    async def update_single_device(self, device: Device) -> SyncResult:
        """Update a single device"""
        try:
            # Find existing device in cache
            existing_device = self.device_cache.get(device.name.lower())

            if not existing_device:
                return SyncResult(
                    action=SyncAction.UPDATE,
                    device_name=device.name,
                    success=False,
                    error="Device not found in NetBox"
                )

            # Update device in NetBox
            device_dict = device.dict(exclude_unset=True)
            updated_device = self.netbox.update_device(existing_device.id, device_dict)

            if updated_device:
                self.logger.info(f"Updated device: {device.name}", device_id=existing_device.id)
                return SyncResult(
                    action=SyncAction.UPDATE,
                    device_name=device.name,
                    success=True,
                    metadata={"device_id": existing_device.id}
                )
            else:
                return SyncResult(
                    action=SyncAction.UPDATE,
                    device_name=device.name,
                    success=False,
                    error="Failed to update device in NetBox"
                )

        except Exception as e:
            return SyncResult(
                action=SyncAction.UPDATE,
                device_name=device.name,
                success=False,
                error=str(e)
            )
    
    def update_stats(self, results: List[SyncResult]):
        """Update synchronization statistics"""
        for result in results:
            if result.success:
                if result.action == SyncAction.CREATE:
                    self.stats['created'] += 1
                elif result.action == SyncAction.UPDATE:
                    self.stats['updated'] += 1
                elif result.action == SyncAction.SKIP:
                    self.stats['skipped'] += 1
            else:
                self.stats['failed'] += 1
            
            if result.conflicts:
                self.stats['conflicts'] += len(result.conflicts)
    
    def get_sync_statistics(self) -> Dict:
        """Get synchronization statistics"""
        return self.stats.copy()
    
    def get_unresolved_conflicts(self) -> List[SyncConflict]:
        """Get list of unresolved conflicts"""
        return self.conflicts.copy()
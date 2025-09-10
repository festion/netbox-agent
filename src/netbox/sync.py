"""NetBox Synchronization Engine"""

import asyncio
import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Set
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
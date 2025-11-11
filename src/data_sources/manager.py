from typing import Dict, List, Any, Optional, Set, Tuple
import asyncio
import hashlib
import time
from collections import defaultdict
from src.data_sources.home_assistant import HomeAssistantDataSource, HomeAssistantDataSourceConfig
from src.data_sources.network_scanner import NetworkScannerDataSource, NetworkScannerConfig
from src.data_sources.filesystem import FilesystemDataSource, FilesystemDataSourceConfig
from src.data_sources.proxmox import ProxmoxDataSource, ProxmoxDataSourceConfig
from src.data_sources.truenas import TrueNASDataSource, TrueNASDataSourceConfig
from src.data_sources.base import DataSource, DiscoveryResult, DataSourceType
from src.netbox.models import Device


class DataSourceManager:
    """Manages all data sources and handles device deduplication"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.sources: Dict[str, DataSource] = {}
        self.last_discovery_results: Dict[str, DiscoveryResult] = {}
        self.deduplication_enabled = config.get("deduplication", {}).get("enabled", True)
        self.deduplication_strategy = config.get("deduplication", {}).get("strategy", "merge")
        self._initialize_sources()
    
    def _initialize_sources(self):
        """Initialize data sources based on configuration"""
        
        # Home Assistant
        if self.config.get("data_sources", {}).get("home_assistant", {}).get("enabled"):
            try:
                ha_config = HomeAssistantDataSourceConfig(**self.config.get("data_sources", {}).get("home_assistant", {}))
                self.sources["home_assistant"] = HomeAssistantDataSource(ha_config)
                print("Initialized Home Assistant data source")
            except Exception as e:
                print(f"Failed to initialize Home Assistant data source: {e}")
        
        # Network Scanner
        if self.config.get("data_sources", {}).get("network_scanner", {}).get("enabled"):
            try:
                scanner_config = NetworkScannerConfig(**self.config.get("data_sources", {}).get("network_scanner", {}))
                self.sources["network_scanner"] = NetworkScannerDataSource(scanner_config)
                print("Initialized Network Scanner data source")
            except Exception as e:
                print(f"Failed to initialize Network Scanner data source: {e}")
        
        # Filesystem
        if self.config.get("data_sources", {}).get("filesystem", {}).get("enabled"):
            try:
                fs_config = FilesystemDataSourceConfig(**self.config.get("data_sources", {}).get("filesystem", {}))
                self.sources["filesystem"] = FilesystemDataSource(fs_config)
                print("Initialized Filesystem data source")
            except Exception as e:
                print(f"Failed to initialize Filesystem data source: {e}")
        
        # Proxmox
        if self.config.get("data_sources", {}).get("proxmox", {}).get("enabled"):
            try:
                proxmox_config = ProxmoxDataSourceConfig(**self.config.get("data_sources", {}).get("proxmox", {}))
                self.sources["proxmox"] = ProxmoxDataSource(proxmox_config)
                print("Initialized Proxmox data source")
            except Exception as e:
                print(f"Failed to initialize Proxmox data source: {e}")

        # TrueNAS
        if self.config.get("data_sources", {}).get("truenas", {}).get("enabled"):
            try:
                truenas_config = TrueNASDataSourceConfig(**self.config.get("data_sources", {}).get("truenas", {}))
                self.sources["truenas"] = TrueNASDataSource(truenas_config)
                print("Initialized TrueNAS data source")
            except Exception as e:
                print(f"Failed to initialize TrueNAS data source: {e}")

        print(f"Data source manager initialized with {len(self.sources)} sources: {list(self.sources.keys())}")
    
    def _generate_device_signature(self, device: Device) -> str:
        """Generate a unique signature for device deduplication"""
        # Use multiple fields to create a signature for matching
        signature_parts = []
        
        # Primary identifiers (most reliable)
        if hasattr(device, 'primary_ip4') and device.primary_ip4:
            signature_parts.append(f"ip:{device.primary_ip4}")
        
        # MAC address from custom fields if available
        if hasattr(device, 'custom_fields') and device.custom_fields:
            for field, value in device.custom_fields.items():
                if 'mac' in field.lower() and value:
                    signature_parts.append(f"mac:{value.lower().replace(':', '').replace('-', '')}")
        
        # Device name (normalized)
        if device.name:
            normalized_name = device.name.lower().replace('-', '').replace('_', '').replace(' ', '')
            signature_parts.append(f"name:{normalized_name}")
        
        # Serial number if available
        if hasattr(device, 'serial') and device.serial:
            signature_parts.append(f"serial:{device.serial}")
        
        # Create hash of all signature parts
        signature_string = "|".join(sorted(signature_parts))
        return hashlib.md5(signature_string.encode()).hexdigest()
    
    def _deduplicate_devices(self, discovery_results: Dict[str, DiscoveryResult]) -> List[Device]:
        """Deduplicate devices across all discovery results"""
        if not self.deduplication_enabled:
            # If deduplication is disabled, just return all devices
            all_devices = []
            for result in discovery_results.values():
                all_devices.extend(result.devices)
            return all_devices
        
        device_groups: Dict[str, List[Tuple[Device, str]]] = defaultdict(list)
        
        # Group devices by signature
        for source_name, result in discovery_results.items():
            if source_name.startswith("_"):  # Skip internal results
                continue
            for device in result.devices:
                signature = self._generate_device_signature(device)
                device_groups[signature].append((device, source_name))
        
        deduplicated_devices = []
        
        for signature, device_list in device_groups.items():
            if len(device_list) == 1:
                # No duplicates, keep as is
                device, source_name = device_list[0]
                deduplicated_devices.append(device)
            else:
                # Handle duplicates based on strategy
                merged_device = self._merge_duplicate_devices(device_list)
                deduplicated_devices.append(merged_device)
        
        return deduplicated_devices
    
    def _merge_duplicate_devices(self, device_list: List[Tuple[Device, str]]) -> Device:
        """Merge duplicate devices from multiple sources"""
        if self.deduplication_strategy == "priority":
            return self._merge_by_priority(device_list)
        elif self.deduplication_strategy == "merge":
            return self._merge_by_combining(device_list)
        else:
            # Default to first device
            return device_list[0][0]
    
    def _merge_by_priority(self, device_list: List[Tuple[Device, str]]) -> Device:
        """Merge devices by source priority"""
        # Define source priority (higher number = higher priority)
        source_priority = {
            "network_scanner": 3,  # Most reliable for network info
            "filesystem": 2,       # Good for static config
            "home_assistant": 1    # Good for IoT devices but less network detail
        }
        
        # Sort by priority (highest first)
        sorted_devices = sorted(device_list, 
                              key=lambda x: source_priority.get(x[1], 0), 
                              reverse=True)
        
        primary_device, primary_source = sorted_devices[0]
        
        # Enhance primary device with additional info from other sources
        for device, source in sorted_devices[1:]:
            primary_device = self._enhance_device_info(primary_device, device, primary_source, source)
        
        return primary_device
    
    def _merge_by_combining(self, device_list: List[Tuple[Device, str]]) -> Device:
        """Merge devices by combining the best information from each"""
        base_device = device_list[0][0]
        
        # Combine information from all devices
        for device, source in device_list[1:]:
            base_device = self._enhance_device_info(base_device, device, "combined", source)
        
        return base_device
    
    def _enhance_device_info(self, primary: Device, secondary: Device, 
                           primary_source: str, secondary_source: str) -> Device:
        """Enhance primary device with information from secondary device"""
        enhanced = primary.model_copy(deep=True)
        
        # Enhance device type information
        if not enhanced.device_type.get("manufacturer") and secondary.device_type.get("manufacturer"):
            enhanced.device_type["manufacturer"] = secondary.device_type["manufacturer"]
        
        if not enhanced.device_type.get("model") and secondary.device_type.get("model"):
            enhanced.device_type["model"] = secondary.device_type["model"]
        
        # Enhance IP information (prefer network scanner for accuracy)
        if secondary_source == "network_scanner" and secondary.primary_ip4:
            enhanced.primary_ip4 = secondary.primary_ip4
        elif not enhanced.primary_ip4 and secondary.primary_ip4:
            enhanced.primary_ip4 = secondary.primary_ip4
        
        # Combine custom fields
        if hasattr(secondary, 'custom_fields') and secondary.custom_fields:
            if not hasattr(enhanced, 'custom_fields') or not enhanced.custom_fields:
                enhanced.custom_fields = {}
            
            for key, value in secondary.custom_fields.items():
                if key not in enhanced.custom_fields or not enhanced.custom_fields[key]:
                    enhanced.custom_fields[key] = value
        
        # Add source information
        if not hasattr(enhanced, 'custom_fields') or not enhanced.custom_fields:
            enhanced.custom_fields = {}
        
        enhanced.custom_fields["discovered_sources"] = enhanced.custom_fields.get(
            "discovered_sources", f"{primary_source}") + f",{secondary_source}"
        
        return enhanced
    
    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all data sources"""
        print("Connecting to all data sources")
        
        results = {}
        tasks = []
        
        for name, source in self.sources.items():
            tasks.append(self._connect_to_source(name, source))
        
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (name, source) in enumerate(self.sources.items()):
            result = completed_tasks[i]
            if isinstance(result, Exception):
                print(f"Failed to connect to {name}: {result}")
                results[name] = False
            else:
                results[name] = result
        
        successful_connections = sum(1 for v in results.values() if v)
        print(f"Connected to {successful_connections}/{len(self.sources)} data sources")
        
        return results
    
    async def _connect_to_source(self, name: str, source: DataSource) -> bool:
        """Connect to a single data source"""
        try:
            print(f"Connecting to {name}")
            result = await source.connect()
            if result:
                print(f"Successfully connected to {name}")
            else:
                print(f"Failed to connect to {name}")
            return result
        except Exception as e:
            print(f"Error connecting to {name}: {e}")
            return False
    
    async def test_all_connections(self) -> Dict[str, bool]:
        """Test connections to all data sources"""
        print("Testing all data source connections")
        
        results = {}
        tasks = []
        
        for name, source in self.sources.items():
            tasks.append(self._test_source_connection(name, source))
        
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (name, source) in enumerate(self.sources.items()):
            result = completed_tasks[i]
            if isinstance(result, Exception):
                print(f"Failed to test connection to {name}: {result}")
                results[name] = False
            else:
                results[name] = result
        
        successful_tests = sum(1 for v in results.values() if v)
        print(f"Connection tests passed for {successful_tests}/{len(self.sources)} data sources")
        
        return results
    
    async def _test_source_connection(self, name: str, source: DataSource) -> bool:
        """Test connection to a single data source"""
        try:
            print(f"Testing connection to {name}")
            result = await source.test_connection()
            if result:
                print(f"Connection test passed for {name}")
            else:
                print(f"Connection test failed for {name}")
            return result
        except Exception as e:
            print(f"Error testing connection to {name}: {e}")
            return False
    
    async def discover_all_devices(self) -> Dict[str, DiscoveryResult]:
        """Discover devices from all data sources with deduplication"""
        print("Starting device discovery from all sources")
        
        results = {}
        tasks = []
        
        for name, source in self.sources.items():
            tasks.append(self._discover_from_source(name, source))
        
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (name, source) in enumerate(self.sources.items()):
            result = completed_tasks[i]
            if isinstance(result, Exception):
                print(f"Discovery failed for {name}: {result}")
                # Create failed discovery result
                failed_result = DiscoveryResult(
                    source_type=source.source_type,
                    source_id=source.source_id
                )
                failed_result.add_error(str(result))
                results[name] = failed_result
            else:
                results[name] = result
        
        # Store results for future reference
        self.last_discovery_results = results
        
        total_devices_before = sum(len(result.devices) for result in results.values() if result.success)
        successful_sources = sum(1 for result in results.values() if result.success)
        
        # Apply deduplication if enabled
        if self.deduplication_enabled:
            deduplicated_devices = self._deduplicate_devices(results)
            print(f"Deduplication: {total_devices_before} devices -> {len(deduplicated_devices)} unique devices")
            
            # Update results with deduplicated devices for summary
            results["_deduplicated"] = DiscoveryResult(
                source_type=DataSourceType.MCP_SERVER,
                source_id="deduplicated",
                devices=deduplicated_devices,
                metadata={
                    "total_before_dedup": total_devices_before,
                    "total_after_dedup": len(deduplicated_devices),
                    "duplicates_removed": total_devices_before - len(deduplicated_devices)
                }
            )
        
        print(f"Discovery completed - {total_devices_before} devices from {successful_sources}/{len(self.sources)} sources")
        
        return results
    
    async def _discover_from_source(self, name: str, source: DataSource) -> DiscoveryResult:
        """Discover devices from a single data source"""
        try:
            print(f"Starting discovery from {name}")
            result = await source.discover()
            
            if result.success:
                print(f"Discovery successful for {name} - found {len(result.devices)} devices in {result.duration:.2f}s")
            else:
                print(f"Discovery failed for {name}: {result.error_message}")
            
            return result
        except Exception as e:
            print(f"Error during discovery from {name}: {e}")
            failed_result = DiscoveryResult(
                source_type=source.source_type,
                source_id=source.source_id
            )
            failed_result.add_error(str(e))
            return failed_result
    
    async def sync_all_sources(self) -> Dict[str, Dict[str, Any]]:
        """Sync devices from all data sources to target system with deduplication"""
        print("Starting sync from all data sources")
        
        # First discover all devices with deduplication
        discovery_results = await self.discover_all_devices()
        
        # Get deduplicated devices if available
        if "_deduplicated" in discovery_results:
            devices_to_sync = discovery_results["_deduplicated"].devices
            print(f"Syncing {len(devices_to_sync)} deduplicated devices")
        else:
            # Fall back to all devices if deduplication is disabled
            devices_to_sync = []
            for result in discovery_results.values():
                if result.success:
                    devices_to_sync.extend(result.devices)
            print(f"Syncing {len(devices_to_sync)} devices (no deduplication)")
        
        # For now, return mock sync results
        # In a real implementation, this would sync to NetBox or other target system
        results = {}
        for source_name in self.sources.keys():
            source_device_count = len(discovery_results.get(source_name, DiscoveryResult(
                source=source_name, success=False, devices=[], statistics={}, duration=0.0
            )).devices)
            
            results[source_name] = {
                "created": source_device_count,  # Mock: assume all are new
                "updated": 0,
                "errors": 0
            }
        
        # Calculate totals
        totals = {
            "created": sum(r.get("created", 0) for r in results.values()),
            "updated": sum(r.get("updated", 0) for r in results.values()),
            "errors": sum(r.get("errors", 0) for r in results.values())
        }
        
        print(f"Sync completed - Created: {totals['created']}, Updated: {totals['updated']}, Errors: {totals['errors']}")
        
        return results
    
    def get_deduplicated_devices(self) -> List[Device]:
        """Get the current list of deduplicated devices"""
        if not self.last_discovery_results:
            return []
        
        if self.deduplication_enabled:
            return self._deduplicate_devices(self.last_discovery_results)
        else:
            all_devices = []
            for result in self.last_discovery_results.values():
                if result.success and not result.source.startswith("_"):
                    all_devices.extend(result.devices)
            return all_devices
    
    def get_deduplication_stats(self) -> Dict[str, Any]:
        """Get statistics about device deduplication"""
        if not self.last_discovery_results:
            return {}
        
        total_devices = sum(len(result.devices) for result in self.last_discovery_results.values() 
                          if result.success and not result.source.startswith("_"))
        
        if self.deduplication_enabled:
            deduplicated_devices = self._deduplicate_devices(self.last_discovery_results)
            duplicates_removed = total_devices - len(deduplicated_devices)
            
            return {
                "enabled": True,
                "strategy": self.deduplication_strategy,
                "total_devices_discovered": total_devices,
                "unique_devices_after_dedup": len(deduplicated_devices),
                "duplicates_removed": duplicates_removed,
                "deduplication_rate": duplicates_removed / total_devices if total_devices > 0 else 0
            }
        else:
            return {
                "enabled": False,
                "total_devices_discovered": total_devices,
                "unique_devices_after_dedup": total_devices,
                "duplicates_removed": 0,
                "deduplication_rate": 0
            }
    
    async def get_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of all data sources and deduplication"""
        summary = {
            "total_sources": len(self.sources),
            "enabled_sources": len(self.sources),  # All sources in manager are enabled
            "last_discovery_time": None,
            "total_devices_discovered": 0,
            "discovery_results": {},
            "deduplication": self.get_deduplication_stats()
        }
        
        if self.last_discovery_results:
            # Filter out the _deduplicated entry for regular summary
            regular_results = {k: v for k, v in self.last_discovery_results.items() if not k.startswith("_")}
            
            summary["total_devices_discovered"] = sum(
                len(result.devices) for result in regular_results.values() if result.success
            )
            summary["discovery_results"] = {
                name: {
                    "success": result.success,
                    "device_count": len(result.devices),
                    "duration": result.duration,
                    "error_message": result.error_message if not result.success else None,
                    "statistics": result.statistics
                }
                for name, result in regular_results.items()
            }
            
            # Add deduplicated summary if available
            if "_deduplicated" in self.last_discovery_results:
                dedup_result = self.last_discovery_results["_deduplicated"]
                summary["deduplicated_devices"] = {
                    "count": len(dedup_result.devices),
                    "statistics": dedup_result.statistics
                }
        
        return summary
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics about all data sources including deduplication"""
        stats = {
            "sources": {},
            "totals": {
                "devices": 0,
                "successful_sources": 0,
                "failed_sources": 0
            },
            "performance": {
                "total_discovery_time": 0.0,
                "average_discovery_time": 0.0
            },
            "deduplication": self.get_deduplication_stats()
        }
        
        if self.last_discovery_results:
            # Filter out the _deduplicated entry for regular stats
            regular_results = {k: v for k, v in self.last_discovery_results.items() if not k.startswith("_")}
            
            for name, result in regular_results.items():
                stats["sources"][name] = {
                    "success": result.success,
                    "device_count": len(result.devices),
                    "duration": result.duration,
                    "statistics": result.statistics,
                    "error_message": result.error_message if not result.success else None
                }
                
                if result.success:
                    stats["totals"]["devices"] += len(result.devices)
                    stats["totals"]["successful_sources"] += 1
                    stats["performance"]["total_discovery_time"] += result.duration
                else:
                    stats["totals"]["failed_sources"] += 1
            
            # Calculate average discovery time
            if stats["totals"]["successful_sources"] > 0:
                stats["performance"]["average_discovery_time"] = (
                    stats["performance"]["total_discovery_time"] / 
                    stats["totals"]["successful_sources"]
                )
        
        return stats
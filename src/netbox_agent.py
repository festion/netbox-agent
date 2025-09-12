#!/usr/bin/env python3
"""
NetBox Agent - Automated NetBox population from various sources using MCP servers

This agent collects data from multiple sources (Home Assistant, network scans,
file systems, etc.) and populates a NetBox instance with discovered infrastructure.
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import asyncio
import schedule

import requests
from pydantic import BaseModel, Field

from src.data_sources.manager import DataSourceManager
from src.data_sources.home_assistant import HomeAssistantDataSourceConfig
from src.data_sources.network_scanner import NetworkScannerConfig  
from src.data_sources.filesystem import FilesystemDataSourceConfig
from src.netbox.sync import AdvancedSyncEngine
from src.netbox.mappings import DataMappingEngine
from src.scheduler.scheduler import AdvancedScheduler, JobPriority
from src.netbox.client import NetBoxClient


class NetBoxConfig(BaseModel):
    """NetBox configuration"""
    url: str
    token: str
    verify_ssl: bool = True


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    file: str = "logs/netbox-agent.log"
    max_size: str = "10MB"
    backup_count: int = 5


class SyncConfig(BaseModel):
    """Synchronization configuration"""
    dry_run: bool = False
    full_sync_interval: int = 86400
    incremental_sync_interval: int = 3600
    batch_size: int = 50
    max_workers: int = 5
    conflict_resolution: Dict[str, str] = {
        "field_mismatch": "prefer_source",
        "duplicate_name": "append_suffix", 
        "duplicate_ip": "prefer_newer",
        "missing_dependency": "create_dependency",
        "type_mismatch": "prefer_existing",
        "role_mismatch": "prefer_source"
    }


class SchedulerConfig(BaseModel):
    """Scheduler configuration"""
    max_concurrent_jobs: int = 3
    max_completed_jobs: int = 100
    rate_limits: Dict[str, int] = {}
    job_cleanup_hours: int = 24


class AgentConfig(BaseModel):
    """Main agent configuration"""
    netbox: NetBoxConfig
    data_sources: Dict[str, Any]  # Updated to match new structure
    logging: LoggingConfig
    sync: SyncConfig
    scheduler: SchedulerConfig = SchedulerConfig()
    mapping_config_path: str = "config/data-mappings.json"


class NetBoxAgent:
    """Main NetBox Agent class"""
    
    def __init__(self, config_path: str = "config/netbox-agent.json"):
        """Initialize the NetBox Agent"""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize Data Source Manager
        self.data_source_manager = DataSourceManager(self.config.model_dump())
        
        # Initialize NetBox Client
        self.netbox_client = NetBoxClient(
            url=self.config.netbox.url,
            token=self.config.netbox.token,
            verify_ssl=self.config.netbox.verify_ssl
        )
        
        # Initialize Advanced Components
        self.sync_engine = AdvancedSyncEngine(self.netbox_client, self.config.model_dump())
        self.data_mapper = DataMappingEngine(self.load_mapping_config())
        self.scheduler = AdvancedScheduler(self.config.scheduler.model_dump())
        
        # Legacy NetBox API session (for backward compatibility)
        self.netbox_session = requests.Session()
        self.netbox_session.headers.update({
            'Authorization': f'Token {self.config.netbox.token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        if not self.config.netbox.verify_ssl:
            self.netbox_session.verify = False
            
        self.logger.info("NetBox Agent initialized with advanced features")
    
    def _load_config(self) -> AgentConfig:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            return AgentConfig(**config_data)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)
    
    def load_mapping_config(self) -> Dict:
        """Load data mapping configuration"""
        mapping_path = Path(self.config.mapping_config_path)
        if not mapping_path.is_absolute():
            mapping_path = self.config_path.parent / mapping_path
            
        try:
            with open(mapping_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"Mapping config not found at {mapping_path}, using empty config")
            return {}
        except Exception as e:
            self.logger.warning(f"Could not load mapping config: {e}")
            return {}
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config.logging.level.upper())
        
        # Create logs directory if it doesn't exist
        log_file = Path(self.config.logging.file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    async def test_netbox_connection(self) -> bool:
        """Test connection to NetBox"""
        try:
            response = self.netbox_session.get(f"{self.config.netbox.url}/api/")
            response.raise_for_status()
            self.logger.info("NetBox connection successful")
            return True
        except Exception as e:
            self.logger.error(f"NetBox connection failed: {e}")
            return False
    
    async def _sync_device_to_netbox(self, device_data: Dict[str, Any]) -> str:
        """Sync a device to NetBox"""
        try:
            if self.config.sync.dry_run:
                self.logger.info(f"[DRY RUN] Would sync device: {device_data.get('name')}")
                return
            
            # Check if device already exists
            device_name = device_data.get('name')
            search_url = f"{self.config.netbox.url}/api/dcim/devices/?name={device_name}"
            response = self.netbox_session.get(search_url)
            response.raise_for_status()
            
            existing_devices = response.json().get('results', [])
            
            if existing_devices:
                # Update existing device
                device_id = existing_devices[0]['id']
                update_url = f"{self.config.netbox.url}/api/dcim/devices/{device_id}/"
                response = self.netbox_session.patch(update_url, json=device_data)
                response.raise_for_status()
                self.logger.info(f"Updated device: {device_name}")
                return "updated"
            else:
                # Create new device
                create_url = f"{self.config.netbox.url}/api/dcim/devices/"
                response = self.netbox_session.post(create_url, json=device_data)
                response.raise_for_status()
                self.logger.info(f"Created device: {device_name}")
                return "created"
                
        except Exception as e:
            self.logger.error(f"Failed to sync device {device_data.get('name')}: {e}")
            raise
    
    async def sync_from_source(self, source_name: str):
        """Sync data from a specific data source"""
        try:
            if source_name not in self.data_source_manager.sources:
                self.logger.warning(f"Data source '{source_name}' not available")
                return {"created": 0, "updated": 0, "errors": 0}
            
            source = self.data_source_manager.sources[source_name]
            self.logger.info(f"Starting sync from {source.name}")
            
            # Discover devices from the source
            discovery_result = await source.discover()
            
            if not discovery_result.success:
                self.logger.error(f"Discovery failed for {source.name}: {discovery_result.error_message}")
                return {"created": 0, "updated": 0, "errors": 1}
            
            self.logger.info(f"Discovered {len(discovery_result.devices)} devices from {source.name}")
            
            # Sync devices to NetBox
            sync_results = {"created": 0, "updated": 0, "errors": 0}
            
            for device in discovery_result.devices:
                try:
                    result = await self._sync_device_to_netbox(device.model_dump())
                    if result == "created":
                        sync_results["created"] += 1
                    elif result == "updated":
                        sync_results["updated"] += 1
                except Exception as e:
                    self.logger.error(f"Failed to sync device {device.name}: {e}")
                    sync_results["errors"] += 1
            
            self.logger.info(f"{source.name} sync completed: {sync_results}")
            return sync_results
            
        except Exception as e:
            self.logger.error(f"Sync from {source_name} failed: {e}")
            return {"created": 0, "updated": 0, "errors": 1}
    
    async def sync_all_sources(self):
        """Sync data from all enabled data sources"""
        self.logger.info("Starting sync from all data sources")
        
        try:
            # Connect to all data sources first
            connection_results = await self.data_source_manager.connect_all()
            self.logger.info(f"Data source connections: {connection_results}")
            
            # Sync from all sources
            sync_results = await self.data_source_manager.sync_all_sources()
            
            # Log summary
            total_created = sum(result.get("created", 0) for result in sync_results.values())
            total_updated = sum(result.get("updated", 0) for result in sync_results.values())
            total_errors = sum(result.get("errors", 0) for result in sync_results.values())
            
            self.logger.info(f"Sync completed - Created: {total_created}, Updated: {total_updated}, Errors: {total_errors}")
            return sync_results
            
        except Exception as e:
            self.logger.error(f"Sync from all sources failed: {e}")
            return {}
    
    async def get_data_source_summary(self):
        """Get summary of all data sources"""
        try:
            summary = await self.data_source_manager.get_summary()
            return summary
        except Exception as e:
            self.logger.error(f"Failed to get data source summary: {e}")
            return {}
    
    async def perform_full_sync(self):
        """Enhanced full synchronization with advanced features"""
        self.logger.info("Starting advanced full synchronization")
        
        # Test NetBox connection first
        if not await self.test_netbox_connection():
            self.logger.error("Cannot proceed without NetBox connection")
            return
        
        try:
            # Build sync caches for performance
            await self.sync_engine.build_caches()
            
            # Discover devices from all sources
            all_discovered_devices = await self.data_source_manager.discover_all_devices()
            
            # Process each source with advanced sync engine
            sync_results = {}
            
            for source_name, devices in all_discovered_devices.items():
                if not devices:
                    continue
                
                self.logger.info(f"Processing {len(devices)} devices from {source_name}")
                
                # Apply data mappings
                mapped_devices = []
                for device in devices:
                    try:
                        mapped_data = self.data_mapper.apply_mappings(
                            device.model_dump(), 
                            source_name
                        )
                        # Update device with mapped data (simplified for now)
                        mapped_devices.append(device)
                    except Exception as e:
                        self.logger.error(f"Mapping failed for device {device.name}: {e}")
                
                # Synchronize to NetBox using advanced engine
                source_results = await self.sync_engine.sync_devices_batch(
                    mapped_devices,
                    source_name,
                    dry_run=self.config.sync.dry_run
                )
                
                sync_results[source_name] = source_results
            
            # Log summary
            self.log_sync_summary(sync_results)
            
        except Exception as e:
            self.logger.error(f"Full synchronization failed: {e}")
        
        self.logger.info("Advanced full synchronization completed")
    
    async def perform_incremental_sync(self):
        """Perform incremental synchronization"""
        self.logger.info("Starting incremental synchronization")
        
        # For incremental sync, we can implement logic to only sync changed data
        # For now, use the same advanced sync approach but with smaller batches
        try:
            # Build caches for change detection
            await self.sync_engine.build_caches()
            
            # Get only recently changed devices (implementation would depend on sources)
            # For now, sync all but mark as incremental
            await self.sync_all_sources()
            
        except Exception as e:
            self.logger.error(f"Incremental synchronization failed: {e}")
        
        self.logger.info("Incremental synchronization completed")
    
    def log_sync_summary(self, results: Dict):
        """Log synchronization summary"""
        total_stats = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'conflicts': 0
        }
        
        for source_name, source_results in results.items():
            if not source_results:
                continue
                
            source_stats = {
                'created': len([r for r in source_results if r.action.value == 'create' and r.success]),
                'updated': len([r for r in source_results if r.action.value == 'update' and r.success]),
                'skipped': len([r for r in source_results if r.action.value == 'skip']),
                'failed': len([r for r in source_results if not r.success]),
                'conflicts': len([r for r in source_results if r.conflicts])
            }
            
            self.logger.info(f"Sync results for {source_name}: {source_stats}")
            
            for key in total_stats:
                total_stats[key] += source_stats[key]
        
        self.logger.info(f"Total sync results: {total_stats}")
        
        # Log unresolved conflicts
        conflicts = self.sync_engine.get_unresolved_conflicts()
        if conflicts:
            self.logger.warning(f"Unresolved conflicts: {len(conflicts)}")
            for conflict in conflicts[:5]:  # Show first 5
                self.logger.warning(f"Conflict: {conflict.device_name} - {conflict.conflict_type.value}")
    
    async def perform_health_check(self):
        """Perform system health check"""
        try:
            # Check NetBox connection
            netbox_ok = await self.test_netbox_connection()
            
            # Check data source connections
            source_status = await self.data_source_manager.test_all_connections()
            
            # Check scheduler status
            scheduler_stats = self.scheduler.get_scheduler_stats()
            
            # Log health status
            self.logger.info(f"Health check - NetBox: {'OK' if netbox_ok else 'FAIL'}, "
                           f"Sources: {source_status}, Scheduler: {scheduler_stats['is_running']}")
            
            return {
                'netbox': netbox_ok,
                'sources': source_status,
                'scheduler': scheduler_stats
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {'error': str(e)}
    
    def schedule_jobs(self):
        """Schedule synchronization jobs with advanced scheduler"""
        
        # Schedule full sync
        self.scheduler.schedule_recurring_job(
            job_id="full_sync",
            name="Full Synchronization",
            function=self.perform_full_sync,
            interval_seconds=self.config.sync.full_sync_interval,
            priority=JobPriority.NORMAL,
            max_runtime=7200  # 2 hours
        )
        
        # Schedule incremental sync
        self.scheduler.schedule_recurring_job(
            job_id="incremental_sync",
            name="Incremental Synchronization",
            function=self.perform_incremental_sync,
            interval_seconds=self.config.sync.incremental_sync_interval,
            priority=JobPriority.HIGH,
            max_runtime=1800  # 30 minutes
        )
        
        # Schedule health checks
        self.scheduler.schedule_recurring_job(
            job_id="health_check",
            name="System Health Check",
            function=self.perform_health_check,
            interval_seconds=300,  # 5 minutes
            priority=JobPriority.LOW,
            max_runtime=60
        )
        
        # Schedule job cleanup
        self.scheduler.schedule_recurring_job(
            job_id="job_cleanup",
            name="Job History Cleanup",
            function=lambda: self.scheduler.cleanup_old_jobs(self.config.scheduler.job_cleanup_hours),
            interval_seconds=3600,  # 1 hour
            priority=JobPriority.LOW,
            max_runtime=60
        )
        
        self.logger.info("Advanced synchronization jobs scheduled")
    
    async def run(self):
        """Enhanced main run loop"""
        self.logger.info("Starting NetBox Agent with advanced features")
        
        try:
            # Start advanced scheduler
            await self.scheduler.start()
            
            # Test initial connection
            if not await self.test_netbox_connection():
                self.logger.error("Initial NetBox connection test failed")
                return
            
            # Connect to data sources
            self.logger.info("Connecting to data sources...")
            connection_status = await self.data_source_manager.connect_all()
            self.logger.info(f"Data source connection status: {connection_status}")
            
            # Test NetBox client
            if not await self.netbox_client.test_connection():
                self.logger.error("NetBox client connection failed - cannot proceed")
                return
            
            # Perform initial sync
            await self.perform_full_sync()
            
            # Schedule jobs
            self.schedule_jobs()
            
            # Main monitoring loop
            while True:
                # Monitor scheduler
                stats = self.scheduler.get_scheduler_stats()
                self.logger.debug(f"Scheduler stats: {stats}")
                
                # Monitor for failures
                failed_jobs = self.scheduler.get_failed_jobs(limit=5)
                if failed_jobs:
                    self.logger.warning(f"Found {len(failed_jobs)} failed jobs in recent history")
                
                await asyncio.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
        finally:
            # Stop scheduler
            await self.scheduler.stop()
            # Cleanup data sources
            self.logger.info("NetBox Agent stopped")


async def main():
    """Main entry point"""
    agent = NetBoxAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
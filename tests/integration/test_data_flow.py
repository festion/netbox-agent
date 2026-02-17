import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.data_sources.manager import DataSourceManager
from src.netbox.sync import AdvancedSyncEngine

@pytest.mark.integration
class TestDataFlowIntegration:
    """Test data flow from sources through sync to NetBox"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_data_flow(self, test_config, mock_netbox_client):
        """Test complete data flow from discovery to NetBox creation"""
        
        # Create data source manager
        ds_manager = DataSourceManager(test_config["sources"])
        
        # Mock data sources to return test devices
        for source_name, source in ds_manager.sources.items():
            source.discover = AsyncMock(return_value=[
                Mock(
                    name=f"{source_name}-device-1",
                    primary_ip4="192.168.1.100",
                    device_type=Mock(manufacturer="Test", model="Device"),
                    device_role=Mock(name="Test Role"),
                    site=Mock(name="Test Site"),
                    serialize=lambda: {"name": f"{source_name}-device-1"}
                )
            ])
        
        # Create sync engine
        sync_engine = AdvancedSyncEngine(mock_netbox_client, test_config)
        sync_engine.device_cache = {}
        
        # Mock NetBox responses
        mock_netbox_client.api.dcim.devices.create.return_value = [
            Mock(id=1, name="homeassistant-device-1"),
            Mock(id=2, name="network_scan-device-1"), 
            Mock(id=3, name="filesystem-device-1")
        ]
        
        # Execute discovery
        all_devices = await ds_manager.discover_all_devices()
        
        # Verify discovery results
        assert len(all_devices) == 3  # Three sources
        total_devices = sum(len(devices) for devices in all_devices.values())
        assert total_devices == 3  # One device per source
        
        # Execute sync for each source
        all_results = []
        for source_name, devices in all_devices.items():
            results = await sync_engine.sync_devices_batch(devices, source_name, dry_run=False)
            all_results.extend(results)
        
        # Verify sync results
        successful_results = [r for r in all_results if r.success]
        assert len(successful_results) == 3
    
    @pytest.mark.asyncio
    async def test_conflict_detection_and_resolution(self, test_config, mock_netbox_client):
        """Test conflict detection when same device exists in multiple sources"""
        
        # Create data source manager
        ds_manager = DataSourceManager(test_config["sources"])
        
        # Mock sources to return the same device
        shared_device = Mock(
            name="shared-router",
            primary_ip4="192.168.1.1",
            device_type=Mock(manufacturer="Ubiquiti", model="Dream Machine"),
            device_role=Mock(name="Router"),
            site=Mock(name="Main Site"),
            serialize=lambda: {"name": "shared-router"}
        )
        
        for source in ds_manager.sources.values():
            source.discover = AsyncMock(return_value=[shared_device])
        
        # Create sync engine with existing device
        sync_engine = AdvancedSyncEngine(mock_netbox_client, test_config)
        sync_engine.device_cache = {
            "shared-router": {
                "name": "shared-router",
                "device_type": {"manufacturer": "Different", "model": "Model"},
                "primary_ip4": "192.168.1.1"
            }
        }
        
        # Execute discovery and sync
        all_devices = await ds_manager.discover_all_devices()
        
        # Sync first source
        first_source = list(all_devices.keys())[0]
        devices = all_devices[first_source]
        
        results = await sync_engine.sync_devices_batch(devices, first_source, dry_run=True)
        
        # Should detect conflicts
        for result in results:
            if result.conflicts:
                assert len(result.conflicts) > 0
                assert result.conflicts[0].type in [ConflictType.FIELD_MISMATCH, ConflictType.MULTIPLE_SOURCES]
    
    @pytest.mark.asyncio
    async def test_incremental_vs_full_sync(self, test_config, mock_netbox_client):
        """Test difference between incremental and full sync"""
        
        # Mock data source that tracks state
        class MockIncrementalSource:
            def __init__(self):
                self.last_sync = None
                self.devices = [
                    Mock(name="device-1", serialize=lambda: {"name": "device-1"}),
                    Mock(name="device-2", serialize=lambda: {"name": "device-2"})
                ]
            
            async def discover(self, since=None):
                if since:
                    # Incremental - return only new/changed devices
                    return [self.devices[1]]  # Only device-2
                else:
                    # Full sync - return all devices
                    return self.devices
        
        # Create sync engine
        sync_engine = AdvancedSyncEngine(mock_netbox_client, test_config)
        sync_engine.device_cache = {}
        
        source = MockIncrementalSource()
        
        # Full sync
        full_devices = await source.discover()
        full_results = await sync_engine.sync_devices_batch(full_devices, "test", dry_run=True)
        
        # Incremental sync
        incremental_devices = await source.discover(since="2024-01-01")
        incremental_results = await sync_engine.sync_devices_batch(incremental_devices, "test", dry_run=True)
        
        # Verify different result counts
        assert len(full_results) == 2
        assert len(incremental_results) == 1
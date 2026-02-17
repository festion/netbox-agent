import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.netbox.sync import AdvancedSyncEngine, SyncAction, ConflictType
from src.netbox.models import Device
from tests.conftest import create_mock_device

class TestAdvancedSyncEngine:
    
    @pytest.mark.asyncio
    async def test_build_caches(self, sync_engine, mock_netbox_client):
        """Test cache building functionality"""
        # Mock API responses
        mock_devices = [Mock(name="device1", serialize=lambda: {"name": "device1"})]
        mock_netbox_client.api.dcim.devices.all.return_value = mock_devices
        
        mock_device_types = [Mock(manufacturer=Mock(name="Manufacturer"), model="Model", serialize=lambda: {})]
        mock_netbox_client.api.dcim.device_types.all.return_value = mock_device_types
        
        await sync_engine.build_caches()
        
        assert len(sync_engine.device_cache) == 1
        assert "device1" in sync_engine.device_cache
    
    @pytest.mark.asyncio
    async def test_validate_device_success(self, sync_engine):
        """Test successful device validation"""
        device = create_mock_device("valid-device", "192.168.1.100")
        
        result = await sync_engine.validate_device(device, "test_source")
        
        assert result.success == True
        assert result.device_name == "valid-device"
    
    @pytest.mark.asyncio
    async def test_validate_device_invalid_name(self, sync_engine):
        """Test device validation with invalid name"""
        device = create_mock_device("invalid name with spaces!", "192.168.1.100")
        
        result = await sync_engine.validate_device(device, "test_source")
        
        assert result.success == False
        assert "Invalid device name format" in result.error
    
    @pytest.mark.asyncio
    async def test_validate_device_invalid_ip(self, sync_engine):
        """Test device validation with invalid IP"""
        device = create_mock_device("valid-device", "not.an.ip.address")
        
        result = await sync_engine.validate_device(device, "test_source")
        
        assert result.success == False
        assert "Invalid IP address" in result.error
    
    @pytest.mark.asyncio
    async def test_determine_sync_action_create(self, sync_engine):
        """Test sync action determination for new device"""
        device = create_mock_device("new-device")
        
        action = await sync_engine.determine_sync_action(device, "test_source")
        
        assert action == SyncAction.CREATE
    
    @pytest.mark.asyncio
    async def test_determine_sync_action_update(self, sync_engine):
        """Test sync action determination for existing device with changes"""
        device = create_mock_device("existing-device")
        
        # Mock existing device in cache
        sync_engine.device_cache["existing-device"] = {
            "name": "existing-device",
            "device_type": {"model": "Old Model"},  # Different from test device
            "device_role": {"name": "Test Role"},
            "site": {"name": "Test Site"}
        }
        
        action = await sync_engine.determine_sync_action(device, "test_source")
        
        assert action == SyncAction.UPDATE
    
    @pytest.mark.asyncio
    async def test_detect_changes(self, sync_engine):
        """Test change detection between devices"""
        device = create_mock_device("test-device")
        existing_device = {
            "name": "test-device",
            "device_type": {"model": "Different Model"},
            "device_role": {"name": "Test Role"},
            "site": {"name": "Test Site"},
            "primary_ip4": "192.168.1.100"
        }
        
        changes = sync_engine.detect_changes(device, existing_device)
        
        assert "device_type" in changes
    
    @pytest.mark.asyncio
    async def test_sync_devices_batch_dry_run(self, sync_engine):
        """Test batch sync in dry-run mode"""
        devices = [
            create_mock_device("device1"),
            create_mock_device("device2")
        ]
        
        results = await sync_engine.sync_devices_batch(devices, "test_source", dry_run=True)
        
        assert len(results) == 2
        for result in results:
            if result.success:
                assert result.metadata.get("dry_run") == True

@pytest.mark.integration
class TestSyncEngineIntegration:
    """Integration tests for sync engine with real-like scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_sync_workflow(self, sync_engine, mock_netbox_client):
        """Test complete sync workflow"""
        # Prepare test devices
        devices = [
            create_mock_device("router-01", "192.168.1.1"),
            create_mock_device("switch-01", "192.168.1.2")
        ]
        
        # Mock NetBox API calls
        mock_netbox_client.api.dcim.devices.create.return_value = [
            Mock(id=1, name="router-01", serialize=lambda: {"id": 1, "name": "router-01"}),
            Mock(id=2, name="switch-01", serialize=lambda: {"id": 2, "name": "switch-01"})
        ]
        
        # Execute sync
        results = await sync_engine.sync_devices_batch(devices, "test_source", dry_run=False)
        
        # Verify results
        successful_results = [r for r in results if r.success]
        assert len(successful_results) >= 2
        
        # Verify statistics
        stats = sync_engine.get_sync_statistics()
        assert stats["created"] >= 2
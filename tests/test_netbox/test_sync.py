"""Tests for NetBox Synchronization Engine"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.netbox.sync import SyncEngine, SyncMode, ConflictResolution, SyncStatistics
from src.netbox.client import NetBoxClient
from src.netbox.models import Device, DeviceType, DeviceRole, Site


@pytest.fixture
def mock_netbox_client():
    """Mock NetBox client"""
    client = Mock(spec=NetBoxClient)
    
    # Mock device operations
    client.get_device_by_name = Mock(return_value=None)
    client.create_device = Mock(return_value=Mock(id=123))
    client.update_device = Mock(return_value=Mock(id=123))
    client.delete_device = Mock(return_value=True)
    client.get_all_devices = Mock(return_value=[])
    
    # Mock IP operations
    client.get_ip_address = Mock(return_value=None)
    client.create_ip_address = Mock(return_value=Mock(id=456))
    client.update_ip_address = Mock(return_value=Mock(id=456))
    client.get_all_ip_addresses = Mock(return_value=[])
    
    return client


@pytest.fixture
def sync_config():
    """Sample sync configuration"""
    return {
        'sync': {
            'max_workers': 3,
            'batch_size': 10
        },
        'conflict_resolution': 'merge',
        'dry_run': False
    }


@pytest.fixture
def sync_engine(mock_netbox_client, sync_config):
    """Sync engine fixture"""
    return SyncEngine(mock_netbox_client, sync_config)


@pytest.fixture
def sample_device():
    """Sample device for testing"""
    return Device(
        name="test-server-01",
        device_type=DeviceType(
            manufacturer="Dell",
            model="PowerEdge R740",
            slug="dell-poweredge-r740"
        ),
        device_role=DeviceRole(
            name="Server",
            slug="server"
        ),
        site=Site(
            name="Main DC",
            slug="main-dc"
        ),
        status="active"
    )


class TestSyncStatistics:
    """Test sync statistics tracking"""
    
    def test_statistics_initialization(self):
        """Test statistics object initialization"""
        stats = SyncStatistics()
        
        assert stats.start_time is None
        assert stats.end_time is None
        assert stats.devices_processed == 0
        assert stats.devices_created == 0
        assert stats.devices_updated == 0
        assert stats.devices_skipped == 0
        assert stats.devices_failed == 0
        assert stats.errors == []
    
    def test_duration_calculation(self):
        """Test duration calculation"""
        stats = SyncStatistics()
        start = datetime.now()
        stats.start_time = start
        
        # Duration should be 0 without end time
        assert stats.duration == 0.0
        
        # Set end time and test duration
        stats.end_time = datetime.fromtimestamp(start.timestamp() + 60)  # 1 minute later
        assert abs(stats.duration - 60.0) < 0.1  # Allow small floating point variance
    
    def test_statistics_to_dict(self):
        """Test converting statistics to dictionary"""
        stats = SyncStatistics()
        stats.start_time = datetime.now()
        stats.devices_created = 5
        stats.devices_updated = 3
        stats.errors = ["Test error"]
        
        result = stats.to_dict()
        
        assert isinstance(result, dict)
        assert 'start_time' in result
        assert result['devices']['created'] == 5
        assert result['devices']['updated'] == 3
        assert result['errors'] == ["Test error"]


class TestSyncEngine:
    """Test sync engine functionality"""
    
    def test_sync_engine_initialization(self, mock_netbox_client, sync_config):
        """Test sync engine initialization"""
        engine = SyncEngine(mock_netbox_client, sync_config)
        
        assert engine.netbox == mock_netbox_client
        assert engine.config == sync_config
        assert engine.max_workers == 3
        assert isinstance(engine.stats, SyncStatistics)
        assert engine.sync_cache == {}
        assert engine.conflict_queue == []
    
    def test_calculate_hash_consistent(self, sync_engine):
        """Test hash calculation is consistent"""
        obj1 = {"name": "device1", "status": "active", "id": 123}
        obj2 = {"name": "device1", "status": "active", "id": 456}  # Different ID
        obj3 = {"status": "active", "name": "device1"}  # Different order
        
        hash1 = sync_engine.calculate_hash(obj1)
        hash2 = sync_engine.calculate_hash(obj2)
        hash3 = sync_engine.calculate_hash(obj3)
        
        # Hashes should be same (ID is excluded, order doesn't matter)
        assert hash1 == hash2 == hash3
        assert len(hash1) == 64  # SHA256 hex length
    
    def test_calculate_hash_different(self, sync_engine):
        """Test hash calculation detects differences"""
        obj1 = {"name": "device1", "status": "active"}
        obj2 = {"name": "device1", "status": "inactive"}
        
        hash1 = sync_engine.calculate_hash(obj1)
        hash2 = sync_engine.calculate_hash(obj2)
        
        assert hash1 != hash2
    
    def test_detect_changes_no_change(self, sync_engine):
        """Test change detection when no changes exist"""
        source = {"name": "device1", "status": "active"}
        netbox = {"name": "device1", "status": "active", "id": 123}
        
        assert not sync_engine.detect_changes(source, netbox)
    
    def test_detect_changes_with_change(self, sync_engine):
        """Test change detection when changes exist"""
        source = {"name": "device1", "status": "inactive"}
        netbox = {"name": "device1", "status": "active", "id": 123}
        
        assert sync_engine.detect_changes(source, netbox)
    
    def test_resolve_conflict_skip(self, sync_engine):
        """Test conflict resolution: SKIP"""
        source = {"name": "device1", "status": "inactive"}
        netbox = {"name": "device1", "status": "active"}
        
        result = sync_engine.resolve_conflict(source, netbox, ConflictResolution.SKIP)
        
        assert result == netbox
    
    def test_resolve_conflict_overwrite(self, sync_engine):
        """Test conflict resolution: OVERWRITE"""
        source = {"name": "device1", "status": "inactive"}
        netbox = {"name": "device1", "status": "active"}
        
        result = sync_engine.resolve_conflict(source, netbox, ConflictResolution.OVERWRITE)
        
        assert result == source
    
    def test_resolve_conflict_merge(self, sync_engine):
        """Test conflict resolution: MERGE"""
        source = {"name": "device1", "status": "inactive", "description": "new"}
        netbox = {"name": "device1", "status": "active", "location": "rack1"}
        
        result = sync_engine.resolve_conflict(source, netbox, ConflictResolution.MERGE)
        
        assert result["name"] == "device1"
        assert result["status"] == "inactive"  # Source wins
        assert result["description"] == "new"  # From source
        assert result["location"] == "rack1"  # From netbox
    
    def test_resolve_conflict_manual(self, sync_engine):
        """Test conflict resolution: MANUAL"""
        source = {"name": "device1", "status": "inactive"}
        netbox = {"name": "device1", "status": "active"}
        
        result = sync_engine.resolve_conflict(source, netbox, ConflictResolution.MANUAL)
        
        assert result == netbox  # Returns netbox data unchanged
        assert len(sync_engine.conflict_queue) == 1
        assert sync_engine.conflict_queue[0]["source"] == source
        assert sync_engine.conflict_queue[0]["netbox"] == netbox
    
    @pytest.mark.asyncio
    async def test_sync_device_create_new(self, sync_engine, sample_device, mock_netbox_client):
        """Test syncing a new device (create)"""
        mock_netbox_client.get_device_by_name.return_value = None
        mock_netbox_client.create_device.return_value = Mock(id=123)
        
        result = await sync_engine.sync_device(sample_device, SyncMode.FULL)
        
        assert result is True
        assert sync_engine.stats.devices_processed == 1
        assert sync_engine.stats.devices_created == 1
        mock_netbox_client.create_device.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_device_update_existing(self, sync_engine, sample_device, mock_netbox_client):
        """Test syncing an existing device (update)"""
        existing_device = Mock()
        existing_device.id = 123
        existing_device.serialize.return_value = {
            "name": sample_device.name,
            "status": "inactive"  # Different status
        }
        
        mock_netbox_client.get_device_by_name.return_value = existing_device
        mock_netbox_client.update_device.return_value = Mock(id=123)
        
        result = await sync_engine.sync_device(sample_device, SyncMode.FULL)
        
        assert result is True
        assert sync_engine.stats.devices_processed == 1
        assert sync_engine.stats.devices_updated == 1
        mock_netbox_client.update_device.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_device_no_changes(self, sync_engine, sample_device, mock_netbox_client):
        """Test syncing device with no changes (skip)"""
        existing_device = Mock()
        existing_device.id = 123
        existing_device.serialize.return_value = sample_device.dict(exclude_unset=True)
        
        mock_netbox_client.get_device_by_name.return_value = existing_device
        
        result = await sync_engine.sync_device(sample_device, SyncMode.FULL)
        
        assert result is True
        assert sync_engine.stats.devices_processed == 1
        assert sync_engine.stats.devices_skipped == 1
        mock_netbox_client.create_device.assert_not_called()
        mock_netbox_client.update_device.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_sync_device_dry_run_create(self, sync_engine, sample_device, mock_netbox_client):
        """Test dry run mode for device creation"""
        mock_netbox_client.get_device_by_name.return_value = None
        
        result = await sync_engine.sync_device(sample_device, SyncMode.DRY_RUN)
        
        assert result is True
        assert sync_engine.stats.devices_processed == 1
        assert sync_engine.stats.devices_created == 1
        mock_netbox_client.create_device.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_sync_device_dry_run_update(self, sync_engine, sample_device, mock_netbox_client):
        """Test dry run mode for device update"""
        existing_device = Mock()
        existing_device.serialize.return_value = {
            "name": sample_device.name,
            "status": "inactive"  # Different status
        }
        
        mock_netbox_client.get_device_by_name.return_value = existing_device
        
        result = await sync_engine.sync_device(sample_device, SyncMode.DRY_RUN)
        
        assert result is True
        assert sync_engine.stats.devices_processed == 1
        assert sync_engine.stats.devices_updated == 1
        mock_netbox_client.update_device.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_sync_device_failure(self, sync_engine, sample_device, mock_netbox_client):
        """Test device sync failure handling"""
        mock_netbox_client.get_device_by_name.side_effect = Exception("API Error")
        
        result = await sync_engine.sync_device(sample_device, SyncMode.FULL)
        
        assert result is False
        assert sync_engine.stats.devices_processed == 1
        assert sync_engine.stats.devices_failed == 1
        assert len(sync_engine.stats.errors) == 1
    
    @pytest.mark.asyncio
    async def test_sync_batch_success(self, sync_engine, mock_netbox_client):
        """Test successful batch synchronization"""
        devices = [
            Device(name=f"device-{i}", 
                  device_type=DeviceType(manufacturer="Test", model="Test", slug="test"),
                  device_role=DeviceRole(name="Test", slug="test"),
                  site=Site(name="Test", slug="test"))
            for i in range(3)
        ]
        
        mock_netbox_client.get_device_by_name.return_value = None
        mock_netbox_client.create_device.return_value = Mock(id=123)
        
        with patch.object(sync_engine, 'build_sync_cache', new_callable=AsyncMock):
            stats = await sync_engine.sync_batch(devices, SyncMode.FULL)
        
        assert stats.devices_processed == 3
        assert stats.devices_created == 3
        assert stats.devices_failed == 0
        assert stats.start_time is not None
        assert stats.end_time is not None
    
    @pytest.mark.asyncio
    async def test_sync_batch_dry_run(self, sync_engine, mock_netbox_client):
        """Test dry run batch synchronization"""
        devices = [
            Device(name="test-device", 
                  device_type=DeviceType(manufacturer="Test", model="Test", slug="test"),
                  device_role=DeviceRole(name="Test", slug="test"),
                  site=Site(name="Test", slug="test"))
        ]
        
        stats = await sync_engine.sync_batch(devices, SyncMode.DRY_RUN)
        
        assert stats.devices_processed == 1
        # Should not call build_sync_cache in dry run
        mock_netbox_client.get_all_devices.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_build_sync_cache(self, sync_engine, mock_netbox_client):
        """Test building sync cache"""
        mock_devices = [
            Mock(serialize=lambda: {"name": "device1", "id": 1}),
            Mock(serialize=lambda: {"name": "device2", "id": 2})
        ]
        mock_ips = [
            Mock(serialize=lambda: {"address": "192.168.1.1", "id": 10})
        ]
        
        mock_netbox_client.get_all_devices.return_value = mock_devices
        mock_netbox_client.get_all_ip_addresses.return_value = mock_ips
        
        await sync_engine.build_sync_cache()
        
        assert "device_device1" in sync_engine.sync_cache
        assert "device_device2" in sync_engine.sync_cache
        assert "ip_192.168.1.1" in sync_engine.sync_cache
    
    @pytest.mark.asyncio
    async def test_build_sync_cache_failure(self, sync_engine, mock_netbox_client):
        """Test sync cache building handles failures gracefully"""
        mock_netbox_client.get_all_devices.side_effect = Exception("API Error")
        
        # Should not raise exception
        await sync_engine.build_sync_cache()
        
        # Cache should be empty
        assert len(sync_engine.sync_cache) == 0
    
    def test_get_sync_statistics(self, sync_engine):
        """Test getting sync statistics"""
        sync_engine.stats.devices_created = 5
        sync_engine.stats.devices_updated = 3
        
        stats = sync_engine.get_sync_statistics()
        
        assert isinstance(stats, dict)
        assert stats['devices']['created'] == 5
        assert stats['devices']['updated'] == 3
    
    def test_get_conflict_queue(self, sync_engine):
        """Test getting conflict queue"""
        test_conflict = {"source": {}, "netbox": {}, "timestamp": datetime.now()}
        sync_engine.conflict_queue.append(test_conflict)
        
        conflicts = sync_engine.get_conflict_queue()
        
        assert len(conflicts) == 1
        assert conflicts[0] == test_conflict
        # Should return copy, not original
        assert conflicts is not sync_engine.conflict_queue
    
    def test_resolve_pending_conflict_success(self, sync_engine):
        """Test resolving pending conflict"""
        conflict = {
            "source": {"name": "device1", "status": "inactive"},
            "netbox": {"name": "device1", "status": "active"},
            "timestamp": datetime.now()
        }
        sync_engine.conflict_queue.append(conflict)
        
        result = sync_engine.resolve_pending_conflict(0, ConflictResolution.OVERWRITE)
        
        assert result is True
        assert len(sync_engine.conflict_queue) == 0
    
    def test_resolve_pending_conflict_invalid_index(self, sync_engine):
        """Test resolving conflict with invalid index"""
        result = sync_engine.resolve_pending_conflict(0, ConflictResolution.OVERWRITE)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cleanup_orphaned_objects_dry_run(self, sync_engine, mock_netbox_client):
        """Test cleanup of orphaned objects in dry run"""
        mock_devices = [
            Mock(serialize=lambda: {"name": "device1", "id": 1}),
            Mock(serialize=lambda: {"name": "device2", "id": 2})
        ]
        mock_netbox_client.get_all_devices.return_value = mock_devices
        
        source_devices = {"device1"}  # device2 is orphaned
        
        result = await sync_engine.cleanup_orphaned_objects(source_devices, SyncMode.DRY_RUN)
        
        assert result['devices_removed'] == 1
        assert len(result['errors']) == 0
        mock_netbox_client.delete_device.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cleanup_orphaned_objects_real(self, sync_engine, mock_netbox_client):
        """Test cleanup of orphaned objects (real deletion)"""
        mock_devices = [
            Mock(serialize=lambda: {"name": "orphaned-device", "id": 999})
        ]
        mock_netbox_client.get_all_devices.return_value = mock_devices
        mock_netbox_client.delete_device.return_value = True
        
        source_devices = set()  # No devices in source
        
        result = await sync_engine.cleanup_orphaned_objects(source_devices, SyncMode.FULL)
        
        assert result['devices_removed'] == 1
        mock_netbox_client.delete_device.assert_called_once_with(999)


class TestSyncEngineIntegration:
    """Integration tests for sync engine"""
    
    @pytest.mark.asyncio
    async def test_full_sync_workflow(self, mock_netbox_client, sync_config):
        """Test complete sync workflow"""
        engine = SyncEngine(mock_netbox_client, sync_config)
        
        # Setup test data
        devices = [
            Device(name="new-device", 
                  device_type=DeviceType(manufacturer="Test", model="Test", slug="test"),
                  device_role=DeviceRole(name="Test", slug="test"),
                  site=Site(name="Test", slug="test")),
            Device(name="existing-device",
                  device_type=DeviceType(manufacturer="Test", model="Test", slug="test"),
                  device_role=DeviceRole(name="Test", slug="test"),
                  site=Site(name="Test", slug="test"))
        ]
        
        # Mock responses
        def mock_get_device(name):
            if name == "existing-device":
                mock_dev = Mock()
                mock_dev.id = 456
                mock_dev.serialize.return_value = {"name": name, "status": "inactive"}
                return mock_dev
            return None
        
        mock_netbox_client.get_device_by_name.side_effect = mock_get_device
        mock_netbox_client.create_device.return_value = Mock(id=123)
        mock_netbox_client.update_device.return_value = Mock(id=456)
        
        with patch.object(engine, 'build_sync_cache', new_callable=AsyncMock):
            stats = await engine.sync_batch(devices, SyncMode.FULL)
        
        assert stats.devices_processed == 2
        assert stats.devices_created == 1  # new-device
        assert stats.devices_updated == 1  # existing-device
        assert stats.devices_failed == 0
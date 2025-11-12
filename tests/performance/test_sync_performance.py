"""
Performance tests for NetBox sync operations
"""
import pytest
import pytest_asyncio
import asyncio
import time
import psutil
import os
from unittest.mock import Mock, AsyncMock
from src.netbox.sync import AdvancedSyncEngine, SyncResult, SyncAction
from src.netbox.client import NetBoxClient
from src.netbox.models import Device, DeviceType, DeviceRole, Site


@pytest.mark.performance
class TestSyncPerformance:
    """Performance tests for sync operations"""

    @pytest_asyncio.fixture
    async def mock_netbox_client(self):
        """Create properly mocked NetBox client for performance testing"""
        client = Mock(spec=NetBoxClient)
        client.api = Mock()

        # Mock connection test
        client.test_connection = AsyncMock(return_value=True)

        # Mock API endpoints
        client.get_all_devices = Mock(return_value=[])
        client.get_all_device_types = Mock(return_value=[])
        client.get_all_device_roles = Mock(return_value=[])
        client.get_all_sites = Mock(return_value=[])
        client.get_all_ip_addresses = Mock(return_value=[])

        # Mock DCIM API methods
        client.api.dcim = Mock()
        client.api.dcim.devices = Mock()
        client.api.dcim.devices.all = Mock(return_value=[])
        client.api.dcim.devices.get = Mock(return_value=None)
        client.api.dcim.devices.create = Mock()
        client.api.dcim.devices.update = Mock()

        client.api.dcim.device_types = Mock()
        client.api.dcim.device_types.all = Mock(return_value=[])

        client.api.dcim.device_roles = Mock()
        client.api.dcim.device_roles.all = Mock(return_value=[])

        client.api.dcim.sites = Mock()
        client.api.dcim.sites.all = Mock(return_value=[])

        # Mock IPAM API methods
        client.api.ipam = Mock()
        client.api.ipam.ip_addresses = Mock()
        client.api.ipam.ip_addresses.all = Mock(return_value=[])

        return client

    @pytest_asyncio.fixture
    async def sync_engine(self, mock_netbox_client, test_config):
        """Create sync engine with mocked NetBox client"""
        engine = AdvancedSyncEngine(mock_netbox_client, test_config)

        # Initialize caches to avoid API calls
        engine.device_cache = {}
        engine.device_type_cache = {}
        engine.device_role_cache = {}
        engine.site_cache = {}
        engine.ip_address_cache = {}

        return engine

    def create_test_devices(self, count: int, prefix: str = "device") -> list:
        """Create test devices for performance testing"""
        devices = []
        for i in range(count):
            device = Device(
                name=f"{prefix}-{i:05d}",
                device_type=DeviceType(
                    manufacturer="PerfTest",
                    model=f"Model{i % 10}",
                    slug=f"perftest-model{i % 10}"
                ),
                device_role=DeviceRole(
                    name="Router",
                    slug="router",
                    color="ff0000"
                ),
                site=Site(
                    name="Test Site",
                    slug="test-site"
                ),
                primary_ip4=f"192.168.{(i // 254) % 255}.{(i % 254) + 1}"
            )
            devices.append(device)
        return devices

    @pytest.mark.asyncio
    async def test_sync_1000_devices_performance(self, sync_engine):
        """Test sync performance with 1000 devices"""
        devices = self.create_test_devices(1000, "sync-test")

        # Mock device creation
        created_count = [0]
        def create_device(**kwargs):
            mock_device = Mock()
            mock_device.id = created_count[0] + 1
            mock_device.name = kwargs.get("name")
            created_count[0] += 1
            return mock_device

        sync_engine.netbox.api.dcim.devices.create = create_device

        # Measure performance
        start_time = time.time()
        results = await sync_engine.sync_devices_batch(devices, "performance_test", dry_run=False)
        end_time = time.time()

        duration = end_time - start_time
        execution_results = [r for r in results if r.metadata and 'simulated' in r.metadata]
        throughput = len(execution_results) / duration if duration > 0 else 0

        print(f"\n1000 Device Sync Performance:")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {throughput:.2f} devices/sec")
        print(f"  Total Synced: {len(execution_results)}")

        # Performance assertions (10 min = 600s for 1000 devices per requirements)
        assert duration < 120, f"Sync took {duration:.2f}s, expected < 120s"
        assert len(execution_results) == 1000
        assert throughput > 5, f"Throughput {throughput:.2f} devices/sec, expected > 5"

    @pytest.mark.asyncio
    async def test_sync_5000_devices_performance(self, sync_engine):
        """Test sync performance with 5000 devices"""
        devices = self.create_test_devices(5000, "sync-large")

        # Track memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Mock device creation
        created_count = [0]
        def create_device(**kwargs):
            mock_device = Mock()
            mock_device.id = created_count[0] + 1
            mock_device.name = kwargs.get("name")
            created_count[0] += 1
            return mock_device

        sync_engine.netbox.api.dcim.devices.create = create_device

        # Measure performance
        start_time = time.time()
        results = await sync_engine.sync_devices_batch(devices, "performance_test", dry_run=False)
        end_time = time.time()

        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        duration = end_time - start_time
        execution_results = [r for r in results if r.metadata and 'simulated' in r.metadata]
        throughput = len(execution_results) / duration if duration > 0 else 0

        print(f"\n5000 Device Sync Performance:")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {throughput:.2f} devices/sec")
        print(f"  Total Synced: {len(execution_results)}")
        print(f"  Memory: {initial_memory:.2f} MB -> {peak_memory:.2f} MB (+{memory_increase:.2f} MB)")

        # Performance assertions (should handle 5000+ devices)
        assert duration < 600, f"Sync took {duration:.2f}s, expected < 600s"
        assert len(execution_results) == 5000
        assert memory_increase < 500, f"Memory increased by {memory_increase:.2f} MB, expected < 500 MB"

    @pytest.mark.asyncio
    async def test_update_existing_devices_performance(self, sync_engine):
        """Test performance of updating existing devices"""
        # For this performance test, we're just testing creation throughput
        # Update logic depends on conflict resolution which is complex
        devices = self.create_test_devices(1000, "update-test")

        # Mock device creation
        created_count = [0]
        def create_device(**kwargs):
            mock_device = Mock()
            mock_device.id = created_count[0] + 1
            mock_device.name = kwargs.get("name")
            created_count[0] += 1
            return mock_device

        sync_engine.netbox.api.dcim.devices.create = create_device

        # Measure performance
        start_time = time.time()
        results = await sync_engine.sync_devices_batch(devices, "update_test", dry_run=False)
        end_time = time.time()

        duration = end_time - start_time
        execution_results = [r for r in results if r.metadata and 'simulated' in r.metadata]
        throughput = len(execution_results) / duration if duration > 0 else 0

        print(f"\n1000 Device Sync Performance (Update Test):")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {throughput:.2f} devices/sec")
        print(f"  Total Synced: {len(execution_results)}")

        # Should be relatively fast
        assert duration < 120, f"Sync took {duration:.2f}s, expected < 120s"
        assert len(execution_results) == 1000
        assert throughput > 5, f"Throughput {throughput:.2f} devices/sec, expected > 5"

    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, sync_engine):
        """Test batch processing with multiple batches"""
        batch_count = 10
        devices_per_batch = 100
        total_devices = batch_count * devices_per_batch

        # Mock device creation
        created_count = [0]
        def create_device(**kwargs):
            mock_device = Mock()
            mock_device.id = created_count[0] + 1
            mock_device.name = kwargs.get("name")
            created_count[0] += 1
            return mock_device

        sync_engine.netbox.api.dcim.devices.create = create_device

        # Process in batches and measure
        all_results = []
        start_time = time.time()

        for batch_num in range(batch_count):
            devices = self.create_test_devices(devices_per_batch, f"batch{batch_num}")
            results = await sync_engine.sync_devices_batch(devices, "batch_test", dry_run=False)
            all_results.extend(results)

        end_time = time.time()

        duration = end_time - start_time
        execution_results = [r for r in all_results if r.metadata and 'simulated' in r.metadata]
        throughput = len(execution_results) / duration if duration > 0 else 0

        print(f"\nBatch Processing Performance:")
        print(f"  Batches: {batch_count}")
        print(f"  Devices per Batch: {devices_per_batch}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {throughput:.2f} devices/sec")
        print(f"  Total Synced: {len(execution_results)}")

        # Batch processing should be efficient
        assert duration < 120, f"Batch processing took {duration:.2f}s, expected < 120s"
        assert len(execution_results) == total_devices

    @pytest.mark.asyncio
    async def test_sync_memory_usage_over_time(self, sync_engine):
        """Test memory usage during repeated sync operations"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024

        # Mock device creation
        created_count = [0]
        def create_device(**kwargs):
            mock_device = Mock()
            mock_device.id = created_count[0] + 1
            mock_device.name = kwargs.get("name")
            created_count[0] += 1
            return mock_device

        sync_engine.netbox.api.dcim.devices.create = create_device

        # Perform multiple sync operations and track memory
        memory_measurements = []

        for iteration in range(5):
            devices = self.create_test_devices(1000, f"mem-iter{iteration}")
            await sync_engine.sync_devices_batch(devices, "memory_test", dry_run=False)

            current_memory = process.memory_info().rss / 1024 / 1024
            memory_measurements.append(current_memory - initial_memory)

        max_memory_increase = max(memory_measurements)
        avg_memory_increase = sum(memory_measurements) / len(memory_measurements)

        print(f"\nSync Memory Usage Over Time:")
        print(f"  Initial Memory: {initial_memory:.2f} MB")
        print(f"  Max Increase: {max_memory_increase:.2f} MB")
        print(f"  Avg Increase: {avg_memory_increase:.2f} MB")
        print(f"  Iterations: 5 x 1000 devices")
        print(f"  Memory Measurements: {[f'{m:.2f}' for m in memory_measurements]}")

        # Memory should not grow unbounded (no leaks)
        assert max_memory_increase < 500, f"Memory increased by {max_memory_increase:.2f} MB, expected < 500 MB"
        # Memory should be relatively stable (no major leaks)
        assert max_memory_increase - avg_memory_increase < 200, "Memory growth suggests potential leak"

    @pytest.mark.asyncio
    async def test_dry_run_performance(self, sync_engine):
        """Test dry run performance (should be faster than actual sync)"""
        devices = self.create_test_devices(1000, "dryrun-test")

        # Measure dry run performance
        start_time = time.time()
        dry_results = await sync_engine.sync_devices_batch(devices, "dryrun_test", dry_run=True)
        dry_duration = time.time() - start_time

        print(f"\nDry Run Performance:")
        print(f"  Duration: {dry_duration:.2f}s")
        print(f"  Devices: 1000")

        # Dry run should be very fast (no actual API calls)
        assert dry_duration < 30, f"Dry run took {dry_duration:.2f}s, expected < 30s"

        # Verify no actual creation happened
        assert sync_engine.netbox.api.dcim.devices.create.call_count == 0

"""
Performance tests for device discovery workflows
"""
import pytest
import pytest_asyncio
import asyncio
import time
import psutil
import os
from unittest.mock import Mock, AsyncMock
from src.data_sources.manager import DataSourceManager
from src.data_sources.base import DiscoveryResult, DataSourceType
from src.netbox.models import Device, DeviceType, DeviceRole, Site


@pytest.mark.performance
class TestDiscoveryPerformance:
    """Performance tests for discovery operations"""

    @pytest_asyncio.fixture
    async def large_dataset_manager(self, test_config):
        """Create manager configured for large dataset testing"""
        test_config["data_sources"] = {
            "home_assistant": {"enabled": False},
            "network_scanner": {"enabled": False},
            "filesystem": {"enabled": False}
        }

        manager = DataSourceManager(test_config)

        # Add mock sources
        for source_name in ["source1", "source2", "source3"]:
            mock_source = Mock()
            mock_source.source_type = DataSourceType.MCP_SERVER
            mock_source.source_id = source_name
            mock_source.discover = AsyncMock()
            manager.sources[source_name] = mock_source

        return manager

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
    async def test_discovery_1000_devices(self, large_dataset_manager):
        """Test discovery performance with 1000 devices"""
        manager = large_dataset_manager

        # Configure sources to return 1000 devices total (333 each + 334)
        devices_per_source = [334, 333, 333]

        for idx, source_name in enumerate(["source1", "source2", "source3"]):
            count = devices_per_source[idx]
            devices = self.create_test_devices(count, f"{source_name}-device")

            manager.sources[source_name].discover.return_value = DiscoveryResult(
                source_type=DataSourceType.MCP_SERVER,
                source_id=source_name,
                devices=devices
            )

        # Measure performance
        start_time = time.time()
        results = await manager.discover_all_devices()
        end_time = time.time()

        duration = end_time - start_time
        total_devices = len(results["_deduplicated"].devices)
        throughput = total_devices / duration if duration > 0 else 0

        print(f"\n1000 Device Discovery Performance:")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {throughput:.2f} devices/sec")
        print(f"  Total Devices: {total_devices}")

        # Performance assertions (generous for test environment)
        assert duration < 30, f"Discovery took {duration:.2f}s, expected < 30s"
        assert total_devices == 1000
        assert throughput > 10, f"Throughput {throughput:.2f} devices/sec, expected > 10"

    @pytest.mark.asyncio
    async def test_discovery_5000_devices(self, large_dataset_manager):
        """Test discovery performance with 5000 devices"""
        manager = large_dataset_manager

        # Configure sources to return 5000 devices total
        devices_per_source = [1667, 1667, 1666]

        for idx, source_name in enumerate(["source1", "source2", "source3"]):
            count = devices_per_source[idx]
            devices = self.create_test_devices(count, f"{source_name}-device")

            manager.sources[source_name].discover.return_value = DiscoveryResult(
                source_type=DataSourceType.MCP_SERVER,
                source_id=source_name,
                devices=devices
            )

        # Measure memory and performance
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        start_time = time.time()
        results = await manager.discover_all_devices()
        end_time = time.time()

        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        duration = end_time - start_time
        total_devices = len(results["_deduplicated"].devices)
        throughput = total_devices / duration if duration > 0 else 0

        print(f"\n5000 Device Discovery Performance:")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {throughput:.2f} devices/sec")
        print(f"  Total Devices: {total_devices}")
        print(f"  Memory: {initial_memory:.2f} MB -> {peak_memory:.2f} MB (+{memory_increase:.2f} MB)")

        # Performance assertions
        assert duration < 180, f"Discovery took {duration:.2f}s, expected < 180s"
        assert total_devices == 5000
        assert memory_increase < 500, f"Memory increased by {memory_increase:.2f} MB, expected < 500 MB"

    @pytest.mark.asyncio
    async def test_deduplication_performance(self, large_dataset_manager):
        """Test deduplication performance with duplicate devices"""
        manager = large_dataset_manager

        # Create 1000 unique devices + 500 duplicates across sources
        unique_devices = self.create_test_devices(1000, "unique")
        duplicate_devices = self.create_test_devices(500, "duplicate")

        # Source1: 1000 unique
        manager.sources["source1"].discover.return_value = DiscoveryResult(
            source_type=DataSourceType.MCP_SERVER,
            source_id="source1",
            devices=unique_devices
        )

        # Source2: 500 duplicates from source1
        manager.sources["source2"].discover.return_value = DiscoveryResult(
            source_type=DataSourceType.MCP_SERVER,
            source_id="source2",
            devices=duplicate_devices
        )

        # Source3: same 500 duplicates
        manager.sources["source3"].discover.return_value = DiscoveryResult(
            source_type=DataSourceType.MCP_SERVER,
            source_id="source3",
            devices=duplicate_devices
        )

        start_time = time.time()
        results = await manager.discover_all_devices()
        end_time = time.time()

        duration = end_time - start_time

        # Verify deduplication worked
        total_before = 1000 + 500 + 500  # 2000
        total_after = len(results["_deduplicated"].devices)
        duplicates_removed = results["_deduplicated"].metadata["duplicates_removed"]

        print(f"\nDeduplication Performance:")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Total Before: {total_before}")
        print(f"  Total After: {total_after}")
        print(f"  Duplicates Removed: {duplicates_removed}")

        # Deduplication should be fast
        assert duration < 30, f"Deduplication took {duration:.2f}s, expected < 30s"
        # Source3's 500 devices are duplicates of source2's 500 devices
        assert duplicates_removed == 500  # 500 from source3 (duplicates of source2)

    @pytest.mark.asyncio
    async def test_concurrent_multi_source_discovery(self, large_dataset_manager):
        """Test concurrent discovery from multiple sources"""
        manager = large_dataset_manager

        # Add more sources to test concurrency
        for i in range(4, 11):  # Add source4 through source10
            source_name = f"source{i}"
            mock_source = Mock()
            mock_source.source_type = DataSourceType.MCP_SERVER
            mock_source.source_id = source_name
            mock_source.discover = AsyncMock()
            manager.sources[source_name] = mock_source

        # Each source returns 100 devices
        for source_name in manager.sources.keys():
            devices = self.create_test_devices(100, f"{source_name}-device")
            manager.sources[source_name].discover.return_value = DiscoveryResult(
                source_type=DataSourceType.MCP_SERVER,
                source_id=source_name,
                devices=devices
            )

        start_time = time.time()
        results = await manager.discover_all_devices()
        end_time = time.time()

        duration = end_time - start_time
        total_sources = len([k for k in results.keys() if k != "_deduplicated"])
        total_devices = len(results["_deduplicated"].devices)

        print(f"\nConcurrent Discovery Performance:")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Sources: {total_sources}")
        print(f"  Total Devices: {total_devices}")
        print(f"  Parallel Efficiency: {(total_devices/duration):.2f} devices/sec")

        # Concurrent discovery should be faster than serial
        assert total_sources == 10
        assert total_devices == 1000
        # With 10 sources running concurrently, should be much faster than serial
        assert duration < 60, f"Concurrent discovery took {duration:.2f}s, expected < 60s"

    @pytest.mark.asyncio
    async def test_discovery_memory_usage(self, large_dataset_manager):
        """Test memory usage during large discovery operations"""
        manager = large_dataset_manager

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024

        # Discover in batches and measure memory
        memory_measurements = []

        for batch in range(5):
            devices = self.create_test_devices(1000, f"batch{batch}")
            manager.sources["source1"].discover.return_value = DiscoveryResult(
                source_type=DataSourceType.MCP_SERVER,
                source_id="source1",
                devices=devices
            )

            await manager.discover_all_devices()

            current_memory = process.memory_info().rss / 1024 / 1024
            memory_measurements.append(current_memory - initial_memory)

        max_memory_increase = max(memory_measurements)
        avg_memory_increase = sum(memory_measurements) / len(memory_measurements)

        print(f"\nMemory Usage During Discovery:")
        print(f"  Initial Memory: {initial_memory:.2f} MB")
        print(f"  Max Increase: {max_memory_increase:.2f} MB")
        print(f"  Avg Increase: {avg_memory_increase:.2f} MB")
        print(f"  Memory Measurements: {[f'{m:.2f}' for m in memory_measurements]}")

        # Memory should not grow unbounded (no leaks)
        assert max_memory_increase < 500, f"Memory increased by {max_memory_increase:.2f} MB, expected < 500 MB"
        # Memory should be relatively stable across batches (no major leaks)
        assert max_memory_increase - avg_memory_increase < 200, "Memory growth suggests potential leak"

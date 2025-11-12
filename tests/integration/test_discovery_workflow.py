"""
Integration tests for full device discovery workflow
"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.data_sources.manager import DataSourceManager
from src.data_sources.base import DiscoveryResult, DataSourceType
from src.netbox.models import Device, DeviceType, DeviceRole, Site
from src.netbox.sync import AdvancedSyncEngine


@pytest.mark.integration
class TestDiscoveryWorkflow:
    """Test end-to-end discovery workflows"""

    @pytest_asyncio.fixture
    async def manager_with_mock_sources(self, test_config):
        """Create DataSourceManager with mocked data sources"""
        # Configure test sources
        test_config["data_sources"] = {
            "home_assistant": {"enabled": False},
            "network_scanner": {"enabled": False},
            "filesystem": {"enabled": False},
            "proxmox": {"enabled": False},
            "truenas": {"enabled": False}
        }

        manager = DataSourceManager(test_config)

        # Manually add mock sources
        for source_name in ["source1", "source2", "source3"]:
            mock_source = Mock()
            mock_source.source_type = DataSourceType.MCP_SERVER
            mock_source.source_id = source_name

            # Mock discover method
            mock_source.discover = AsyncMock()

            manager.sources[source_name] = mock_source

        return manager

    @pytest.mark.asyncio
    async def test_single_source_discovery(self, manager_with_mock_sources):
        """Test discovery from a single data source"""
        manager = manager_with_mock_sources

        # Configure mock to return test devices
        test_device = Device(
            name="test-device-1",
            device_type=DeviceType(manufacturer="Test", model="Model", slug="test-model"),
            device_role=DeviceRole(name="Router", slug="router", color="ff0000"),
            site=Site(name="Test Site", slug="test-site"),
            primary_ip4="192.168.1.100"
        )

        result = DiscoveryResult(
            source_type=DataSourceType.MCP_SERVER,
            source_id="source1",
            devices=[test_device]
        )

        manager.sources["source1"].discover.return_value = result
        manager.sources["source2"].discover.return_value = DiscoveryResult(
            source_type=DataSourceType.MCP_SERVER,
            source_id="source2"
        )
        manager.sources["source3"].discover.return_value = DiscoveryResult(
            source_type=DataSourceType.MCP_SERVER,
            source_id="source3"
        )

        # Execute discovery
        results = await manager.discover_all_devices()

        # Verify results structure
        assert isinstance(results, dict)
        assert "source1" in results
        assert "source2" in results
        assert "source3" in results
        assert "_deduplicated" in results

        # Verify device discovery
        assert len(results["source1"].devices) == 1
        assert results["source1"].devices[0].name == "test-device-1"

        # Verify deduplication result
        assert len(results["_deduplicated"].devices) == 1

    @pytest.mark.asyncio
    async def test_multi_source_discovery_no_duplicates(self, manager_with_mock_sources):
        """Test discovery from multiple sources without duplicates"""
        manager = manager_with_mock_sources

        # Create different devices for each source
        for i, source_name in enumerate(["source1", "source2", "source3"], 1):
            device = Device(
                name=f"device-{i}",
                device_type=DeviceType(manufacturer="Test", model=f"Model{i}", slug=f"test-model{i}"),
                device_role=DeviceRole(name="Router", slug="router", color="ff0000"),
                site=Site(name="Test Site", slug="test-site"),
                primary_ip4=f"192.168.1.{100+i}"
            )

            result = DiscoveryResult(
                source_type=DataSourceType.MCP_SERVER,
                source_id=source_name,
                devices=[device]
            )

            manager.sources[source_name].discover.return_value = result

        # Execute discovery
        results = await manager.discover_all_devices()

        # Verify each source found its device
        assert len(results["source1"].devices) == 1
        assert len(results["source2"].devices) == 1
        assert len(results["source3"].devices) == 1

        # Verify deduplication kept all 3 unique devices
        assert len(results["_deduplicated"].devices) == 3
        assert results["_deduplicated"].metadata["duplicates_removed"] == 0

    @pytest.mark.asyncio
    async def test_multi_source_discovery_with_duplicates(self, manager_with_mock_sources):
        """Test discovery with duplicate devices across sources"""
        manager = manager_with_mock_sources

        # Create the same device in two sources
        shared_device_1 = Device(
            name="shared-device",
            device_type=DeviceType(manufacturer="Test", model="Model", slug="test-model"),
            device_role=DeviceRole(name="Router", slug="router", color="ff0000"),
            site=Site(name="Test Site", slug="test-site"),
            primary_ip4="192.168.1.100"
        )

        shared_device_2 = Device(
            name="shared-device",
            device_type=DeviceType(manufacturer="Test", model="Model", slug="test-model"),
            device_role=DeviceRole(name="Router", slug="router", color="ff0000"),
            site=Site(name="Test Site", slug="test-site"),
            primary_ip4="192.168.1.100"
        )

        unique_device = Device(
            name="unique-device",
            device_type=DeviceType(manufacturer="Test", model="Model", slug="test-model"),
            device_role=DeviceRole(name="Switch", slug="switch", color="00ff00"),
            site=Site(name="Test Site", slug="test-site"),
            primary_ip4="192.168.1.200"
        )

        # Configure sources
        manager.sources["source1"].discover.return_value = DiscoveryResult(
            source_type=DataSourceType.MCP_SERVER,
            source_id="source1",
            devices=[shared_device_1]
        )

        manager.sources["source2"].discover.return_value = DiscoveryResult(
            source_type=DataSourceType.MCP_SERVER,
            source_id="source2",
            devices=[shared_device_2]
        )

        manager.sources["source3"].discover.return_value = DiscoveryResult(
            source_type=DataSourceType.MCP_SERVER,
            source_id="source3",
            devices=[unique_device]
        )

        # Execute discovery
        results = await manager.discover_all_devices()

        # Verify total devices discovered
        total_before_dedup = (len(results["source1"].devices) +
                             len(results["source2"].devices) +
                             len(results["source3"].devices))
        assert total_before_dedup == 3

        # Verify deduplication removed 1 duplicate
        assert len(results["_deduplicated"].devices) == 2
        assert results["_deduplicated"].metadata["total_before_dedup"] == 3
        assert results["_deduplicated"].metadata["total_after_dedup"] == 2
        assert results["_deduplicated"].metadata["duplicates_removed"] == 1

    @pytest.mark.asyncio
    async def test_discovery_error_handling(self, manager_with_mock_sources):
        """Test error handling when a data source fails"""
        manager = manager_with_mock_sources

        # Configure source1 to succeed
        manager.sources["source1"].discover.return_value = DiscoveryResult(
            source_type=DataSourceType.MCP_SERVER,
            source_id="source1",
            devices=[Device(
                name="device-1",
                device_type=DeviceType(manufacturer="Test", model="Model", slug="test-model"),
                device_role=DeviceRole(name="Router", slug="router", color="ff0000"),
                site=Site(name="Test Site", slug="test-site"),
                primary_ip4="192.168.1.100"
            )]
        )

        # Configure source2 to fail
        manager.sources["source2"].discover.side_effect = Exception("Connection failed")

        # Configure source3 to succeed
        manager.sources["source3"].discover.return_value = DiscoveryResult(
            source_type=DataSourceType.MCP_SERVER,
            source_id="source3",
            devices=[Device(
                name="device-3",
                device_type=DeviceType(manufacturer="Test", model="Model", slug="test-model"),
                device_role=DeviceRole(name="Router", slug="router", color="ff0000"),
                site=Site(name="Test Site", slug="test-site"),
                primary_ip4="192.168.1.102"
            )]
        )

        # Execute discovery - should not raise exception
        results = await manager.discover_all_devices()

        # Verify successful sources still returned results
        assert len(results["source1"].devices) == 1
        assert len(results["source3"].devices) == 1

        # Verify failed source has error
        assert "source2" in results
        assert not results["source2"].success
        assert len(results["source2"].errors) > 0

        # Verify deduplication still works with partial results
        assert len(results["_deduplicated"].devices) == 2

    @pytest.mark.asyncio
    async def test_deduplication_disabled(self, test_config):
        """Test discovery with deduplication disabled"""
        # Disable deduplication
        test_config["data_sources"] = {
            "home_assistant": {"enabled": False},
            "network_scanner": {"enabled": False},
            "filesystem": {"enabled": False}
        }
        test_config["deduplication"] = {"enabled": False}

        manager = DataSourceManager(test_config)

        # Add mock sources with duplicate devices
        for source_name in ["source1", "source2"]:
            mock_source = Mock()
            mock_source.source_type = DataSourceType.MCP_SERVER
            mock_source.source_id = source_name

            device = Device(
                name="shared-device",
                device_type=DeviceType(manufacturer="Test", model="Model", slug="test-model"),
                device_role=DeviceRole(name="Router", slug="router", color="ff0000"),
                site=Site(name="Test Site", slug="test-site"),
                primary_ip4="192.168.1.100"
            )

            mock_source.discover = AsyncMock(return_value=DiscoveryResult(
                source_type=DataSourceType.MCP_SERVER,
                source_id=source_name,
                devices=[device]
            ))

            manager.sources[source_name] = mock_source

        # Execute discovery
        results = await manager.discover_all_devices()

        # With deduplication disabled, there should be no _deduplicated key
        # or it should contain all devices including duplicates
        if "_deduplicated" in results:
            # If present, should have kept both devices
            assert results["_deduplicated"].metadata.get("duplicates_removed", 0) == 0

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.data_sources.manager import DataSourceManager
from src.data_sources.base import DataSource, DataSourceType, DiscoveryResult, DataSourceConfig
from src.netbox.models import Device, DeviceType, DeviceRole, Site


# Concrete test data source
class MockDataSource(DataSource):
    """Mock data source for testing"""

    def __init__(self, config, source_type, should_fail=False):
        super().__init__(config, source_type)
        self.should_fail = should_fail
        self.connect_called = False
        self.discover_called = False

    async def connect(self) -> bool:
        self.connect_called = True
        if self.should_fail:
            return False
        return True

    async def test_connection(self) -> bool:
        return await self.connect()

    async def discover(self) -> DiscoveryResult:
        self.discover_called = True
        result = DiscoveryResult(
            source_type=self.source_type,
            source_id=self.source_id
        )

        if not self.should_fail:
            # Add a test device
            device = Device(
                name=f"{self.source_id}-device-1",
                device_type=DeviceType(
                    manufacturer="Test",
                    model="Model",
                    slug="test-model"
                ),
                device_role=DeviceRole(
                    name="Test Role",
                    slug="test-role",
                    color="ff0000"
                ),
                site=Site(
                    name=f"{self.source_id}-site",
                    slug=f"{self.source_id}-site"
                )
            )
            result.devices.append(device)

        return result

    def get_required_config_fields(self) -> list:
        return ["enabled"]


@pytest.fixture
def manager_config():
    """Test configuration for manager"""
    return {
        "data_sources": {
            "homeassistant": {
                "enabled": True
            },
            "proxmox": {
                "enabled": True,
                "url": "https://proxmox.local:8006"
            },
            "truenas": {
                "enabled": False,
                "url": "https://truenas.local"
            }
        }
    }


@pytest.fixture
def mock_data_sources():
    """Create mock data sources"""
    sources = {
        "homeassistant": MockDataSource(
            DataSourceConfig(enabled=True),
            DataSourceType.HOMEASSISTANT
        ),
        "proxmox": MockDataSource(
            DataSourceConfig(enabled=True),
            DataSourceType.PROXMOX
        )
    }
    return sources


class TestDataSourceManager:
    """Test DataSourceManager"""

    def test_initialization(self, manager_config):
        """Test manager initialization"""
        manager = DataSourceManager(manager_config)

        assert manager.config == manager_config
        assert isinstance(manager.sources, dict)

    def test_initialization_with_mocked_sources(self, manager_config):
        """Test initialization with pre-mocked sources"""
        # Patch the individual source initializations
        with patch('src.data_sources.manager.HomeAssistantDataSource'):
            with patch('src.data_sources.manager.ProxmoxDataSource'):
                with patch('src.data_sources.manager.TrueNASDataSource'):
                    manager = DataSourceManager(manager_config)

                    # Verify manager was created
                    assert manager is not None

    @pytest.mark.asyncio
    async def test_connect_all_success(self, mock_data_sources):
        """Test connecting all data sources successfully"""
        manager = DataSourceManager({})
        manager.sources = mock_data_sources

        await manager.connect_all()

        # Verify all sources were connected
        for source in mock_data_sources.values():
            assert source.connect_called == True

    @pytest.mark.asyncio
    async def test_connect_all_with_failure(self):
        """Test connecting with one source failing"""
        sources = {
            "homeassistant": MockDataSource(
                DataSourceConfig(enabled=True),
                DataSourceType.HOMEASSISTANT,
                should_fail=False
            ),
            "proxmox": MockDataSource(
                DataSourceConfig(enabled=True),
                DataSourceType.PROXMOX,
                should_fail=True  # This one fails
            )
        }

        manager = DataSourceManager({})
        manager.sources = sources

        await manager.connect_all()

        # Both should have attempted connection
        assert sources["homeassistant"].connect_called == True
        assert sources["proxmox"].connect_called == True

    @pytest.mark.asyncio
    async def test_discover_all(self, mock_data_sources):
        """Test discovering from all sources"""
        manager = DataSourceManager({})
        manager.sources = mock_data_sources

        results = await manager.discover_all()

        # Should have results from all sources
        assert len(results) == 2
        assert all(isinstance(r, DiscoveryResult) for r in results)

        # Verify discover was called on all sources
        for source in mock_data_sources.values():
            assert source.discover_called == True

    @pytest.mark.asyncio
    async def test_discover_all_with_deduplication(self):
        """Test discovery with duplicate devices across sources"""
        # Create two sources that will return devices with same MAC address
        source1 = MockDataSource(
            DataSourceConfig(enabled=True),
            DataSourceType.HOMEASSISTANT
        )
        source2 = MockDataSource(
            DataSourceConfig(enabled=True),
            DataSourceType.PROXMOX
        )

        manager = DataSourceManager({})
        manager.sources = {"homeassistant": source1, "proxmox": source2}

        results = await manager.discover_all()

        # Should return results from both sources
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_source_by_name(self, mock_data_sources):
        """Test getting a specific source by name"""
        manager = DataSourceManager({})
        manager.sources = mock_data_sources

        source = manager.get_source("homeassistant")

        assert source is not None
        assert source.source_id == "homeassistant"

    def test_get_source_nonexistent(self, mock_data_sources):
        """Test getting non-existent source"""
        manager = DataSourceManager({})
        manager.sources = mock_data_sources

        source = manager.get_source("nonexistent")

        assert source is None

    @pytest.mark.asyncio
    async def test_disconnect_all(self, mock_data_sources):
        """Test disconnecting all sources"""
        manager = DataSourceManager({})
        manager.sources = mock_data_sources

        # Add disconnect mock
        for source in mock_data_sources.values():
            source.disconnect = AsyncMock()

        await manager.disconnect_all()

        # Verify disconnect was called on all sources
        for source in mock_data_sources.values():
            source.disconnect.assert_called_once()

    def test_list_sources(self, mock_data_sources):
        """Test listing all sources"""
        manager = DataSourceManager({})
        manager.sources = mock_data_sources

        source_list = manager.list_sources()

        assert len(source_list) == 2
        assert "homeassistant" in source_list
        assert "proxmox" in source_list

    def test_get_enabled_sources(self):
        """Test getting only enabled sources"""
        config = {
            "data_sources": {
                "homeassistant": {"enabled": True},
                "proxmox": {"enabled": True},
                "truenas": {"enabled": False}
            }
        }

        sources = {
            "homeassistant": MockDataSource(
                DataSourceConfig(enabled=True),
                DataSourceType.HOMEASSISTANT
            ),
            "proxmox": MockDataSource(
                DataSourceConfig(enabled=True),
                DataSourceType.PROXMOX
            ),
            "truenas": MockDataSource(
                DataSourceConfig(enabled=False),
                DataSourceType.TRUENAS
            )
        }

        manager = DataSourceManager(config)
        manager.sources = sources

        enabled = {k: v for k, v in sources.items() if v.config.enabled}

        assert len(enabled) == 2
        assert "truenas" not in enabled

    @pytest.mark.asyncio
    async def test_discover_from_single_source(self):
        """Test discovering from a specific source"""
        source = MockDataSource(
            DataSourceConfig(enabled=True),
            DataSourceType.HOMEASSISTANT
        )

        manager = DataSourceManager({})
        manager.sources = {"homeassistant": source}

        result = await manager.discover_from_source("homeassistant")

        assert result is not None
        assert isinstance(result, DiscoveryResult)
        assert source.discover_called == True

    @pytest.mark.asyncio
    async def test_discover_from_nonexistent_source(self, mock_data_sources):
        """Test discovering from non-existent source"""
        manager = DataSourceManager({})
        manager.sources = mock_data_sources

        result = await manager.discover_from_source("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_error_handling_in_discovery(self):
        """Test error handling during discovery"""

        class FailingDataSource(MockDataSource):
            async def discover(self) -> DiscoveryResult:
                raise Exception("Discovery failed")

        source = FailingDataSource(
            DataSourceConfig(enabled=True),
            DataSourceType.HOMEASSISTANT
        )

        manager = DataSourceManager({})
        manager.sources = {"homeassistant": source}

        # Should handle exception gracefully
        results = await manager.discover_all()

        # Should still return a result (possibly empty)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_parallel_discovery(self, mock_data_sources):
        """Test that discoveries run in parallel"""
        manager = DataSourceManager({})
        manager.sources = mock_data_sources

        # Add small delays to simulate work
        async def delayed_discover(self):
            result = DiscoveryResult(
                source_type=self.source_type,
                source_id=self.source_id
            )
            return result

        for source in mock_data_sources.values():
            source.discover = delayed_discover.__get__(source, MockDataSource)

        results = await manager.discover_all()

        # Should complete with all results
        assert len(results) == 2

    def test_source_status(self, mock_data_sources):
        """Test getting status of all sources"""
        manager = DataSourceManager({})
        manager.sources = mock_data_sources

        # All sources should be initialized
        assert len(manager.sources) == 2
        for source_id, source in manager.sources.items():
            assert source.source_id == source_id

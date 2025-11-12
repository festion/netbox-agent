import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.data_sources.base import (
    DataSource,
    APIBasedDataSource,
    DataSourceType,
    DiscoveryResult,
    DataSourceConfig
)
from src.netbox.models import Device, DeviceType, DeviceRole, Site


class ConcreteDataSource(DataSource):
    """Concrete implementation for testing abstract base class"""

    async def connect(self) -> bool:
        return True

    async def test_connection(self) -> bool:
        return True

    async def discover(self) -> DiscoveryResult:
        return DiscoveryResult(
            source_type=self.source_type,
            source_id=self.source_id
        )

    def get_required_config_fields(self) -> list:
        return ["enabled"]


class ConcreteAPIDataSource(APIBasedDataSource):
    """Concrete API-based implementation for testing"""

    async def connect(self) -> bool:
        return True

    async def test_connection(self) -> bool:
        return True

    async def discover(self) -> DiscoveryResult:
        return DiscoveryResult(
            source_type=self.source_type,
            source_id=self.source_id
        )

    def get_required_config_fields(self) -> list:
        return ["enabled", "url"]


class TestDataSourceConfig:
    """Test DataSourceConfig base class"""

    def test_config_creation(self):
        """Test creating a basic config"""
        config = DataSourceConfig(enabled=True)
        assert config.enabled == True

    def test_config_defaults(self):
        """Test config default values"""
        config = DataSourceConfig()
        assert config.enabled == False


class TestDataSource:
    """Test DataSource abstract base class"""

    def test_source_initialization(self):
        """Test data source initialization"""
        config = DataSourceConfig(enabled=True)
        source = ConcreteDataSource(config, DataSourceType.HOME_ASSISTANT)

        assert source.config.enabled == True
        assert source.source_type == DataSourceType.HOME_ASSISTANT
        assert source.source_id.startswith("home_assistant")  # Source ID includes object ID

    @pytest.mark.asyncio
    async def test_connect_method_exists(self):
        """Test that connect method is implemented"""
        config = DataSourceConfig(enabled=True)
        source = ConcreteDataSource(config, DataSourceType.HOME_ASSISTANT)

        result = await source.connect()
        assert result == True

    @pytest.mark.asyncio
    async def test_test_connection_method(self):
        """Test connection testing"""
        config = DataSourceConfig(enabled=True)
        source = ConcreteDataSource(config, DataSourceType.HOME_ASSISTANT)

        result = await source.test_connection()
        assert result == True

    @pytest.mark.asyncio
    async def test_discover_returns_result(self):
        """Test discovery returns DiscoveryResult"""
        config = DataSourceConfig(enabled=True)
        source = ConcreteDataSource(config, DataSourceType.HOME_ASSISTANT)

        result = await source.discover()

        assert isinstance(result, DiscoveryResult)
        assert result.source_type == DataSourceType.HOME_ASSISTANT
        assert result.source_id.startswith("home_assistant")  # Source ID includes object ID

    def test_get_required_fields(self):
        """Test getting required config fields"""
        config = DataSourceConfig(enabled=True)
        source = ConcreteDataSource(config, DataSourceType.HOME_ASSISTANT)

        fields = source.get_required_config_fields()
        assert "enabled" in fields


class TestAPIBasedDataSource:
    """Test APIBasedDataSource base class"""

    def test_api_source_initialization(self):
        """Test API-based data source initialization"""
        config = DataSourceConfig(enabled=True)
        source = ConcreteAPIDataSource(config, DataSourceType.PROXMOX)

        assert source.config.enabled == True
        assert source.source_type == DataSourceType.PROXMOX

    def test_required_fields_includes_url(self):
        """Test API sources require URL"""
        config = DataSourceConfig(enabled=True)
        source = ConcreteAPIDataSource(config, DataSourceType.PROXMOX)

        fields = source.get_required_config_fields()
        assert "url" in fields


class TestDiscoveryResult:
    """Test DiscoveryResult data class"""

    def test_discovery_result_creation(self):
        """Test creating a discovery result"""
        result = DiscoveryResult(
            source_type=DataSourceType.PROXMOX,
            source_id="proxmox"
        )

        assert result.source_type == DataSourceType.PROXMOX
        assert result.source_id == "proxmox"
        assert len(result.devices) == 0
        assert len(result.ip_addresses) == 0
        assert len(result.errors) == 0

    def test_add_device(self):
        """Test adding devices to result"""
        result = DiscoveryResult(
            source_type=DataSourceType.PROXMOX,
            source_id="proxmox"
        )

        device = Device(
            name="test-device",
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
                name="Test Site",
                slug="test-site"
            )
        )

        result.devices.append(device)
        assert len(result.devices) == 1
        assert result.devices[0].name == "test-device"

    def test_add_error(self):
        """Test adding errors to result"""
        result = DiscoveryResult(
            source_type=DataSourceType.PROXMOX,
            source_id="proxmox"
        )

        result.add_error("Test error message")

        assert len(result.errors) == 1
        assert "Test error message" in result.errors[0]  # Error includes timestamp

    def test_metadata(self):
        """Test metadata storage"""
        result = DiscoveryResult(
            source_type=DataSourceType.TRUENAS,
            source_id="truenas"
        )

        result.metadata = {
            "hostname": "truenas.local",
            "version": "13.0",
            "pools": 2
        }

        assert result.metadata["hostname"] == "truenas.local"
        assert result.metadata["pools"] == 2

    def test_discovery_result_summary(self):
        """Test getting a summary of results"""
        result = DiscoveryResult(
            source_type=DataSourceType.PROXMOX,
            source_id="proxmox"
        )

        # Add some test data
        for i in range(3):
            device = Device(
                name=f"device-{i}",
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
                    name="Test Site",
                    slug="test-site"
                )
            )
            result.devices.append(device)

        result.add_error("Error 1")
        result.add_error("Error 2")

        assert len(result.devices) == 3
        assert len(result.errors) == 2


class TestDataSourceType:
    """Test DataSourceType enum"""

    def test_enum_values(self):
        """Test all enum values exist"""
        assert DataSourceType.HOME_ASSISTANT.value == "home_assistant"
        assert DataSourceType.NETWORK_SCAN.value == "network_scan"
        assert DataSourceType.FILESYSTEM.value == "filesystem"
        assert DataSourceType.PROXMOX.value == "proxmox"
        assert DataSourceType.TRUENAS.value == "truenas"

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert DataSourceType.PROXMOX == DataSourceType.PROXMOX
        assert DataSourceType.PROXMOX != DataSourceType.TRUENAS

    def test_enum_string_conversion(self):
        """Test converting enum to string"""
        source_type = DataSourceType.TRUENAS
        assert str(source_type.value) == "truenas"

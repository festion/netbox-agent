import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import aiohttp
from src.data_sources.truenas import TrueNASDataSource, TrueNASDataSourceConfig
from src.data_sources.base import DataSourceType, DiscoveryResult
from src.netbox.models import Device


@pytest.fixture
def truenas_config():
    """TrueNAS data source configuration"""
    return TrueNASDataSourceConfig(
        enabled=True,
        url="https://truenas.local",
        api_key="test-api-key",
        verify_ssl=False,
        include_pools=True,
        include_datasets=True,
        include_shares=True,
        include_network=True
    )


@pytest.fixture
def mock_truenas_system_info():
    """Mock TrueNAS system info"""
    return {
        "hostname": "truenas.local",
        "version": "TrueNAS-13.0-U6.7",
        "system_manufacturer": "Supermicro",
        "system_product": "X11SPL-F",
        "system_serial": "0123456789"
    }


@pytest.fixture
def mock_truenas_interfaces():
    """Mock TrueNAS network interfaces"""
    return [
        {
            "name": "igb0",
            "state": {
                "link_state": "LINK_STATE_UP",
                "aliases": [
                    {
                        "type": "INET",
                        "address": "192.168.1.98",
                        "netmask": 24
                    }
                ]
            }
        },
        {
            "name": "igb1",
            "state": {
                "link_state": "LINK_STATE_DOWN",
                "aliases": []
            }
        }
    ]


@pytest.fixture
def mock_truenas_pools():
    """Mock TrueNAS storage pools"""
    return [
        {
            "name": "tank",
            "status": "ONLINE",
            "size": 10995116277760,
            "allocated": 5497558138880,
            "free": 5497558138880
        },
        {
            "name": "backup",
            "status": "ONLINE",
            "size": 2199023255552,
            "allocated": 1099511627776,
            "free": 1099511627776
        }
    ]


@pytest.fixture
def mock_truenas_datasets():
    """Mock TrueNAS datasets"""
    return [
        {
            "name": "tank/data",
            "type": "FILESYSTEM",
            "used": {"parsed": 1099511627776},
            "available": {"parsed": 4398046511104}
        },
        {
            "name": "tank/media",
            "type": "FILESYSTEM",
            "used": {"parsed": 2199023255552},
            "available": {"parsed": 2199023255552}
        }
    ]


@pytest.fixture
def mock_truenas_nfs_shares():
    """Mock TrueNAS NFS shares"""
    return [
        {
            "path": "/mnt/tank/data",
            "enabled": True,
            "networks": ["192.168.1.0/24"]
        }
    ]


@pytest.fixture
def mock_truenas_smb_shares():
    """Mock TrueNAS SMB shares"""
    return [
        {
            "name": "media",
            "path": "/mnt/tank/media",
            "enabled": True
        },
        {
            "name": "backups",
            "path": "/mnt/backup",
            "enabled": True
        }
    ]


class TestTrueNASDataSourceConfig:
    """Test TrueNAS data source configuration"""

    def test_config_creation(self):
        """Test creating TrueNAS config"""
        config = TrueNASDataSourceConfig(
            enabled=True,
            url="https://truenas.local",
            api_key="test-key"
        )

        assert config.enabled == True
        assert config.url == "https://truenas.local"
        assert config.api_key == "test-key"

    def test_config_defaults(self):
        """Test config default values"""
        config = TrueNASDataSourceConfig(
            enabled=True,
            url="https://truenas.local",
            api_key="test-key"
        )

        assert config.verify_ssl == False
        assert config.include_pools == True
        assert config.include_datasets == True
        assert config.include_shares == True
        assert config.include_network == True


class TestTrueNASDataSource:
    """Test TrueNAS data source"""

    def test_initialization(self, truenas_config):
        """Test TrueNAS data source initialization"""
        source = TrueNASDataSource(truenas_config)

        assert source.config.enabled == True
        assert source.source_type == DataSourceType.TRUENAS
        assert source.source_id == "truenas"
        assert source.truenas_config == truenas_config

    def test_required_config_fields(self, truenas_config):
        """Test required configuration fields"""
        source = TrueNASDataSource(truenas_config)
        fields = source.get_required_config_fields()

        assert "url" in fields
        assert "api_key" in fields
        assert "enabled" in fields

    @pytest.mark.asyncio
    async def test_connect_success(self, truenas_config, mock_truenas_system_info):
        """Test successful connection to TrueNAS"""
        source = TrueNASDataSource(truenas_config)

        # Mock aiohttp session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_truenas_system_info)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session.get = Mock(return_value=mock_response)
            mock_session_class.return_value = mock_session

            source.session = mock_session

            result = await source.connect()

            assert result == True
            assert source.system_info is not None
            assert source.system_info["hostname"] == "truenas.local"

    @pytest.mark.asyncio
    async def test_connect_failure(self, truenas_config):
        """Test failed connection to TrueNAS"""
        source = TrueNASDataSource(truenas_config)

        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session.get = Mock(return_value=mock_response)
            mock_session_class.return_value = mock_session

            source.session = mock_session

            result = await source.connect()

            assert result == False

    @pytest.mark.asyncio
    async def test_discover_basic(self, truenas_config, mock_truenas_system_info):
        """Test basic discovery without optional components"""
        source = TrueNASDataSource(truenas_config)
        source.system_info = mock_truenas_system_info

        # Mock session to prevent actual API calls
        source.session = AsyncMock()

        # Mock connect
        with patch.object(source, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True

            # Mock discovery methods to do nothing
            with patch.object(source, '_discover_network_interfaces', new_callable=AsyncMock):
                with patch.object(source, '_discover_storage_pools', new_callable=AsyncMock):
                    with patch.object(source, '_discover_datasets', new_callable=AsyncMock):
                        with patch.object(source, '_discover_shares', new_callable=AsyncMock):
                            result = await source.discover()

            assert isinstance(result, DiscoveryResult)
            assert result.source_type == DataSourceType.TRUENAS
            assert len(result.devices) == 1
            assert result.devices[0].name == "truenas.local"
            assert result.devices[0].platform == "TrueNAS Core"

    @pytest.mark.asyncio
    async def test_discover_with_network(self, truenas_config, mock_truenas_system_info, mock_truenas_interfaces):
        """Test discovery with network interfaces"""
        source = TrueNASDataSource(truenas_config)
        source.system_info = mock_truenas_system_info

        # Mock network interface response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_truenas_interfaces)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = Mock(return_value=mock_response)
        source.session = mock_session

        result = DiscoveryResult(source_type=DataSourceType.TRUENAS, source_id="truenas")
        device = Mock()

        await source._discover_network_interfaces(result, device)

        assert len(result.ip_addresses) == 1
        assert result.ip_addresses[0].address == "192.168.1.98/24"

    @pytest.mark.asyncio
    async def test_discover_storage_pools(self, truenas_config, mock_truenas_pools):
        """Test discovering storage pools"""
        source = TrueNASDataSource(truenas_config)
        source.system_info = {"hostname": "truenas.local"}

        # Mock pools response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_truenas_pools)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = Mock(return_value=mock_response)
        source.session = mock_session

        result = DiscoveryResult(source_type=DataSourceType.TRUENAS, source_id="truenas")

        await source._discover_storage_pools(result)

        assert result.metadata is not None
        assert "storage_pools" in result.metadata
        assert len(result.metadata["storage_pools"]) == 2
        assert result.metadata["storage_pools"][0]["name"] == "tank"

    @pytest.mark.asyncio
    async def test_discover_datasets(self, truenas_config, mock_truenas_datasets):
        """Test discovering datasets"""
        source = TrueNASDataSource(truenas_config)
        source.system_info = {"hostname": "truenas.local"}

        # Mock datasets response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_truenas_datasets)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = Mock(return_value=mock_response)
        source.session = mock_session

        result = DiscoveryResult(source_type=DataSourceType.TRUENAS, source_id="truenas")

        await source._discover_datasets(result)

        assert result.metadata is not None
        assert "datasets" in result.metadata
        assert "total_datasets" in result.metadata
        assert result.metadata["total_datasets"] == 2

    @pytest.mark.asyncio
    async def test_discover_shares(self, truenas_config, mock_truenas_nfs_shares, mock_truenas_smb_shares):
        """Test discovering shares"""
        source = TrueNASDataSource(truenas_config)
        source.system_info = {"hostname": "truenas.local"}

        # Create a function to return appropriate mocks based on URL
        def mock_get_response(url, **kwargs):
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            if "/sharing/nfs" in url:
                mock_response.json = AsyncMock(return_value=mock_truenas_nfs_shares)
            elif "/sharing/smb" in url:
                mock_response.json = AsyncMock(return_value=mock_truenas_smb_shares)
            elif "/iscsi/target" in url:
                mock_response.json = AsyncMock(return_value=[])
            else:
                mock_response.json = AsyncMock(return_value={})

            return mock_response

        mock_session = AsyncMock()
        mock_session.get = Mock(side_effect=mock_get_response)
        source.session = mock_session

        result = DiscoveryResult(source_type=DataSourceType.TRUENAS, source_id="truenas")

        await source._discover_shares(result)

        assert result.metadata is not None
        assert "shares" in result.metadata
        assert len(result.metadata["shares"]["nfs_shares"]) == 1
        assert len(result.metadata["shares"]["smb_shares"]) == 2
        assert len(result.metadata["shares"]["iscsi_targets"]) == 0

    @pytest.mark.asyncio
    async def test_discover_connection_failure(self, truenas_config):
        """Test discovery when connection fails"""
        source = TrueNASDataSource(truenas_config)

        # Mock failed connection
        with patch.object(source, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = False

            result = await source.discover()

            assert len(result.errors) > 0
            assert "Failed to connect" in result.errors[0]

    @pytest.mark.asyncio
    async def test_disconnect(self, truenas_config):
        """Test disconnection"""
        source = TrueNASDataSource(truenas_config)

        # Mock session
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        source.session = mock_session

        await source.disconnect()

        mock_session.close.assert_called_once()
        assert source.session is None

    @pytest.mark.asyncio
    async def test_test_connection(self, truenas_config):
        """Test connection testing"""
        source = TrueNASDataSource(truenas_config)

        # Mock connect
        with patch.object(source, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True

            result = await source.test_connection()

            assert result == True
            mock_connect.assert_called_once()

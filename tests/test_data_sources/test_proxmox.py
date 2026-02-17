import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.data_sources.proxmox import ProxmoxDataSource, ProxmoxDataSourceConfig
from src.data_sources.base import DataSourceType, DiscoveryResult
from src.netbox.models import Device


@pytest.fixture
def proxmox_config():
    """Proxmox data source configuration"""
    return ProxmoxDataSourceConfig(
        enabled=True,
        url="https://test-proxmox.local:8006",
        username="root@pam",
        token="test-token",
        verify_ssl=False,
        include_stopped=True,
        include_containers=True,
        include_vms=True,
        node_as_site=True,
        cluster_name="test-cluster"
    )


@pytest.fixture
def mock_mcp_proxmox_tools():
    """Mock MCP Proxmox tools"""
    tools = {
        "get_system_info": {
            "version": "7.4-3",
            "hostname": "pve-test",
            "cluster": "test-cluster"
        },
        "get_node_status": {
            "node": "pve-node1",
            "status": "online",
            "uptime": 86400,
            "cpu": 0.25,
            "memory": {
                "total": 67108864000,
                "used": 33554432000
            }
        },
        "list_virtual_machines": [
            {
                "vmid": "100",
                "name": "test-vm-1",
                "status": "running",
                "node": "pve-node1",
                "type": "qemu",
                "cpus": 2,
                "memory": 4096
            },
            {
                "vmid": "101",
                "name": "test-vm-2",
                "status": "stopped",
                "node": "pve-node1",
                "type": "qemu",
                "cpus": 4,
                "memory": 8192
            }
        ],
        "list_containers": [
            {
                "vmid": "200",
                "name": "test-ct-1",
                "status": "running",
                "node": "pve-node1",
                "type": "lxc",
                "cpus": 1,
                "memory": 512
            }
        ]
    }
    return tools


class TestProxmoxDataSourceConfig:
    """Test Proxmox data source configuration"""

    def test_config_creation(self):
        """Test creating Proxmox config"""
        config = ProxmoxDataSourceConfig(
            enabled=True,
            url="https://proxmox.local:8006",
            username="root@pam",
            token="test-token"
        )

        assert config.enabled == True
        assert config.url == "https://proxmox.local:8006"
        assert config.username == "root@pam"
        assert config.token == "test-token"

    def test_config_defaults(self):
        """Test config default values"""
        config = ProxmoxDataSourceConfig(
            enabled=True,
            url="https://proxmox.local:8006"
        )

        assert config.verify_ssl == False
        assert config.include_stopped == True
        assert config.include_containers == True
        assert config.include_vms == True
        assert config.node_as_site == True


class TestProxmoxDataSource:
    """Test Proxmox data source"""

    def test_initialization(self, proxmox_config):
        """Test Proxmox data source initialization"""
        source = ProxmoxDataSource(proxmox_config)

        assert source.config.enabled == True
        assert source.source_type == DataSourceType.PROXMOX
        assert source.source_id == "proxmox"

    def test_required_config_fields(self, proxmox_config):
        """Test required configuration fields"""
        source = ProxmoxDataSource(proxmox_config)
        fields = source.get_required_config_fields()

        assert "url" in fields
        assert "username" in fields
        assert "enabled" in fields

    @pytest.mark.asyncio
    async def test_connect_success(self, proxmox_config):
        """Test successful connection to Proxmox"""
        source = ProxmoxDataSource(proxmox_config)

        result = await source.connect()

        # Current implementation always returns True
        assert result == True

    @pytest.mark.asyncio
    async def test_connect_failure(self, proxmox_config):
        """Test failed connection to Proxmox"""
        source = ProxmoxDataSource(proxmox_config)

        # Mock MCP client failure
        with patch.object(source, 'mcp_client') as mock_client:
            mock_client.connect = AsyncMock(side_effect=Exception("Connection failed"))

            result = await source.connect()

            assert result == False

    @pytest.mark.asyncio
    async def test_discover_vms(self, proxmox_config, mock_mcp_proxmox_tools):
        """Test discovering VMs"""
        source = ProxmoxDataSource(proxmox_config)

        # Mock MCP client
        with patch.object(source, 'mcp_client') as mock_client:
            mock_client.connect = AsyncMock(return_value=True)
            mock_client.call_tool = AsyncMock(side_effect=lambda tool, **kwargs: {
                "mcp__proxmox-mcp__get_system_info": mock_mcp_proxmox_tools["get_system_info"],
                "mcp__proxmox-mcp__list_virtual_machines": mock_mcp_proxmox_tools["list_virtual_machines"],
                "mcp__proxmox-mcp__list_containers": []
            }.get(tool, {}))
            mock_client.disconnect = AsyncMock()

            result = await source.discover()

            assert isinstance(result, DiscoveryResult)
            assert result.source_type == DataSourceType.PROXMOX
            assert len(result.devices) > 0
            assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_discover_containers(self, proxmox_config, mock_mcp_proxmox_tools):
        """Test discovering LXC containers"""
        source = ProxmoxDataSource(proxmox_config)

        # Mock MCP client
        with patch.object(source, 'mcp_client') as mock_client:
            mock_client.connect = AsyncMock(return_value=True)
            mock_client.call_tool = AsyncMock(side_effect=lambda tool, **kwargs: {
                "mcp__proxmox-mcp__get_system_info": mock_mcp_proxmox_tools["get_system_info"],
                "mcp__proxmox-mcp__list_virtual_machines": [],
                "mcp__proxmox-mcp__list_containers": mock_mcp_proxmox_tools["list_containers"]
            }.get(tool, {}))
            mock_client.disconnect = AsyncMock()

            result = await source.discover()

            assert isinstance(result, DiscoveryResult)
            assert len(result.devices) > 0

    @pytest.mark.asyncio
    async def test_discover_with_stopped_vms(self, proxmox_config, mock_mcp_proxmox_tools):
        """Test discovering including stopped VMs"""
        source = ProxmoxDataSource(proxmox_config)
        source.config.include_stopped = True

        # Mock MCP client
        with patch.object(source, 'mcp_client') as mock_client:
            mock_client.connect = AsyncMock(return_value=True)
            mock_client.call_tool = AsyncMock(side_effect=lambda tool, **kwargs: {
                "mcp__proxmox-mcp__get_system_info": mock_mcp_proxmox_tools["get_system_info"],
                "mcp__proxmox-mcp__list_virtual_machines": mock_mcp_proxmox_tools["list_virtual_machines"],
                "mcp__proxmox-mcp__list_containers": []
            }.get(tool, {}))
            mock_client.disconnect = AsyncMock()

            result = await source.discover()

            # Should include both running and stopped VMs
            assert len(result.devices) == 2

    @pytest.mark.asyncio
    async def test_discover_exclude_stopped_vms(self, proxmox_config, mock_mcp_proxmox_tools):
        """Test discovering excluding stopped VMs"""
        source = ProxmoxDataSource(proxmox_config)
        source.config.include_stopped = False

        # Mock MCP client
        with patch.object(source, 'mcp_client') as mock_client:
            mock_client.connect = AsyncMock(return_value=True)
            mock_client.call_tool = AsyncMock(side_effect=lambda tool, **kwargs: {
                "mcp__proxmox-mcp__get_system_info": mock_mcp_proxmox_tools["get_system_info"],
                "mcp__proxmox-mcp__list_virtual_machines": mock_mcp_proxmox_tools["list_virtual_machines"],
                "mcp__proxmox-mcp__list_containers": []
            }.get(tool, {}))
            mock_client.disconnect = AsyncMock()

            result = await source.discover()

            # Should only include running VM
            assert len(result.devices) == 1

    @pytest.mark.asyncio
    async def test_discover_connection_failure(self, proxmox_config):
        """Test discovery when connection fails"""
        source = ProxmoxDataSource(proxmox_config)

        # Mock connection failure
        with patch.object(source, 'mcp_client') as mock_client:
            mock_client.connect = AsyncMock(return_value=False)

            result = await source.discover()

            assert len(result.errors) > 0
            assert "Failed to connect" in result.errors[0]

    @pytest.mark.asyncio
    async def test_discover_metadata(self, proxmox_config, mock_mcp_proxmox_tools):
        """Test discovery result metadata"""
        source = ProxmoxDataSource(proxmox_config)

        # Mock MCP client
        with patch.object(source, 'mcp_client') as mock_client:
            mock_client.connect = AsyncMock(return_value=True)
            mock_client.call_tool = AsyncMock(side_effect=lambda tool, **kwargs: {
                "mcp__proxmox-mcp__get_system_info": mock_mcp_proxmox_tools["get_system_info"],
                "mcp__proxmox-mcp__list_virtual_machines": mock_mcp_proxmox_tools["list_virtual_machines"],
                "mcp__proxmox-mcp__list_containers": mock_mcp_proxmox_tools["list_containers"]
            }.get(tool, {}))
            mock_client.disconnect = AsyncMock()

            result = await source.discover()

            assert result.metadata is not None
            assert "cluster_name" in result.metadata
            assert result.metadata["cluster_name"] == "test-cluster"

    @pytest.mark.asyncio
    async def test_test_connection(self, proxmox_config):
        """Test connection testing"""
        source = ProxmoxDataSource(proxmox_config)

        # Mock successful connection
        with patch.object(source, 'connect') as mock_connect:
            mock_connect.return_value = AsyncMock(return_value=True)()

            result = await source.test_connection()

            assert result == True

    @pytest.mark.asyncio
    async def test_disconnect(self, proxmox_config):
        """Test disconnection"""
        source = ProxmoxDataSource(proxmox_config)

        # Mock MCP client
        with patch.object(source, 'mcp_client') as mock_client:
            mock_client.disconnect = AsyncMock()

            await source.disconnect()

            mock_client.disconnect.assert_called_once()

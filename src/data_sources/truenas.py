import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from src.data_sources.base import APIBasedDataSource, DataSourceType, DiscoveryResult, DataSourceConfig
from src.netbox.models import Device, IPAddress, Interface, DeviceType, DeviceRole, Site
import structlog


class TrueNASDataSourceConfig(DataSourceConfig):
    """Configuration for TrueNAS Core data source"""
    url: str
    api_key: str = ""
    verify_ssl: bool = False
    include_pools: bool = True
    include_datasets: bool = True
    include_shares: bool = True
    include_network: bool = True


class TrueNASDataSource(APIBasedDataSource):
    """Data source for TrueNAS Core integration"""

    def __init__(self, config: TrueNASDataSourceConfig):
        super().__init__(config, DataSourceType.TRUENAS)
        self.truenas_config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.system_info = None
        self.logger = structlog.get_logger(__name__)

    async def connect(self) -> bool:
        """Test connection to TrueNAS Core"""
        try:
            if not self.session:
                connector = aiohttp.TCPConnector(ssl=False if not self.truenas_config.verify_ssl else None)
                self.session = aiohttp.ClientSession(connector=connector)

            headers = {
                'Authorization': f'Bearer {self.truenas_config.api_key}',
                'Content-Type': 'application/json'
            }

            async with self.session.get(
                f"{self.truenas_config.url}/api/v2.0/system/info",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    self.system_info = await response.json()
                    self.logger.info("TrueNAS Core connection successful",
                                   version=self.system_info.get('version'))
                    return True
                else:
                    self.logger.error("TrueNAS Core connection failed",
                                    status=response.status,
                                    text=await response.text())
                    return False

        except Exception as e:
            self.logger.error("TrueNAS Core connection error", error=str(e))
            return False

    async def test_connection(self) -> bool:
        """Test connection to TrueNAS Core"""
        return await self.connect()

    async def discover(self) -> DiscoveryResult:
        """Discover devices from TrueNAS Core"""
        result = DiscoveryResult(
            source_type=self.source_type,
            source_id=self.source_id
        )

        try:
            # Ensure we're connected
            if not self.session or not self.system_info:
                if not await self.connect():
                    result.add_error("Failed to connect to TrueNAS Core")
                    return result

            # Get system information
            hostname = self.system_info.get('hostname', 'truenas')
            version = self.system_info.get('version', 'unknown')

            # Create the TrueNAS device
            truenas_device = Device(
                name=hostname,
                device_type=DeviceType(
                    manufacturer="iXsystems",
                    model="TrueNAS Core",
                    slug="truenas-core",
                    u_height=2.0
                ),
                device_role=DeviceRole(
                    name="Storage",
                    slug="storage",
                    color="4caf50",
                    description="Network Attached Storage"
                ),
                site=Site(
                    name=f"Storage-{hostname}",
                    slug=f"storage-{hostname.lower()}",
                    description=f"TrueNAS Core: {hostname}"
                ),
                status="active",
                platform="TrueNAS Core",
                serial=self.system_info.get('system_serial'),
                custom_fields={
                    "truenas_version": version,
                    "truenas_hostname": hostname,
                    "truenas_type": "core",
                    "discovery_source": "truenas",
                    "system_manufacturer": self.system_info.get('system_manufacturer'),
                    "system_product": self.system_info.get('system_product'),
                    "last_discovered": self.last_incremental_sync.isoformat() if self.last_incremental_sync else None
                }
            )

            result.devices.append(truenas_device)

            # Get network interfaces if enabled
            if self.truenas_config.include_network:
                await self._discover_network_interfaces(result, truenas_device)

            # Get storage pools if enabled
            if self.truenas_config.include_pools:
                await self._discover_storage_pools(result)

            # Get datasets if enabled
            if self.truenas_config.include_datasets:
                await self._discover_datasets(result)

            # Get shares if enabled
            if self.truenas_config.include_shares:
                await self._discover_shares(result)

        except Exception as e:
            result.add_error(f"Discovery failed: {str(e)}")
            import traceback
            self.logger.error("TrueNAS Core discovery error",
                            error=str(e),
                            traceback=traceback.format_exc())

        result.metadata = {
            "hostname": self.system_info.get('hostname') if self.system_info else 'unknown',
            "version": self.system_info.get('version') if self.system_info else 'unknown',
            "total_devices": len(result.devices),
            "pools_included": self.truenas_config.include_pools,
            "datasets_included": self.truenas_config.include_datasets,
            "shares_included": self.truenas_config.include_shares,
            "network_included": self.truenas_config.include_network
        }

        return result

    async def _discover_network_interfaces(self, result: DiscoveryResult, device: Device):
        """Discover network interfaces from TrueNAS Core"""
        try:
            headers = {
                'Authorization': f'Bearer {self.truenas_config.api_key}',
                'Content-Type': 'application/json'
            }

            async with self.session.get(
                f"{self.truenas_config.url}/api/v2.0/interface",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    interfaces = await response.json()

                    for iface in interfaces:
                        if iface.get('state', {}).get('link_state') == 'LINK_STATE_UP':
                            # Get IP addresses for this interface
                            aliases = iface.get('state', {}).get('aliases', [])
                            for alias in aliases:
                                if alias.get('type') in ['INET', 'INET6']:
                                    ip_addr = IPAddress(
                                        address=f"{alias.get('address')}/{alias.get('netmask')}",
                                        status="active",
                                        dns_name=self.system_info.get('hostname'),
                                        description=f"TrueNAS interface {iface.get('name')}"
                                    )
                                    result.ip_addresses.append(ip_addr)

                    self.logger.info("Discovered network interfaces",
                                   count=len(interfaces))
                else:
                    self.logger.warning("Failed to get network interfaces",
                                      status=response.status)

        except Exception as e:
            self.logger.error("Failed to discover network interfaces", error=str(e))

    async def _discover_storage_pools(self, result: DiscoveryResult):
        """Discover ZFS storage pools"""
        try:
            headers = {
                'Authorization': f'Bearer {self.truenas_config.api_key}',
                'Content-Type': 'application/json'
            }

            async with self.session.get(
                f"{self.truenas_config.url}/api/v2.0/pool",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    pools = await response.json()

                    pool_info = []
                    for pool in pools:
                        pool_info.append({
                            'name': pool.get('name'),
                            'status': pool.get('status'),
                            'size': pool.get('size'),
                            'allocated': pool.get('allocated'),
                            'free': pool.get('free')
                        })

                    if pool_info:
                        result.metadata['storage_pools'] = pool_info

                    self.logger.info("Discovered storage pools", count=len(pools))
                else:
                    self.logger.warning("Failed to get storage pools",
                                      status=response.status)

        except Exception as e:
            self.logger.error("Failed to discover storage pools", error=str(e))

    async def _discover_datasets(self, result: DiscoveryResult):
        """Discover ZFS datasets"""
        try:
            headers = {
                'Authorization': f'Bearer {self.truenas_config.api_key}',
                'Content-Type': 'application/json'
            }

            async with self.session.get(
                f"{self.truenas_config.url}/api/v2.0/pool/dataset",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    datasets = await response.json()

                    dataset_info = []
                    for dataset in datasets[:10]:  # Limit to first 10 for metadata
                        dataset_info.append({
                            'name': dataset.get('name'),
                            'type': dataset.get('type'),
                            'used': dataset.get('used', {}).get('parsed'),
                            'available': dataset.get('available', {}).get('parsed')
                        })

                    if dataset_info:
                        result.metadata['datasets'] = dataset_info
                        result.metadata['total_datasets'] = len(datasets)

                    self.logger.info("Discovered datasets", count=len(datasets))
                else:
                    self.logger.warning("Failed to get datasets",
                                      status=response.status)

        except Exception as e:
            self.logger.error("Failed to discover datasets", error=str(e))

    async def _discover_shares(self, result: DiscoveryResult):
        """Discover NFS and SMB shares"""
        try:
            headers = {
                'Authorization': f'Bearer {self.truenas_config.api_key}',
                'Content-Type': 'application/json'
            }

            share_info = {
                'nfs_shares': [],
                'smb_shares': [],
                'iscsi_targets': []
            }

            # Get NFS shares
            async with self.session.get(
                f"{self.truenas_config.url}/api/v2.0/sharing/nfs",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    nfs_shares = await response.json()
                    for share in nfs_shares:
                        share_info['nfs_shares'].append({
                            'path': share.get('path'),
                            'enabled': share.get('enabled'),
                            'networks': share.get('networks', [])
                        })

            # Get SMB shares
            async with self.session.get(
                f"{self.truenas_config.url}/api/v2.0/sharing/smb",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    smb_shares = await response.json()
                    for share in smb_shares:
                        share_info['smb_shares'].append({
                            'name': share.get('name'),
                            'path': share.get('path'),
                            'enabled': share.get('enabled')
                        })

            # Get iSCSI targets
            async with self.session.get(
                f"{self.truenas_config.url}/api/v2.0/iscsi/target",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    iscsi_targets = await response.json()
                    for target in iscsi_targets:
                        share_info['iscsi_targets'].append({
                            'name': target.get('name'),
                            'alias': target.get('alias')
                        })

            result.metadata['shares'] = share_info
            total_shares = (len(share_info['nfs_shares']) +
                          len(share_info['smb_shares']) +
                          len(share_info['iscsi_targets']))

            self.logger.info("Discovered shares",
                           nfs=len(share_info['nfs_shares']),
                           smb=len(share_info['smb_shares']),
                           iscsi=len(share_info['iscsi_targets']))

        except Exception as e:
            self.logger.error("Failed to discover shares", error=str(e))

    async def disconnect(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None

    def get_required_config_fields(self) -> List[str]:
        """Return required configuration fields"""
        return ["url", "api_key", "enabled"]

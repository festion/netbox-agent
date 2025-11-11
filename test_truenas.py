#!/usr/bin/env python3
"""Test script for TrueNAS Core data source"""

import asyncio
import sys
sys.path.insert(0, '/home/dev/workspace/netbox-agent')

from src.data_sources.truenas import TrueNASDataSource, TrueNASDataSourceConfig


async def test_truenas():
    """Test TrueNAS Core connection and discovery"""

    print("=" * 60)
    print("TrueNAS Core Data Source Test")
    print("=" * 60)

    # Prompt for TrueNAS details
    print("\nPlease provide your TrueNAS Core details:")
    url = input("TrueNAS URL (e.g., https://192.168.1.100): ").strip()
    api_key = input("API Key: ").strip()

    if not url or not api_key:
        print("\nError: URL and API key are required!")
        return

    # Create configuration
    config = TrueNASDataSourceConfig(
        enabled=True,
        url=url,
        api_key=api_key,
        verify_ssl=False,
        include_pools=True,
        include_datasets=True,
        include_shares=True,
        include_network=True
    )

    # Create data source
    truenas = TrueNASDataSource(config)

    try:
        # Test connection
        print("\n" + "=" * 60)
        print("Testing Connection...")
        print("=" * 60)

        connected = await truenas.connect()

        if not connected:
            print("\n❌ Connection failed!")
            return

        print("✅ Connection successful!")

        if truenas.system_info:
            print(f"\nSystem Info:")
            print(f"  Hostname: {truenas.system_info.get('hostname')}")
            print(f"  Version: {truenas.system_info.get('version')}")
            print(f"  System: {truenas.system_info.get('system_manufacturer')} {truenas.system_info.get('system_product')}")
            if truenas.system_info.get('system_serial'):
                print(f"  Serial: {truenas.system_info.get('system_serial')}")

        # Test discovery
        print("\n" + "=" * 60)
        print("Running Discovery...")
        print("=" * 60)

        result = await truenas.discover()

        print(f"\n✅ Discovery completed!")
        print(f"\nResults:")
        print(f"  Devices discovered: {len(result.devices)}")
        print(f"  IP addresses found: {len(result.ip_addresses)}")
        print(f"  Errors: {len(result.errors)}")

        if result.errors:
            print(f"\n  Errors encountered:")
            for error in result.errors:
                print(f"    - {error}")

        # Show discovered devices
        if result.devices:
            print(f"\n  Devices:")
            for device in result.devices:
                print(f"    - {device.name} ({device.device_type.model})")
                print(f"      Platform: {device.platform}")
                if hasattr(device, 'serial') and device.serial:
                    print(f"      Serial: {device.serial}")

        # Show metadata
        if result.metadata:
            print(f"\n  Discovery Metadata:")
            print(f"    Hostname: {result.metadata.get('hostname')}")
            print(f"    Version: {result.metadata.get('version')}")

            if 'storage_pools' in result.metadata:
                pools = result.metadata['storage_pools']
                print(f"\n    Storage Pools ({len(pools)}):")
                for pool in pools:
                    size_gb = pool.get('size', 0) / (1024**3) if pool.get('size') else 0
                    free_gb = pool.get('free', 0) / (1024**3) if pool.get('free') else 0
                    print(f"      - {pool['name']}: {size_gb:.1f} GB total, {free_gb:.1f} GB free ({pool.get('status')})")

            if 'total_datasets' in result.metadata:
                print(f"\n    Datasets: {result.metadata['total_datasets']} total")

            if 'shares' in result.metadata:
                shares = result.metadata['shares']
                print(f"\n    Shares:")
                print(f"      NFS: {len(shares.get('nfs_shares', []))}")
                print(f"      SMB: {len(shares.get('smb_shares', []))}")
                print(f"      iSCSI: {len(shares.get('iscsi_targets', []))}")

        print("\n" + "=" * 60)
        print("Test completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up
        await truenas.disconnect()


if __name__ == "__main__":
    asyncio.run(test_truenas())

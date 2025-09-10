import asyncio
import aiohttp
import time
from typing import Dict
from contextlib import asynccontextmanager
import logging

class ConnectionPoolManager:
    """Manages HTTP connection pools for external services"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.pools = {}
        self.stats = {}
    
    async def get_pool(self, service_name: str) -> aiohttp.ClientSession:
        """Get or create connection pool for service"""
        if service_name not in self.pools:
            await self._create_pool(service_name)
        return self.pools[service_name]
    
    async def _create_pool(self, service_name: str):
        """Create connection pool for service"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            keepalive_timeout=60
        )
        
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        self.pools[service_name] = session
        self.stats[service_name] = {"requests": 0, "failures": 0}
        self.logger.info(f"Created connection pool for {service_name}")
    
    @asynccontextmanager
    async def get_session(self, service_name: str):
        """Context manager to get session"""
        session = await self.get_pool(service_name)
        try:
            yield session
        finally:
            pass
    
    async def close_all(self):
        """Close all connection pools"""
        for service_name, session in self.pools.items():
            await session.close()
            self.logger.info(f"Closed connection pool for {service_name}")
        self.pools.clear()
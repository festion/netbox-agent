import asyncio
import time
import psutil
import aiohttp
from typing import Dict, Optional
from enum import Enum
from dataclasses import dataclass

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"

@dataclass
class HealthCheck:
    """Individual health check result"""
    name: str
    status: HealthStatus
    message: str
    response_time: float
    timestamp: float
    metadata: Dict = None

class HealthMonitor:
    """System health monitoring"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.system_status = HealthStatus.HEALTHY
        self.last_check = None
        
    async def run_all_checks(self) -> Dict[str, HealthCheck]:
        """Run all health checks"""
        results = {
            "system_resources": await self.check_system_resources(),
            "netbox_api": await self.check_netbox_api(),
            "disk_space": await self.check_disk_space(),
            "memory_usage": await self.check_memory_usage(),
        }
        
        self.system_status = self.determine_system_status(results)
        self.last_check = time.time()
        
        return results
    
    def determine_system_status(self, results: Dict[str, HealthCheck]) -> HealthStatus:
        """Determine overall system health status"""
        if any(check.status == HealthStatus.CRITICAL for check in results.values()):
            return HealthStatus.CRITICAL
        elif any(check.status == HealthStatus.UNHEALTHY for check in results.values()):
            return HealthStatus.UNHEALTHY
        elif any(check.status == HealthStatus.DEGRADED for check in results.values()):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    async def check_system_resources(self) -> HealthCheck:
        """Check system resource usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        issues = []
        status = HealthStatus.HEALTHY
        
        if cpu_percent > 90:
            issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            status = HealthStatus.DEGRADED
        
        if memory.percent > 85:
            issues.append(f"High memory usage: {memory.percent:.1f}%")
            status = HealthStatus.DEGRADED
        
        message = "System resources normal" if not issues else "; ".join(issues)
        
        return HealthCheck(
            name="system_resources",
            status=status,
            message=message,
            response_time=0,
            timestamp=time.time(),
            metadata={
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent
            }
        )
    
    async def check_netbox_api(self) -> HealthCheck:
        """Check NetBox API connectivity"""
        netbox_url = self.config.get("netbox", {}).get("url")
        if not netbox_url:
            return HealthCheck(
                name="netbox_api",
                status=HealthStatus.CRITICAL,
                message="NetBox URL not configured",
                response_time=0,
                timestamp=time.time()
            )
        
        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.get(f"{netbox_url}/api/", timeout=10) as response:
                    response_time = time.time() - start_time
                    
                    status = HealthStatus.HEALTHY if response.status == 200 else HealthStatus.UNHEALTHY
                    message = f"NetBox API responding ({response_time:.2f}s)"
                    
                    return HealthCheck(
                        name="netbox_api",
                        status=status,
                        message=message,
                        response_time=response_time,
                        timestamp=time.time()
                    )
        except Exception as e:
            return HealthCheck(
                name="netbox_api",
                status=HealthStatus.CRITICAL,
                message=f"NetBox API unreachable: {e}",
                response_time=0,
                timestamp=time.time()
            )
    
    async def check_disk_space(self) -> HealthCheck:
        """Check available disk space"""
        disk = psutil.disk_usage('/')
        free_gb = disk.free / (1024**3)
        
        if free_gb < 1:
            status = HealthStatus.CRITICAL
            message = f"Critical: Only {free_gb:.1f}GB disk space remaining"
        elif free_gb < 5:
            status = HealthStatus.UNHEALTHY
            message = f"Warning: Only {free_gb:.1f}GB disk space remaining"
        elif free_gb < 10:
            status = HealthStatus.DEGRADED
            message = f"Low disk space: {free_gb:.1f}GB remaining"
        else:
            status = HealthStatus.HEALTHY
            message = f"Disk space normal: {free_gb:.1f}GB free"
        
        return HealthCheck(
            name="disk_space",
            status=status,
            message=message,
            response_time=0,
            timestamp=time.time(),
            metadata={"free_gb": free_gb}
        )
    
    async def check_memory_usage(self) -> HealthCheck:
        """Check memory usage patterns"""
        memory = psutil.virtual_memory()
        process = psutil.Process()
        process_memory_mb = process.memory_info().rss / (1024**2)
        
        status = HealthStatus.HEALTHY
        issues = []
        
        if process_memory_mb > 1000:
            issues.append(f"High process memory usage: {process_memory_mb:.1f}MB")
            status = HealthStatus.DEGRADED
        
        if memory.percent > 90:
            issues.append(f"System memory critical: {memory.percent:.1f}%")
            status = HealthStatus.CRITICAL
        elif memory.percent > 80:
            issues.append(f"System memory high: {memory.percent:.1f}%")
            status = HealthStatus.DEGRADED
        
        message = "Memory usage normal" if not issues else "; ".join(issues)
        
        return HealthCheck(
            name="memory_usage",
            status=status,
            message=message,
            response_time=0,
            timestamp=time.time(),
            metadata={
                "system_memory_percent": memory.percent,
                "process_memory_mb": process_memory_mb
            }
        )
    
    def get_health_summary(self) -> Dict:
        """Get health summary for API/monitoring"""
        return {
            "status": self.system_status.value,
            "timestamp": self.last_check
        }
import asyncio
import time
import json
import hashlib
from typing import Any, Optional, Dict
from dataclasses import dataclass

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float]
    hit_count: int = 0

class CacheManager:
    """High-performance in-memory caching"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = config.get("max_cache_entries", 1000)
        
        # Statistics
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        if key not in self.cache:
            self.stats["misses"] += 1
            return default
        
        entry = self.cache[key]
        
        # Check expiration
        if entry.expires_at and time.time() > entry.expires_at:
            del self.cache[key]
            self.stats["misses"] += 1
            return default
        
        entry.hit_count += 1
        self.stats["hits"] += 1
        return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        # Check if we need to evict
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        expires_at = None
        if ttl:
            expires_at = time.time() + ttl
        
        self.cache[key] = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            expires_at=expires_at
        )
    
    def _evict_lru(self):
        """Evict least recently used item"""
        if not self.cache:
            return
        
        lru_key = min(
            self.cache.keys(),
            key=lambda k: (self.cache[k].hit_count, self.cache[k].created_at)
        )
        
        del self.cache[lru_key]
        self.stats["evictions"] += 1
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            "hit_rate_percent": hit_rate,
            "cache_entries": len(self.cache)
        }

def cache_result(ttl: int = 300):
    """Decorator to cache function results"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                # Generate cache key
                key_data = f"{func.__name__}{args}{kwargs}"
                cache_key = hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()
                
                # Try to get from cache
                if hasattr(func, '_cache'):
                    cached = await func._cache.get(cache_key)
                    if cached is not None:
                        return cached
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                if hasattr(func, '_cache'):
                    await func._cache.set(cache_key, result, ttl)
                
                return result
            return async_wrapper
    return decorator
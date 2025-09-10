import logging
import traceback
import asyncio
import time
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass
from contextlib import asynccontextmanager
import functools

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    NETWORK = "network"
    API = "api"
    DATA = "data"
    CONFIG = "config"
    SYSTEM = "system"
    EXTERNAL = "external"

@dataclass
class ErrorEvent:
    """Represents an error event"""
    timestamp: float
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    exception_type: str
    traceback: str
    context: Dict[str, Any]
    retry_count: int = 0
    resolved: bool = False

class ErrorHandler:
    """Centralized error handling and recovery"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Error tracking
        self.error_history = []
        self.error_counts = {}
        self.circuit_breakers = {}
        
        # Recovery strategies
        self.recovery_strategies = {
            ErrorCategory.NETWORK: self.network_recovery,
            ErrorCategory.API: self.api_recovery,
            ErrorCategory.DATA: self.data_recovery,
            ErrorCategory.CONFIG: self.config_recovery,
            ErrorCategory.SYSTEM: self.system_recovery,
            ErrorCategory.EXTERNAL: self.external_recovery
        }
        
        # Retry configuration
        self.retry_config = config.get("error_handling", {}).get("retry", {
            "max_attempts": 3,
            "base_delay": 1,
            "max_delay": 60,
            "backoff_multiplier": 2
        })
    
    def handle_error(self, 
                    exception: Exception,
                    severity: ErrorSeverity,
                    category: ErrorCategory,
                    context: Dict[str, Any] = None) -> ErrorEvent:
        """Handle an error event"""
        
        error_event = ErrorEvent(
            timestamp=time.time(),
            severity=severity,
            category=category,
            message=str(exception),
            exception_type=type(exception).__name__,
            traceback=traceback.format_exc(),
            context=context or {}
        )
        
        # Log error
        self.log_error(error_event)
        
        # Track error
        self.track_error(error_event)
        
        # Check circuit breaker
        if self.should_circuit_break(category, error_event):
            self.trigger_circuit_breaker(category)
        
        # Attempt recovery
        asyncio.create_task(self.attempt_recovery(error_event))
        
        return error_event
    
    def log_error(self, error_event: ErrorEvent):
        """Log error event with appropriate level"""
        log_data = {
            "severity": error_event.severity.value,
            "category": error_event.category.value,
            "exception_type": error_event.exception_type,
            "message": error_event.message,
            "context": error_event.context
        }
        
        if error_event.severity == ErrorSeverity.CRITICAL:
            self.logger.critical("Critical error occurred", extra=log_data)
        elif error_event.severity == ErrorSeverity.HIGH:
            self.logger.error("High severity error", extra=log_data)
        elif error_event.severity == ErrorSeverity.MEDIUM:
            self.logger.warning("Medium severity error", extra=log_data)
        else:
            self.logger.info("Low severity error", extra=log_data)
    
    def track_error(self, error_event: ErrorEvent):
        """Track error for pattern analysis"""
        self.error_history.append(error_event)
        
        # Keep only recent errors (last 1000)
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
        
        # Update error counts
        key = f"{error_event.category.value}:{error_event.exception_type}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
    
    def should_circuit_break(self, category: ErrorCategory, error_event: ErrorEvent) -> bool:
        """Determine if circuit breaker should be triggered"""
        
        # Check error rate in last 5 minutes
        cutoff_time = time.time() - 300
        recent_errors = [
            e for e in self.error_history 
            if e.timestamp > cutoff_time and e.category == category
        ]
        
        # Circuit break if more than 10 errors in 5 minutes
        return len(recent_errors) > 10 or error_event.severity == ErrorSeverity.CRITICAL
    
    def trigger_circuit_breaker(self, category: ErrorCategory):
        """Trigger circuit breaker for category"""
        self.circuit_breakers[category] = {
            "triggered_at": time.time(),
            "duration": 300,  # 5 minutes
            "reason": f"High error rate in {category.value}"
        }
        
        self.logger.warning(f"Circuit breaker triggered for {category.value}")
    
    def is_circuit_open(self, category: ErrorCategory) -> bool:
        """Check if circuit breaker is open for category"""
        breaker = self.circuit_breakers.get(category)
        
        if not breaker:
            return False
        
        # Check if breaker has expired
        if time.time() - breaker["triggered_at"] > breaker["duration"]:
            del self.circuit_breakers[category]
            self.logger.info(f"Circuit breaker reset for {category.value}")
            return False
        
        return True
    
    async def attempt_recovery(self, error_event: ErrorEvent):
        """Attempt to recover from error"""
        recovery_func = self.recovery_strategies.get(error_event.category)
        
        if recovery_func:
            try:
                await recovery_func(error_event)
                error_event.resolved = True
                self.logger.info(f"Successfully recovered from {error_event.category.value} error")
            except Exception as e:
                self.logger.error(f"Recovery failed for {error_event.category.value}: {e}")
    
    # Recovery strategies
    async def network_recovery(self, error_event: ErrorEvent):
        """Recover from network errors"""
        await asyncio.sleep(min(2 ** error_event.retry_count, 30))
    
    async def api_recovery(self, error_event: ErrorEvent):
        """Recover from API errors"""
        # Check API endpoint health, refresh auth, etc.
        pass
    
    async def data_recovery(self, error_event: ErrorEvent):
        """Recover from data errors"""
        # Validate data format, skip corrupted records
        pass
    
    async def config_recovery(self, error_event: ErrorEvent):
        """Recover from configuration errors"""
        # Reload configuration, use defaults
        pass
    
    async def system_recovery(self, error_event: ErrorEvent):
        """Recover from system errors"""
        # Check system resources, clear caches
        pass
    
    async def external_recovery(self, error_event: ErrorEvent):
        """Recover from external service errors"""
        # Switch to alternative service, use cached data
        pass
    
    def get_error_statistics(self) -> Dict:
        """Get error statistics for monitoring"""
        cutoff_time = time.time() - 3600  # Last hour
        recent_errors = [e for e in self.error_history if e.timestamp > cutoff_time]
        
        return {
            "total_errors_last_hour": len(recent_errors),
            "active_circuit_breakers": len(self.circuit_breakers),
            "error_rate_per_minute": len(recent_errors) / 60 if recent_errors else 0
        }

def retry_with_backoff(max_attempts: int = 3, base_delay: float = 1.0):
    """Decorator for automatic retry with exponential backoff"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt == max_attempts - 1:
                            raise
                        delay = base_delay * (2 ** attempt)
                        await asyncio.sleep(min(delay, 60))
                raise last_exception
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt == max_attempts - 1:
                            raise
                        delay = base_delay * (2 ** attempt)
                        time.sleep(min(delay, 60))
                raise last_exception
            return sync_wrapper
    return decorator
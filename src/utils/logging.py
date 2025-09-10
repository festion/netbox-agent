"""Advanced logging infrastructure with structlog"""

import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional, Union
import structlog
from datetime import datetime
import json
import os


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for logging"""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        elif hasattr(obj, '_asdict'):  # Named tuples
            return obj._asdict()
        return super().default(obj)


def timestamper(_, __, event_dict):
    """Add timestamp to log events"""
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def add_log_level(_, __, event_dict):
    """Add log level to event dict"""
    if "level" not in event_dict:
        event_dict["level"] = "info"
    return event_dict


def add_logger_name(_, name, event_dict):
    """Add logger name to event dict"""
    event_dict["logger"] = name
    return event_dict


def add_process_info(_, __, event_dict):
    """Add process information"""
    event_dict["pid"] = os.getpid()
    return event_dict


class ContextualFilter(logging.Filter):
    """Filter to add contextual information to log records"""
    
    def __init__(self, context: Dict[str, Any] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record):
        # Add context to record
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


class PerformanceFilter(logging.Filter):
    """Filter to add performance metrics"""
    
    def __init__(self):
        super().__init__()
        self.start_time = datetime.utcnow()
    
    def filter(self, record):
        # Add uptime to record
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        setattr(record, 'uptime', f"{uptime:.2f}s")
        return True


class NetBoxAgentFormatter(logging.Formatter):
    """Custom formatter for NetBox Agent logs"""
    
    def format(self, record):
        # Create a structured log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "module": getattr(record, 'module', record.name),
            "function": getattr(record, 'funcName', ''),
            "line": getattr(record, 'lineno', 0),
            "pid": os.getpid()
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                          'relativeCreated', 'thread', 'threadName', 'processName', 'process',
                          'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry, cls=CustomJSONEncoder, ensure_ascii=False)


class LoggingManager:
    """Advanced logging manager with multiple handlers and structured logging"""
    
    def __init__(self):
        self.configured = False
        self.handlers = {}
        self.loggers = {}
        self.context = {}
    
    def setup(self, 
              level: str = "INFO",
              log_file: Optional[str] = None,
              max_size: str = "10MB",
              backup_count: int = 5,
              console_output: bool = True,
              json_format: bool = True,
              structured: bool = True,
              context: Dict[str, Any] = None):
        """
        Setup comprehensive logging infrastructure
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file (None to disable file logging)
            max_size: Maximum log file size before rotation
            backup_count: Number of backup files to keep
            console_output: Whether to output to console
            json_format: Whether to use JSON formatting
            structured: Whether to use structured logging with structlog
            context: Global context to add to all log messages
        """
        if self.configured:
            return
        
        self.context = context or {}
        
        # Convert log level
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        
        # Configure structlog if requested
        if structured:
            self._setup_structlog(level, json_format)
        
        # Setup standard logging
        self._setup_standard_logging(
            level=numeric_level,
            log_file=log_file,
            max_size=max_size,
            backup_count=backup_count,
            console_output=console_output,
            json_format=json_format
        )
        
        self.configured = True
    
    def _setup_structlog(self, level: str, json_format: bool):
        """Setup structlog configuration"""
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            timestamper,
            add_process_info,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
        
        if json_format:
            processors.append(structlog.processors.JSONRenderer(serializer=CustomJSONEncoder))
        else:
            processors.append(structlog.dev.ConsoleRenderer())
        
        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    def _setup_standard_logging(self,
                              level: int,
                              log_file: Optional[str],
                              max_size: str,
                              backup_count: int,
                              console_output: bool,
                              json_format: bool):
        """Setup standard Python logging"""
        
        # Create root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Setup file handler if requested
        if log_file:
            self._setup_file_handler(
                log_file=log_file,
                level=level,
                max_size=max_size,
                backup_count=backup_count,
                json_format=json_format
            )
        
        # Setup console handler if requested
        if console_output:
            self._setup_console_handler(level=level, json_format=json_format)
        
        # Set levels for third-party loggers
        self._configure_third_party_loggers()
    
    def _setup_file_handler(self,
                           log_file: str,
                           level: int,
                           max_size: str,
                           backup_count: int,
                           json_format: bool):
        """Setup rotating file handler"""
        
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Parse max size
        max_bytes = self._parse_size(max_size)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        file_handler.setLevel(level)
        
        if json_format:
            file_handler.setFormatter(NetBoxAgentFormatter())
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
        
        # Add contextual filter
        if self.context:
            file_handler.addFilter(ContextualFilter(self.context))
        
        # Add performance filter
        file_handler.addFilter(PerformanceFilter())
        
        # Add to root logger
        logging.getLogger().addHandler(file_handler)
        self.handlers['file'] = file_handler
    
    def _setup_console_handler(self, level: int, json_format: bool):
        """Setup console handler"""
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        if json_format:
            console_handler.setFormatter(NetBoxAgentFormatter())
        else:
            # Use colored output for console if available
            try:
                import coloredlogs
                formatter = coloredlogs.ColoredFormatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            except ImportError:
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            console_handler.setFormatter(formatter)
        
        # Add contextual filter
        if self.context:
            console_handler.addFilter(ContextualFilter(self.context))
        
        # Add to root logger
        logging.getLogger().addHandler(console_handler)
        self.handlers['console'] = console_handler
    
    def _configure_third_party_loggers(self):
        """Configure log levels for third-party libraries"""
        
        # Reduce verbosity of common libraries
        noisy_loggers = {
            'urllib3': logging.WARNING,
            'requests': logging.WARNING,
            'pynetbox': logging.INFO,
            'aiohttp': logging.INFO,
            'asyncio': logging.WARNING,
        }
        
        for logger_name, log_level in noisy_loggers.items():
            logging.getLogger(logger_name).setLevel(log_level)
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '10MB' to bytes"""
        size_str = size_str.upper().strip()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def get_logger(self, name: str) -> Union[logging.Logger, structlog.BoundLogger]:
        """
        Get a logger instance
        
        Args:
            name: Logger name
            
        Returns:
            Logger instance (structlog or standard logging)
        """
        if name in self.loggers:
            return self.loggers[name]
        
        # Return structlog logger if configured, otherwise standard logger
        try:
            logger = structlog.get_logger(name)
            # Add global context
            if self.context:
                logger = logger.bind(**self.context)
            self.loggers[name] = logger
            return logger
        except Exception:
            # Fallback to standard logging
            logger = logging.getLogger(name)
            self.loggers[name] = logger
            return logger
    
    def add_context(self, **kwargs):
        """Add global context to all future log messages"""
        self.context.update(kwargs)
        
        # Update filters
        for handler in self.handlers.values():
            # Remove old contextual filter
            for filter_obj in handler.filters[:]:
                if isinstance(filter_obj, ContextualFilter):
                    handler.removeFilter(filter_obj)
            
            # Add new contextual filter
            handler.addFilter(ContextualFilter(self.context))
    
    def remove_context(self, *keys):
        """Remove keys from global context"""
        for key in keys:
            self.context.pop(key, None)
    
    def set_level(self, level: str):
        """Change log level dynamically"""
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        
        # Update all handlers
        for handler in self.handlers.values():
            handler.setLevel(numeric_level)
        
        # Update root logger
        logging.getLogger().setLevel(numeric_level)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        stats = {
            'configured': self.configured,
            'handlers': list(self.handlers.keys()),
            'loggers_created': len(self.loggers),
            'global_context': self.context.copy()
        }
        
        # Add handler-specific stats
        for name, handler in self.handlers.items():
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                stats[f'{name}_handler'] = {
                    'type': 'RotatingFileHandler',
                    'filename': handler.baseFilename,
                    'max_bytes': handler.maxBytes,
                    'backup_count': handler.backupCount,
                    'current_size': Path(handler.baseFilename).stat().st_size if Path(handler.baseFilename).exists() else 0
                }
            elif isinstance(handler, logging.StreamHandler):
                stats[f'{name}_handler'] = {
                    'type': 'StreamHandler',
                    'stream': str(handler.stream)
                }
        
        return stats
    
    def cleanup(self):
        """Cleanup logging resources"""
        for handler in self.handlers.values():
            if hasattr(handler, 'close'):
                handler.close()
        
        self.handlers.clear()
        self.loggers.clear()
        self.configured = False


# Global logging manager instance
_logging_manager = LoggingManager()


def setup_logging(**kwargs):
    """Setup logging with the global manager"""
    _logging_manager.setup(**kwargs)


def get_logger(name: str):
    """Get a logger instance"""
    return _logging_manager.get_logger(name)


def add_logging_context(**kwargs):
    """Add global context to all log messages"""
    _logging_manager.add_context(**kwargs)


def remove_logging_context(*keys):
    """Remove keys from global logging context"""
    _logging_manager.remove_context(*keys)


def set_log_level(level: str):
    """Set global log level"""
    _logging_manager.set_level(level)


def get_logging_stats():
    """Get logging statistics"""
    return _logging_manager.get_stats()


def cleanup_logging():
    """Cleanup logging resources"""
    _logging_manager.cleanup()
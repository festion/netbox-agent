"""Advanced configuration management with environment variable substitution"""

import json
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Type
import structlog
from pydantic import BaseModel, Field, ValidationError, validator
from dotenv import load_dotenv


class ConfigError(Exception):
    """Configuration related errors"""
    pass


class ConfigValidationError(ConfigError):
    """Configuration validation errors"""
    pass


class NetBoxConfig(BaseModel):
    """NetBox configuration"""
    url: str
    token: str
    verify_ssl: bool = True
    timeout: int = 30
    max_retries: int = 3
    
    @validator('url')
    def validate_url(cls, v):
        if not v:
            raise ValueError('NetBox URL is required')
        v = v.rstrip('/')
        if not v.startswith(('http://', 'https://')):
            raise ValueError('NetBox URL must start with http:// or https://')
        return v
    
    @validator('token')
    def validate_token(cls, v):
        if not v:
            raise ValueError('NetBox token is required')
        if len(v) < 10:
            raise ValueError('NetBox token seems too short')
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        if v <= 0:
            raise ValueError('Timeout must be positive')
        return v


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    file: Optional[str] = None
    max_size: str = "10MB"
    backup_count: int = 5
    console_output: bool = True
    json_format: bool = True
    structured: bool = True
    
    @validator('level')
    def validate_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Invalid log level: {v}. Must be one of {valid_levels}')
        return v.upper()
    
    @validator('max_size')
    def validate_max_size(cls, v):
        if not re.match(r'^\d+[KMGT]?B$', v.upper()):
            raise ValueError('Invalid max_size format. Use format like "10MB", "1GB", etc.')
        return v
    
    @validator('backup_count')
    def validate_backup_count(cls, v):
        if v < 0:
            raise ValueError('Backup count must be non-negative')
        return v


class SyncConfig(BaseModel):
    """Synchronization configuration"""
    dry_run: bool = False
    full_sync_interval: int = 86400  # 24 hours
    incremental_sync_interval: int = 3600  # 1 hour
    batch_size: int = 50
    max_workers: int = 5
    conflict_resolution: str = "merge"  # skip, overwrite, merge, manual
    
    @validator('full_sync_interval')
    def validate_full_sync_interval(cls, v):
        if v <= 0:
            raise ValueError('Full sync interval must be positive')
        return v
    
    @validator('incremental_sync_interval')
    def validate_incremental_sync_interval(cls, v):
        if v <= 0:
            raise ValueError('Incremental sync interval must be positive')
        return v
    
    @validator('batch_size')
    def validate_batch_size(cls, v):
        if v <= 0:
            raise ValueError('Batch size must be positive')
        return v
    
    @validator('max_workers')
    def validate_max_workers(cls, v):
        if v <= 0:
            raise ValueError('Max workers must be positive')
        return v
    
    @validator('conflict_resolution')
    def validate_conflict_resolution(cls, v):
        valid_options = ['skip', 'overwrite', 'merge', 'manual']
        if v not in valid_options:
            raise ValueError(f'Invalid conflict resolution: {v}. Must be one of {valid_options}')
        return v


class DataSourceConfig(BaseModel):
    """Base data source configuration"""
    enabled: bool = False
    sync_interval: int = 3600
    timeout: int = 300
    retry_attempts: int = 3
    retry_delay: int = 5
    
    @validator('sync_interval')
    def validate_sync_interval(cls, v):
        if v <= 0:
            raise ValueError('Sync interval must be positive')
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        if v <= 0:
            raise ValueError('Timeout must be positive')
        return v
    
    @validator('retry_attempts')
    def validate_retry_attempts(cls, v):
        if v < 0:
            raise ValueError('Retry attempts must be non-negative')
        return v


class HomeAssistantConfig(DataSourceConfig):
    """Home Assistant configuration"""
    url: str = ""
    token: str = ""
    
    @validator('url')
    def validate_url(cls, v, values):
        if values.get('enabled', False) and not v:
            raise ValueError('Home Assistant URL is required when enabled')
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Home Assistant URL must start with http:// or https://')
        return v.rstrip('/') if v else v
    
    @validator('token')
    def validate_token(cls, v, values):
        if values.get('enabled', False) and not v:
            raise ValueError('Home Assistant token is required when enabled')
        return v


class NetworkScanConfig(DataSourceConfig):
    """Network scanning configuration"""
    networks: List[str] = Field(default_factory=list)
    scan_ports: List[int] = Field(default_factory=lambda: [22, 23, 80, 443, 161])
    scan_timeout: int = 30
    
    @validator('networks')
    def validate_networks(cls, v, values):
        if values.get('enabled', False) and not v:
            raise ValueError('Network ranges are required when network scanning is enabled')
        
        # Basic CIDR validation
        import ipaddress
        for network in v:
            try:
                ipaddress.ip_network(network, strict=False)
            except ValueError:
                raise ValueError(f'Invalid network CIDR: {network}')
        
        return v
    
    @validator('scan_ports')
    def validate_scan_ports(cls, v):
        for port in v:
            if not (1 <= port <= 65535):
                raise ValueError(f'Invalid port number: {port}')
        return v


class FilesystemConfig(DataSourceConfig):
    """Filesystem monitoring configuration"""
    config_paths: List[str] = Field(default_factory=list)
    file_patterns: List[str] = Field(default_factory=lambda: ['*.yaml', '*.yml', '*.json'])
    watch_changes: bool = True
    
    @validator('config_paths')
    def validate_config_paths(cls, v, values):
        if values.get('enabled', False) and not v:
            raise ValueError('Config paths are required when filesystem monitoring is enabled')
        
        # Check if paths exist
        for path in v:
            if not Path(path).exists():
                raise ValueError(f'Config path does not exist: {path}')
        
        return v


class ProxmoxConfig(DataSourceConfig):
    """Proxmox configuration"""
    url: str = ""
    username: str = ""
    token: str = ""
    verify_ssl: bool = True
    
    @validator('url')
    def validate_url(cls, v, values):
        if values.get('enabled', False) and not v:
            raise ValueError('Proxmox URL is required when enabled')
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Proxmox URL must start with http:// or https://')
        return v.rstrip('/') if v else v
    
    @validator('username')
    def validate_username(cls, v, values):
        if values.get('enabled', False) and not v:
            raise ValueError('Proxmox username is required when enabled')
        return v
    
    @validator('token')
    def validate_token(cls, v, values):
        if values.get('enabled', False) and not v:
            raise ValueError('Proxmox token is required when enabled')
        return v


class TrueNASConfig(DataSourceConfig):
    """TrueNAS configuration"""
    url: str = ""
    api_key: str = ""
    verify_ssl: bool = True
    
    @validator('url')
    def validate_url(cls, v, values):
        if values.get('enabled', False) and not v:
            raise ValueError('TrueNAS URL is required when enabled')
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('TrueNAS URL must start with http:// or https://')
        return v.rstrip('/') if v else v
    
    @validator('api_key')
    def validate_api_key(cls, v, values):
        if values.get('enabled', False) and not v:
            raise ValueError('TrueNAS API key is required when enabled')
        return v


class DataSourcesConfig(BaseModel):
    """All data sources configuration"""
    homeassistant: HomeAssistantConfig = Field(default_factory=HomeAssistantConfig)
    network_scan: NetworkScanConfig = Field(default_factory=NetworkScanConfig)
    filesystem: FilesystemConfig = Field(default_factory=FilesystemConfig)
    proxmox: ProxmoxConfig = Field(default_factory=ProxmoxConfig)
    truenas: TrueNASConfig = Field(default_factory=TrueNASConfig)


class AgentConfig(BaseModel):
    """Main agent configuration"""
    netbox: NetBoxConfig
    sources: DataSourcesConfig = Field(default_factory=DataSourcesConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    
    # Global settings
    agent_name: str = "NetBox Agent"
    agent_version: str = "1.0.0"
    default_site: str = "Main"
    timezone: str = "UTC"
    
    @validator('agent_name')
    def validate_agent_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Agent name cannot be empty')
        return v.strip()


class ConfigManager:
    """Advanced configuration management with environment variable substitution"""
    
    def __init__(self, 
                 config_path: Optional[str] = None,
                 env_path: Optional[str] = None,
                 env_prefix: str = "NETBOX_"):
        """
        Initialize configuration manager
        
        Args:
            config_path: Path to JSON configuration file
            env_path: Path to .env file
            env_prefix: Prefix for environment variables
        """
        self.config_path = config_path or "config/netbox-agent.json"
        self.env_path = env_path or ".env"
        self.env_prefix = env_prefix
        self.logger = structlog.get_logger(__name__)
        
        self._config: Optional[AgentConfig] = None
        self._raw_config: Optional[Dict[str, Any]] = None
        self._env_vars: Dict[str, str] = {}
        
        # Load environment variables
        self._load_env()
    
    def _load_env(self):
        """Load environment variables from .env file and system"""
        # Load from .env file if it exists
        if Path(self.env_path).exists():
            load_dotenv(self.env_path)
            self.logger.debug("Loaded environment from .env file", path=self.env_path)
        
        # Capture relevant environment variables
        for key, value in os.environ.items():
            if key.startswith(self.env_prefix) or key in [
                'NETBOX_URL', 'NETBOX_TOKEN', 'NETBOX_VERIFY_SSL',
                'HA_URL', 'HA_TOKEN', 'GITHUB_TOKEN',
                'PROXMOX_URL', 'PROXMOX_USERNAME', 'PROXMOX_TOKEN',
                'TRUENAS_URL', 'TRUENAS_API_KEY',
                'LOG_LEVEL', 'LOG_FILE', 'ENVIRONMENT'
            ]:
                self._env_vars[key] = value
        
        self.logger.debug("Loaded environment variables", count=len(self._env_vars))
    
    def load_config(self) -> AgentConfig:
        """Load and parse configuration with validation"""
        try:
            # Load raw JSON configuration
            self._raw_config = self._load_json_config()
            
            # Substitute environment variables
            substituted_config = self._substitute_env_vars(self._raw_config)
            
            # Parse and validate with Pydantic
            self._config = AgentConfig(**substituted_config)
            
            self.logger.info("Configuration loaded successfully", 
                           config_path=self.config_path,
                           env_vars_used=len([k for k in self._env_vars if k in str(self._raw_config)]))
            
            return self._config
            
        except FileNotFoundError:
            raise ConfigError(f"Configuration file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in configuration file: {e}")
        except ValidationError as e:
            raise ConfigValidationError(f"Configuration validation failed: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load configuration: {e}")
    
    def _load_json_config(self) -> Dict[str, Any]:
        """Load raw JSON configuration"""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            # Try to find config in common locations
            possible_paths = [
                "config/netbox-agent.json",
                "netbox-agent.json",
                "/etc/netbox-agent/config.json",
                str(Path.home() / ".netbox-agent" / "config.json")
            ]
            
            for path in possible_paths:
                if Path(path).exists():
                    config_file = Path(path)
                    self.config_path = str(config_file)
                    break
            else:
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _substitute_env_vars(self, obj: Any) -> Any:
        """Recursively substitute environment variables in configuration"""
        if isinstance(obj, str):
            return self._substitute_string(obj)
        elif isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        else:
            return obj
    
    def _substitute_string(self, text: str) -> Union[str, int, float, bool]:
        """Substitute environment variables in a string"""
        if not isinstance(text, str):
            return text
        
        # Handle ${VAR} pattern
        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(3) if match.group(3) is not None else ""
            
            # Look for variable in environment
            value = self._env_vars.get(var_name)
            if value is not None:
                return value
            
            # Look for prefixed variable
            prefixed_name = f"{self.env_prefix}{var_name}"
            value = self._env_vars.get(prefixed_name)
            if value is not None:
                return value
            
            # Use default value
            if default_value:
                return default_value
            
            # Variable not found and no default
            self.logger.warning("Environment variable not found", 
                              variable=var_name, 
                              prefixed=prefixed_name)
            return match.group(0)  # Return original string
        
        # Pattern: ${VAR} or ${VAR:default}
        pattern = r'\$\{([A-Za-z_][A-Za-z0-9_]*)(:(.*?))?\}'
        result = re.sub(pattern, replace_var, text)
        
        # Try to convert to appropriate type
        return self._convert_type(result)
    
    def _convert_type(self, value: str) -> Union[str, int, float, bool]:
        """Convert string value to appropriate Python type"""
        if not isinstance(value, str):
            return value
        
        # Boolean conversion
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        if value.lower() in ('false', 'no', '0', 'off'):
            return False
        
        # Number conversion
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def get_config(self) -> AgentConfig:
        """Get the loaded configuration"""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def reload_config(self) -> AgentConfig:
        """Reload configuration from file"""
        self._config = None
        self._raw_config = None
        self._load_env()  # Reload environment variables
        return self.load_config()
    
    def validate_config(self) -> bool:
        """Validate the current configuration"""
        try:
            config = self.get_config()
            
            # Additional validation beyond Pydantic
            
            # Check NetBox connectivity requirements
            if not config.netbox.url or not config.netbox.token:
                raise ConfigValidationError("NetBox URL and token are required")
            
            # Check that at least one data source is enabled
            sources_enabled = any([
                config.sources.homeassistant.enabled,
                config.sources.network_scan.enabled,
                config.sources.filesystem.enabled,
                config.sources.proxmox.enabled,
                config.sources.truenas.enabled
            ])
            
            if not sources_enabled:
                self.logger.warning("No data sources are enabled")
            
            # Validate sync intervals
            if config.sync.incremental_sync_interval > config.sync.full_sync_interval:
                self.logger.warning("Incremental sync interval is longer than full sync interval")
            
            return True
            
        except Exception as e:
            self.logger.error("Configuration validation failed", error=str(e))
            return False
    
    def get_env_var(self, key: str, default: Any = None) -> Any:
        """Get environment variable with optional default"""
        # Try direct key first
        value = self._env_vars.get(key)
        if value is not None:
            return self._convert_type(value)
        
        # Try with prefix
        prefixed_key = f"{self.env_prefix}{key}"
        value = self._env_vars.get(prefixed_key)
        if value is not None:
            return self._convert_type(value)
        
        return default
    
    def set_env_var(self, key: str, value: str):
        """Set environment variable (runtime only)"""
        self._env_vars[key] = value
        os.environ[key] = value
    
    def save_config(self, config: AgentConfig, path: Optional[str] = None) -> bool:
        """Save configuration to file"""
        try:
            save_path = path or self.config_path
            
            # Convert to dictionary
            config_dict = config.dict()
            
            # Create backup of existing config
            config_file = Path(save_path)
            if config_file.exists():
                backup_path = config_file.with_suffix('.json.backup')
                config_file.replace(backup_path)
                self.logger.info("Created configuration backup", backup_path=str(backup_path))
            
            # Ensure directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write configuration
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info("Configuration saved", path=save_path)
            return True
            
        except Exception as e:
            self.logger.error("Failed to save configuration", error=str(e), path=path)
            return False
    
    def create_example_config(self, path: str) -> bool:
        """Create an example configuration file"""
        try:
            example_config = {
                "netbox": {
                    "url": "${NETBOX_URL:https://netbox.example.com}",
                    "token": "${NETBOX_TOKEN:your-netbox-api-token}",
                    "verify_ssl": "${NETBOX_VERIFY_SSL:true}"
                },
                "sources": {
                    "homeassistant": {
                        "enabled": "${HA_ENABLED:false}",
                        "url": "${HA_URL:http://192.168.1.10:8123}",
                        "token": "${HA_TOKEN:your-ha-token}"
                    },
                    "network_scan": {
                        "enabled": "${NETWORK_SCAN_ENABLED:false}",
                        "networks": ["${NETWORK_RANGES:192.168.1.0/24}"]
                    },
                    "filesystem": {
                        "enabled": "${FILESYSTEM_ENABLED:false}",
                        "config_paths": ["/etc/network", "/opt/configs"]
                    },
                    "proxmox": {
                        "enabled": "${PROXMOX_ENABLED:false}",
                        "url": "${PROXMOX_URL:https://proxmox.example.com:8006}",
                        "username": "${PROXMOX_USERNAME:api@pve}",
                        "token": "${PROXMOX_TOKEN:your-proxmox-token}"
                    },
                    "truenas": {
                        "enabled": "${TRUENAS_ENABLED:false}",
                        "url": "${TRUENAS_URL:https://truenas.example.com}",
                        "api_key": "${TRUENAS_API_KEY:your-truenas-api-key}"
                    }
                },
                "logging": {
                    "level": "${LOG_LEVEL:INFO}",
                    "file": "${LOG_FILE:/var/log/netbox-agent.log}",
                    "json_format": "${LOG_JSON:true}"
                },
                "sync": {
                    "dry_run": "${SYNC_DRY_RUN:false}",
                    "full_sync_interval": 86400,
                    "incremental_sync_interval": 3600
                }
            }
            
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(example_config, f, indent=2, ensure_ascii=False)
            
            self.logger.info("Example configuration created", path=path)
            return True
            
        except Exception as e:
            self.logger.error("Failed to create example configuration", error=str(e), path=path)
            return False
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration"""
        if not self._config:
            return {"status": "not_loaded"}
        
        config = self._config
        
        return {
            "status": "loaded",
            "config_path": self.config_path,
            "agent_name": config.agent_name,
            "agent_version": config.agent_version,
            "netbox_url": config.netbox.url,
            "netbox_ssl_verify": config.netbox.verify_ssl,
            "data_sources": {
                "homeassistant": {"enabled": config.sources.homeassistant.enabled},
                "network_scan": {"enabled": config.sources.network_scan.enabled},
                "filesystem": {"enabled": config.sources.filesystem.enabled},
                "proxmox": {"enabled": config.sources.proxmox.enabled},
                "truenas": {"enabled": config.sources.truenas.enabled}
            },
            "logging": {
                "level": config.logging.level,
                "file": config.logging.file,
                "json_format": config.logging.json_format
            },
            "sync": {
                "dry_run": config.sync.dry_run,
                "full_sync_interval": config.sync.full_sync_interval,
                "incremental_sync_interval": config.sync.incremental_sync_interval
            },
            "env_vars_available": len(self._env_vars)
        }
    
    def test_config(self) -> Dict[str, Any]:
        """Test configuration validity and connectivity"""
        results = {
            "config_valid": False,
            "netbox_reachable": False,
            "data_sources": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # Test config loading and validation
            config = self.get_config()
            results["config_valid"] = True
            
            # Test NetBox connectivity (basic URL check)
            try:
                import requests
                response = requests.head(config.netbox.url, 
                                      timeout=10, 
                                      verify=config.netbox.verify_ssl)
                results["netbox_reachable"] = response.status_code < 400
            except Exception as e:
                results["errors"].append(f"NetBox connectivity test failed: {e}")
            
            # Test data source configurations
            for source_name in ["homeassistant", "network_scan", "filesystem", "proxmox", "truenas"]:
                source_config = getattr(config.sources, source_name)
                results["data_sources"][source_name] = {
                    "enabled": source_config.enabled,
                    "configured": source_config.enabled  # Basic check
                }
            
        except Exception as e:
            results["errors"].append(f"Configuration test failed: {e}")
        
        return results
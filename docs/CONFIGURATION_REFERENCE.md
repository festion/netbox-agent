# NetBox Agent Configuration Reference

**Version**: 1.0.0
**Last Updated**: 2025-11-12

---

## Overview

The NetBox Agent uses JSON configuration files to define its behavior. This reference documents all available configuration options, their default values, and usage examples.

## Configuration Files

| File | Purpose | Required |
|------|---------|----------|
| `config/netbox-agent.json` | Main configuration | ✅ Yes |
| `config/alerts.json` | Alert rules and notification channels | ⬜ Optional |
| `config/data-mappings.json` | Custom data mappings | ⬜ Optional |
| `.env` | Environment variables and secrets | ✅ Yes |

---

## Main Configuration

**File**: `config/netbox-agent.json`

### Complete Example

```json
{
  "netbox": {
    "url": "https://netbox.example.com",
    "token": "your-api-token-here",
    "verify_ssl": true,
    "timeout": 30,
    "max_retries": 3
  },
  "data_sources": {
    "homeassistant": {
      "enabled": true,
      "url": "http://homeassistant.local:8123",
      "token_path": "/config/ha_token",
      "sync_interval": 3600,
      "include_entities": ["sensor", "switch", "light", "device_tracker"]
    },
    "network_scan": {
      "enabled": true,
      "networks": ["192.168.1.0/24", "10.0.0.0/24"],
      "scan_interval": 3600,
      "scan_ports": [22, 80, 443, 161, 8080],
      "timeout": 5,
      "max_concurrent": 50
    },
    "filesystem": {
      "enabled": false,
      "config_paths": [
        "/etc/network/interfaces",
        "/etc/ansible/hosts",
        "/opt/configs"
      ],
      "watch_interval": 300,
      "recursive": true
    },
    "proxmox": {
      "enabled": true,
      "url": "https://proxmox.local:8006",
      "username": "root@pam",
      "token": "proxmox-api-token",
      "verify_ssl": false,
      "include_stopped": true,
      "include_containers": true,
      "include_vms": true,
      "node_as_site": true,
      "cluster_name": "production"
    },
    "truenas": {
      "enabled": true,
      "url": "https://truenas.local",
      "api_key": "truenas-api-key",
      "verify_ssl": true,
      "include_pools": true,
      "include_datasets": true,
      "include_shares": true,
      "include_network": true
    }
  },
  "sync": {
    "mode": "incremental",
    "dry_run": false,
    "full_sync_interval": 86400,
    "incremental_sync_interval": 3600,
    "batch_size": 500,
    "conflict_resolution": "prefer_netbox",
    "create_missing_types": true,
    "create_missing_roles": true,
    "auto_assign_ips": true
  },
  "deduplication": {
    "enabled": true,
    "strategy": "prefer_newest",
    "match_fields": ["name", "serial", "mac_address"],
    "ignore_sources": []
  },
  "logging": {
    "level": "INFO",
    "file": "/var/log/netbox-agent/netbox-agent.log",
    "max_size": 10485760,
    "backup_count": 5,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  },
  "monitoring": {
    "enabled": true,
    "health_check_port": 8080,
    "metrics_enabled": true,
    "collect_interval": 60
  }
}
```

---

## Configuration Sections

### NetBox Section

Configures connection to NetBox server.

```json
{
  "netbox": {
    "url": "https://netbox.example.com",
    "token": "your-api-token-here",
    "verify_ssl": true,
    "timeout": 30,
    "max_retries": 3
  }
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | ✅ Yes | - | NetBox server URL (include protocol) |
| `token` | string | ✅ Yes | - | NetBox API token |
| `verify_ssl` | boolean | ⬜ No | `true` | Verify SSL certificates |
| `timeout` | integer | ⬜ No | `30` | Request timeout in seconds |
| `max_retries` | integer | ⬜ No | `3` | Maximum retry attempts for failed requests |

**Notes**:
- Set `verify_ssl: false` only for testing/development
- Token should have write permissions for DCIM module
- URL should not include trailing slash

**Environment Variables**:
- `NETBOX_URL` - Overrides `url` parameter
- `NETBOX_TOKEN` - Overrides `token` parameter

---

### Data Sources Section

Configures which data sources to use for device discovery.

#### Home Assistant Data Source

Discovers devices from Home Assistant via REST API.

```json
{
  "homeassistant": {
    "enabled": true,
    "url": "http://homeassistant.local:8123",
    "token_path": "/config/ha_token",
    "sync_interval": 3600,
    "include_entities": ["sensor", "switch", "light", "device_tracker"]
  }
}
```

##### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `enabled` | boolean | ✅ Yes | `false` | Enable this data source |
| `url` | string | ✅ Yes | - | Home Assistant URL |
| `token_path` | string | ✅ Yes | - | Path to file containing HA token |
| `sync_interval` | integer | ⬜ No | `3600` | Sync interval in seconds |
| `include_entities` | array | ⬜ No | All | Entity types to include |

**Environment Variables**:
- `HA_URL` - Overrides `url` parameter
- `HA_TOKEN` - Direct token (alternative to `token_path`)

---

#### Network Scanner Data Source

Discovers devices through network scanning (ICMP, port scanning).

```json
{
  "network_scan": {
    "enabled": true,
    "networks": ["192.168.1.0/24", "10.0.0.0/24"],
    "scan_interval": 3600,
    "scan_ports": [22, 80, 443, 161, 8080],
    "timeout": 5,
    "max_concurrent": 50
  }
}
```

##### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `enabled` | boolean | ✅ Yes | `false` | Enable this data source |
| `networks` | array | ✅ Yes | - | CIDR networks to scan |
| `scan_interval` | integer | ⬜ No | `3600` | Scan interval in seconds |
| `scan_ports` | array | ⬜ No | `[22,80,443]` | Ports to scan for service detection |
| `timeout` | integer | ⬜ No | `5` | Scan timeout per host (seconds) |
| `max_concurrent` | integer | ⬜ No | `50` | Maximum concurrent scans |

**Notes**:
- Requires appropriate network permissions
- Large networks may take time to scan
- Consider firewall rules when selecting ports

---

#### Filesystem Data Source

Discovers devices from configuration files (Ansible inventories, network configs, etc.).

```json
{
  "filesystem": {
    "enabled": false,
    "config_paths": [
      "/etc/network/interfaces",
      "/etc/ansible/hosts",
      "/opt/configs"
    ],
    "watch_interval": 300,
    "recursive": true
  }
}
```

##### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `enabled` | boolean | ✅ Yes | `false` | Enable this data source |
| `config_paths` | array | ✅ Yes | - | Paths to config files/directories |
| `watch_interval` | integer | ⬜ No | `300` | File watch interval in seconds |
| `recursive` | boolean | ⬜ No | `true` | Recursively search directories |

**Supported File Formats**:
- Ansible inventory files
- Network configuration files
- CSV/JSON device lists

---

#### Proxmox Data Source

Discovers virtual machines and containers from Proxmox VE cluster.

```json
{
  "proxmox": {
    "enabled": true,
    "url": "https://proxmox.local:8006",
    "username": "root@pam",
    "token": "proxmox-api-token",
    "verify_ssl": false,
    "include_stopped": true,
    "include_containers": true,
    "include_vms": true,
    "node_as_site": true,
    "cluster_name": "production"
  }
}
```

##### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `enabled` | boolean | ✅ Yes | `false` | Enable this data source |
| `url` | string | ✅ Yes | - | Proxmox VE URL |
| `username` | string | ✅ Yes | - | Proxmox username (e.g., `root@pam`) |
| `token` | string | ✅ Yes | - | API token name |
| `verify_ssl` | boolean | ⬜ No | `true` | Verify SSL certificates |
| `include_stopped` | boolean | ⬜ No | `true` | Include stopped VMs/containers |
| `include_containers` | boolean | ⬜ No | `true` | Include LXC containers |
| `include_vms` | boolean | ⬜ No | `true` | Include QEMU VMs |
| `node_as_site` | boolean | ⬜ No | `true` | Create NetBox sites from Proxmox nodes |
| `cluster_name` | string | ⬜ No | - | Custom cluster name for grouping |

**Environment Variables**:
- `PROXMOX_URL` - Overrides `url` parameter
- `PROXMOX_TOKEN` - Overrides `token` parameter

**Notes**:
- Uses Proxmox MCP server for communication
- Requires API token with read permissions
- VMs/containers map to NetBox virtual machines

---

#### TrueNAS Data Source

Discovers storage systems, pools, and shares from TrueNAS.

```json
{
  "truenas": {
    "enabled": true,
    "url": "https://truenas.local",
    "api_key": "truenas-api-key",
    "verify_ssl": true,
    "include_pools": true,
    "include_datasets": true,
    "include_shares": true,
    "include_network": true
  }
}
```

##### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `enabled` | boolean | ✅ Yes | `false` | Enable this data source |
| `url` | string | ✅ Yes | - | TrueNAS URL |
| `api_key` | string | ✅ Yes | - | TrueNAS API key |
| `verify_ssl` | boolean | ⬜ No | `true` | Verify SSL certificates |
| `include_pools` | boolean | ⬜ No | `true` | Include storage pools |
| `include_datasets` | boolean | ⬜ No | `true` | Include datasets |
| `include_shares` | boolean | ⬜ No | `true` | Include NFS/SMB/iSCSI shares |
| `include_network` | boolean | ⬜ No | `true` | Include network interfaces |

**Environment Variables**:
- `TRUENAS_URL` - Overrides `url` parameter
- `TRUENAS_API_KEY` - Overrides `api_key` parameter

**Notes**:
- API key requires full read permissions
- TrueNAS system maps to NetBox device
- Pools/datasets tracked as custom fields

---

### Sync Section

Configures synchronization behavior between data sources and NetBox.

```json
{
  "sync": {
    "mode": "incremental",
    "dry_run": false,
    "full_sync_interval": 86400,
    "incremental_sync_interval": 3600,
    "batch_size": 500,
    "conflict_resolution": "prefer_netbox",
    "create_missing_types": true,
    "create_missing_roles": true,
    "auto_assign_ips": true
  }
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `mode` | string | ⬜ No | `incremental` | Sync mode: `incremental` or `full` |
| `dry_run` | boolean | ⬜ No | `false` | Preview changes without applying |
| `full_sync_interval` | integer | ⬜ No | `86400` | Full sync interval in seconds (24h) |
| `incremental_sync_interval` | integer | ⬜ No | `3600` | Incremental sync interval (1h) |
| `batch_size` | integer | ⬜ No | `500` | Devices per batch |
| `conflict_resolution` | string | ⬜ No | `prefer_netbox` | Conflict strategy (see below) |
| `create_missing_types` | boolean | ⬜ No | `true` | Auto-create device types |
| `create_missing_roles` | boolean | ⬜ No | `true` | Auto-create device roles |
| `auto_assign_ips` | boolean | ⬜ No | `true` | Automatically assign IP addresses |

#### Conflict Resolution Strategies

| Strategy | Behavior |
|----------|----------|
| `prefer_netbox` | Keep existing NetBox data, ignore source changes |
| `prefer_source` | Overwrite NetBox data with source data |
| `merge` | Merge non-conflicting fields |
| `manual` | Skip conflicts, log for manual resolution |

---

### Deduplication Section

Configures how duplicate devices are handled.

```json
{
  "deduplication": {
    "enabled": true,
    "strategy": "prefer_newest",
    "match_fields": ["name", "serial", "mac_address"],
    "ignore_sources": []
  }
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `enabled` | boolean | ⬜ No | `true` | Enable deduplication |
| `strategy` | string | ⬜ No | `prefer_newest` | Deduplication strategy |
| `match_fields` | array | ⬜ No | See below | Fields to match for duplicates |
| `ignore_sources` | array | ⬜ No | `[]` | Sources to exclude from deduplication |

#### Deduplication Strategies

| Strategy | Behavior |
|----------|----------|
| `prefer_newest` | Keep device from most recent discovery |
| `prefer_source` | Prioritize specific source (requires `preferred_source` param) |
| `merge_all` | Merge data from all duplicate devices |

#### Default Match Fields

- `name` - Device hostname/name
- `serial` - Serial number
- `mac_address` - Primary MAC address
- `management_ip` - Management IP address

---

### Logging Section

Configures application logging.

```json
{
  "logging": {
    "level": "INFO",
    "file": "/var/log/netbox-agent/netbox-agent.log",
    "max_size": 10485760,
    "backup_count": 5,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `level` | string | ⬜ No | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `file` | string | ⬜ No | `./logs/netbox-agent.log` | Log file path |
| `max_size` | integer | ⬜ No | `10485760` | Max log file size in bytes (10MB) |
| `backup_count` | integer | ⬜ No | `5` | Number of backup logs to keep |
| `format` | string | ⬜ No | Standard | Python logging format string |

---

### Monitoring Section

Configures health checks and metrics collection.

```json
{
  "monitoring": {
    "enabled": true,
    "health_check_port": 8080,
    "metrics_enabled": true,
    "collect_interval": 60
  }
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `enabled` | boolean | ⬜ No | `true` | Enable monitoring endpoints |
| `health_check_port` | integer | ⬜ No | `8080` | HTTP port for health checks |
| `metrics_enabled` | boolean | ⬜ No | `true` | Enable metrics collection |
| `collect_interval` | integer | ⬜ No | `60` | Metrics collection interval (seconds) |

**Endpoints**:
- `http://localhost:8080/health` - Health check endpoint
- `http://localhost:8080/metrics` - Metrics endpoint

---

## Environment Variables

Environment variables override configuration file values and store secrets.

**File**: `.env`

### Required Variables

```bash
# NetBox Configuration
NETBOX_URL=https://netbox.example.com
NETBOX_TOKEN=your-netbox-api-token

# Home Assistant (if enabled)
HA_URL=http://homeassistant.local:8123
HA_TOKEN=your-homeassistant-token

# Proxmox (if enabled)
PROXMOX_URL=https://proxmox.local:8006
PROXMOX_TOKEN=your-proxmox-token

# TrueNAS (if enabled)
TRUENAS_URL=https://truenas.local
TRUENAS_API_KEY=your-truenas-api-key
```

### Optional Variables

```bash
# Monitoring
ALERT_WEBHOOK_URL=https://webhook.site/your-webhook-id

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/netbox-agent/netbox-agent.log

# Sync Behavior
SYNC_DRY_RUN=false
SYNC_BATCH_SIZE=500
```

---

## Alert Configuration

**File**: `config/alerts.json`

Defines alert rules and notification channels. See [MONITORING.md](MONITORING.md) for complete reference.

### Example

```json
{
  "alert_rules": {
    "system_health": {
      "critical_disk_space": {
        "condition": "disk_free_gb < 1",
        "severity": "critical",
        "message": "Critical: Less than 1GB disk space remaining",
        "actions": ["notify_admin", "log_critical"]
      }
    }
  },
  "notification_channels": {
    "notify_admin": {
      "type": "webhook",
      "url": "${ALERT_WEBHOOK_URL}",
      "enabled": true
    }
  }
}
```

---

## Data Mappings Configuration

**File**: `config/data-mappings.json`

Defines custom mappings between data source fields and NetBox fields.

### Example

```json
{
  "device_type_mappings": {
    "Raspberry Pi 4": {
      "manufacturer": "Raspberry Pi Foundation",
      "model": "Raspberry Pi 4 Model B",
      "u_height": 1
    }
  },
  "device_role_mappings": {
    "nas": "Storage Server",
    "switch": "Network Switch",
    "router": "Router"
  },
  "site_mappings": {
    "home": "Home Lab",
    "office": "Office Network"
  }
}
```

---

## Configuration Validation

Validate configuration before starting the agent:

```bash
python scripts/validate-config.py
```

This checks:
- JSON syntax validity
- Required fields present
- Valid field types
- Reachable URLs
- Valid credentials (connection test)

---

## Best Practices

### Security

1. **Never commit secrets**
   - Use `.env` for tokens/passwords
   - Add `.env` to `.gitignore`
   - Use environment-specific `.env` files

2. **Use SSL verification**
   - Only set `verify_ssl: false` for testing
   - Use valid certificates in production

3. **Restrict API tokens**
   - Create tokens with minimum required permissions
   - Rotate tokens regularly (every 90 days)
   - Use separate tokens per environment

### Performance

1. **Adjust batch sizes**
   - Larger batches: Better for many devices (5000+)
   - Smaller batches: Better for limited memory

2. **Tune sync intervals**
   - Longer intervals: Reduce API load
   - Shorter intervals: More up-to-date data

3. **Enable only needed sources**
   - Disable unused data sources
   - Reduces discovery time and resource usage

### Reliability

1. **Enable monitoring**
   - Monitor health endpoint
   - Track metrics trends
   - Configure alerts

2. **Configure logging**
   - Use INFO level for production
   - Use DEBUG for troubleshooting
   - Enable log rotation

3. **Test configuration**
   - Always validate after changes
   - Use dry-run mode first
   - Test in non-production environment

---

## Troubleshooting

### Configuration Not Loading

**Issue**: Agent fails to start with config error

**Solutions**:
1. Validate JSON syntax: `python -m json.tool config/netbox-agent.json`
2. Check file permissions: `ls -la config/`
3. Verify file encoding (should be UTF-8)

### Environment Variables Not Working

**Issue**: `.env` values not being used

**Solutions**:
1. Check `.env` file location (should be in project root)
2. Verify no spaces around `=`: `KEY=value` (not `KEY = value`)
3. Restart agent after changing `.env`

### Connection Failures

**Issue**: Cannot connect to NetBox/data sources

**Solutions**:
1. Test connectivity: `curl ${NETBOX_URL}/api/`
2. Verify token/credentials
3. Check firewall rules
4. Verify SSL settings

---

## Migration Guide

### Upgrading from v0.x to v1.0

1. **Configuration structure changed**
   - `sources` renamed to `data_sources`
   - `sync_settings` merged into `sync`
   - New monitoring section added

2. **New required fields**
   - `sync.mode` (default: `incremental`)
   - `monitoring.enabled` (default: `true`)

3. **Deprecated fields**
   - `global.timeout` → `netbox.timeout`
   - `sources.*.poll_interval` → `sources.*.sync_interval`

### Migration Script

```bash
# Backup current config
cp config/netbox-agent.json config/netbox-agent.json.backup

# Use provided migration tool
python scripts/migrate-config.py --from-version 0.9 --to-version 1.0
```

---

## Reference Links

- [Deployment Guide](DEPLOYMENT.md)
- [Monitoring Guide](MONITORING.md)
- [API Reference](API_REFERENCE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Operational Runbook](RUNBOOK.md)

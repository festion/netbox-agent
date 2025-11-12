# NetBox Agent Monitoring Guide

## Overview

The NetBox Agent includes comprehensive monitoring and alerting capabilities to ensure reliable operation in production environments. This guide covers health checks, metrics collection, alerting, and operational monitoring.

## Architecture

### Components

1. **Health Monitor** (`src/monitoring/health.py`)
   - System resource monitoring
   - NetBox API connectivity checks
   - Disk space monitoring
   - Memory usage tracking

2. **Metrics Collector** (`src/monitoring/metrics.py`)
   - Counter metrics (cumulative values)
   - Histogram metrics (value distributions)
   - Gauge metrics (point-in-time values)
   - Built-in statistics calculation

3. **Health Server** (`scripts/health_server.py`)
   - HTTP endpoints for health checks
   - Metrics exposure
   - Container-ready health checks

4. **Alert Engine** (Configuration-based)
   - Rule-based alerting
   - Multiple notification channels
   - Alert aggregation and cooldown

## Health Checks

### Available Endpoints

#### `/health` - System Health Check
Returns overall system health status and individual check results.

**Example Request:**
```bash
curl http://localhost:8080/health
```

**Example Response:**
```json
{
  "status": "healthy",
  "timestamp": 1699824000.0,
  "checks": {
    "system_resources": {
      "status": "healthy",
      "message": "System resources normal",
      "metadata": {
        "cpu_percent": 45.2,
        "memory_percent": 62.1
      }
    },
    "netbox_api": {
      "status": "healthy",
      "message": "NetBox API responding (0.23s)",
      "response_time": 0.23
    },
    "disk_space": {
      "status": "healthy",
      "message": "Disk space normal: 125.3GB free",
      "metadata": {
        "free_gb": 125.3
      }
    },
    "memory_usage": {
      "status": "healthy",
      "message": "Memory usage normal",
      "metadata": {
        "system_memory_percent": 62.1,
        "process_memory_mb": 156.4
      }
    }
  }
}
```

**Health Status Values:**
- `healthy` - All checks passed
- `degraded` - Some non-critical issues detected
- `unhealthy` - Significant issues detected
- `critical` - Critical issues requiring immediate attention

#### `/metrics` - Metrics Collection
Returns collected metrics for monitoring systems.

**Example Request:**
```bash
curl http://localhost:8080/metrics
```

**Example Response:**
```json
{
  "uptime_seconds": 86400.0,
  "counters": {
    "discovery_runs:{}": 144,
    "discovery_success:{}": 142,
    "discovery_failed:{}": 2,
    "devices_discovered:{}": 15234,
    "sync_runs:{}": 144,
    "sync_success:{}": 143,
    "sync_failed:{}": 1,
    "devices_synced:{}": 15180
  },
  "gauges": {
    "active_data_sources:{}": 3,
    "cached_devices:{}": 15234,
    "last_sync_duration:{}": 12.45
  },
  "histograms": {
    "discovery_duration:{}": {
      "count": 144,
      "avg": 8.23,
      "min": 2.1,
      "max": 45.6
    },
    "sync_duration:{}": {
      "count": 144,
      "avg": 12.34,
      "min": 5.2,
      "max": 89.3
    }
  }
}
```

### Health Check Types

#### 1. System Resources Check
Monitors CPU and memory usage at the system level.

**Thresholds:**
- **Degraded**: CPU > 90% OR Memory > 85%
- **Healthy**: Below thresholds

**Metrics Collected:**
- `cpu_percent` - CPU utilization percentage
- `memory_percent` - System memory utilization percentage

#### 2. NetBox API Check
Validates connectivity and responsiveness of NetBox API.

**Thresholds:**
- **Critical**: API unreachable or not configured
- **Unhealthy**: API returning error status codes
- **Healthy**: API responding with 200 status

**Metrics Collected:**
- `response_time` - API response time in seconds

#### 3. Disk Space Check
Monitors available disk space for logs and cache.

**Thresholds:**
- **Critical**: < 1GB free
- **Unhealthy**: < 5GB free
- **Degraded**: < 10GB free
- **Healthy**: >= 10GB free

**Metrics Collected:**
- `free_gb` - Available disk space in gigabytes

#### 4. Memory Usage Check
Monitors process memory usage and system memory patterns.

**Thresholds:**
- **Critical**: System memory > 90%
- **Degraded**: Process memory > 1GB OR System memory > 80%
- **Healthy**: Below thresholds

**Metrics Collected:**
- `system_memory_percent` - System memory utilization
- `process_memory_mb` - NetBox Agent process memory in MB

## Metrics Collection

### Metric Types

#### Counters
Cumulative values that only increase (e.g., total sync runs, total errors).

**Example Usage:**
```python
metrics.increment_counter("sync_success", labels={"source": "homeassistant"})
metrics.increment_counter("devices_synced", value=150, labels={"batch": "1"})
```

#### Histograms
Track distributions of values over time (e.g., sync duration, discovery time).

**Example Usage:**
```python
metrics.record_histogram("sync_duration", duration, labels={"source": "proxmox"})
metrics.record_histogram("api_response_time", response_time)
```

#### Gauges
Point-in-time values that can go up or down (e.g., active connections, cache size).

**Example Usage:**
```python
metrics.set_gauge("active_data_sources", len(data_sources))
metrics.set_gauge("cached_devices", device_count)
```

### Key Metrics

#### Discovery Metrics
- `discovery_runs` - Total discovery operations
- `discovery_success` - Successful discoveries
- `discovery_failed` - Failed discoveries
- `devices_discovered` - Total devices discovered
- `discovery_duration` - Time taken for discovery (histogram)
- `discovery_error_rate` - Error rate percentage

#### Sync Metrics
- `sync_runs` - Total sync operations
- `sync_success` - Successful syncs
- `sync_failed` - Failed syncs
- `devices_synced` - Total devices synced
- `sync_duration` - Time taken for sync (histogram)
- `sync_error_rate` - Error rate percentage
- `sync_conflicts` - Number of conflict resolutions

#### Data Source Metrics
- `data_source_connections` - Connection attempts per source
- `data_source_failures` - Connection failures per source
- `data_source_response_time` - Response time per source (histogram)
- `active_data_sources` - Currently active sources (gauge)

#### System Metrics
- `uptime_seconds` - Agent uptime
- `cpu_percent` - CPU usage (gauge)
- `memory_percent` - Memory usage (gauge)
- `process_memory_mb` - Process memory usage (gauge)

## Alert Configuration

### Alert Rules

Alert rules are defined in `config/alerts.json`. Each rule includes:
- **Condition**: Expression to evaluate
- **Severity**: `critical` or `warning`
- **Message**: Alert description
- **Actions**: List of notification channels

**Example Rule:**
```json
{
  "critical_disk_space": {
    "condition": "disk_free_gb < 1",
    "severity": "critical",
    "message": "Critical: Less than 1GB disk space remaining",
    "actions": ["notify_admin", "log_critical"]
  }
}
```

### Alert Categories

#### System Health Alerts
- Critical disk space (< 1GB)
- Low disk space (< 5GB)
- High memory usage (> 85%)
- Critical memory usage (> 90%)
- High CPU usage (> 90%)
- Process memory high (> 1GB)

#### NetBox Connectivity Alerts
- NetBox unreachable
- NetBox slow response (> 5s)
- NetBox degraded status

#### Sync Operation Alerts
- Sync failure (> 3 failures)
- High sync error rate (> 20%)
- Sync duration high (> 10 min)
- No devices synced

#### Discovery Operation Alerts
- Discovery failure (> 3 failures)
- High discovery error rate (> 20%)
- No devices discovered
- Discovery timeout (> 5 min)

#### Data Source Alerts
- Data source unreachable
- Data source slow (> 10s)
- Authentication failure

### Notification Channels

#### Log Notifications
All alerts are logged at appropriate levels:
```json
{
  "log_warning": {
    "type": "logging",
    "level": "warning",
    "enabled": true
  },
  "log_critical": {
    "type": "logging",
    "level": "critical",
    "enabled": true
  }
}
```

#### Webhook Notifications
Send alerts to external systems (Slack, PagerDuty, etc.):
```json
{
  "notify_admin": {
    "type": "webhook",
    "url": "${ALERT_WEBHOOK_URL}",
    "enabled": false
  }
}
```

**Configuration:**
1. Set `ALERT_WEBHOOK_URL` in `.env` file
2. Enable webhook in `config/alerts.json`
3. Format should support JSON POST requests

**Webhook Payload:**
```json
{
  "severity": "critical",
  "message": "Critical: Less than 1GB disk space remaining",
  "timestamp": 1699824000.0,
  "alert_rule": "critical_disk_space",
  "metadata": {
    "disk_free_gb": 0.8
  }
}
```

### Alert Settings

#### Check Interval
How often to evaluate alert conditions:
```json
{
  "check_interval_seconds": 60
}
```

#### Evaluation Window
Time window for evaluating conditions:
```json
{
  "evaluation_window_seconds": 300
}
```

#### Cooldown Period
Minimum time between duplicate alerts:
```json
{
  "cooldown_seconds": 300
}
```

#### Alert Throttling
Prevent alert storms:
```json
{
  "aggregate_similar_alerts": true,
  "max_alerts_per_hour": 10
}
```

## Integration with Monitoring Systems

### Prometheus Integration

The `/metrics` endpoint can be scraped by Prometheus:

**Prometheus Configuration (prometheus.yml):**
```yaml
scrape_configs:
  - job_name: 'netbox-agent'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 60s
```

### Grafana Dashboard

Create dashboards using Prometheus data source:

**Example Queries:**
```promql
# Discovery success rate
rate(discovery_success[5m]) / rate(discovery_runs[5m])

# Average sync duration
avg(sync_duration)

# Memory usage trend
process_memory_mb
```

### Docker Health Checks

The health endpoint is used for Docker health checks:

**docker-compose.yml:**
```yaml
healthcheck:
  test: ["CMD", "python3", "/app/scripts/health_check.py"]
  interval: 60s
  timeout: 10s
  retries: 3
  start_period: 30s
```

### Kubernetes Probes

Use health endpoint for liveness and readiness probes:

**Deployment YAML:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 60

readinessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 30
```

## Troubleshooting

### Health Check Failures

#### NetBox API Unreachable
**Symptoms:** `/health` shows `netbox_api` status as `critical`

**Investigation:**
1. Verify NetBox URL in configuration
2. Check network connectivity: `curl ${NETBOX_URL}/api/`
3. Verify API token is valid
4. Check firewall rules

**Resolution:**
- Update NetBox URL in `config/netbox-agent.json`
- Regenerate API token if expired
- Configure network access

#### High Memory Usage
**Symptoms:** `/health` shows `memory_usage` status as `degraded` or `critical`

**Investigation:**
1. Check process memory: `ps aux | grep netbox_agent`
2. Review sync batch sizes
3. Check for memory leaks in logs

**Resolution:**
- Reduce batch size in configuration
- Restart agent to clear memory
- Review recent code changes for leaks

#### Disk Space Critical
**Symptoms:** `/health` shows `disk_space` status as `critical`

**Investigation:**
1. Check disk usage: `df -h`
2. Check log file sizes: `du -sh logs/`
3. Verify log rotation is working

**Resolution:**
- Clean old log files
- Configure log rotation (see DEPLOYMENT.md)
- Increase disk space if needed

### Metrics Not Updating

**Symptoms:** `/metrics` shows stale data or zero values

**Investigation:**
1. Check if agent is running: `systemctl status netbox-agent`
2. Verify sync/discovery is executing
3. Check for errors in logs

**Resolution:**
- Restart agent
- Verify data source connections
- Check configuration for disabled features

### Alert Not Triggering

**Symptoms:** Alert condition met but no notification received

**Investigation:**
1. Check alert configuration in `config/alerts.json`
2. Verify notification channel is enabled
3. Check webhook URL if using webhooks
4. Review alert cooldown settings

**Resolution:**
- Enable notification channel
- Configure webhook URL in `.env`
- Adjust cooldown period if needed

## Best Practices

### Production Monitoring

1. **Enable Health Checks**
   - Always enable health endpoint in production
   - Configure appropriate timeouts
   - Use in load balancer health checks

2. **Set Up External Monitoring**
   - Use Prometheus/Grafana for visualization
   - Configure alerting to external systems
   - Monitor trends over time

3. **Regular Review**
   - Review metrics weekly
   - Adjust thresholds based on patterns
   - Update alert rules as needed

4. **Log Management**
   - Configure log rotation
   - Archive old logs
   - Monitor log volume

### Alert Configuration

1. **Appropriate Thresholds**
   - Set warning levels before critical
   - Allow time for intervention
   - Avoid alert fatigue

2. **Notification Routing**
   - Critical alerts to on-call
   - Warnings to team channel
   - Use escalation policies

3. **Alert Testing**
   - Test webhook endpoints
   - Verify notification delivery
   - Practice incident response

### Performance Monitoring

1. **Baseline Metrics**
   - Establish normal operating ranges
   - Document expected values
   - Track changes over time

2. **Capacity Planning**
   - Monitor growth trends
   - Project resource needs
   - Plan for scaling

3. **Optimization**
   - Identify slow operations
   - Optimize high-latency calls
   - Tune batch sizes

## Reference

### Configuration Files
- `config/alerts.json` - Alert rule definitions
- `config/netbox-agent.json` - Monitoring settings
- `.env` - Webhook URLs and secrets

### Scripts
- `scripts/health_check.py` - Container health check
- `scripts/health_server.py` - HTTP health server

### Source Files
- `src/monitoring/health.py` - Health check implementation
- `src/monitoring/metrics.py` - Metrics collection

### Related Documentation
- [Deployment Guide](DEPLOYMENT.md) - Installation and setup
- [Operational Runbook](RUNBOOK.md) - Incident response procedures
- [Configuration Reference](../template-config.json) - Configuration options

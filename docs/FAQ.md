# NetBox Agent - Frequently Asked Questions

**Last Updated**: 2025-11-12

---

## General Questions

### What is the NetBox Agent?

The NetBox Agent is an automation tool that discovers network devices from multiple sources (Home Assistant, Proxmox, TrueNAS, network scans, configuration files) and automatically syncs them to NetBox for inventory management and documentation.

### What are the system requirements?

- **Python**: 3.8 or higher
- **Memory**: 1GB minimum, 2GB recommended
- **Disk**: 10GB for logs and cache
- **Network**: Access to NetBox API and data sources
- **OS**: Linux, macOS, or Windows (Linux recommended for production)

### Is it production-ready?

Yes! The NetBox Agent is production-ready with:
- 126 automated tests (98% pass rate)
- Comprehensive monitoring and alerting
- Multiple deployment methods (systemd, Docker, quick-start)
- Complete operational documentation
- Security audited
- Performance tested (handles 5000+ devices)

---

## Installation & Setup

### How do I install the NetBox Agent?

Three methods available:

**1. Quick Start** (Development/Testing):
```bash
git clone https://github.com/festion/netbox-agent.git
cd netbox-agent
./scripts/quick-start.sh
```

**2. Systemd Service** (Production):
```bash
sudo ./scripts/install.sh
```

**3. Docker**:
```bash
docker compose up -d
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

### How do I configure the agent?

1. Copy template configuration:
   ```bash
   cp template-config.json config/netbox-agent.json
   ```

2. Edit configuration with your NetBox URL and token
3. Configure data sources you want to use
4. Validate configuration:
   ```bash
   python scripts/validate-config.py
   ```

See [CONFIGURATION_REFERENCE.md](CONFIGURATION_REFERENCE.md) for complete options.

### Where do I get a NetBox API token?

In NetBox:
1. Go to Admin → API Tokens
2. Click "+ Add" to create new token
3. Give it write permissions for DCIM module
4. Copy the token to `.env` file or config

### Can I use self-signed SSL certificates?

Yes, set `verify_ssl: false` in configuration. However, this is only recommended for testing. In production, use valid certificates or configure a proper CA.

---

## Data Sources

### Which data sources are supported?

- **Home Assistant**: Smart home devices
- **Proxmox VE**: Virtual machines and containers
- **TrueNAS**: Storage systems
- **Network Scanner**: ICMP/port scanning
- **Filesystem**: Configuration files (Ansible, network configs)

### Do I need to enable all data sources?

No! Enable only the sources you need. Each source can be independently enabled/disabled in configuration.

### Can I create a custom data source?

Yes! Inherit from the `DataSource` base class and implement `connect()`, `discover()`, and `test_connection()` methods. See [API_REFERENCE.md](API_REFERENCE.md#custom-development) for a complete guide.

### How often does the agent discover devices?

Configurable per source with `sync_interval` (default: 3600 seconds / 1 hour). You can also run manual discovery anytime.

### Why aren't all Home Assistant devices being discovered?

The agent only discovers network-relevant devices (devices with IP addresses, MAC addresses, or network connectivity). Smart bulbs, sensors without network interfaces, etc. are filtered out.

---

## Synchronization

### What's the difference between full and incremental sync?

- **Full Sync**: Syncs all discovered devices (default: every 24 hours)
- **Incremental Sync**: Syncs only changed/new devices (default: every hour)

Both are configurable in the `sync` section of configuration.

### Can I preview changes before applying them?

Yes! Use dry-run mode:
```bash
python src/netbox_agent.py --sync --dry-run
```

This shows what would be created/updated without actually modifying NetBox.

### What happens when the same device is found in multiple sources?

The deduplication engine identifies duplicates by matching fields (name, serial, MAC address) and merges them based on your configured strategy (prefer_newest, prefer_source, or merge_all).

### What if NetBox already has devices with the same names?

The agent uses conflict resolution strategies:
- `prefer_netbox`: Keeps existing NetBox data (default)
- `prefer_source`: Overwrites with discovered data
- `merge`: Merges non-conflicting fields
- `manual`: Skips conflicts and logs for manual resolution

Configure in the `sync.conflict_resolution` setting.

### Will the agent delete devices from NetBox?

No. The agent never deletes devices. It only creates new devices and updates existing ones (based on conflict resolution strategy).

---

## Troubleshooting

### The agent won't start. What should I check?

1. Validate configuration:
   ```bash
   python scripts/validate-config.py
   ```

2. Check logs:
   ```bash
   tail -50 logs/netbox-agent.log
   ```

3. Test connections:
   ```bash
   python src/netbox_agent.py --test-connections
   ```

4. Common issues:
   - Invalid JSON in configuration
   - Wrong NetBox URL/token
   - Network connectivity issues
   - Missing dependencies

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed guides.

### NetBox API connection fails. What's wrong?

Check these:
1. NetBox URL is correct (include `http://` or `https://`)
2. API token is valid and has write permissions
3. Network connectivity: `curl ${NETBOX_URL}/api/`
4. Firewall rules allow access
5. SSL verification settings (`verify_ssl`)

### Devices aren't showing up in NetBox. Why?

1. Check if discovery is finding devices:
   ```bash
   python src/netbox_agent.py --discover-only
   ```

2. Check sync isn't in dry-run mode
3. Review logs for sync errors
4. Verify NetBox token has write permissions
5. Check conflict resolution isn't skipping devices

### Performance is slow. How can I improve it?

1. **Increase batch size**: Higher = faster (if you have memory)
   ```json
   {"sync": {"batch_size": 1000}}
   ```

2. **Reduce sync intervals**: Sync less frequently
   ```json
   {"sync": {"incremental_sync_interval": 7200}}
   ```

3. **Disable unused sources**: Only enable needed data sources

4. **Limit network scanning**: Reduce scanned networks/ports

See [PERFORMANCE_BENCHMARKS.md](PERFORMANCE_BENCHMARKS.md) for expected performance.

---

## Monitoring & Operations

### How do I monitor the agent?

The agent provides two HTTP endpoints:

1. **Health Check**: `http://localhost:8080/health`
   - System resources, disk space, memory
   - NetBox API connectivity
   - Returns healthy/degraded/unhealthy/critical

2. **Metrics**: `http://localhost:8080/metrics`
   - Discovery/sync success rates
   - Performance metrics
   - Resource usage

See [MONITORING.md](MONITORING.md) for complete guide.

### How do I set up alerts?

Configure alerts in `config/alerts.json`:
1. Define alert conditions (disk space, memory, sync failures, etc.)
2. Configure notification channels (webhooks, logging)
3. Set alert thresholds and cooldown periods

See [MONITORING.md](MONITORING.md#alert-configuration) for examples.

### How do I check if the agent is running?

**Systemd**:
```bash
systemctl status netbox-agent
```

**Docker**:
```bash
docker ps | grep netbox-agent
```

**Health Check**:
```bash
curl http://localhost:8080/health
```

### Where are the logs?

| Deployment | Location |
|------------|----------|
| Systemd | `/opt/netbox-agent/logs/` |
| Docker | `docker logs netbox-agent` |
| Quick Start | `./logs/` |

### How do I rotate logs?

Logs are automatically rotated if you:
- Use systemd deployment (configured by install script)
- Configure logrotate manually (see [DEPLOYMENT.md](DEPLOYMENT.md#log-rotation))

---

## Security

### Is it secure to store tokens in configuration files?

No! Use environment variables in `.env` file instead:
```bash
NETBOX_TOKEN=your-token-here
PROXMOX_TOKEN=your-token-here
```

Add `.env` to `.gitignore` to prevent committing secrets.

### Should I use verify_ssl: false in production?

No! Only use `verify_ssl: false` for testing with self-signed certificates. In production:
- Use valid SSL certificates
- Configure proper CA certificates
- Use `verify_ssl: true`

### What permissions does the NetBox token need?

Minimum required permissions:
- **DCIM module**: Read + Write
  - Devices
  - Device Types
  - Device Roles
  - Sites
  - Interfaces

### Can I run the agent as root?

Not recommended! The agent should run as a non-root user:
- Systemd: Runs as `netboxagent` user
- Docker: Runs as UID 1000
- Quick Start: Runs as your current user

### How often should I rotate API tokens?

Recommended: Every 90 days. Steps:
1. Generate new token in NetBox
2. Update `.env` file
3. Restart agent
4. Verify connectivity
5. Revoke old token

---

## Advanced Usage

### Can I run multiple instances?

Yes, but be careful:
- Use different configuration files
- Ensure different data sources (avoid duplicates)
- Monitor for conflicts in NetBox
- Consider using tags to identify sources

### How do I migrate to a new NetBox instance?

1. Update NetBox URL in configuration
2. Generate new API token in new NetBox
3. Run with `--dry-run` first to preview
4. Full sync to new instance
5. Verify data migrated correctly

### Can I customize device naming?

Yes! Use data mappings in `config/data-mappings.json`:
```json
{
  "device_name": {
    "source_field": "name",
    "transform_function": "clean_device_name"
  }
}
```

### How do I exclude certain devices?

Use filters in data source configuration:
```json
{
  "network_scan": {
    "networks": ["192.168.1.0/24"],
    "exclude_hosts": ["192.168.1.1", "192.168.1.254"]
  }
}
```

Or use tags in NetBox to mark devices as managed manually.

### Can I run the agent in Kubernetes?

Yes! Use the Docker image with Kubernetes deployment:
1. Create ConfigMap for configuration
2. Create Secret for tokens
3. Deploy with liveness/readiness probes
4. Use health endpoints for probes

See [DEPLOYMENT.md](DEPLOYMENT.md#kubernetes-probes) for example YAML.

---

## Development & Contribution

### How do I run tests?

```bash
# All tests
pytest

# Specific test suite
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/

# With coverage
pytest --cov=src --cov-report=html
```

### How do I contribute?

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Run test suite
5. Submit pull request

See `CONTRIBUTING.md` (if exists) or contact maintainers.

### Where can I get help?

1. **Documentation**: Check the `docs/` directory
2. **Issues**: Create GitHub issue
3. **Logs**: Check agent logs for errors
4. **Community**: (Add community channels if available)

---

## Performance & Scalability

### How many devices can the agent handle?

Tested and validated:
- **1000 devices**: < 1 second discovery, ~0.3 second sync
- **5000 devices**: < 1 second discovery, ~1.5 second sync
- **Memory**: < 250MB for 5000 devices

No hard limit - performance depends on available resources.

### Does it support clustering?

Not currently. The agent is designed to run as a single instance. For high availability:
- Run multiple instances with different data sources
- Use systemd auto-restart or Docker restart policies
- Monitor health endpoints

### How do I optimize for large deployments?

1. Increase batch size: `"batch_size": 1000`
2. Use incremental sync more frequently
3. Limit full sync to off-peak hours
4. Use network scanning sparingly
5. Monitor resource usage

---

## Compatibility

### Which NetBox versions are supported?

Tested with NetBox 3.0+. Should work with any NetBox 3.x version. NetBox 4.x compatibility may require updates.

### Which Proxmox versions are supported?

Proxmox VE 7.x and 8.x are supported via the Proxmox MCP server.

### Which Home Assistant versions are supported?

Home Assistant Core 2021.x and newer are supported via REST API.

### Does it work on Windows?

Yes, but Linux is recommended for production:
- Development/testing: Windows works fine
- Production: Use Linux for systemd service and better performance
- Docker: Works on all platforms

---

## Backup & Recovery

### What should I backup?

Critical files:
- `config/netbox-agent.json` - Configuration
- `config/alerts.json` - Alert rules
- `config/data-mappings.json` - Custom mappings
- `.env` - Environment variables/secrets
- `logs/` - Optional (for troubleshooting history)

### How do I restore from backup?

1. Stop agent
2. Restore configuration files
3. Validate configuration
4. Test connections
5. Start agent

### What if I lose configuration?

If you have a backup:
- Restore from backup and restart

If no backup:
- Reconfigure from `template-config.json`
- Test with `--dry-run` before live sync
- Agent won't delete existing NetBox data

---

## Cost & Licensing

### Is the NetBox Agent free?

Yes! The NetBox Agent is open source under MIT license.

### What are the costs?

No licensing costs. Only infrastructure costs:
- NetBox instance (can be self-hosted free)
- Server/container to run agent
- Network connectivity

### Can I use it commercially?

Yes! MIT license allows commercial use, modification, and distribution.

---

## Getting Started Checklist

New to the NetBox Agent? Follow this checklist:

- [ ] Install Python 3.8+ and dependencies
- [ ] Clone repository
- [ ] Run quick-start script
- [ ] Configure NetBox URL and token in `.env`
- [ ] Enable one data source (start with Proxmox or network scan)
- [ ] Validate configuration
- [ ] Test connections
- [ ] Run discovery in dry-run mode
- [ ] Review discovered devices
- [ ] Run actual sync
- [ ] Verify devices in NetBox
- [ ] Set up monitoring
- [ ] Configure alerts
- [ ] Schedule automatic syncs
- [ ] Read operational runbook

---

## Additional Resources

- [Quick Start Guide](../README.md#quick-start)
- [Deployment Guide](DEPLOYMENT.md)
- [Configuration Reference](CONFIGURATION_REFERENCE.md)
- [API Reference](API_REFERENCE.md)
- [Monitoring Guide](MONITORING.md)
- [Operational Runbook](RUNBOOK.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Performance Benchmarks](PERFORMANCE_BENCHMARKS.md)
- [Security Audit Report](SECURITY_AUDIT.md)

---

## Still Have Questions?

If your question isn't answered here:
1. Check the relevant documentation in `docs/`
2. Search existing GitHub issues
3. Create a new GitHub issue with:
   - Your question
   - Relevant configuration (redact secrets!)
   - Log excerpts (if applicable)
   - Environment details (OS, Python version, etc.)

We're here to help! 🚀

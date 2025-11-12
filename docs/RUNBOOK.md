# NetBox Agent Operational Runbook

## Overview

This runbook provides step-by-step procedures for common operational tasks, troubleshooting, and incident response for the NetBox Agent in production environments.

**Target Audience:** System administrators, DevOps engineers, on-call engineers

**Prerequisites:**
- Access to production server/container
- NetBox admin access
- Log access
- Monitoring system access

---

## Quick Reference

### Service Management

| Task | Command |
|------|---------|
| Check status | `systemctl status netbox-agent` |
| Start service | `systemctl start netbox-agent` |
| Stop service | `systemctl stop netbox-agent` |
| Restart service | `systemctl restart netbox-agent` |
| View logs | `journalctl -u netbox-agent -f` |
| Check health | `curl http://localhost:8080/health` |
| View metrics | `curl http://localhost:8080/metrics` |

### Docker Commands

| Task | Command |
|------|---------|
| Check status | `docker ps \| grep netbox-agent` |
| View logs | `docker logs -f netbox-agent` |
| Restart container | `docker restart netbox-agent` |
| Check health | `docker inspect --format='{{.State.Health.Status}}' netbox-agent` |
| Shell access | `docker exec -it netbox-agent /bin/bash` |

### Log Locations

| Deployment | Location |
|------------|----------|
| Systemd | `/opt/netbox-agent/logs/` |
| Docker | `docker logs netbox-agent` |
| Quick Start | `./logs/` |

---

## Alert Response Procedures

### Critical Alerts

#### ALERT: NetBox API Unreachable

**Severity:** Critical
**Impact:** No sync operations possible, devices not updated in NetBox

**Immediate Actions:**
1. Check NetBox API status:
   ```bash
   curl ${NETBOX_URL}/api/
   ```

2. Verify network connectivity:
   ```bash
   ping netbox-hostname
   traceroute netbox-hostname
   ```

3. Check agent logs for error details:
   ```bash
   tail -100 /opt/netbox-agent/logs/netbox-agent.log | grep -i netbox
   ```

**Troubleshooting Steps:**

1. **Verify NetBox is running:**
   - Check NetBox service status on NetBox server
   - Verify NetBox web interface is accessible
   - Check NetBox logs for errors

2. **Verify network path:**
   - Check firewall rules between agent and NetBox
   - Verify DNS resolution: `nslookup netbox-hostname`
   - Test network path: `telnet netbox-hostname 443`

3. **Verify authentication:**
   - Check API token is valid in NetBox UI
   - Verify token in agent configuration matches
   - Check token permissions in NetBox

4. **Check agent configuration:**
   ```bash
   cat /opt/netbox-agent/config/netbox-agent.json | grep -A5 '"netbox"'
   ```

**Resolution:**
- Update NetBox URL if changed
- Regenerate API token if expired
- Fix firewall rules if blocking
- Restart agent after configuration changes

**Escalation:**
- If NetBox server is down: Contact NetBox admin team
- If network issue: Contact network operations
- If unresolved after 30 minutes: Escalate to senior engineer

---

#### ALERT: Critical Disk Space

**Severity:** Critical
**Impact:** Log files cannot be written, potential data loss

**Immediate Actions:**
1. Check disk usage:
   ```bash
   df -h
   du -sh /opt/netbox-agent/logs/*
   ```

2. Find largest files:
   ```bash
   du -ah /opt/netbox-agent | sort -rh | head -20
   ```

**Troubleshooting Steps:**

1. **Clean old log files:**
   ```bash
   # List logs older than 30 days
   find /opt/netbox-agent/logs -name "*.log" -mtime +30

   # Remove logs older than 30 days
   find /opt/netbox-agent/logs -name "*.log" -mtime +30 -delete
   ```

2. **Compress old logs:**
   ```bash
   gzip /opt/netbox-agent/logs/*.log.1
   gzip /opt/netbox-agent/logs/*.log.2
   ```

3. **Configure log rotation:**
   ```bash
   sudo nano /etc/logrotate.d/netbox-agent
   ```

   Add:
   ```
   /opt/netbox-agent/logs/*.log {
       daily
       rotate 7
       compress
       delaycompress
       missingok
       notifempty
   }
   ```

4. **Check for runaway processes:**
   ```bash
   lsof | grep deleted  # Find deleted files still held open
   systemctl restart netbox-agent  # Release file handles
   ```

**Resolution:**
- Clean old logs immediately
- Configure proper log rotation
- Monitor disk usage daily
- Consider increasing disk size if recurring

**Prevention:**
- Implement automated log rotation
- Set up disk space monitoring alerts at 80%
- Archive old logs to separate storage

---

#### ALERT: Critical Memory Usage

**Severity:** Critical
**Impact:** Service may crash or become unresponsive

**Immediate Actions:**
1. Check memory usage:
   ```bash
   free -h
   ps aux | grep netbox_agent | head -1
   ```

2. Review agent memory:
   ```bash
   curl http://localhost:8080/health | jq '.checks.memory_usage'
   ```

**Troubleshooting Steps:**

1. **Check for memory leak:**
   ```bash
   # Monitor memory over time
   watch -n 5 'ps aux | grep netbox_agent | head -1'
   ```

2. **Review recent operations:**
   ```bash
   tail -100 /opt/netbox-agent/logs/netbox-agent.log | grep -E 'sync|discovery'
   ```

3. **Check batch sizes:**
   ```bash
   cat /opt/netbox-agent/config/netbox-agent.json | grep -i batch
   ```

**Resolution:**

1. **Temporary fix - Restart service:**
   ```bash
   systemctl restart netbox-agent
   ```

2. **Permanent fix - Reduce batch size:**
   Edit `config/netbox-agent.json`:
   ```json
   {
     "sync": {
       "batch_size": 100  // Reduce from default 500
     }
   }
   ```

3. **Monitor after restart:**
   ```bash
   watch -n 10 'curl -s http://localhost:8080/health | jq ".checks.memory_usage"'
   ```

**Escalation:**
- If memory continues to grow: Potential memory leak, escalate to development team
- If recurring: Review application code for optimization

---

### Warning Alerts

#### ALERT: High Sync Error Rate

**Severity:** Warning
**Impact:** Some devices may not be synced properly

**Investigation:**
1. Check sync metrics:
   ```bash
   curl http://localhost:8080/metrics | jq '.counters'
   ```

2. Review error logs:
   ```bash
   grep -i "error\|failed" /opt/netbox-agent/logs/netbox-agent.log | tail -50
   ```

3. Identify failing sources:
   ```bash
   grep "sync_failed" /opt/netbox-agent/logs/netbox-agent.log | cut -d: -f3 | sort | uniq -c
   ```

**Common Causes:**
- NetBox API rate limiting
- Invalid device data
- Network timeouts
- Configuration errors

**Resolution:**
1. Review and fix invalid data
2. Increase API timeout in configuration
3. Add retry logic for transient failures
4. Contact NetBox admin if rate-limited

---

#### ALERT: Data Source Unreachable

**Severity:** Warning
**Impact:** Devices from this source not discovered

**Investigation:**
1. Identify failing source:
   ```bash
   grep "data_source.*unreachable" /opt/netbox-agent/logs/netbox-agent.log | tail -10
   ```

2. Test connectivity:
   ```bash
   # For Home Assistant
   curl -H "Authorization: Bearer ${HA_TOKEN}" ${HA_URL}/api/

   # For Proxmox
   curl -k ${PROXMOX_URL}/api2/json/cluster/resources
   ```

**Resolution:**
1. Verify data source is running
2. Check authentication credentials
3. Verify network connectivity
4. Update configuration if URLs changed
5. Temporarily disable source if maintenance window

---

## Routine Operations

### Daily Tasks

#### Check Service Health
```bash
# Check overall health
curl http://localhost:8080/health | jq '.'

# Check service status
systemctl status netbox-agent

# Review recent logs
journalctl -u netbox-agent --since "1 hour ago" | grep -i "error\|warn"
```

**Expected Results:**
- Health status: `healthy`
- Service: `active (running)`
- No error or warning messages

---

#### Monitor Sync Success Rate
```bash
# Get metrics
curl http://localhost:8080/metrics | jq '.counters'

# Calculate success rate
sync_success=$(curl -s http://localhost:8080/metrics | jq -r '.counters["sync_success:{}"]')
sync_total=$(curl -s http://localhost:8080/metrics | jq -r '.counters["sync_runs:{}"]')
echo "Success rate: $(echo "scale=2; $sync_success * 100 / $sync_total" | bc)%"
```

**Target:** > 98% success rate

---

### Weekly Tasks

#### Review Performance Metrics
```bash
# Get average sync duration
curl http://localhost:8080/metrics | jq '.histograms."sync_duration:{}"'

# Get average discovery duration
curl http://localhost:8080/metrics | jq '.histograms."discovery_duration:{}"'

# Check device counts
curl http://localhost:8080/metrics | jq '.counters."devices_synced:{}"'
```

**Actions:**
- Document baseline metrics
- Identify performance trends
- Optimize if degradation detected

---

#### Log Review
```bash
# Check log file sizes
du -h /opt/netbox-agent/logs/*

# Review error patterns
grep -i error /opt/netbox-agent/logs/netbox-agent.log | \
  awk '{print $5}' | sort | uniq -c | sort -rn

# Check for warnings
grep -i warn /opt/netbox-agent/logs/netbox-agent.log | tail -20
```

**Actions:**
- Archive logs older than 30 days
- Investigate recurring errors
- Update documentation with new issues

---

#### Configuration Review
```bash
# Backup current configuration
cp /opt/netbox-agent/config/netbox-agent.json \
   /opt/netbox-agent/config/netbox-agent.json.backup-$(date +%Y%m%d)

# Validate configuration
python3 /opt/netbox-agent/scripts/validate-config.py

# Review enabled data sources
cat /opt/netbox-agent/config/netbox-agent.json | jq '.data_sources'
```

---

### Monthly Tasks

#### Performance Baseline Update
```bash
# Collect 7-day average metrics
./scripts/collect-metrics.sh --days 7 > metrics-baseline-$(date +%Y%m).json

# Compare with previous month
diff metrics-baseline-$(date +%Y%m).json metrics-baseline-$(date -d "1 month ago" +%Y%m).json
```

---

#### Security Review
```bash
# Check for updates
cd /opt/netbox-agent
git fetch origin
git log HEAD..origin/main --oneline

# Review security advisories
# Check requirements for CVEs
pip list --outdated

# Review API token age
# Rotate tokens if > 90 days old
```

---

#### Capacity Planning
```bash
# Review resource trends
curl http://localhost:8080/metrics | jq '.gauges'

# Check disk usage trend
df -h | grep /opt/netbox-agent

# Estimate growth
devices_per_day=$(echo "scale=2; $devices_total / 30" | bc)
echo "Device growth: $devices_per_day devices/day"
```

**Actions:**
- Project next 3 months resource needs
- Plan scaling if needed
- Update capacity documentation

---

## Maintenance Procedures

### Service Restart

**When to Restart:**
- After configuration changes
- Memory usage high
- Performance degradation
- After updates

**Procedure:**
```bash
# 1. Check current status
systemctl status netbox-agent

# 2. Stop service gracefully
systemctl stop netbox-agent

# 3. Wait for processes to stop (max 30s)
sleep 5

# 4. Verify stopped
systemctl status netbox-agent

# 5. Start service
systemctl start netbox-agent

# 6. Verify started
systemctl status netbox-agent

# 7. Check health
sleep 10
curl http://localhost:8080/health
```

---

### Configuration Changes

**Procedure:**
```bash
# 1. Backup current configuration
cp /opt/netbox-agent/config/netbox-agent.json \
   /opt/netbox-agent/config/netbox-agent.json.backup

# 2. Edit configuration
nano /opt/netbox-agent/config/netbox-agent.json

# 3. Validate configuration
python3 /opt/netbox-agent/scripts/validate-config.py

# 4. Test with dry-run
cd /opt/netbox-agent
source venv/bin/activate
python src/netbox_agent.py --sync --dry-run

# 5. If successful, restart service
systemctl restart netbox-agent

# 6. Monitor for errors
journalctl -u netbox-agent -f
```

**Rollback if needed:**
```bash
cp /opt/netbox-agent/config/netbox-agent.json.backup \
   /opt/netbox-agent/config/netbox-agent.json
systemctl restart netbox-agent
```

---

### Software Updates

**Procedure:**
```bash
# 1. Check for updates
cd /opt/netbox-agent
git fetch origin
git log HEAD..origin/main --oneline

# 2. Backup current state
systemctl stop netbox-agent
tar czf /tmp/netbox-agent-backup-$(date +%Y%m%d).tar.gz /opt/netbox-agent

# 3. Pull updates
git pull origin main

# 4. Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# 5. Validate installation
python scripts/validate-config.py
./scripts/validate-deployment.sh

# 6. Test with dry-run
python src/netbox_agent.py --test-connections

# 7. Start service
systemctl start netbox-agent

# 8. Monitor for 15 minutes
journalctl -u netbox-agent -f
```

**Rollback if needed:**
```bash
systemctl stop netbox-agent
cd /opt/netbox-agent
git reset --hard HEAD@{1}
pip install -r requirements.txt
systemctl start netbox-agent
```

---

## Disaster Recovery

### Service Not Starting

**Symptoms:**
- `systemctl start netbox-agent` fails
- Service immediately stops after starting

**Troubleshooting:**
```bash
# 1. Check service logs
journalctl -u netbox-agent -n 100 --no-pager

# 2. Check for port conflicts
sudo netstat -tlnp | grep :8080

# 3. Check file permissions
ls -la /opt/netbox-agent/src/netbox_agent.py

# 4. Try manual start
cd /opt/netbox-agent
source venv/bin/activate
python src/netbox_agent.py
```

**Common Fixes:**
- Fix configuration syntax errors
- Kill process using port 8080
- Fix file permissions: `chown -R netboxagent:netboxagent /opt/netbox-agent`
- Reinstall dependencies: `pip install -r requirements.txt`

---

### Data Corruption

**Symptoms:**
- Sync fails with validation errors
- Unexpected device updates
- Duplicate devices created

**Recovery:**
```bash
# 1. Stop service immediately
systemctl stop netbox-agent

# 2. Backup current state
tar czf /tmp/netbox-agent-state-$(date +%Y%m%d-%H%M).tar.gz /opt/netbox-agent

# 3. Clear cache (if cache-related)
rm -rf /opt/netbox-agent/cache/*

# 4. Run discovery without sync
cd /opt/netbox-agent
source venv/bin/activate
python src/netbox_agent.py --discover-only --dry-run

# 5. Review discovered devices
cat /opt/netbox-agent/logs/netbox-agent.log | grep "Discovered"

# 6. If data looks correct, sync with dry-run
python src/netbox_agent.py --sync --dry-run

# 7. Review planned changes
cat /opt/netbox-agent/logs/netbox-agent.log | grep "Would"

# 8. If acceptable, perform actual sync
python src/netbox_agent.py --sync

# 9. Start service
systemctl start netbox-agent
```

---

### Complete System Restore

**When to Use:**
- Agent completely broken
- Configuration corrupted
- Multiple failures

**Procedure:**
```bash
# 1. Stop service
systemctl stop netbox-agent

# 2. Restore from backup
cd /
tar xzf /tmp/netbox-agent-backup-YYYYMMDD.tar.gz

# 3. Verify configuration
python3 /opt/netbox-agent/scripts/validate-config.py

# 4. Start service
systemctl start netbox-agent

# 5. Monitor
journalctl -u netbox-agent -f
```

---

## Contact Information

### Escalation Path

| Level | Contact | When to Escalate |
|-------|---------|------------------|
| L1 - Operations | ops-team@company.com | Initial alert response |
| L2 - Senior Ops | senior-ops@company.com | Unresolved after 30 min |
| L3 - Development | dev-team@company.com | Code issue suspected |
| L4 - Management | it-manager@company.com | Critical impact > 4 hours |

### External Contacts

| Service | Contact | Purpose |
|---------|---------|---------|
| NetBox Admin | netbox-admin@company.com | NetBox API issues |
| Network Ops | network-ops@company.com | Connectivity issues |
| Security | security@company.com | Security incidents |

---

## Appendix

### Useful Commands

**View active connections:**
```bash
lsof -i -P -n | grep netbox
```

**Check process tree:**
```bash
pstree -p | grep netbox
```

**Monitor resource usage:**
```bash
top -p $(pidof python)
```

**Test NetBox API:**
```bash
curl -H "Authorization: Token ${NETBOX_TOKEN}" \
     -H "Content-Type: application/json" \
     ${NETBOX_URL}/api/dcim/devices/
```

### Configuration Locations

| File | Purpose |
|------|---------|
| `/opt/netbox-agent/config/netbox-agent.json` | Main configuration |
| `/opt/netbox-agent/config/alerts.json` | Alert rules |
| `/opt/netbox-agent/.env` | Environment variables |
| `/etc/systemd/system/netbox-agent.service` | Service definition |

### Log Analysis

**Find sync failures:**
```bash
grep "sync_failed\|SyncError" /opt/netbox-agent/logs/netbox-agent.log
```

**Count errors by type:**
```bash
grep -i error /opt/netbox-agent/logs/netbox-agent.log | \
  awk '{print $5}' | sort | uniq -c | sort -rn
```

**Performance analysis:**
```bash
grep "duration" /opt/netbox-agent/logs/netbox-agent.log | \
  awk '{print $NF}' | sort -n | tail -10
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-12
**Review Schedule:** Quarterly

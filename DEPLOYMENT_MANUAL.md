# NetBox Agent - Manual Deployment to 192.168.1.200

## Deployment Package Ready

A deployment package has been created at: `/tmp/netbox-agent-deploy.tar.gz` (24MB)

## Deployment Steps

### Option 1: Direct SSH Deployment (Recommended if SSH works)

From your current machine, run these commands:

```bash
# Copy deployment package
scp /tmp/netbox-agent-deploy.tar.gz dev@192.168.1.200:/tmp/

# Connect to remote host
ssh dev@192.168.1.200

# On the remote host (192.168.1.200):
sudo mkdir -p /opt/netbox-agent
cd /opt/netbox-agent
sudo tar -xzf /tmp/netbox-agent-deploy.tar.gz
sudo chown -R $(whoami):$(whoami) /opt/netbox-agent
mkdir -p logs cache
rm /tmp/netbox-agent-deploy.tar.gz

# Build and start the Docker container
docker-compose build
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f netbox-agent
```

### Option 2: Manual File Transfer

If SSH is not working, you can:

1. **Copy the file using another method** (USB, network share, etc.):
   - Source: `/tmp/netbox-agent-deploy.tar.gz` on current machine
   - Destination: Any location on 192.168.1.200

2. **On 192.168.1.200**, extract and deploy:
```bash
sudo mkdir -p /opt/netbox-agent
cd /opt/netbox-agent
sudo tar -xzf /path/to/netbox-agent-deploy.tar.gz
sudo chown -R $USER:$USER /opt/netbox-agent
mkdir -p logs cache
docker-compose build
docker-compose up -d
```

## Configuration Review

Your current configuration (`config/netbox-agent.json`):

- **NetBox URL**: https://netbox.internal.lakehouse.wtf/
- **Dry Run Mode**: ENABLED (safe - won't modify NetBox yet)
- **Enabled Sources**:
  - ✅ Home Assistant (192.168.1.155:8123)
  - ✅ Network Scanner (192.168.1.0/24, 10.0.0.0/24)
  - ✅ Proxmox (192.168.1.137:8006)
  - ✅ TrueNAS (192.168.1.98)
  - ❌ Filesystem (disabled)

## Post-Deployment Verification

After deployment, run these checks on 192.168.1.200:

```bash
# Check container is running
cd /opt/netbox-agent
docker-compose ps

# View logs
docker-compose logs -f netbox-agent

# Check health (inside container)
docker exec netbox-agent python scripts/health_check.py

# Check metrics
docker exec netbox-agent curl -s http://localhost:8080/metrics

# View configuration
docker exec netbox-agent cat config/netbox-agent.json
```

## Important Notes

### Dry Run Mode
The agent is currently in **DRY RUN mode** (`"dry_run": true`). This means:
- ✅ It will discover devices from all sources
- ✅ It will log what changes it would make
- ❌ It will NOT actually create/update anything in NetBox

### To Enable Production Mode

1. Edit the config on the remote host:
```bash
ssh dev@192.168.1.200
cd /opt/netbox-agent
nano config/netbox-agent.json
```

2. Change `"dry_run": true` to `"dry_run": false`

3. Restart the container:
```bash
docker-compose restart
```

## Troubleshooting

### SSH Connection Issues

If SSH is failing:
1. Verify SSH service is running on 192.168.1.200
2. Check if password authentication is enabled in `/etc/ssh/sshd_config`
3. Verify the username is correct
4. Try connecting directly: `ssh dev@192.168.1.200`

### Container Fails to Start

Check logs for errors:
```bash
docker-compose logs netbox-agent
```

Common issues:
- Network connectivity to data sources
- Invalid API tokens
- Port conflicts
- Permission issues

### Health Check Fails

```bash
# Check what's failing
docker exec netbox-agent python scripts/health_check.py

# Check NetBox connectivity
docker exec netbox-agent curl -k https://netbox.internal.lakehouse.wtf/api/

# Check Home Assistant connectivity
docker exec netbox-agent curl http://192.168.1.155:8123
```

## Next Steps

1. ✅ Copy deployment package to 192.168.1.200
2. ✅ Extract and build Docker container
3. ✅ Verify container is running
4. ✅ Check logs for any errors
5. ✅ Review dry-run results
6. ⬜ Disable dry-run mode when ready
7. ⬜ Monitor first production sync

## Security Notes

- The configuration contains API tokens for NetBox, Proxmox, and TrueNAS
- Ensure `/opt/netbox-agent/config/` has appropriate permissions
- Consider using Docker secrets for sensitive data in production
- SSL verification is disabled for Proxmox and TrueNAS (set to false)

## Support

For issues, check:
- Container logs: `docker-compose logs -f`
- Health endpoint: `docker exec netbox-agent python scripts/health_check.py`
- Documentation: `/opt/netbox-agent/docs/`

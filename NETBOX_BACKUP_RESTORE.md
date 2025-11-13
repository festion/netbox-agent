# NetBox Database Backup and Restoration Guide

## Backup Information

**Created:** 2025-11-13 08:54:19 CST
**Location:** `root@192.168.1.138:/backup/netbox/netbox_backup_20251113_085419.dump`
**Size:** 847 KB (compressed)
**Database:** netbox (PostgreSQL 16.10)
**Format:** Custom (pg_dump -Fc)
**Compression:** gzip
**TOC Entries:** 2,039
**Tables:** 197 public tables
**Current Device Count:** 0 (empty database - baseline before agent population)

## Backup Details

- **Database Host:** 192.168.1.138 (NetBox LXC Container 131 on proxmox2)
- **Database Name:** netbox
- **Database User:** netbox
- **PostgreSQL Version:** 16.10 (Debian 16.10-1.pgdg12+1)
- **Backup Type:** Full database dump with compression

## Pre-Production State

This backup was created BEFORE enabling the netbox-agent production mode, capturing the clean state of NetBox with:
- All schemas and tables present
- No device data populated yet
- Configuration and user accounts intact
- Perfect baseline for restoration if agent causes issues

## Restoration Procedures

### Quick Restoration (If Data Corruption Occurs)

```bash
# 1. SSH to NetBox host
ssh root@192.168.1.138

# 2. Stop NetBox services
systemctl stop netbox netbox-rq

# 3. Drop and recreate the database
su - postgres -c "dropdb netbox"
su - postgres -c "createdb netbox -O netbox"

# 4. Restore from backup
su - postgres -c "pg_restore -d netbox /backup/netbox/netbox_backup_20251113_085419.dump"

# 5. Restart NetBox services
systemctl start netbox netbox-rq

# 6. Verify restoration
su - postgres -c 'psql -d netbox -c "SELECT COUNT(*) FROM dcim_device;"'
```

### Detailed Restoration with Verification

```bash
# 1. SSH to NetBox host
ssh root@192.168.1.138

# 2. Create a safety backup of current state (optional)
su - postgres -c "pg_dump -Fc netbox -f /backup/netbox/netbox_before_restore_$(date +%Y%m%d_%H%M%S).dump"

# 3. Stop all NetBox services
systemctl stop netbox netbox-rq nginx

# 4. Verify services are stopped
systemctl status netbox netbox-rq | grep Active

# 5. Drop existing database
su - postgres -c "dropdb netbox"

# 6. Recreate database with proper ownership
su - postgres -c "createdb netbox -O netbox"

# 7. Restore from the baseline backup
su - postgres -c "pg_restore -d netbox /backup/netbox/netbox_backup_20251113_085419.dump"

# 8. Verify restoration success
su - postgres -c 'psql -d netbox -c "SELECT COUNT(*) as tables FROM information_schema.tables WHERE table_schema = '\''public'\'';"'
su - postgres -c 'psql -d netbox -c "SELECT COUNT(*) FROM dcim_device;"'

# 9. Run NetBox migrations (if needed)
cd /opt/netbox
source venv/bin/activate
cd netbox
python manage.py migrate

# 10. Restart services
systemctl start netbox netbox-rq nginx

# 11. Check service status
systemctl status netbox netbox-rq nginx

# 12. Verify NetBox API is accessible
curl -k https://netbox.internal.lakehouse.wtf/api/
```

### Restoration to a Different Host (Disaster Recovery)

```bash
# 1. Copy backup to new host
scp root@192.168.1.138:/backup/netbox/netbox_backup_20251113_085419.dump /tmp/

# 2. On new host, create database
su - postgres -c "createdb netbox -O netbox"

# 3. Create netbox user if doesn't exist
su - postgres -c "psql -c \"CREATE USER netbox WITH PASSWORD 'your_password';\""

# 4. Restore backup
su - postgres -c "pg_restore -d netbox /tmp/netbox_backup_20251113_085419.dump"

# 5. Update NetBox configuration.py with new database credentials

# 6. Start NetBox services
systemctl start netbox netbox-rq
```

## Verification Commands

### Check Database Size
```bash
ssh root@192.168.1.138 "su - postgres -c 'psql -d netbox -c \"SELECT pg_size_pretty(pg_database_size('\''netbox'\''));\"'"
```

### Check Device Count
```bash
ssh root@192.168.1.138 "su - postgres -c 'psql -d netbox -c \"SELECT COUNT(*) FROM dcim_device;\"'"
```

### Check Table Count
```bash
ssh root@192.168.1.138 "su - postgres -c 'psql -d netbox -c \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '\''public'\'';\"'"
```

### Verify Backup Integrity
```bash
ssh root@192.168.1.138 "su - postgres -c 'pg_restore --list /backup/netbox/netbox_backup_20251113_085419.dump | head -20'"
```

### Check NetBox API Health
```bash
curl -k https://netbox.internal.lakehouse.wtf/api/status/
```

## Automated Backup Script

Create `/root/backup-netbox.sh` on 192.168.1.138:

```bash
#!/bin/bash
# NetBox Database Backup Script

BACKUP_DIR="/backup/netbox"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/netbox_backup_${TIMESTAMP}.dump"
RETENTION_DAYS=30

# Create backup directory if it doesn't exist
mkdir -p ${BACKUP_DIR}
chown postgres:postgres ${BACKUP_DIR}

# Create backup
echo "Creating backup: ${BACKUP_FILE}"
su - postgres -c "pg_dump -Fc netbox -f ${BACKUP_FILE}"

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "Backup created successfully: ${BACKUP_FILE}"
    ls -lh ${BACKUP_FILE}

    # Delete backups older than retention period
    find ${BACKUP_DIR} -name "netbox_backup_*.dump" -mtime +${RETENTION_DAYS} -delete
    echo "Cleaned up backups older than ${RETENTION_DAYS} days"
else
    echo "ERROR: Backup failed!"
    exit 1
fi
```

Make it executable and add to cron:
```bash
chmod +x /root/backup-netbox.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /root/backup-netbox.sh >> /var/log/netbox-backup.log 2>&1" | crontab -
```

## Important Notes

1. **Before Restoration:**
   - Always stop NetBox services to prevent data corruption
   - Consider creating a backup of the current state before restoring
   - Ensure sufficient disk space for temporary restore files

2. **After Restoration:**
   - Run Django migrations if needed: `python manage.py migrate`
   - Clear NetBox cache: `python manage.py invalidate all`
   - Restart all services: `systemctl restart netbox netbox-rq nginx`

3. **Backup Strategy:**
   - Keep this baseline backup permanently (pre-agent state)
   - Implement automated daily backups using the provided script
   - Store backups on separate storage if possible
   - Test restoration procedure quarterly

4. **NetBox Agent Impact:**
   - The agent will add devices from: Proxmox (3 devices), TrueNAS (1 device), Home Assistant, Network Scan
   - Agent runs in dry-run mode initially (safe)
   - After enabling production mode, monitor first sync carefully
   - You can always restore to this clean baseline

## Troubleshooting

### Restoration Fails with "database is being accessed"
```bash
# Terminate all connections to the database
su - postgres -c "psql -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'netbox' AND pid <> pg_backend_pid();\""
```

### Permission Denied During Restore
```bash
# Ensure postgres user owns the backup file
chown postgres:postgres /backup/netbox/netbox_backup_20251113_085419.dump
```

### NetBox Won't Start After Restore
```bash
# Check logs
journalctl -u netbox -n 50
journalctl -u netbox-rq -n 50

# Verify database connection
su - postgres -c 'psql -d netbox -c "SELECT version();"'

# Run migrations
cd /opt/netbox/netbox
source ../venv/bin/activate
python manage.py migrate
```

## Next Steps

1. ✅ Backup created and verified
2. ✅ Restoration procedure documented
3. ⬜ Test restoration on staging environment (optional)
4. ⬜ Enable netbox-agent production mode
5. ⬜ Monitor first sync
6. ⬜ Implement automated backup cron job

## Contact

For issues with backup/restore:
- Check NetBox logs: `journalctl -u netbox -f`
- Check PostgreSQL logs: `tail -f /var/log/postgresql/postgresql-16-main.log`
- NetBox documentation: https://docs.netbox.dev/

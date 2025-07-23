# Troubleshooting Guide

This guide covers common issues and solutions when using the Homelab Project Template.

## Setup Issues

### Script Permission Errors

**Problem**: `Permission denied` when running setup scripts

**Solutions**:
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Or run with bash explicitly
bash scripts/setup.sh
```

### Template Configuration Validation Errors

**Problem**: Invalid JSON in `template-config.json`

**Solutions**:
```bash
# Validate JSON syntax
cat template-config.json | python -m json.tool

# Use online JSON validator
# Copy content to https://jsonlint.com/

# Common JSON issues:
# - Missing commas between objects
# - Trailing commas (not allowed in JSON)
# - Unquoted keys or values
# - Mismatched brackets/braces
```

### Node.js Version Compatibility

**Problem**: Setup fails with Node.js version errors

**Solutions**:
```bash
# Check Node.js version
node --version

# Install correct version (requires Node 16+)
# Using nvm:
nvm install 18
nvm use 18

# Using package manager:
# Ubuntu/Debian:
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# macOS:
brew install node@18
```

### Git Repository Issues

**Problem**: Git operations fail or repository not properly initialized

**Solutions**:
```bash
# Check git status
git status

# Initialize if needed
git init
git add .
git commit -m "Initial commit"

# Fix remote origin
git remote -v
git remote remove origin  # if wrong URL
git remote add origin https://github.com/username/repo.git

# Fix branch name
git branch -M main
```

## MCP Configuration Issues

### MCP Server Not Starting

**Problem**: AI assistant can't connect to MCP servers

**Solutions**:
```bash
# Check if npx can install MCP servers
npx -y @modelcontextprotocol/server-filesystem --version

# Verify Node.js compatibility
node --version  # Should be 16+

# Test server manually
npx -y @modelcontextprotocol/server-filesystem . --debug

# Check .mcp.json syntax
cat .mcp.json | python -m json.tool
```

### Environment Variable Issues

**Problem**: MCP servers can't access required tokens/credentials

**Solutions**:
```bash
# Check if environment variables are set
echo $GITHUB_TOKEN
echo $HA_TOKEN

# Load from .env file
source .env

# Verify .env file exists and has correct format
cat .env
# Should contain:
# GITHUB_TOKEN=ghp_xxxxxxxxxxxx
# HA_TOKEN=eyxxxxxxxxxxxx

# Check token permissions
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

### Token Authentication Failures

**Problem**: GitHub or Home Assistant tokens rejected

**Solutions**:

**GitHub Token Issues**:
```bash
# Test token validity
curl -H "Authorization: token $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/user

# Required scopes for GitHub token:
# - repo (for repository access)
# - workflow (for GitHub Actions)
# - admin:org (if accessing organization repos)

# Create new token at:
# https://github.com/settings/tokens
```

**Home Assistant Token Issues**:
```bash
# Test HA token
curl -H "Authorization: Bearer $HA_TOKEN" \
     -H "Content-Type: application/json" \
     $HA_URL/api/

# Create new long-lived token in HA:
# Profile → Long-Lived Access Tokens → Create Token
```

## GitHub Integration Issues

### GitHub Actions Not Running

**Problem**: Workflows don't trigger or fail to run

**Solutions**:
```bash
# Check if Actions are enabled in repository settings
# Go to: Settings → Actions → General
# Ensure "Allow all actions and reusable workflows" is selected

# Check workflow files
ls -la .github/workflows/

# Validate workflow syntax
# Use GitHub's workflow validator or:
# https://rhymond.github.io/yamllint/

# Check repository permissions
# Settings → Actions → General → Workflow permissions
# Ensure sufficient permissions are granted
```

### Workflow Failures

**Problem**: GitHub Actions workflows failing

**Common Solutions**:

1. **Node.js Version Issues**:
   ```yaml
   # In .github/workflows/*.yml
   - uses: actions/setup-node@v3
     with:
       node-version: '18'  # Ensure compatible version
   ```

2. **Missing Dependencies**:
   ```yaml
   - name: Install dependencies
     run: |
       npm ci  # Use ci for faster, reliable installs
       # or
       npm install
   ```

3. **Environment Variables**:
   ```yaml
   env:
     GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
     NODE_ENV: test
   ```

4. **Permission Issues**:
   ```yaml
   permissions:
     contents: read
     actions: read
     security-events: write
   ```

### Repository Secrets

**Problem**: Workflows can't access required secrets

**Solutions**:
```bash
# Add secrets in repository settings:
# Settings → Secrets and variables → Actions

# Common secrets needed:
# - GITHUB_TOKEN (automatically provided)
# - HA_TOKEN (for Home Assistant integration)
# - DEPLOY_KEY (for deployment)
# - NPM_TOKEN (for publishing)

# Reference in workflows:
# ${{ secrets.SECRET_NAME }}
```

## Development Issues

### Package Installation Failures

**Problem**: npm/yarn install fails

**Solutions**:
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Try with different registry
npm install --registry https://registry.npmjs.org/

# Use yarn instead
yarn install

# Check for platform-specific issues
npm config get platform
npm config get arch
```

### Port Conflicts

**Problem**: Development server can't start due to port conflicts

**Solutions**:
```bash
# Check what's using the port
lsof -i :3000
netstat -tulpn | grep :3000

# Kill process using port
kill -9 <PID>

# Use different port
PORT=3001 npm start

# In package.json:
"scripts": {
  "start": "PORT=3001 node server.js"
}
```

### Hot Reload Not Working

**Problem**: Changes not reflected during development

**Solutions**:
```bash
# For React/Vite projects
# Check if FAST_REFRESH is enabled
echo $FAST_REFRESH

# For file watching issues on Linux
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# For Windows/WSL
# Add to .env:
CHOKIDAR_USEPOLLING=true
```

## Home Assistant Integration Issues

### Connection Timeouts

**Problem**: Can't connect to Home Assistant instance

**Solutions**:
```bash
# Test connectivity
curl -I $HA_URL

# Check if Home Assistant is running
ping ha.local  # or your HA hostname/IP

# Verify URL format
# Correct: http://192.168.1.100:8123
# Correct: https://ha.example.com
# Incorrect: http://192.168.1.100 (missing port)

# Check firewall/network
telnet 192.168.1.100 8123
```

### SSL Certificate Issues

**Problem**: HTTPS connections fail with certificate errors

**Solutions**:
```bash
# For self-signed certificates, add to .env:
NODE_TLS_REJECT_UNAUTHORIZED=0

# Better solution: Add certificate to trust store
# Or use HTTP for local development
HA_URL=http://192.168.1.100:8123
```

### API Rate Limiting

**Problem**: Too many requests to Home Assistant API

**Solutions**:
```bash
# Reduce polling frequency in configuration
# Add delays between requests
# Use WebSocket connections instead of polling where possible

# Check HA logs for rate limit messages:
# Settings → System → Logs
```

## Network and Connectivity Issues

### DNS Resolution Problems

**Problem**: Can't resolve hostnames (ha.local, nas.local, etc.)

**Solutions**:
```bash
# Test DNS resolution
nslookup ha.local
dig ha.local

# Use IP addresses instead of hostnames
HA_URL=http://192.168.1.100:8123

# Configure /etc/hosts
echo "192.168.1.100 ha.local" | sudo tee -a /etc/hosts

# Check network interface
ip addr show
route -n
```

### Firewall Issues

**Problem**: Connections blocked by firewall

**Solutions**:
```bash
# Check firewall status
sudo ufw status
sudo iptables -L

# Allow specific ports
sudo ufw allow 8123  # Home Assistant
sudo ufw allow 3000  # Development server

# Temporarily disable for testing
sudo ufw disable  # Re-enable after testing!
```

### Proxy Configuration

**Problem**: Behind corporate proxy or firewall

**Solutions**:
```bash
# Configure npm proxy
npm config set proxy http://proxy.company.com:8080
npm config set https-proxy http://proxy.company.com:8080

# Configure git proxy
git config --global http.proxy http://proxy.company.com:8080

# Set environment variables
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1,.local
```

## File System Issues

### Directory Permission Problems

**Problem**: Can't create/modify files in project directory

**Solutions**:
```bash
# Check current permissions
ls -la

# Fix ownership
sudo chown -R $USER:$USER .

# Fix permissions
chmod -R 755 .
chmod +x scripts/*.sh

# For WSL users
# Add to ~/.bashrc:
umask 022
```

### Disk Space Issues

**Problem**: No space left on device

**Solutions**:
```bash
# Check disk usage
df -h
du -sh * | sort -hr

# Clean npm cache
npm cache clean --force

# Clean node_modules
find . -name "node_modules" -type d -prune -exec rm -rf '{}' +

# Clean Docker (if using)
docker system prune -a
```

### Symbolic Link Issues

**Problem**: Symbolic links not working (especially on Windows)

**Solutions**:
```bash
# Enable developer mode on Windows
# Or run terminal as administrator

# Use junction points instead
mklink /J link target

# For WSL, ensure symlinks are enabled
echo "[automount]" >> /etc/wsl.conf
echo "options = metadata" >> /etc/wsl.conf
```

## Database Issues

### Connection Problems

**Problem**: Can't connect to database

**Solutions**:
```bash
# Check database is running
sudo systemctl status postgresql
# or
docker ps | grep postgres

# Test connection
psql -h localhost -U username -d database_name

# Check connection string format
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### Migration Failures

**Problem**: Database migrations fail

**Solutions**:
```bash
# Check migration files
ls -la migrations/

# Run migrations manually
npm run migrate
# or
npx prisma migrate dev

# Reset database (development only!)
npm run db:reset
```

## Performance Issues

### Slow Build Times

**Problem**: Build process takes too long

**Solutions**:
```bash
# Use faster package manager
npm install -g pnpm
pnpm install

# Enable build caching
# Add to package.json:
"scripts": {
  "build": "vite build --mode production"
}

# Exclude unnecessary files from build
# Update .gitignore and .dockerignore

# Use multi-core builds
npm config set maxsockets 15
```

### Memory Issues

**Problem**: Out of memory during build/development

**Solutions**:
```bash
# Increase Node.js memory limit
export NODE_OPTIONS="--max-old-space-size=4096"

# Add to package.json scripts:
"build": "NODE_OPTIONS='--max-old-space-size=4096' vite build"

# Monitor memory usage
htop
free -h
```

## Debugging Tools

### Enable Debug Logging

```bash
# For MCP servers
export DEBUG=mcp:*

# For Node.js applications
export DEBUG=app:*

# For npm
npm config set loglevel verbose
```

### Log Analysis

```bash
# View recent logs
tail -f logs/app.log

# Search logs
grep -i "error" logs/app.log

# System logs
sudo journalctl -u service-name -f
```

### Network Debugging

```bash
# Monitor network connections
netstat -tupln
ss -tupln

# Trace network calls
curl -v https://api.example.com
wget --debug https://api.example.com
```

## Getting Help

### Information to Include

When reporting issues, include:

1. **Environment Information**:
   ```bash
   node --version
   npm --version
   git --version
   uname -a
   ```

2. **Configuration Files**:
   - `template-config.json`
   - `.mcp.json` (without sensitive data)
   - `package.json`
   - Error logs

3. **Steps to Reproduce**:
   - Exact commands run
   - Expected vs actual behavior
   - Error messages (complete stack traces)

### Support Channels

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/festion/homelab-project-template/issues)
- 💬 **Questions**: [GitHub Discussions](https://github.com/festion/homelab-project-template/discussions)
- 📖 **Documentation**: Check other files in `/docs` directory
- 🔍 **Search**: Search existing issues before creating new ones

### Self-Help Resources

1. **Run Validation Script**:
   ```bash
   ./scripts/validate-config.sh
   ```

2. **Check System Requirements**:
   - Node.js 16+
   - Git 2.0+
   - Sufficient disk space (500MB+)
   - Network connectivity

3. **Review Configuration**:
   - JSON syntax validation
   - Environment variable setup
   - Token permissions
   - Network accessibility

Remember: Most issues are configuration-related and can be resolved by carefully following the setup instructions and checking the troubleshooting steps above.
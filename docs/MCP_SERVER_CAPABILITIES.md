# MCP Server Capabilities Documentation

This document provides a comprehensive overview of the MCP (Model Context Protocol) servers available for the NetBox Agent project. These servers provide various capabilities for data collection, automation, and infrastructure management.

## Available MCP Servers

### 1. Filesystem MCP Server
**Path**: `@modelcontextprotocol/server-filesystem`
**Purpose**: File system operations and directory management

**Capabilities**:
- Read, write, and manage files and directories
- Search for files matching patterns
- Create and delete directories
- Monitor file changes
- Access to configuration files and device inventories

**Use Cases for NetBox Agent**:
- Parse network configuration files
- Read device inventory files
- Access YAML/JSON configuration data
- Monitor configuration changes

### 2. Network FS MCP Server
**Path**: `/home/dev/workspace/mcp-servers/network-mcp-server/`
**Purpose**: Network file system operations

**Capabilities**:
- Access network shares (NFS, SMB/CIFS)
- Read files from remote network locations
- Monitor network file systems
- Handle network-attached storage

**Use Cases for NetBox Agent**:
- Access device configurations on network shares
- Read inventory data from TrueNAS or other NAS systems
- Monitor shared configuration repositories

### 3. Serena Enhanced MCP Server
**Path**: `/home/dev/workspace/serena/`
**Purpose**: Enhanced coding and project management

**Capabilities**:
- Advanced code analysis and generation
- Project structure management
- Memory and context management
- Symbol-based code operations
- Integration with development workflows

**Use Cases for NetBox Agent**:
- Generate NetBox API integration code
- Manage project configuration
- Automate code quality and testing

### 4. Home Assistant MCP Server
**Path**: `/home/dev/workspace/wrappers/home-assistant.sh`
**Purpose**: Home Assistant integration and IoT device management

**Capabilities**:
- Access Home Assistant entities and states
- Retrieve device information
- Monitor sensor data
- Control IoT devices
- Access automation and scene data

**Use Cases for NetBox Agent**:
- Discover IoT devices and sensors
- Extract network device information
- Map Home Assistant entities to NetBox devices
- Monitor device status and connectivity

### 5. GitHub MCP Server
**Path**: `ghcr.io/github/github-mcp-server`
**Purpose**: GitHub repository and API operations

**Capabilities**:
- Repository management (create, update, delete)
- Issue and pull request operations
- Branch and commit management
- GitHub Actions workflow management
- Organization and team management

**Use Cases for NetBox Agent**:
- Version control for NetBox configurations
- Automated deployment and CI/CD
- Issue tracking for discovered devices
- Repository-based configuration management

### 6. Code Linter MCP Server
**Path**: `/home/dev/workspace/wrappers/code-linter.sh`
**Purpose**: Code quality and linting operations

**Capabilities**:
- Python code linting (flake8, black, mypy)
- JavaScript/TypeScript linting (eslint)
- Shell script validation
- Code formatting and style enforcement
- Pre-commit hook integration

**Use Cases for NetBox Agent**:
- Ensure code quality for agent scripts
- Validate configuration files
- Automated code formatting
- Pre-commit validation

### 7. Directory Polling MCP Server
**Path**: `/home/dev/workspace/wrappers/directory-polling.sh`
**Purpose**: File and directory monitoring

**Capabilities**:
- Real-time file system monitoring
- Directory change detection
- Pattern-based file watching
- Event-driven file operations
- Configurable polling intervals

**Use Cases for NetBox Agent**:
- Monitor configuration file changes
- Detect new device inventory files
- Real-time synchronization triggers
- Automated discovery on file changes

### 8. TrueNAS MCP Server
**Path**: `/home/dev/workspace/wrappers/truenas.sh`
**Purpose**: TrueNAS storage system integration

**Capabilities**:
- TrueNAS API integration
- Storage pool and dataset management
- Network share configuration
- System monitoring and alerts
- User and permission management

**Use Cases for NetBox Agent**:
- Discover storage devices and arrays
- Map network shares to NetBox
- Monitor storage system health
- Extract storage infrastructure data

### 9. WikiJS MCP Server
**Path**: `/home/dev/workspace/wrappers/wikijs.sh`
**Purpose**: WikiJS documentation system integration

**Capabilities**:
- Wiki page creation and management
- Content search and retrieval
- Category and tag management
- User and permission handling
- Automated documentation generation

**Use Cases for NetBox Agent**:
- Generate device documentation
- Create network topology documentation
- Maintain infrastructure wikis
- Automated knowledge base updates

### 10. Proxmox MCP Server
**Path**: `/home/dev/workspace/wrappers/proxmox.sh`
**Purpose**: Proxmox virtualization platform integration

**Capabilities**:
- Virtual machine management
- Container (LXC) operations
- Cluster and node monitoring
- Storage and network configuration
- User and permission management

**Use Cases for NetBox Agent**:
- Discover virtual machines and containers
- Map VM network configurations
- Extract cluster topology
- Monitor virtualization infrastructure

## Integration Patterns

### Data Collection Pattern
1. **Home Assistant** → IoT devices and sensors
2. **Proxmox** → Virtual infrastructure
3. **TrueNAS** → Storage systems
4. **Network FS** → Configuration files
5. **Directory Polling** → Real-time monitoring

### Automation Pattern
1. **Serena Enhanced** → Code generation and management
2. **GitHub** → Version control and deployment
3. **Code Linter** → Quality assurance
4. **WikiJS** → Documentation generation

### Configuration Management Pattern
1. **Filesystem** → Local configuration access
2. **Network FS** → Remote configuration access
3. **Directory Polling** → Change monitoring
4. **GitHub** → Version control

## Best Practices

### 1. Data Source Priority
- Primary: Home Assistant, Proxmox, TrueNAS
- Secondary: Network scanning, file system parsing
- Tertiary: Manual configuration files

### 2. MCP Server Orchestration
- Use Serena Enhanced as the primary orchestrator
- Coordinate multiple MCP servers for complex operations
- Implement error handling and fallback mechanisms

### 3. Security Considerations
- Use secure wrappers for all MCP server access
- Implement token-based authentication where available
- Monitor access logs and audit trails

### 4. Performance Optimization
- Cache frequently accessed data
- Use incremental synchronization
- Implement rate limiting for API calls

## Configuration Examples

### NetBox Agent MCP Configuration
```json
{
  "mcp": {
    "servers": {
      "home-assistant": {
        "enabled": true,
        "priority": "high",
        "sync_interval": 3600
      },
      "proxmox-mcp": {
        "enabled": true,
        "priority": "high",
        "sync_interval": 1800
      },
      "truenas": {
        "enabled": true,
        "priority": "medium",
        "sync_interval": 7200
      },
      "directory-polling": {
        "enabled": true,
        "priority": "high",
        "watch_paths": ["/config", "/inventory"]
      }
    }
  }
}
```

## Troubleshooting

### Common Issues
1. **Connection Failures**: Check network connectivity and authentication
2. **Permission Errors**: Verify API tokens and user permissions
3. **Rate Limiting**: Implement backoff strategies and respect API limits
4. **Data Inconsistencies**: Implement validation and conflict resolution

### Debugging Tips
- Enable debug logging for all MCP servers
- Use dry-run mode for testing configurations
- Monitor resource utilization during sync operations
- Implement health checks for all data sources

## Future Enhancements

### Planned MCP Server Integrations
- **Docker MCP Server**: Container discovery and management
- **Kubernetes MCP Server**: K8s cluster integration
- **SNMP MCP Server**: Network device discovery via SNMP
- **DNS MCP Server**: DNS record management and discovery

### Advanced Features
- **Multi-site Support**: Coordinate multiple NetBox instances
- **Conflict Resolution**: Handle data conflicts between sources
- **Custom Plugins**: Extensible plugin architecture
- **Real-time Sync**: WebSocket-based real-time updates
# NetBox Agent

An intelligent agent for populating a NetBox server with data from various sources using MCP (Model Context Protocol) servers. This agent automates the discovery and population of network infrastructure data into NetBox from multiple sources including Home Assistant, network devices, and file systems.

## Features

- 🌐 **NetBox Integration** - Automated population of NetBox with infrastructure data
- 🤖 **MCP Server Integration** - Leverages multiple MCP servers for data collection
- 🏠 **Home Assistant Integration** - Discovers and imports IoT devices and network entities
- 📡 **Network Discovery** - Scans and imports network infrastructure components
- 🔄 **Automated Synchronization** - Scheduled updates and data synchronization
- 📊 **Monitoring & Logging** - Comprehensive monitoring of agent operations

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/festion/netbox-agent.git
   cd netbox-agent
   ```

2. **Initialize the project**:
   ```bash
   ./scripts/setup.sh
   ```

3. **Configure the agent** by editing `config/netbox-agent.json`:
   ```json
   {
     "netbox": {
       "url": "https://netbox.example.com",
       "token": "your-netbox-api-token"
     },
     "sources": {
       "homeassistant": true,
       "network_scan": true,
       "filesystem": true
     }
   }
   ```

4. **Run the agent**:
   ```bash
   python src/netbox_agent.py
   ```

## Data Sources

- **Home Assistant** - IoT devices, sensors, switches, and network entities
- **Network Scanning** - Automated discovery of network devices and infrastructure
- **File System** - Configuration files and device inventories
- **Proxmox** - Virtual machines and container information
- **TrueNAS** - Storage systems and network shares

## MCP Server Support

This agent leverages multiple MCP servers for data collection and automation:

- **Filesystem** - Configuration file parsing and device inventory access
- **GitHub** - Repository management and configuration version control
- **Home Assistant** - IoT device discovery and entity data extraction
- **Network FS** - Access to network shares and storage systems
- **Directory Polling** - Real-time monitoring of configuration changes
- **Proxmox** - VM and container inventory management
- **TrueNAS** - Storage system and network share management

See [docs/MCP_CONFIGURATION.md](docs/MCP_CONFIGURATION.md) for detailed configuration.

## Documentation

- [Setup Guide](docs/SETUP.md) - Detailed setup instructions
- [Customization Guide](docs/CUSTOMIZATION.md) - How to customize the template
- [MCP Configuration](docs/MCP_CONFIGURATION.md) - MCP server setup and usage
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions

## Examples

Check the `/examples` directory for:
- Basic project setup
- Advanced customization examples
- Integration patterns

## Scripts

- `scripts/setup.sh` - Initialize new project from template
- `scripts/validate-config.sh` - Validate project configuration
- `scripts/update-template.sh` - Update template to latest version

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- 📖 Check the [documentation](docs/)
- 🐛 Report issues on [GitHub Issues](https://github.com/festion/homelab-project-template/issues)
- 💬 Join discussions in [GitHub Discussions](https://github.com/festion/homelab-project-template/discussions)
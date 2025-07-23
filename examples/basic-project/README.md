# Basic Project Example

This example demonstrates a minimal configuration using the Homelab Project Template.

## Configuration

This example uses:
- **Project Type**: `generic` - Basic project structure
- **MCP Servers**: `minimal` - Only filesystem and GitHub
- **Features**: Minimal set for simple projects
- **Structure**: Documentation and scripts only

## Setup

1. Copy this configuration:
   ```bash
   cp examples/basic-project/template-config.json ./template-config.json
   ```

2. Customize the project details:
   ```json
   {
     "project": {
       "name": "your-project-name",
       "description": "Your project description",
       "author": "Your Name <your.email@example.com>"
     }
   }
   ```

3. Run setup:
   ```bash
   ./scripts/setup.sh
   ```

## What You Get

### Directory Structure
```
your-project/
├── docs/                    # Project documentation
├── scripts/                 # Utility scripts
├── .mcp.json               # AI assistant configuration
├── README.md               # Project overview
├── LICENSE                 # MIT License
├── .gitignore              # Git ignore patterns
└── template-config.json    # Template configuration
```

### MCP Integration
- **Filesystem**: Basic file operations
- **GitHub**: Repository management

### Scripts
- `scripts/setup.sh` - Project initialization
- `scripts/validate-config.sh` - Configuration validation
- `scripts/update-template.sh` - Template updates

## Use Cases

This configuration is ideal for:
- Documentation projects
- Script collections
- Simple automation projects
- Learning and experimentation
- Projects that don't need web interfaces

## Next Steps

1. Add your project files to appropriate directories
2. Update documentation in `/docs`
3. Add utility scripts to `/scripts`
4. Configure environment variables in `.env`

## Upgrading

To add more features later:

1. **Add API**: Change `structure.api.enabled` to `true`
2. **Add Dashboard**: Change `structure.dashboard.enabled` to `true`
3. **Enable CI/CD**: Change `features.cicd` to `true`
4. **Add More MCP Servers**: Change `mcp.servers` to `"all"`

Then run `./scripts/setup.sh` again to apply changes.
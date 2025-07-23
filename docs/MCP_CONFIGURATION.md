# MCP Configuration Guide

This guide covers the setup and configuration of Model Context Protocol (MCP) servers for enhanced AI assistant integration.

## Overview

MCP servers provide AI assistants with enhanced capabilities for:
- File system operations
- GitHub repository management
- Home Assistant integration
- Network file system access
- Directory monitoring

## Available MCP Servers

### 1. Filesystem Server

**Purpose**: File operations and directory management

**Configuration**:
```json
{
  "mcp": {
    "configuration": {
      "filesystem": {
        "enabled": true,
        "allowedDirectories": [
          ".",
          "./src",
          "./docs",
          "./scripts",
          "./api",
          "./dashboard"
        ]
      }
    }
  }
}
```

**Capabilities**:
- Read/write files
- Create directories
- File search operations
- Directory listings
- File metadata retrieval

### 2. GitHub Server

**Purpose**: Repository management and GitHub API integration

**Configuration**:
```json
{
  "mcp": {
    "configuration": {
      "github": {
        "enabled": true,
        "defaultOrg": "your-github-org",
        "repositories": ["repo1", "repo2"]
      }
    }
  }
}
```

**Environment Variables**:
```bash
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token_here
```

**Capabilities**:
- Create/manage repositories
- Handle pull requests and issues
- Manage workflows and actions
- Repository operations (clone, commit, push)
- Organization management

### 3. Home Assistant Server

**Purpose**: Home automation system integration

**Configuration**:
```json
{
  "mcp": {
    "configuration": {
      "homeAssistant": {
        "enabled": true,
        "apiUrl": "http://your-ha-instance:8123",
        "tokenPath": "/path/to/ha-token"
      }
    }
  }
}
```

**Environment Variables**:
```bash
HA_URL=http://your-ha-instance:8123
HA_TOKEN=your_long_lived_access_token
```

**Capabilities**:
- Control devices and entities
- Read sensor data
- Manage automations
- System health monitoring
- Service calls

### 4. Network FS Server

**Purpose**: Network file system operations

**Configuration**:
```json
{
  "mcp": {
    "configuration": {
      "networkFs": {
        "enabled": true,
        "shares": {
          "nas": {
            "host": "nas.local",
            "path": "/share/data",
            "credentials": {
              "username": "user",
              "passwordPath": "/path/to/password"
            }
          }
        }
      }
    }
  }
}
```

**Capabilities**:
- Access network shares
- Remote file operations
- Cross-platform file sharing
- Backup operations

### 5. Directory Polling Server

**Purpose**: File system monitoring and change detection

**Configuration**:
```json
{
  "mcp": {
    "configuration": {
      "directoryPolling": {
        "enabled": true,
        "watchDirectories": [
          {
            "path": "./src",
            "patterns": ["*.js", "*.ts", "*.json"],
            "recursive": true
          },
          {
            "path": "./docs",
            "patterns": ["*.md"],
            "recursive": false
          }
        ]
      }
    }
  }
}
```

**Capabilities**:
- Monitor file changes
- Directory scanning
- Pattern matching
- Change notifications

## Setup Process

### 1. Automatic Setup

The setup script handles MCP configuration automatically:

```bash
./scripts/setup.sh
```

This creates:
- `.mcp.json` - MCP server configuration
- Environment variable templates
- Token management scripts

### 2. Manual Configuration

#### Create MCP Configuration

```bash
cat > .mcp.json << 'EOF'
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
      "env": {}
    },
    "github": {
      "command": "npx", 
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
EOF
```

#### Set Environment Variables

```bash
# Add to .env file
echo "GITHUB_TOKEN=your_token_here" >> .env
echo "HA_TOKEN=your_ha_token_here" >> .env
```

### 3. Token Setup

#### GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Create token with required scopes:
   - `repo` - Repository access
   - `workflow` - GitHub Actions
   - `admin:org` - Organization access (if needed)
3. Add token to environment variables

#### Home Assistant Token

1. In Home Assistant: Profile → Long-Lived Access Tokens
2. Create new token with descriptive name
3. Copy token to environment variables

## Usage Examples

### With Claude Desktop

1. **Load Project Context**:
   - Open Claude Desktop
   - Load `.mcp.json` configuration
   - Project capabilities are automatically available

2. **Common Operations**:
   ```
   # File operations
   "Read the contents of src/main.js"
   "Create a new file docs/api.md with API documentation"
   
   # GitHub operations  
   "Create a new issue for bug tracking"
   "List all open pull requests in this repository"
   
   # Home Assistant operations
   "Show me the current temperature sensors"
   "Turn on the living room lights"
   ```

### With Other AI Assistants

MCP configuration works with any MCP-compatible AI assistant:

1. Load the `.mcp.json` configuration
2. Ensure environment variables are set
3. Test connectivity with basic operations

## Security Considerations

### Token Management

1. **Never commit tokens to repository**:
   ```bash
   # Add to .gitignore
   echo ".env*" >> .gitignore
   echo "*.token" >> .gitignore
   ```

2. **Use environment variables**:
   ```bash
   # In .env file (not committed)
   GITHUB_TOKEN=ghp_xxxxxxxxxxxx
   HA_TOKEN=eyxxxxxxxxxxxxxx
   ```

3. **Set appropriate token permissions**:
   - GitHub: Minimal required scopes
   - Home Assistant: Read-only where possible

### Network Security

1. **Use HTTPS/TLS** for all connections
2. **Limit network access** to required services
3. **Use VPN** for remote access when possible

### File System Access

1. **Limit allowed directories**:
   ```json
   {
     "filesystem": {
       "allowedDirectories": ["./src", "./docs"]
     }
   }
   ```

2. **Avoid sensitive directories**:
   - Don't include `/etc`, `/root`, or system directories
   - Exclude directories with credentials or secrets

## Troubleshooting

### Common Issues

1. **MCP Server Not Starting**:
   ```bash
   # Check if npx can install packages
   npx -y @modelcontextprotocol/server-filesystem --version
   
   # Verify Node.js version
   node --version  # Should be v16+
   ```

2. **Authentication Failures**:
   ```bash
   # Test GitHub token
   curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
   
   # Test Home Assistant token
   curl -H "Authorization: Bearer $HA_TOKEN" $HA_URL/api/
   ```

3. **Environment Variable Issues**:
   ```bash
   # Check if variables are loaded
   echo $GITHUB_TOKEN
   echo $HA_TOKEN
   
   # Source environment file
   source .env
   ```

4. **Permission Errors**:
   ```bash
   # Check directory permissions
   ls -la .
   
   # Ensure scripts are executable
   chmod +x scripts/*.sh
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", ".", "--debug"],
      "env": {
        "DEBUG": "mcp:*"
      }
    }
  }
}
```

### Validation Script

Run the validation script to check configuration:

```bash
./scripts/validate-config.sh
```

This checks:
- JSON syntax
- Required environment variables
- Token validity
- Server connectivity

## Advanced Configuration

### Custom Server Paths

For development or custom installations:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "/custom/path/to/server",
      "args": ["--config", "/custom/config.json"],
      "env": {}
    }
  }
}
```

### Multiple Instances

Run multiple instances of the same server type:

```json
{
  "mcpServers": {
    "filesystem-src": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./src"],
      "env": {}
    },
    "filesystem-docs": {
      "command": "npx", 
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./docs"],
      "env": {}
    }
  }
}
```

### Custom Environment

Per-server environment configuration:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}",
        "GITHUB_API_URL": "https://api.github.com",
        "DEBUG": "github:*"
      }
    }
  }
}
```

## Support

For MCP-specific issues:

- 📖 [MCP Documentation](https://modelcontextprotocol.io/)
- 🐛 [MCP GitHub Issues](https://github.com/modelcontextprotocol/servers/issues)
- 💬 [Claude Community](https://claude.ai/community)

For template-specific issues:

- 🐛 [Template Issues](https://github.com/festion/homelab-project-template/issues)
- 💬 [Template Discussions](https://github.com/festion/homelab-project-template/discussions)
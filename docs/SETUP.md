# Setup Guide

This guide walks you through setting up a new project using the Homelab Project Template.

## Prerequisites

- Git installed on your system
- Node.js (v16 or higher) if using JavaScript/TypeScript features
- GitHub account for repository management
- Basic familiarity with command line operations

## Quick Setup

### Option 1: Use GitHub Template (Recommended)

1. **Create new repository from template**:
   - Navigate to the [template repository](https://github.com/festion/homelab-project-template)
   - Click "Use this template" button
   - Choose "Create a new repository"
   - Fill in repository details and create

2. **Clone your new repository**:
   ```bash
   git clone https://github.com/yourusername/your-project-name.git
   cd your-project-name
   ```

3. **Run the setup script**:
   ```bash
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```

### Option 2: Manual Clone and Setup

1. **Clone the template**:
   ```bash
   git clone https://github.com/festion/homelab-project-template.git my-project
   cd my-project
   ```

2. **Remove template git history**:
   ```bash
   rm -rf .git
   git init
   git add .
   git commit -m "Initial commit from homelab-project-template"
   ```

3. **Run setup script**:
   ```bash
   ./scripts/setup.sh
   ```

## Configuration

### 1. Project Configuration

Edit `template-config.json` to customize your project:

```json
{
  "project": {
    "name": "my-awesome-project",
    "description": "Brief description of your project",
    "type": "fullstack",
    "language": "javascript",
    "author": "Your Name",
    "license": "MIT"
  }
}
```

**Project Types:**
- `generic` - Basic project structure
- `api` - Backend API with Express.js
- `dashboard` - Frontend dashboard with React
- `fullstack` - Complete full-stack application
- `automation` - Script-based automation project

### 2. MCP Server Configuration

Configure MCP servers for AI assistance:

```json
{
  "mcp": {
    "servers": "all",
    "configuration": {
      "filesystem": {
        "enabled": true,
        "allowedDirectories": [".", "./src", "./docs"]
      },
      "github": {
        "enabled": true,
        "defaultOrg": "your-github-org"
      },
      "homeAssistant": {
        "enabled": true,
        "apiUrl": "http://your-ha-instance:8123",
        "tokenPath": "/path/to/ha-token"
      }
    }
  }
}
```

### 3. Project Structure Configuration

Enable/disable components based on your needs:

```json
{
  "structure": {
    "api": {
      "enabled": true,
      "framework": "express",
      "language": "javascript"
    },
    "dashboard": {
      "enabled": true,
      "framework": "react",
      "language": "javascript"
    }
  }
}
```

## Environment Setup

### 1. Environment Variables

Create `.env` file for sensitive configuration:

```bash
# GitHub Configuration
GITHUB_TOKEN=your_github_token_here

# Home Assistant (if using)
HA_URL=http://your-ha-instance:8123
HA_TOKEN=your_ha_token_here

# API Configuration (if using)
PORT=3000
NODE_ENV=development

# Database (if using)
DATABASE_URL=your_database_url_here
```

### 2. MCP Configuration

The setup script will create `.mcp.json` for AI assistant integration:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/project"],
      "env": {}
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your-token"
      }
    }
  }
}
```

## Project Initialization

### 1. Install Dependencies

For JavaScript/TypeScript projects:

```bash
# API dependencies (if enabled)
cd api && npm install

# Dashboard dependencies (if enabled)  
cd dashboard && npm install
```

### 2. Initialize Git Repository

```bash
git remote add origin https://github.com/yourusername/your-project.git
git branch -M main
git push -u origin main
```

### 3. Set up GitHub Features

If using GitHub integration:

```bash
# Enable GitHub Actions
git add .github/
git commit -m "Add GitHub Actions workflows"
git push

# Configure repository settings
# - Enable Actions in repository settings
# - Set up branch protection rules
# - Configure required status checks
```

## Validation

### 1. Run Configuration Validation

```bash
./scripts/validate-config.sh
```

This checks:
- JSON configuration validity
- Required environment variables
- MCP server accessibility
- Project structure integrity

### 2. Test MCP Integration

If using Claude AI with MCP:

1. Open Claude Desktop or compatible AI assistant
2. Load project context from `.mcp.json`
3. Test basic commands:
   - File operations
   - GitHub integration
   - Project-specific features

### 3. Test GitHub Integration

```bash
# Test GitHub Actions (if enabled)
git add .
git commit -m "Test GitHub integration"
git push

# Check Actions tab in GitHub repository
```

## Next Steps

1. **Customize Documentation**: Update files in `/docs` directory
2. **Set up Development Environment**: Install additional tools as needed
3. **Configure CI/CD**: Customize GitHub Actions workflows
4. **Add Project-Specific Features**: Implement your core functionality
5. **Set up Monitoring**: Configure logging and monitoring (if enabled)

## Troubleshooting

### Common Issues

1. **Permission Denied on Scripts**:
   ```bash
   chmod +x scripts/*.sh
   ```

2. **MCP Configuration Issues**:
   - Check environment variables
   - Verify token permissions
   - Test connectivity to services

3. **GitHub Actions Failing**:
   - Check repository secrets
   - Verify workflow permissions
   - Review action logs

4. **Node.js Version Issues**:
   ```bash
   node --version  # Should be v16+
   npm --version   # Should be v8+
   ```

For more troubleshooting help, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Support

- 📖 Check the [documentation](../README.md)
- 🐛 Report issues on [GitHub Issues](https://github.com/festion/homelab-project-template/issues)
- 💬 Join discussions in [GitHub Discussions](https://github.com/festion/homelab-project-template/discussions)
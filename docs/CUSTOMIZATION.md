# Customization Guide

This guide explains how to customize the Homelab Project Template for your specific needs.

## Template Configuration

### Basic Project Settings

Edit `template-config.json` to customize core project settings:

```json
{
  "project": {
    "name": "my-awesome-project",
    "description": "A comprehensive homelab automation system",
    "type": "fullstack",
    "language": "javascript",
    "author": "Your Name <your.email@example.com>",
    "license": "MIT"
  }
}
```

**Available Project Types:**

| Type | Description | Includes |
|------|-------------|----------|
| `generic` | Basic structure | docs, scripts, basic configs |
| `api` | Backend API | Express.js, API structure, middleware |
| `dashboard` | Frontend only | React, UI components, routing |
| `fullstack` | Complete app | API + Dashboard + integration |
| `automation` | Script-based | Cron jobs, monitoring, alerts |

### Language Support

**JavaScript/TypeScript:**
```json
{
  "project": {
    "language": "javascript",
    "typescript": true,
    "nodeVersion": "18"
  }
}
```

**Python:**
```json
{
  "project": {
    "language": "python",
    "pythonVersion": "3.9",
    "framework": "fastapi"
  }
}
```

**Go:**
```json
{
  "project": {
    "language": "go",
    "goVersion": "1.21",
    "framework": "gin"
  }
}
```

## Component Configuration

### API Configuration

```json
{
  "structure": {
    "api": {
      "enabled": true,
      "framework": "express",
      "language": "javascript",
      "features": {
        "authentication": true,
        "logging": true,
        "validation": true,
        "swagger": true
      },
      "database": {
        "type": "postgresql",
        "orm": "prisma"
      }
    }
  }
}
```

**Supported API Frameworks:**
- `express` - Express.js (Node.js)
- `fastapi` - FastAPI (Python)
- `gin` - Gin (Go)
- `spring` - Spring Boot (Java)

### Dashboard Configuration

```json
{
  "structure": {
    "dashboard": {
      "enabled": true,
      "framework": "react",
      "language": "javascript",
      "features": {
        "routing": "react-router",
        "stateManagement": "redux",
        "uiLibrary": "material-ui",
        "charts": "recharts"
      },
      "buildTool": "vite"
    }
  }
}
```

**Supported Dashboard Frameworks:**
- `react` - React with modern tooling
- `vue` - Vue.js 3 with Composition API
- `angular` - Angular with TypeScript
- `svelte` - Svelte with SvelteKit

## MCP Server Customization

### Server Selection

Choose which MCP servers to include:

```json
{
  "mcp": {
    "servers": "custom",
    "enabledServers": [
      "filesystem",
      "github", 
      "home-assistant"
    ]
  }
}
```

**Available Options:**
- `all` - Include all available servers
- `minimal` - Only filesystem and basic servers
- `custom` - Specify exact servers to include
- `none` - Disable MCP integration

### Custom Server Configuration

```json
{
  "mcp": {
    "customPaths": {
      "myCustomServer": "/path/to/custom/server",
      "orgInternalServer": "npm:@myorg/mcp-server"
    },
    "configuration": {
      "myCustomServer": {
        "enabled": true,
        "config": {
          "apiKey": "${CUSTOM_API_KEY}",
          "endpoint": "https://api.example.com"
        }
      }
    }
  }
}
```

## GitHub Integration

### Workflow Customization

```json
{
  "github": {
    "useTemplates": true,
    "workflowSync": true,
    "workflows": {
      "ci": {
        "enabled": true,
        "nodeVersions": ["16", "18", "20"],
        "testCommand": "npm test",
        "lintCommand": "npm run lint"
      },
      "cd": {
        "enabled": true,
        "deployBranch": "main",
        "deploymentTarget": "production"
      },
      "security": {
        "enabled": true,
        "dependabot": true,
        "codeql": true
      }
    }
  }
}
```

### Issue and PR Templates

```json
{
  "github": {
    "issueTemplates": [
      {
        "name": "Bug Report",
        "about": "Report a bug or issue",
        "labels": ["bug"]
      },
      {
        "name": "Feature Request", 
        "about": "Request a new feature",
        "labels": ["enhancement"]
      }
    ],
    "prTemplate": {
      "enabled": true,
      "requireChecklist": true,
      "requireDescription": true
    }
  }
}
```

## Feature Toggles

### Development Features

```json
{
  "features": {
    "linting": {
      "enabled": true,
      "tools": ["eslint", "prettier"],
      "rules": "standard"
    },
    "testing": {
      "enabled": true,
      "framework": "jest",
      "coverage": true,
      "e2e": "playwright"
    },
    "typescript": {
      "enabled": false,
      "strict": true
    }
  }
}
```

### Infrastructure Features

```json
{
  "features": {
    "docker": {
      "enabled": true,
      "multiStage": true,
      "baseImage": "node:18-alpine"
    },
    "monitoring": {
      "enabled": true,
      "metrics": "prometheus",
      "logging": "winston",
      "tracing": "jaeger"
    },
    "security": {
      "enabled": true,
      "secrets": "vault",
      "scanning": "snyk"
    }
  }
}
```

## Directory Structure Customization

### Custom Directory Layout

```json
{
  "structure": {
    "customDirectories": {
      "lib": "Custom libraries and utilities",
      "config": "Configuration files",
      "assets": "Static assets and resources",
      "migrations": "Database migrations",
      "tests": "Test files and fixtures"
    },
    "excludeDirectories": ["examples"]
  }
}
```

### Template Files

Create custom template files in your project:

```
homelab-project-template/
├── templates/
│   ├── api/
│   │   ├── server.js.template
│   │   └── package.json.template
│   ├── dashboard/
│   │   ├── App.jsx.template
│   │   └── package.json.template
│   └── scripts/
│       └── deploy.sh.template
```

## Environment Configuration

### Environment Templates

```json
{
  "environments": {
    "development": {
      "nodeEnv": "development",
      "debug": true,
      "hotReload": true
    },
    "staging": {
      "nodeEnv": "staging", 
      "debug": false,
      "ssl": true
    },
    "production": {
      "nodeEnv": "production",
      "debug": false,
      "ssl": true,
      "monitoring": true
    }
  }
}
```

### Secret Management

```json
{
  "secrets": {
    "vault": {
      "enabled": false,
      "endpoint": "https://vault.example.com",
      "authMethod": "token"
    },
    "dotenv": {
      "enabled": true,
      "files": [".env", ".env.local"]
    },
    "kubernetes": {
      "enabled": false,
      "secretName": "app-secrets"
    }
  }
}
```

## Script Customization

### Custom Setup Scripts

Create `scripts/custom-setup.sh`:

```bash
#!/bin/bash
# Custom setup steps for your specific requirements

echo "Running custom setup..."

# Install additional dependencies
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Set up custom services
docker-compose up -d database

# Configure additional tools
./scripts/setup-monitoring.sh

echo "Custom setup complete!"
```

### Hook Scripts

```json
{
  "hooks": {
    "preSetup": "./scripts/pre-setup.sh",
    "postSetup": "./scripts/post-setup.sh", 
    "preDeploy": "./scripts/pre-deploy.sh",
    "postDeploy": "./scripts/post-deploy.sh"
  }
}
```

## Documentation Customization

### Custom Documentation Structure

```json
{
  "documentation": {
    "structure": {
      "api": {
        "enabled": true,
        "generator": "swagger",
        "outputPath": "docs/api"
      },
      "architecture": {
        "enabled": true,
        "diagrams": true,
        "format": "mermaid"
      },
      "deployment": {
        "enabled": true,
        "runbooks": true,
        "troubleshooting": true
      }
    }
  }
}
```

### README Template Customization

Create `templates/README.md.template`:

```markdown
# {{PROJECT_NAME}}

{{PROJECT_DESCRIPTION}}

## Quick Start

1. Clone the repository
2. Install dependencies: `{{INSTALL_COMMAND}}`
3. Start development: `{{DEV_COMMAND}}`

## Architecture

{{ARCHITECTURE_DESCRIPTION}}

## Contributing

Please read our [Contributing Guide](CONTRIBUTING.md).
```

## Advanced Customization

### Multi-Project Templates

For organizations with multiple project types:

```json
{
  "templates": {
    "microservice": {
      "description": "Microservice template",
      "structure": {
        "api": {"enabled": true, "framework": "express"},
        "docker": {"enabled": true, "multiStage": true}
      }
    },
    "frontend": {
      "description": "Frontend application template",
      "structure": {
        "dashboard": {"enabled": true, "framework": "react"},
        "cicd": {"enabled": true, "deployTarget": "s3"}
      }
    }
  }
}
```

### Plugin System

Create custom plugins for additional functionality:

```json
{
  "plugins": {
    "monitoring": {
      "enabled": true,
      "package": "@myorg/template-monitoring-plugin",
      "config": {
        "dashboardUrl": "https://grafana.example.com"
      }
    },
    "security": {
      "enabled": true,
      "package": "./plugins/security-plugin",
      "config": {
        "scanOnBuild": true
      }
    }
  }
}
```

## Validation and Testing

### Configuration Validation

The template includes validation for customizations:

```bash
# Validate configuration
./scripts/validate-config.sh

# Test template generation
./scripts/test-template.sh --config custom-config.json
```

### Template Testing

Create tests for your customizations:

```bash
# Test custom setup
./scripts/test-setup.sh

# Integration tests
./scripts/test-integration.sh
```

## Best Practices

### 1. Configuration Management

- Keep sensitive data in environment variables
- Use reasonable defaults for all options
- Validate configuration before processing
- Document all configuration options

### 2. Template Maintenance

- Version your template configurations
- Test changes with multiple project types
- Keep templates up to date with dependencies
- Document breaking changes

### 3. Documentation

- Update documentation when adding features
- Provide examples for common customizations
- Include troubleshooting for custom configurations
- Maintain changelog for template updates

### 4. Security

- Never commit secrets or tokens
- Use least-privilege access patterns
- Validate all user inputs
- Audit dependencies regularly

## Examples

See the `/examples` directory for complete customization examples:

- `examples/basic-project/` - Minimal customization
- `examples/advanced-project/` - Full-featured setup
- `examples/microservice/` - Microservice template
- `examples/frontend-only/` - Frontend-only project

## Support

For customization help:

- 📖 Check the [setup guide](SETUP.md)
- 🐛 Report issues on [GitHub](https://github.com/festion/homelab-project-template/issues)
- 💬 Join discussions in [GitHub Discussions](https://github.com/festion/homelab-project-template/discussions)
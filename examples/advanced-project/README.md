# Advanced Project Example

This example demonstrates a full-featured configuration using the Homelab Project Template with all available features enabled.

## Configuration

This example uses:
- **Project Type**: `fullstack` - Complete full-stack application
- **MCP Servers**: `all` - All available MCP servers
- **Features**: All features enabled for production-ready projects
- **Structure**: API + Dashboard + comprehensive tooling

## Setup

1. Copy this configuration:
   ```bash
   cp examples/advanced-project/template-config.json ./template-config.json
   ```

2. Customize the project details:
   ```json
   {
     "project": {
       "name": "your-advanced-project",
       "description": "Your advanced project description",
       "author": "Your Name <your.email@example.com>"
     },
     "mcp": {
       "configuration": {
         "homeAssistant": {
           "apiUrl": "http://your-ha-instance:8123"
         },
         "networkFs": {
           "shares": {
             "nas": {
               "host": "your-nas.local"
             }
           }
         }
       }
     }
   }
   ```

3. Set up environment variables:
   ```bash
   # Create .env file
   cat > .env << 'EOF'
   NODE_ENV=development
   GITHUB_TOKEN=your_github_token
   HA_URL=http://your-ha-instance:8123
   HA_TOKEN=your_ha_token
   DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
   EOF
   ```

4. Run setup:
   ```bash
   ./scripts/setup.sh
   ```

## What You Get

### Full Directory Structure
```
your-project/
├── api/                     # Backend API
│   ├── src/                 # API source code
│   ├── routes/              # API routes
│   ├── middleware/          # Express middleware
│   ├── models/              # Database models
│   └── tests/               # API tests
├── dashboard/               # Frontend dashboard
│   ├── src/                 # React source code
│   ├── components/          # React components
│   ├── pages/               # Page components
│   └── tests/               # Frontend tests
├── docs/                    # Comprehensive documentation
├── scripts/                 # Utility and deployment scripts
├── .github/                 # GitHub Actions workflows
├── config/                  # Configuration files
├── logs/                    # Application logs
└── assets/                  # Static assets
```

### Complete MCP Integration
- **Filesystem**: Advanced file operations
- **GitHub**: Full repository management
- **Home Assistant**: Home automation integration
- **Network FS**: Network file system access
- **Directory Polling**: Real-time file monitoring

### Development Features
- **Linting**: ESLint + Prettier
- **Testing**: Jest + Playwright (E2E)
- **CI/CD**: GitHub Actions workflows
- **Docker**: Multi-stage production builds
- **Monitoring**: Prometheus + Winston + Jaeger
- **Security**: Vault + Snyk scanning

### API Features
- **Framework**: Express.js with full middleware stack
- **Authentication**: JWT-based auth system
- **Validation**: Request/response validation
- **Documentation**: Auto-generated Swagger docs
- **Database**: PostgreSQL with Prisma ORM

### Dashboard Features
- **Framework**: React with modern tooling
- **Routing**: React Router for navigation
- **State Management**: Redux for complex state
- **UI Library**: Material-UI components
- **Charts**: Recharts for data visualization
- **Build Tool**: Vite for fast development

## Environment Configuration

### Development
```bash
# Development settings
NODE_ENV=development
DEBUG=true
HOT_RELOAD=true
```

### Staging
```bash
# Staging settings
NODE_ENV=staging
SSL=true
DEBUG=false
```

### Production
```bash
# Production settings
NODE_ENV=production
SSL=true
MONITORING=true
DEBUG=false
```

## Available Scripts

### Development
```bash
# Start development servers
npm run dev:api      # Start API server
npm run dev:dashboard # Start dashboard
npm run dev          # Start both

# Testing
npm test             # Run all tests
npm run test:watch   # Watch mode
npm run test:e2e     # End-to-end tests

# Code quality
npm run lint         # Run linter
npm run format       # Format code
```

### Production
```bash
# Build for production
npm run build:api
npm run build:dashboard
npm run build

# Deploy
npm run deploy:staging
npm run deploy:production
```

## Database Setup

1. **Install PostgreSQL**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   
   # macOS
   brew install postgresql
   ```

2. **Create database**:
   ```sql
   CREATE DATABASE your_project_db;
   CREATE USER your_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE your_project_db TO your_user;
   ```

3. **Configure Prisma**:
   ```bash
   cd api
   npx prisma migrate dev
   npx prisma generate
   ```

## Docker Deployment

### Development
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up
```

### Production
```bash
# Build production images
docker build -t your-project-api ./api
docker build -t your-project-dashboard ./dashboard

# Run production stack
docker-compose -f docker-compose.prod.yml up
```

## Monitoring Setup

### Metrics (Prometheus)
- API metrics at `/metrics`
- Custom business metrics
- Infrastructure monitoring

### Logging (Winston)
- Structured JSON logging
- Multiple log levels
- Log aggregation ready

### Tracing (Jaeger)
- Distributed tracing
- Performance monitoring
- Request flow visualization

## Security Features

### Secrets Management
- HashiCorp Vault integration
- Environment-based secrets
- Secure token rotation

### Code Scanning
- Snyk vulnerability scanning
- Dependency security checks
- SAST/DAST integration

### Access Control
- JWT-based authentication
- Role-based permissions
- API rate limiting

## CI/CD Pipeline

### Continuous Integration
- Multi-Node.js version testing
- Code quality checks
- Security scanning
- Test coverage reporting

### Continuous Deployment
- Automated staging deployments
- Production deployment approval
- Rollback capabilities
- Health checks

## Monitoring and Alerts

### Health Checks
- API health endpoints
- Database connectivity
- External service status

### Alerting
- Performance degradation
- Error rate increases
- Security incidents

## Use Cases

This configuration is ideal for:
- Production web applications
- Complex homelab dashboards
- IoT data collection systems
- Home automation interfaces
- Multi-service architectures
- Enterprise-grade projects

## Customization

### Simplify for Smaller Projects
```json
{
  "features": {
    "docker": {"enabled": false},
    "monitoring": {"enabled": false},
    "security": {"enabled": false}
  }
}
```

### Add Additional Services
```json
{
  "structure": {
    "api": {
      "microservices": true,
      "messageQueue": "redis"
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Database Connection**:
   ```bash
   # Test connection
   psql -h localhost -U your_user -d your_project_db
   ```

2. **Port Conflicts**:
   ```bash
   # Check port usage
   lsof -i :3000
   lsof -i :5432
   ```

3. **Environment Variables**:
   ```bash
   # Verify environment
   ./scripts/validate-config.sh
   ```

### Performance Optimization

1. **API Performance**:
   - Enable Redis caching
   - Optimize database queries
   - Use connection pooling

2. **Dashboard Performance**:
   - Code splitting
   - Lazy loading
   - Bundle optimization

## Support

For issues with this advanced configuration:
- Check [Troubleshooting Guide](../../docs/TROUBLESHOOTING.md)
- Review logs in `/logs` directory
- Use `./scripts/validate-config.sh` for diagnostics
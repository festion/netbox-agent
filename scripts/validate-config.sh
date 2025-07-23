#!/bin/bash

# Configuration Validation Script
# Validates template configuration and environment setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/template-config.json"
MCP_CONFIG_FILE="$PROJECT_ROOT/.mcp.json"
ENV_FILE="$PROJECT_ROOT/.env"

# Counters
ERRORS=0
WARNINGS=0
CHECKS=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((CHECKS++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((ERRORS++))
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Get configuration value
get_config() {
    local key="$1"
    local default="$2"
    
    if command_exists jq; then
        local value=$(jq -r "$key // \"$default\"" "$CONFIG_FILE" 2>/dev/null)
        echo "$value"
    else
        echo "$default"
    fi
}

# Validate JSON file
validate_json() {
    local file="$1"
    local description="$2"
    
    if [ ! -f "$file" ]; then
        log_error "$description not found: $file"
        return 1
    fi
    
    if command_exists jq; then
        if jq empty "$file" >/dev/null 2>&1; then
            log_success "$description has valid JSON syntax"
            return 0
        else
            log_error "$description has invalid JSON syntax"
            return 1
        fi
    else
        if python3 -m json.tool "$file" >/dev/null 2>&1; then
            log_success "$description has valid JSON syntax"
            return 0
        else
            log_error "$description has invalid JSON syntax"
            return 1
        fi
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Node.js
    if command_exists node; then
        local node_version=$(node --version | sed 's/v//')
        local major_version=$(echo "$node_version" | cut -d'.' -f1)
        
        if [ "$major_version" -ge 16 ]; then
            log_success "Node.js version $node_version (>= 16.0.0)"
        else
            log_error "Node.js version $node_version is too old (requires >= 16.0.0)"
        fi
    else
        log_error "Node.js is not installed"
    fi
    
    # Check npm
    if command_exists npm; then
        local npm_version=$(npm --version)
        log_success "npm version $npm_version"
    else
        log_error "npm is not installed"
    fi
    
    # Check Git
    if command_exists git; then
        local git_version=$(git --version | awk '{print $3}')
        log_success "Git version $git_version"
    else
        log_error "Git is not installed"
    fi
    
    # Check jq (optional but recommended)
    if command_exists jq; then
        local jq_version=$(jq --version | sed 's/jq-//')
        log_success "jq version $jq_version (for enhanced JSON processing)"
    else
        log_warning "jq is not installed (recommended for better JSON processing)"
    fi
    
    # Check Python (for JSON validation fallback)
    if command_exists python3; then
        local python_version=$(python3 --version | awk '{print $2}')
        log_success "Python version $python_version (for JSON validation)"
    else
        log_warning "Python3 is not available (used for JSON validation fallback)"
    fi
}

# Validate template configuration
validate_template_config() {
    log_info "Validating template configuration..."
    
    if ! validate_json "$CONFIG_FILE" "Template configuration"; then
        return 1
    fi
    
    # Check required fields
    local project_name=$(get_config ".project.name" "")
    local project_type=$(get_config ".project.type" "generic")
    
    if [ -z "$project_name" ]; then
        log_warning "Project name is not set in configuration"
    else
        log_success "Project name: $project_name"
    fi
    
    # Validate project type
    case "$project_type" in
        generic|api|dashboard|fullstack|automation)
            log_success "Project type: $project_type"
            ;;
        *)
            log_error "Invalid project type: $project_type (must be: generic, api, dashboard, fullstack, automation)"
            ;;
    esac
    
    # Check structure configuration
    local api_enabled=$(get_config ".structure.api.enabled" "false")
    local dashboard_enabled=$(get_config ".structure.dashboard.enabled" "false")
    
    if [ "$project_type" = "fullstack" ]; then
        if [ "$api_enabled" != "true" ] || [ "$dashboard_enabled" != "true" ]; then
            log_warning "Fullstack project should have both API and dashboard enabled"
        fi
    fi
    
    if [ "$project_type" = "api" ] && [ "$api_enabled" != "true" ]; then
        log_warning "API project should have API structure enabled"
    fi
    
    if [ "$project_type" = "dashboard" ] && [ "$dashboard_enabled" != "true" ]; then
        log_warning "Dashboard project should have dashboard structure enabled"
    fi
}

# Validate MCP configuration
validate_mcp_config() {
    log_info "Validating MCP configuration..."
    
    if [ -f "$MCP_CONFIG_FILE" ]; then
        if validate_json "$MCP_CONFIG_FILE" "MCP configuration"; then
            # Check if servers are configured
            if command_exists jq; then
                local server_count=$(jq '.mcpServers | length' "$MCP_CONFIG_FILE" 2>/dev/null || echo "0")
                if [ "$server_count" -gt 0 ]; then
                    log_success "MCP configuration has $server_count server(s) configured"
                else
                    log_warning "MCP configuration has no servers configured"
                fi
            else
                log_success "MCP configuration file exists"
            fi
        fi
    else
        log_warning "MCP configuration file not found (run setup.sh to create)"
    fi
}

# Check environment variables
check_environment_variables() {
    log_info "Checking environment variables..."
    
    # Load .env file if it exists
    if [ -f "$ENV_FILE" ]; then
        set -a  # automatically export all variables
        source "$ENV_FILE"
        set +a
        log_success "Environment file loaded from .env"
    else
        log_warning "Environment file not found: .env"
    fi
    
    # Check GitHub token
    if [ -n "$GITHUB_TOKEN" ]; then
        if [[ "$GITHUB_TOKEN" =~ ^ghp_[a-zA-Z0-9]{36}$ ]]; then
            log_success "GitHub token format is valid"
            
            # Test GitHub token (if curl is available)
            if command_exists curl; then
                if curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user >/dev/null 2>&1; then
                    log_success "GitHub token is valid and accessible"
                else
                    log_error "GitHub token is invalid or cannot access GitHub API"
                fi
            fi
        else
            log_error "GitHub token format is invalid (should start with 'ghp_')"
        fi
    else
        log_warning "GITHUB_TOKEN environment variable is not set"
    fi
    
    # Check Home Assistant configuration
    if [ -n "$HA_URL" ]; then
        log_success "Home Assistant URL is set: $HA_URL"
        
        # Validate URL format
        if [[ "$HA_URL" =~ ^https?://.*:[0-9]+$ ]]; then
            log_success "Home Assistant URL format is valid"
        else
            log_warning "Home Assistant URL format may be invalid (should include protocol and port)"
        fi
        
        # Test connectivity (if curl is available)
        if command_exists curl && [ -n "$HA_TOKEN" ]; then
            if curl -s -m 5 -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/" >/dev/null 2>&1; then
                log_success "Home Assistant is accessible with provided token"
            else
                log_warning "Cannot connect to Home Assistant (may be network issue or invalid token)"
            fi
        fi
    else
        log_info "Home Assistant URL not set (optional)"
    fi
    
    # Check Home Assistant token
    if [ -n "$HA_TOKEN" ]; then
        if [[ "$HA_TOKEN" =~ ^[a-zA-Z0-9._-]{100,}$ ]]; then
            log_success "Home Assistant token format appears valid"
        else
            log_warning "Home Assistant token format may be invalid"
        fi
    else
        log_info "Home Assistant token not set (optional)"
    fi
}

# Check project structure
check_project_structure() {
    log_info "Checking project structure..."
    
    # Check essential files
    local essential_files=("README.md" "LICENSE" ".gitignore" "template-config.json")
    
    for file in "${essential_files[@]}"; do
        if [ -f "$PROJECT_ROOT/$file" ]; then
            log_success "Essential file exists: $file"
        else
            log_error "Essential file missing: $file"
        fi
    done
    
    # Check directories
    local expected_dirs=("docs" "scripts" "api" "dashboard" "examples")
    
    for dir in "${expected_dirs[@]}"; do
        if [ -d "$PROJECT_ROOT/$dir" ]; then
            log_success "Directory exists: $dir"
        else
            log_warning "Directory missing: $dir"
        fi
    done
    
    # Check if scripts are executable
    if [ -f "$PROJECT_ROOT/scripts/setup.sh" ]; then
        if [ -x "$PROJECT_ROOT/scripts/setup.sh" ]; then
            log_success "setup.sh is executable"
        else
            log_warning "setup.sh is not executable (run: chmod +x scripts/setup.sh)"
        fi
    fi
}

# Check Git repository
check_git_repository() {
    log_info "Checking Git repository..."
    
    if [ -d "$PROJECT_ROOT/.git" ]; then
        log_success "Git repository is initialized"
        
        # Check if there are any commits
        if git -C "$PROJECT_ROOT" rev-parse HEAD >/dev/null 2>&1; then
            log_success "Git repository has commits"
            
            # Check for remote origin
            if git -C "$PROJECT_ROOT" remote get-url origin >/dev/null 2>&1; then
                local remote_url=$(git -C "$PROJECT_ROOT" remote get-url origin)
                log_success "Git remote origin configured: $remote_url"
            else
                log_warning "Git remote origin not configured"
            fi
        else
            log_warning "Git repository has no commits"
        fi
    else
        log_warning "Git repository not initialized (run: git init)"
    fi
}

# Check dependencies (if package.json exists)
check_dependencies() {
    log_info "Checking project dependencies..."
    
    # Check API dependencies
    if [ -f "$PROJECT_ROOT/api/package.json" ]; then
        log_success "API package.json exists"
        
        if [ -d "$PROJECT_ROOT/api/node_modules" ]; then
            log_success "API dependencies installed"
        else
            log_warning "API dependencies not installed (run: cd api && npm install)"
        fi
    fi
    
    # Check dashboard dependencies
    if [ -f "$PROJECT_ROOT/dashboard/package.json" ]; then
        log_success "Dashboard package.json exists"
        
        if [ -d "$PROJECT_ROOT/dashboard/node_modules" ]; then
            log_success "Dashboard dependencies installed"
        else
            log_warning "Dashboard dependencies not installed (run: cd dashboard && npm install)"
        fi
    fi
}

# Test MCP servers (if npx is available)
test_mcp_servers() {
    log_info "Testing MCP server availability..."
    
    if ! command_exists npx; then
        log_warning "npx not available, skipping MCP server tests"
        return
    fi
    
    # Test filesystem server
    if timeout 10s npx -y @modelcontextprotocol/server-filesystem --version >/dev/null 2>&1; then
        log_success "MCP filesystem server is accessible"
    else
        log_warning "MCP filesystem server is not accessible or timed out"
    fi
    
    # Test GitHub server
    if timeout 10s npx -y @modelcontextprotocol/server-github --version >/dev/null 2>&1; then
        log_success "MCP GitHub server is accessible"
    else
        log_warning "MCP GitHub server is not accessible or timed out"
    fi
}

# Check network connectivity
check_network_connectivity() {
    log_info "Checking network connectivity..."
    
    # Test GitHub API
    if command_exists curl; then
        if curl -s -m 5 https://api.github.com >/dev/null 2>&1; then
            log_success "GitHub API is accessible"
        else
            log_warning "Cannot connect to GitHub API"
        fi
        
        # Test npm registry
        if curl -s -m 5 https://registry.npmjs.org >/dev/null 2>&1; then
            log_success "npm registry is accessible"
        else
            log_warning "Cannot connect to npm registry"
        fi
    else
        log_warning "curl not available, skipping network connectivity tests"
    fi
}

# Print validation summary
print_summary() {
    echo
    log_info "Validation Summary:"
    echo "  Checks passed: $CHECKS"
    echo "  Warnings: $WARNINGS"
    echo "  Errors: $ERRORS"
    echo
    
    if [ $ERRORS -eq 0 ]; then
        if [ $WARNINGS -eq 0 ]; then
            log_success "All validations passed! Your project is ready to use."
        else
            log_warning "Validation completed with warnings. Check the warnings above."
        fi
    else
        log_error "Validation failed with $ERRORS error(s). Please fix the errors above."
        exit 1
    fi
}

# Print recommendations
print_recommendations() {
    echo
    log_info "Recommendations:"
    
    if [ $WARNINGS -gt 0 ]; then
        echo "  • Address the warnings above for optimal functionality"
    fi
    
    if [ ! -f "$ENV_FILE" ]; then
        echo "  • Create .env file with your configuration (run setup.sh)"
    fi
    
    if [ -z "$GITHUB_TOKEN" ]; then
        echo "  • Set GITHUB_TOKEN for GitHub integration"
    fi
    
    if ! command_exists jq; then
        echo "  • Install jq for better JSON processing: sudo apt-get install jq"
    fi
    
    echo "  • See docs/SETUP.md for detailed setup instructions"
    echo "  • See docs/TROUBLESHOOTING.md if you encounter issues"
}

# Main execution
main() {
    log_info "Starting configuration validation..."
    echo
    
    check_prerequisites
    echo
    
    validate_template_config
    echo
    
    validate_mcp_config
    echo
    
    check_environment_variables
    echo
    
    check_project_structure
    echo
    
    check_git_repository
    echo
    
    check_dependencies
    echo
    
    test_mcp_servers
    echo
    
    check_network_connectivity
    
    print_summary
    print_recommendations
}

# Run main function
main "$@"
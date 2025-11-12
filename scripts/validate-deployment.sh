#!/bin/bash
###############################################################################
# NetBox Agent Deployment Validation Script
#
# This script validates all deployment methods for the NetBox Agent:
# 1. Quick Start (manual/development)
# 2. Systemd Service (production)
# 3. Docker/Docker Compose
#
# Usage: ./scripts/validate-deployment.sh [--method METHOD]
#   METHOD: quickstart, systemd, docker, all (default: all)
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Default method
METHOD="${1:-all}"

###############################################################################
# Helper Functions
###############################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((TESTS_PASSED++))
    ((TESTS_RUN++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((TESTS_FAILED++))
    ((TESTS_RUN++))
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        log_success "Command available: $1"
        return 0
    else
        log_error "Command not found: $1"
        return 1
    fi
}

check_file() {
    if [ -f "$1" ]; then
        log_success "File exists: $1"
        return 0
    else
        log_error "File missing: $1"
        return 1
    fi
}

check_directory() {
    if [ -d "$1" ]; then
        log_success "Directory exists: $1"
        return 0
    else
        log_error "Directory missing: $1"
        return 1
    fi
}

check_readable() {
    if [ -r "$1" ]; then
        log_success "File readable: $1"
        return 0
    else
        log_error "File not readable: $1"
        return 1
    fi
}

check_executable() {
    if [ -x "$1" ]; then
        log_success "File executable: $1"
        return 0
    else
        log_error "File not executable: $1"
        return 1
    fi
}

check_json_valid() {
    if python3 -c "import json; json.load(open('$1'))" 2>/dev/null; then
        log_success "Valid JSON: $1"
        return 0
    else
        log_error "Invalid JSON: $1"
        return 1
    fi
}

###############################################################################
# Validation Tests
###############################################################################

validate_prerequisites() {
    log_section "Validating Prerequisites"

    # Check Python
    check_command python3 || log_warn "Python 3 required for manual deployment"

    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        log_info "Python version: $PYTHON_VERSION"

        MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 8 ]; then
            log_success "Python version >= 3.8"
        else
            log_error "Python version >= 3.8 required (found: $PYTHON_VERSION)"
        fi
    fi

    # Check Docker (optional)
    if [ "$METHOD" = "docker" ] || [ "$METHOD" = "all" ]; then
        check_command docker || log_warn "Docker required for Docker deployment"
        check_command docker-compose || check_command docker compose || log_warn "Docker Compose required for Docker deployment"
    fi

    # Check systemd (optional)
    if [ "$METHOD" = "systemd" ] || [ "$METHOD" = "all" ]; then
        check_command systemctl || log_warn "systemd required for systemd deployment"
    fi
}

validate_project_structure() {
    log_section "Validating Project Structure"

    # Required directories
    check_directory "src"
    check_directory "config"
    check_directory "scripts"
    check_directory "tests"

    # Core files
    check_file "requirements.txt"
    check_file "src/netbox_agent.py"
    check_file "README.md"

    # Configuration files
    check_file "template-config.json"
    check_json_valid "template-config.json"
}

validate_quickstart() {
    log_section "Validating Quick Start Deployment"

    # Check quick start script
    check_file "scripts/quick-start.sh"
    check_executable "scripts/quick-start.sh"

    # Check validation script
    check_file "scripts/validate-config.py"
    check_executable "scripts/validate-config.py" || log_warn "validate-config.py should be executable"

    # Validate script syntax
    log_info "Checking quick-start.sh syntax..."
    if bash -n scripts/quick-start.sh 2>/dev/null; then
        log_success "quick-start.sh syntax valid"
    else
        log_error "quick-start.sh has syntax errors"
    fi

    # Check if venv can be created (test only)
    log_info "Testing virtual environment creation..."
    if python3 -m venv --help &>/dev/null; then
        log_success "Python venv module available"
    else
        log_error "Python venv module not available"
    fi
}

validate_systemd() {
    log_section "Validating Systemd Deployment"

    # Check install script
    check_file "scripts/install.sh"
    check_executable "scripts/install.sh"

    # Check service file
    check_file "scripts/netbox-agent.service"

    # Validate install script syntax
    log_info "Checking install.sh syntax..."
    if bash -n scripts/install.sh 2>/dev/null; then
        log_success "install.sh syntax valid"
    else
        log_error "install.sh has syntax errors"
    fi

    # Validate service file format
    log_info "Validating service file format..."
    if grep -q "\[Unit\]" scripts/netbox-agent.service && \
       grep -q "\[Service\]" scripts/netbox-agent.service && \
       grep -q "\[Install\]" scripts/netbox-agent.service; then
        log_success "Service file has correct structure"
    else
        log_error "Service file missing required sections"
    fi

    # Check for required service directives
    if grep -q "ExecStart=" scripts/netbox-agent.service; then
        log_success "Service file has ExecStart directive"
    else
        log_error "Service file missing ExecStart directive"
    fi

    if grep -q "Restart=" scripts/netbox-agent.service; then
        log_success "Service file has Restart directive"
    else
        log_warn "Service file should have Restart directive"
    fi
}

validate_docker() {
    log_section "Validating Docker Deployment"

    # Check Dockerfile
    check_file "Dockerfile"

    # Check docker-compose.yml
    check_file "docker-compose.yml"

    # Validate Dockerfile syntax
    log_info "Validating Dockerfile..."
    if grep -q "FROM " Dockerfile; then
        log_success "Dockerfile has FROM instruction"
    else
        log_error "Dockerfile missing FROM instruction"
    fi

    if grep -q "CMD " Dockerfile || grep -q "ENTRYPOINT " Dockerfile; then
        log_success "Dockerfile has CMD or ENTRYPOINT"
    else
        log_error "Dockerfile missing CMD or ENTRYPOINT"
    fi

    if grep -q "HEALTHCHECK " Dockerfile; then
        log_success "Dockerfile has HEALTHCHECK"
    else
        log_warn "Dockerfile should have HEALTHCHECK for production"
    fi

    # Validate docker-compose.yml
    log_info "Validating docker-compose.yml..."
    if command -v docker-compose &> /dev/null; then
        if docker-compose config &>/dev/null; then
            log_success "docker-compose.yml is valid"
        else
            log_error "docker-compose.yml has errors"
        fi
    elif command -v docker &> /dev/null && docker compose version &>/dev/null; then
        if docker compose config &>/dev/null; then
            log_success "docker-compose.yml is valid"
        else
            log_error "docker-compose.yml has errors"
        fi
    else
        log_warn "Cannot validate docker-compose.yml (docker-compose not available)"
    fi

    # Check health check script
    check_file "scripts/health_check.py"
}

validate_documentation() {
    log_section "Validating Documentation"

    # Check deployment guide
    check_file "docs/DEPLOYMENT.md"

    # Check README
    check_file "README.md"

    # Verify deployment methods are documented
    log_info "Checking documentation completeness..."
    if grep -q "Quick Start\|quick-start\|quick start" docs/DEPLOYMENT.md; then
        log_success "Quick start documented"
    else
        log_warn "Quick start should be documented in DEPLOYMENT.md"
    fi

    if grep -q "Systemd\|systemd" docs/DEPLOYMENT.md; then
        log_success "Systemd deployment documented"
    else
        log_warn "Systemd deployment should be documented"
    fi

    if grep -q "Docker\|docker" docs/DEPLOYMENT.md; then
        log_success "Docker deployment documented"
    else
        log_warn "Docker deployment should be documented"
    fi
}

validate_dependencies() {
    log_section "Validating Dependencies"

    # Check requirements.txt
    check_file "requirements.txt"

    # Validate requirements.txt format
    log_info "Validating requirements.txt format..."
    if grep -qE "^[a-zA-Z0-9\-_]+[>=<]" requirements.txt; then
        log_success "requirements.txt has version specifications"
    else
        log_warn "requirements.txt should specify versions"
    fi

    # Check for security-sensitive packages
    log_info "Checking for security packages..."
    if grep -q "cryptography" requirements.txt; then
        log_success "Cryptography package present"
    fi

    if grep -q "requests" requirements.txt || grep -q "aiohttp" requirements.txt; then
        log_success "HTTP client package present"
    fi
}

###############################################################################
# Main Execution
###############################################################################

main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║   NetBox Agent Deployment Validation                  ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""

    log_info "Validation method: $METHOD"
    echo ""

    # Run validations based on method
    validate_prerequisites
    validate_project_structure
    validate_dependencies
    validate_documentation

    case "$METHOD" in
        quickstart)
            validate_quickstart
            ;;
        systemd)
            validate_systemd
            ;;
        docker)
            validate_docker
            ;;
        all)
            validate_quickstart
            validate_systemd
            validate_docker
            ;;
        *)
            log_error "Unknown method: $METHOD"
            echo "Usage: $0 [quickstart|systemd|docker|all]"
            exit 1
            ;;
    esac

    # Summary
    log_section "Validation Summary"
    echo ""
    echo "Total Tests: $TESTS_RUN"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    echo ""

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ✓ All deployment validations passed!         ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
        echo ""
        exit 0
    else
        echo -e "${RED}╔════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║  ✗ Some deployment validations failed         ║${NC}"
        echo -e "${RED}╚════════════════════════════════════════════════╝${NC}"
        echo ""
        exit 1
    fi
}

# Run main function
main

#!/bin/bash

# NetBox Agent Runner Script
# This script activates the virtual environment and runs the NetBox agent

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
VENV_PATH="$PROJECT_ROOT/venv"
AGENT_SCRIPT="$PROJECT_ROOT/src/netbox_agent.py"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment exists
check_venv() {
    if [ ! -d "$VENV_PATH" ]; then
        log_error "Virtual environment not found at $VENV_PATH"
        log_info "Please run ./scripts/setup.sh first to create the virtual environment"
        exit 1
    fi
}

# Check if agent script exists
check_agent() {
    if [ ! -f "$AGENT_SCRIPT" ]; then
        log_error "NetBox agent script not found at $AGENT_SCRIPT"
        exit 1
    fi
}

# Activate virtual environment and run agent
run_agent() {
    log_info "Starting NetBox Agent..."
    
    # Change to project directory
    cd "$PROJECT_ROOT"
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Run the agent
    python "$AGENT_SCRIPT" "$@"
    
    # Deactivate virtual environment
    deactivate
}

# Print usage information
print_usage() {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --dry-run     Run in dry-run mode (no changes to NetBox)"
    echo "  --config      Specify custom configuration file"
    echo "  --log-level   Set log level (DEBUG, INFO, WARNING, ERROR)"
    echo "  --help        Show this help message"
    echo
    echo "Examples:"
    echo "  $0                           # Run with default configuration"
    echo "  $0 --dry-run                 # Run without making changes"
    echo "  $0 --log-level DEBUG         # Run with debug logging"
    echo "  $0 --config /path/to/config  # Use custom configuration"
}

# Main execution
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                print_usage
                exit 0
                ;;
            *)
                # Pass all other arguments to the agent
                break
                ;;
        esac
    done
    
    # Perform checks
    check_venv
    check_agent
    
    # Run the agent with all arguments
    run_agent "$@"
}

# Run main function
main "$@"
#!/bin/bash

# Template Update Script
# Updates an existing project to the latest template version

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
TEMPLATE_REPO="https://github.com/festion/homelab-project-template.git"
TEMP_DIR="/tmp/homelab-template-update-$$"
BACKUP_DIR="$PROJECT_ROOT/template-update-backup-$(date +%Y%m%d-%H%M%S)"

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Git
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed. Please install Git and try again."
        exit 1
    fi
    
    # Check if we're in a git repository
    if [ ! -d "$PROJECT_ROOT/.git" ]; then
        log_error "Not in a git repository. Initialize git first: git init"
        exit 1
    fi
    
    # Check for uncommitted changes
    if ! git -C "$PROJECT_ROOT" diff-index --quiet HEAD -- 2>/dev/null; then
        log_warning "You have uncommitted changes. Consider committing them first."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Update cancelled."
            exit 0
        fi
    fi
    
    log_success "Prerequisites check passed"
}

# Create backup
create_backup() {
    log_info "Creating backup..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup critical files
    local backup_files=(
        "template-config.json"
        ".mcp.json"
        ".env"
        "README.md"
        "docs/"
        "scripts/"
        ".github/"
    )
    
    for item in "${backup_files[@]}"; do
        if [ -e "$PROJECT_ROOT/$item" ]; then
            cp -r "$PROJECT_ROOT/$item" "$BACKUP_DIR/"
            log_info "Backed up: $item"
        fi
    done
    
    log_success "Backup created at: $BACKUP_DIR"
}

# Clone latest template
clone_template() {
    log_info "Downloading latest template..."
    
    # Clean up any existing temp directory
    rm -rf "$TEMP_DIR"
    
    # Clone template repository
    git clone --depth 1 "$TEMPLATE_REPO" "$TEMP_DIR"
    
    # Remove .git directory from template
    rm -rf "$TEMP_DIR/.git"
    
    log_success "Latest template downloaded"
}

# Detect current version
detect_current_version() {
    local current_version="unknown"
    
    if [ -f "$PROJECT_ROOT/template-config.json" ] && command -v jq &> /dev/null; then
        current_version=$(jq -r '.version // "unknown"' "$PROJECT_ROOT/template-config.json" 2>/dev/null)
    fi
    
    echo "$current_version"
}

# Get template version
get_template_version() {
    local template_version="unknown"
    
    if [ -f "$TEMP_DIR/template-config.json" ] && command -v jq &> /dev/null; then
        template_version=$(jq -r '.version // "unknown"' "$TEMP_DIR/template-config.json" 2>/dev/null)
    fi
    
    echo "$template_version"
}

# Update non-conflicting files
update_safe_files() {
    log_info "Updating safe files..."
    
    # Files that can be safely updated
    local safe_files=(
        ".gitignore"
        "LICENSE"
        "docs/SETUP.md"
        "docs/MCP_CONFIGURATION.md"
        "docs/CUSTOMIZATION.md"
        "docs/TROUBLESHOOTING.md"
        "scripts/validate-config.sh"
        "scripts/update-template.sh"
        ".github/workflows/"
    )
    
    for file in "${safe_files[@]}"; do
        if [ -e "$TEMP_DIR/$file" ]; then
            # Create directory if it doesn't exist
            local dir=$(dirname "$PROJECT_ROOT/$file")
            mkdir -p "$dir"
            
            # Copy file
            cp -r "$TEMP_DIR/$file" "$PROJECT_ROOT/$file"
            log_success "Updated: $file"
        fi
    done
}

# Merge configuration updates
merge_config_updates() {
    log_info "Merging configuration updates..."
    
    if [ ! -f "$PROJECT_ROOT/template-config.json" ]; then
        log_warning "No existing template-config.json found, copying new one"
        cp "$TEMP_DIR/template-config.json" "$PROJECT_ROOT/"
        return
    fi
    
    # If jq is available, do smart merge
    if command -v jq &> /dev/null; then
        log_info "Performing smart configuration merge..."
        
        # Get current config
        local current_config=$(cat "$PROJECT_ROOT/template-config.json")
        local new_config=$(cat "$TEMP_DIR/template-config.json")
        
        # Merge configurations (new template fields + existing user values)
        local merged_config=$(echo "$new_config" "$current_config" | jq -s '.[0] * .[1]')
        
        # Write merged config
        echo "$merged_config" | jq '.' > "$PROJECT_ROOT/template-config.json.new"
        
        # Show diff if available
        if command -v diff &> /dev/null; then
            log_info "Configuration changes:"
            diff "$PROJECT_ROOT/template-config.json" "$PROJECT_ROOT/template-config.json.new" || true
        fi
        
        # Replace original
        mv "$PROJECT_ROOT/template-config.json.new" "$PROJECT_ROOT/template-config.json"
        log_success "Configuration merged successfully"
    else
        log_warning "jq not available, manual configuration merge required"
        cp "$TEMP_DIR/template-config.json" "$PROJECT_ROOT/template-config.json.new"
        log_info "New configuration saved as template-config.json.new"
        log_info "Please manually merge your settings from the backup"
    fi
}

# Update scripts with user confirmation
update_scripts() {
    log_info "Updating scripts..."
    
    # Check if setup.sh was customized
    if [ -f "$PROJECT_ROOT/scripts/setup.sh" ]; then
        log_warning "setup.sh exists and may have been customized"
        
        if command -v diff &> /dev/null; then
            log_info "Comparing with new version:"
            diff "$PROJECT_ROOT/scripts/setup.sh" "$TEMP_DIR/scripts/setup.sh" || true
        fi
        
        read -p "Replace setup.sh with new version? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp "$TEMP_DIR/scripts/setup.sh" "$PROJECT_ROOT/scripts/"
            chmod +x "$PROJECT_ROOT/scripts/setup.sh"
            log_success "Updated: scripts/setup.sh"
        else
            cp "$TEMP_DIR/scripts/setup.sh" "$PROJECT_ROOT/scripts/setup.sh.new"
            log_info "New version saved as scripts/setup.sh.new"
        fi
    else
        cp "$TEMP_DIR/scripts/setup.sh" "$PROJECT_ROOT/scripts/"
        chmod +x "$PROJECT_ROOT/scripts/setup.sh"
        log_success "Added: scripts/setup.sh"
    fi
}

# Update README with user confirmation
update_readme() {
    log_info "Updating README..."
    
    if [ -f "$PROJECT_ROOT/README.md" ]; then
        # Check if README was significantly customized
        local readme_size=$(wc -l < "$PROJECT_ROOT/README.md")
        local template_readme_size=$(wc -l < "$TEMP_DIR/README.md")
        
        # If sizes are very different, assume customization
        if [ $((readme_size - template_readme_size)) -gt 10 ] || [ $((template_readme_size - readme_size)) -gt 10 ]; then
            log_warning "README.md appears to be customized (size difference: $((readme_size - template_readme_size)) lines)"
            
            read -p "Replace README.md with template version? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                cp "$TEMP_DIR/README.md" "$PROJECT_ROOT/"
                log_success "Updated: README.md"
                log_warning "Remember to customize it for your project"
            else
                cp "$TEMP_DIR/README.md" "$PROJECT_ROOT/README.md.new"
                log_info "New version saved as README.md.new"
            fi
        else
            # Sizes are similar, likely safe to update
            cp "$TEMP_DIR/README.md" "$PROJECT_ROOT/"
            log_success "Updated: README.md"
        fi
    else
        cp "$TEMP_DIR/README.md" "$PROJECT_ROOT/"
        log_success "Added: README.md"
    fi
}

# Add new features
add_new_features() {
    log_info "Checking for new features..."
    
    # Check for new directories in template
    local new_dirs=()
    
    for dir in "$TEMP_DIR"/*; do
        if [ -d "$dir" ]; then
            local dirname=$(basename "$dir")
            if [ ! -d "$PROJECT_ROOT/$dirname" ] && [[ ! "$dirname" =~ ^\. ]]; then
                new_dirs+=("$dirname")
            fi
        fi
    done
    
    if [ ${#new_dirs[@]} -gt 0 ]; then
        log_info "New directories found: ${new_dirs[*]}"
        
        for dir in "${new_dirs[@]}"; do
            read -p "Add new directory '$dir'? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                cp -r "$TEMP_DIR/$dir" "$PROJECT_ROOT/"
                log_success "Added: $dir"
            fi
        done
    fi
    
    # Check for new files in existing directories
    local new_files=()
    
    for file in "$TEMP_DIR"/*.md "$TEMP_DIR"/*.json; do
        if [ -f "$file" ]; then
            local filename=$(basename "$file")
            if [ ! -f "$PROJECT_ROOT/$filename" ] && [[ ! "$filename" =~ ^README.md$ ]] && [[ ! "$filename" =~ ^template-config.json$ ]]; then
                new_files+=("$filename")
            fi
        fi
    done
    
    if [ ${#new_files[@]} -gt 0 ]; then
        log_info "New files found: ${new_files[*]}"
        
        for file in "${new_files[@]}"; do
            read -p "Add new file '$file'? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                cp "$TEMP_DIR/$file" "$PROJECT_ROOT/"
                log_success "Added: $file"
            fi
        done
    fi
}

# Update MCP configuration
update_mcp_config() {
    log_info "Updating MCP configuration..."
    
    if [ -f "$PROJECT_ROOT/.mcp.json" ]; then
        log_warning ".mcp.json exists and may have been customized"
        
        read -p "Replace .mcp.json with template version? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Run setup to regenerate MCP config
            log_info "Regenerating MCP configuration based on current template-config.json"
            cd "$PROJECT_ROOT"
            ./scripts/setup.sh --mcp-only 2>/dev/null || true
            log_success "Updated: .mcp.json"
        else
            log_info "MCP configuration left unchanged"
        fi
    else
        log_info "No existing .mcp.json found, will be created by setup.sh if needed"
    fi
}

# Clean up
cleanup() {
    log_info "Cleaning up..."
    rm -rf "$TEMP_DIR"
    log_success "Cleanup completed"
}

# Print update summary
print_summary() {
    local current_version=$(detect_current_version)
    local new_version=$(get_template_version)
    
    log_success "Template update completed!"
    echo
    log_info "Version information:"
    echo "  Previous version: $current_version"
    echo "  Updated to version: $new_version"
    echo
    log_info "Backup location: $BACKUP_DIR"
    echo
    log_info "Next steps:"
    echo "1. Review updated files and configuration"
    echo "2. Test your project functionality"
    echo "3. Run validation: ./scripts/validate-config.sh"
    echo "4. Commit changes: git add . && git commit -m 'Update template'"
    echo "5. Remove backup if everything works: rm -rf '$BACKUP_DIR'"
    echo
    log_info "If you encounter issues:"
    echo "• Restore from backup: cp -r '$BACKUP_DIR'/* ."
    echo "• Check docs/TROUBLESHOOTING.md"
    echo "• Report issues: https://github.com/festion/homelab-project-template/issues"
}

# Show what will be updated
show_update_plan() {
    log_info "Update plan:"
    echo "• Safe files will be automatically updated"
    echo "• Configuration will be merged intelligently"
    echo "• Customized files will require confirmation"
    echo "• New features will be offered for addition"
    echo "• A backup will be created before changes"
    echo
    
    read -p "Continue with update? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Update cancelled."
        exit 0
    fi
}

# Main execution
main() {
    log_info "Starting template update..."
    
    local current_version=$(detect_current_version)
    log_info "Current template version: $current_version"
    echo
    
    check_prerequisites
    clone_template
    
    local new_version=$(get_template_version)
    log_info "Available template version: $new_version"
    
    if [ "$current_version" == "$new_version" ] && [ "$current_version" != "unknown" ]; then
        log_info "Already using the latest template version."
        read -p "Force update anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            cleanup
            exit 0
        fi
    fi
    
    echo
    show_update_plan
    
    create_backup
    update_safe_files
    merge_config_updates
    update_scripts
    update_readme
    add_new_features
    update_mcp_config
    cleanup
    
    echo
    print_summary
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Template Update Script"
        echo
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h    Show this help message"
        echo "  --version     Show current template version"
        echo "  --check       Check for updates without applying"
        echo
        exit 0
        ;;
    --version)
        echo "Current template version: $(detect_current_version)"
        exit 0
        ;;
    --check)
        log_info "Checking for updates..."
        clone_template
        local current_version=$(detect_current_version)
        local new_version=$(get_template_version)
        echo "Current version: $current_version"
        echo "Latest version: $new_version"
        if [ "$current_version" != "$new_version" ]; then
            echo "Update available!"
            exit 1
        else
            echo "Already up to date."
            exit 0
        fi
        cleanup
        ;;
    *)
        main "$@"
        ;;
esac
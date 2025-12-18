#!/bin/bash
# Development setup script using uv for fast Python dependency management
# This script sets up the complete development environment for fplaunchwrapper

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if uv is installed
check_uv() {
    if ! command -v uv &> /dev/null; then
        log_info "Installing uv (fast Python package installer)..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi

    if command -v uv &> /dev/null; then
        log_success "uv is available: $(uv --version)"
        return 0
    else
        log_error "Failed to install uv"
        return 1
    fi
}

# Install Python dependencies using uv
install_dependencies() {
    local mode="${1:-dev}"

    log_info "Installing Python dependencies with uv (mode: $mode)..."

    case "$mode" in
        "minimal")
            uv pip install -e .
            ;;
        "robustness")
            uv pip install -e ".[robustness]"
            ;;
        "advanced")
            uv pip install -e ".[robustness,advanced]"
            ;;
        "dev")
            uv pip install -e ".[robustness,advanced,dev]"
            ;;
        "full")
            uv pip install -e ".[all]"
            ;;
        *)
            log_error "Unknown installation mode: $mode"
            echo "Available modes: minimal, robustness, advanced, dev, full"
            return 1
            ;;
    esac

    log_success "Python dependencies installed successfully"
}

# Install system dependencies
install_system_deps() {
    log_info "Checking for system dependencies..."

    local missing_deps=()

    # Check for Flatpak
    if ! command -v flatpak &> /dev/null; then
        missing_deps+=("flatpak")
    fi

    # Check for dialog (for interactive prompts)
    if ! command -v dialog &> /dev/null; then
        missing_deps+=("dialog")
    fi

    # Check for bash testing framework
    if ! command -v bats &> /dev/null; then
        missing_deps+=("bats")
    fi

    # Check for shell script linting
    if ! command -v shellcheck &> /dev/null; then
        missing_deps+=("shellcheck")
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_warn "Missing system dependencies: ${missing_deps[*]}"
        log_info "Installing system dependencies..."

        # Detect package manager
        if command -v apt-get &> /dev/null; then
            # Debian/Ubuntu
            sudo apt-get update
            sudo apt-get install -y flatpak dialog bats shellcheck
        elif command -v dnf &> /dev/null; then
            # Fedora/RHEL
            sudo dnf install -y flatpak dialog bats shellcheck
        elif command -v pacman &> /dev/null; then
            # Arch Linux
            sudo pacman -S --noconfirm flatpak dialog bats shellcheck
        elif command -v zypper &> /dev/null; then
            # openSUSE
            sudo zypper install -y flatpak dialog bats shellcheck
        else
            log_error "Unsupported package manager. Please install manually:"
            echo "  - flatpak"
            echo "  - dialog"
            echo "  - bats"
            echo "  - shellcheck"
            return 1
        fi

        # Initialize Flatpak if not already done
        if ! flatpak remotes | grep -q flathub; then
            log_info "Adding Flathub remote..."
            flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
        fi

        log_success "System dependencies installed"
    else
        log_success "All system dependencies are available"
    fi
}

# Set up development environment
setup_dev_environment() {
    log_info "Setting up development environment..."

    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        log_info "Creating virtual environment..."
        uv venv .venv
    fi

    # Activate virtual environment
    source .venv/bin/activate

    # Install development dependencies
    install_dependencies "dev"

    # Create symlinks for development scripts
    log_info "Creating development script symlinks..."

    # Make scripts executable
    chmod +x fplaunch-generate fplaunch-manage fplaunch-cleanup fplaunch-setup-systemd
    chmod +x tests/test_security_fixes.sh

    # Create symlinks in ~/.local/bin if it exists
    local local_bin="$HOME/.local/bin"
    if [ -d "$local_bin" ]; then
        ln -sf "$(pwd)/fplaunch-generate" "$local_bin/" 2>/dev/null || true
        ln -sf "$(pwd)/fplaunch-manage" "$local_bin/" 2>/dev/null || true
        ln -sf "$(pwd)/fplaunch-cleanup" "$local_bin/" 2>/dev/null || true
        ln -sf "$(pwd)/fplaunch-setup-systemd" "$local_bin/" 2>/dev/null || true
        log_info "Created symlinks in $local_bin"
    fi

    log_success "Development environment setup complete"
}

# Run tests
run_tests() {
    log_info "Running test suite..."

    # Activate virtual environment
    source .venv/bin/activate

    # Run Python tests
    if command -v pytest &> /dev/null; then
        log_info "Running Python tests..."
        pytest tests/python/ -v --tb=short
    else
        log_warn "pytest not available, skipping Python tests"
    fi

    # Run Bash tests
    if command -v bats &> /dev/null; then
        log_info "Running Bash tests..."
        bats tests/bash/ 2>/dev/null || log_warn "Some Bash tests failed"
    else
        log_warn "bats not available, skipping Bash tests"
    fi

    # Run security test
    if [ -f "tests/test_security_fixes.sh" ]; then
        log_info "Running security verification tests..."
        ./tests/test_security_fixes.sh
    fi

    log_success "Test suite completed"
}

# Show usage information
show_usage() {
    cat << EOF
fplaunchwrapper Development Setup Script

USAGE:
    $0 [COMMAND] [OPTIONS]

COMMANDS:
    setup       Set up complete development environment (default)
    deps        Install only Python dependencies
    system      Install only system dependencies
    test        Run test suite
    clean       Clean up development environment

OPTIONS:
    --mode MODE     Dependency installation mode:
                    minimal    - Core dependencies only
                    robustness - + pydantic, tomli, psutil
                    advanced   - + click, rich, validators
                    dev        - + testing and development tools (default)
                    full       - All dependencies

EXAMPLES:
    $0                           # Full development setup
    $0 deps --mode minimal       # Install minimal dependencies
    $0 system                    # Install system dependencies only
    $0 test                      # Run tests

DEPENDENCY MODES:
    minimal     - Core functionality only
    robustness  - Type-safe config, process monitoring
    advanced    - Modern CLI, rich output, validation
    dev         - Testing, linting, formatting tools
    full        - Everything including security and integration tools

EOF
}

# Main function
main() {
    local command="${1:-setup}"
    local mode="dev"

    # Parse arguments
    shift
    while [ $# -gt 0 ]; do
        case "$1" in
            --mode)
                mode="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    case "$command" in
        setup)
            log_info "Starting complete development environment setup..."
            check_uv
            install_system_deps
            setup_dev_environment
            run_tests
            log_success "Development environment setup complete!"
            echo ""
            echo "Next steps:"
            echo "  1. Activate virtual environment: source .venv/bin/activate"
            echo "  2. Run tests: uv run pytest"
            echo "  3. Start developing!"
            ;;
        deps)
            check_uv
            install_dependencies "$mode"
            ;;
        system)
            install_system_deps
            ;;
        test)
            run_tests
            ;;
        clean)
            log_info "Cleaning up development environment..."
            rm -rf .venv
            rm -rf .pytest_cache
            rm -rf .coverage
            rm -rf htmlcov
            rm -rf __pycache__
            find . -name "*.pyc" -delete
            find . -name "*.pyo" -delete
            log_success "Development environment cleaned"
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
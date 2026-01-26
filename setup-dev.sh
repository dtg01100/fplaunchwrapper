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

    # Python testing is built-in, no additional dependencies needed

    # Check for shell script linting
    if ! command -v shellcheck &> /dev/null; then
        missing_deps+=("shellcheck")
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_warn "Missing system dependencies: ${missing_deps[*]}"
        log_info "Installing system dependencies..."

        # Detect package manager and install dependencies
        if command -v apt-get &> /dev/null; then
            # Debian/Ubuntu
            sudo apt-get update
            sudo apt-get install -y flatpak dialog
        elif command -v dnf &> /dev/null; then
            # Fedora/RHEL
            sudo dnf install -y flatpak dialog
        elif command -v pacman &> /dev/null; then
            # Arch Linux
            sudo pacman -S --noconfirm flatpak dialog
        elif command -v zypper &> /dev/null; then
            # openSUSE
            sudo zypper install -y flatpak dialog
        else
            log_error "Unsupported package manager. Please install manually:"
            echo "  - flatpak"
            echo "  - dialog"
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
    log_info "Running comprehensive test suite..."

    # Check for Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found"
        return 1
    fi

    # Run performance tests
    log_info "Running performance benchmarks..."
    if python3 test_performance_simple.py; then
        log_success "Performance tests passed"
    else
        log_error "Performance tests failed"
    fi

    # Run safety validation tests
    log_info "Running safety validation tests..."
    if python3 test_integration_safety.py; then
        log_success "Safety tests passed"
    else
        log_error "Safety tests failed"
    fi

    # Run Python unit tests
    if command -v pytest &> /dev/null; then
        log_info "Running Python unit tests..."
        if python3 -c "
import sys
sys.path.insert(0, '.')

# Run key test suites
from tests.python.test_safe_constructor import TestSafeConstructorValidation
from tests.python.test_edge_cases_focused import TestInputValidationEdgeCases

# Test constructor validation
test_constructor = TestSafeConstructorValidation()
test_constructor.test_wrapper_generator_constructor()
test_constructor.test_wrapper_manager_constructor()
test_constructor.test_wrapper_cleanup_constructor()
test_constructor.test_app_launcher_constructor()
test_constructor.test_systemd_setup_constructor()

# Test edge cases
test_edges = TestInputValidationEdgeCases()
test_edges.test_empty_and_none_inputs()
test_edges.test_extremely_long_inputs()

print('All Python tests passed!')
"; then
            log_success "Python unit tests passed"
        else
            log_error "Python unit tests failed"
        fi
    else
        log_warn "pytest not available, running basic validation..."
        if python3 -c "
from lib.generate import WrapperGenerator
from lib.manage import WrapperManager
from lib.cleanup import WrapperCleanup
from lib.launch import AppLauncher
print('✅ Python modules imported successfully')
"; then
            log_success "Basic Python validation passed"
        else
            log_error "Basic Python validation failed"
        fi
    fi
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
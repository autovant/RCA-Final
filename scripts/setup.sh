#!/bin/bash
# RCA Engine Setup Script
# Automated setup for development environment

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[SETUP]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3.11+ is required but not installed"
        exit 1
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        error "Node.js 18+ is required but not installed"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        warning "Docker is not installed. You'll need it for production deployment"
    fi
    
    # Check PostgreSQL
    if ! command -v psql &> /dev/null; then
        warning "PostgreSQL client is not installed"
    fi
    
    success "Prerequisites check completed"
}

# Setup Python environment
setup_python_env() {
    log "Setting up Python environment..."
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        success "Created virtual environment"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    pip install -r requirements.txt
    
    success "Python environment setup completed"
}

# Setup Node.js environment
setup_node_env() {
    log "Setting up Node.js environment..."
    
    cd ui
    
    # Install dependencies
    npm install
    
    # Run security audit
    npm audit --audit-level high
    
    cd ..
    
    success "Node.js environment setup completed"
}

# Setup environment file
setup_env_file() {
    log "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        warning "Created .env file - please update it with your settings"
        warning "Especially: JWT_SECRET_KEY, POSTGRES_PASSWORD, GRAFANA_PASSWORD"
    else
        warning ".env file already exists - skipping"
    fi
}

# Setup database
setup_database() {
    log "Setting up database..."
    
    # Check if PostgreSQL is running
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        # Create database if needed
        createdb rca_engine 2>/dev/null || true
        
        # Run migrations
        alembic upgrade head
        
        success "Database setup completed"
    else
        warning "PostgreSQL is not running - skipping database setup"
        warning "Start PostgreSQL and run: alembic upgrade head"
    fi
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p uploads reports logs watch-folder
    
    # Set permissions
    chmod 755 uploads reports logs watch-folder
    
    success "Directories created"
}

# Run security checks
run_security_checks() {
    log "Running security checks..."
    
    # Python security audit
    if command -v pip-audit &> /dev/null; then
        pip-audit --desc
    else
        warning "pip-audit not installed - skipping Python security audit"
    fi
    
    # Node.js security audit
    cd ui
    npm audit --audit-level high
    cd ..
    
    success "Security checks completed"
}

# Display next steps
show_next_steps() {
    log "Setup completed! Next steps:"
    echo ""
    echo "1. Update .env file with your settings:"
    echo "   - JWT_SECRET_KEY (generate strong random key)"
    echo "   - POSTGRES_PASSWORD (secure database password)"
    echo "   - GRAFANA_PASSWORD (Grafana admin password)"
    echo ""
    echo "2. Start development servers:"
    echo "   - API: python apps/api/main.py"
    echo "   - Worker: python apps/worker/main.py"
    echo "   - UI: cd ui && npm run dev"
    echo ""
    echo "3. Or use Docker for full stack:"
    echo "   cd deploy/docker && docker-compose up -d"
    echo ""
    echo "4. Access the application:"
    echo "   - API: http://localhost:8000/docs"
    echo "   - UI: http://localhost:3000"
    echo "   - Grafana: http://localhost:3001"
    echo ""
    echo "5. Run tests:"
    echo "   pytest tests/"
    echo ""
    echo "6. Check health:"
    echo "   curl http://localhost:8001/health"
}

# Main execution
main() {
    echo "RCA Engine Setup Script"
    echo "======================"
    echo ""
    
    check_prerequisites
    setup_python_env
    setup_node_env
    setup_env_file
    setup_database
    create_directories
    run_security_checks
    
    show_next_steps
    
    success "Setup completed successfully!"
}

# Run main function
main "$@"
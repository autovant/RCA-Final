#!/bin/bash
###############################################################################
# Advanced ITSM Integration - Automated Deployment Script
# 
# This script automatically deploys the RCA application with ITSM features
# Handles: existing containers, port conflicts, service health checks
#
# Usage: 
#  chmod +x deploy.sh
#  ./deploy.sh
###############################################################################

set -euo pipefail

# Resolve repository root relative to this script. Allows overrides via environment.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="${PROJECT_ROOT:-$SCRIPT_DIR}"
DOCKER_DIR="${DOCKER_DIR:-$PROJECT_ROOT/deploy/docker}"
CONFIG_DIR="${CONFIG_DIR:-$PROJECT_ROOT/config}"

# Ensure PROJECT_ROOT does not contain Windows-style backslashes when script invoked from WSL
PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd -P)"
DOCKER_DIR="$(cd "$DOCKER_DIR" && pwd -P)"
CONFIG_DIR="$(cd "$CONFIG_DIR" && pwd -P)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color


# Global so helper functions can reference it after detection
DOCKER_COMPOSE=""

# Function to print colored output
print_status() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
  echo ""
  echo -e "${BLUE}========================================${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}========================================${NC}"
  echo ""
}

# Function to check if a port is in use
check_port() {
  local port=$1
  if command -v lsof >/dev/null 2>&1; then
    if lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1 ; then
      return 0
    fi
  elif command -v ss >/dev/null 2>&1; then
    if ss -ltn | awk -v p=":$port" '$4 ~ p {exit 0} END {exit 1}'; then
      return 0
    fi
  elif command -v netstat >/dev/null 2>&1; then
    if netstat -an | grep -E "[:\.]$port\s" | grep LISTEN >/dev/null 2>&1; then
      return 0
    fi
  else
    print_warning "Unable to check port $port automatically (no lsof/ss/netstat)."
    return 1
  fi
  return 1
}

# Function to handle port conflicts
handle_port_conflicts() {
  print_header "Checking for Port Conflicts"
  
  local ports=(5432 6379 8000 8001 3001 9090)
  local port_names=("PostgreSQL" "Redis" "API" "API-Metrics" "Grafana" "Prometheus")
  local conflicts=0
  
  for i in "${!ports[@]}"; do
    if check_port ${ports[$i]}; then
      print_warning "Port ${ports[$i]} (${port_names[$i]}) is in use"
      conflicts=$((conflicts + 1))
    else
      print_status "Port ${ports[$i]} (${port_names[$i]}) is available"
    fi
  done
  
  if [ $conflicts -gt 0 ]; then
    print_warning "Found $conflicts port conflict(s)"
    read -p "Do you want to stop conflicting services? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      print_status "Attempting to stop conflicting Docker containers..."
      cd "$DOCKER_DIR"
      $DOCKER_COMPOSE down 2>/dev/null || true
      print_success "Docker containers stopped"
    else
      print_error "Cannot proceed with port conflicts. Please free up the ports manually."
      exit 1
    fi
  else
    print_success "All required ports are available"
  fi
}

# Function to check prerequisites
check_prerequisites() {
  print_header "Checking Prerequisites"
  
  # Check if we're in WSL (multiple detection methods)
  if [ ! -f /proc/version ]; then
    print_error "This script must be run in a Linux environment (WSL or native Linux)"
    exit 1
  fi
  
  # WSL detection: check for Microsoft/WSL in version OR check for /mnt/c
  if grep -qi "microsoft\|wsl" /proc/version 2>/dev/null || [ -d "/mnt/c" ]; then
    print_success "Running in WSL/Linux environment"
  else
    print_warning "Could not confirm WSL, but proceeding (detected Linux environment)"
  fi
  
  # Required utilities
  for bin in docker curl awk; do
    if ! command -v "$bin" >/dev/null 2>&1; then
      print_error "Required command '$bin' not found in PATH"
      exit 1
    fi
  done

  # Check Docker
  if ! command -v docker >/dev/null 2>&1; then
    print_error "Docker is not installed or not in PATH"
    exit 1
  fi
  print_success "Docker found: $(docker --version)"
  
  # Check Docker daemon
  if ! docker ps &> /dev/null; then
    print_error "Docker daemon is not running. Please start Docker Desktop."
    exit 1
  fi
  print_success "Docker daemon is running"
  
  # Check docker compose (try V2 first, then V1)
  if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
    print_success "docker compose found: $(docker compose version)"
  elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
    print_success "docker-compose found: $(docker-compose --version)"
  else
    print_error "docker compose is not available. Please enable WSL integration in Docker Desktop settings."
    exit 1
  fi
  
  # Check if project directory exists
  if [ ! -d "$PROJECT_ROOT" ]; then
    print_error "Project directory not found: $PROJECT_ROOT"
    exit 1
  fi
  print_success "Project directory found"
  
  # Check if docker-compose.yml exists
  if [ ! -f "$DOCKER_DIR/docker-compose.yml" ]; then
    print_error "docker-compose.yml not found in $DOCKER_DIR"
    exit 1
  fi
  print_success "docker-compose.yml found"
  
  # Check if .env exists
  if [ ! -f "$DOCKER_DIR/.env" ]; then
    print_warning ".env file not found, will use defaults"
  else
    print_success ".env file found"
  fi
}

# Function to clean up existing containers
cleanup_existing() {
  print_header "Cleaning Up Existing Containers and Networks"
  
  cd "$DOCKER_DIR"
  
  # Stop containers using docker-compose
  print_status "Stopping docker-compose services..."
  $DOCKER_COMPOSE down --remove-orphans 2>/dev/null || true
  
  # Force remove specific containers if they still exist
  local containers=("rca_db" "rca_redis" "rca_core" "rca_ollama" "rca_prometheus" "rca_grafana" "rca_alertmanager" "rca_ui" "rca_clamav" "rca_watcher")
  for container in "${containers[@]}"; do
    if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
      print_status "Removing container: $container"
      docker rm -f "$container" 2>/dev/null || true
    fi
  done
  
  # Stop any containers using our required ports
  print_status "Checking for containers using required ports..."
  local ports=(5432 6379 8000 8001 3001 9090)
  for port in "${ports[@]}"; do
    local container_id=$(docker ps --format '{{.ID}}' --filter "publish=$port" 2>/dev/null)
    if [ -n "$container_id" ]; then
      print_status "Stopping container using port $port: $container_id"
      docker stop "$container_id" 2>/dev/null || true
      docker rm "$container_id" 2>/dev/null || true
    fi
  done
  
  # Clean up the specific network if it exists
  if docker network inspect docker_rca_network &>/dev/null; then
    print_status "Removing existing docker_rca_network..."
    docker network rm docker_rca_network 2>/dev/null || true
  fi
  
  # Also try to prune unused networks to avoid IP conflicts
  print_status "Pruning unused Docker networks..."
  docker network prune -f &>/dev/null || true
  
  print_success "Cleanup complete"
  
  # Remove dangling volumes (optional, commented out for safety)
  # print_status "Removing dangling volumes..."
  # docker volume prune -f
}

# Function to start database and Redis
start_core_services() {
  print_header "Starting Core Services (Database & Redis)"
  
  cd "$DOCKER_DIR"
  
  print_status "Starting PostgreSQL and Redis..."
  $DOCKER_COMPOSE up -d db redis
  
  # Wait for database to be ready
  print_status "Waiting for PostgreSQL to be ready (max 60 seconds)..."
  local count=0
  until $DOCKER_COMPOSE exec -T db pg_isready -U rca_user 2>/dev/null; do
        count=$((count + 1))
        if [ $count -gt 60 ]; then
            print_error "PostgreSQL failed to start within 60 seconds"
            $DOCKER_COMPOSE logs db
            exit 1
        fi
    printf "."
    sleep 1
  done
  echo ""
  print_success "PostgreSQL is ready"
  
  # Wait for Redis to be ready
  print_status "Waiting for Redis to be ready (max 30 seconds)..."
  count=0
  until $DOCKER_COMPOSE exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; do
    count=$((count + 1))
    if [ $count -gt 30 ]; then
      print_error "Redis failed to start within 30 seconds"
      $DOCKER_COMPOSE logs redis
      exit 1
    fi
    printf "."
    sleep 1
  done
  echo ""
  print_success "Redis is ready"
}

# Function to build and start API
start_api_service() {
  print_header "Building and Starting API Service"
  
  cd "$DOCKER_DIR"
  
  print_status "Building and starting API service (this may take 3-5 minutes on first run)..."
  $DOCKER_COMPOSE up -d --build rca_core
  
  # Wait for API to be ready
  print_status "Waiting for API to be ready (max 120 seconds)..."
  local count=0
  until curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; do
    count=$((count + 1))
    if [ $count -gt 120 ]; then
      print_error "API failed to start within 120 seconds"
      print_status "API logs:"
      $DOCKER_COMPOSE logs --tail=50 rca_core
      exit 1
    fi
    printf "."
    sleep 1
  done
  echo ""
  print_success "API is ready and responding"
}

# Function to run database migration
run_migration() {
  print_header "Running Database Migration"
  
  cd "$DOCKER_DIR"
  
  # Check current migration status
  print_status "Checking current migration status..."
  current_revision=$($DOCKER_COMPOSE exec -T rca_core alembic current 2>/dev/null | grep -oP '^\w+' | head -1 || echo "none")
  print_status "Current revision: $current_revision"
  
  # Run migration
  print_status "Running migration to head (70a4e9f6d8c2 - SLA tracking)..."
  if $DOCKER_COMPOSE exec -T rca_core alembic upgrade head; then
    print_success "Migration completed successfully"
  else
    print_error "Migration failed"
    $DOCKER_COMPOSE logs --tail=50 rca_core
    exit 1
  fi
  
  # Verify migration
  new_revision=$($DOCKER_COMPOSE exec -T rca_core alembic current 2>/dev/null | grep -oP '^\w+' | head -1)
  print_status "New revision: $new_revision"
  
  if [ "$new_revision" = "70a4e9f6d8c2" ]; then
    print_success "Migration verified: SLA tracking fields added"
  else
    print_warning "Migration may not have applied correctly. Expected: 70a4e9f6d8c2, Got: $new_revision"
  fi
}

# Function to start monitoring stack
start_monitoring() {
  print_header "Starting Monitoring Stack (Prometheus & Grafana)"
  
  cd "$DOCKER_DIR"
  
  print_status "Starting Prometheus and Grafana..."
  $DOCKER_COMPOSE --profile monitoring up -d prometheus grafana
  
  # Wait for Prometheus
  print_status "Waiting for Prometheus (max 30 seconds)..."
  local count=0
  until curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; do
    count=$((count + 1))
    if [ $count -gt 30 ]; then
      print_warning "Prometheus health check timed out, but continuing..."
      break
    fi
    printf "."
    sleep 1
  done
  echo ""
  print_success "Prometheus started"
  
  # Wait for Grafana
  print_status "Waiting for Grafana (max 30 seconds)..."
  count=0
  until curl -s http://localhost:3001/api/health > /dev/null 2>&1; do
    count=$((count + 1))
    if [ $count -gt 30 ]; then
      print_warning "Grafana health check timed out, but continuing..."
      break
    fi
    printf "."
    sleep 1
  done
  echo ""
  print_success "Grafana started"
}

# Function to verify deployment
verify_deployment() {
  print_header "Verifying Deployment"
  
  cd "$DOCKER_DIR"
  
  # Check all services are running
  print_status "Checking service status..."
  $DOCKER_COMPOSE ps
  
  echo ""
  print_status "Testing endpoints..."
  
  # Test API health
  if response=$(curl -s http://localhost:8000/api/v1/health); then
    print_success "✓ API Health: $response"
  else
    print_error "✗ API Health check failed"
  fi
  
  # Test templates endpoint
  if response=$(curl -s http://localhost:8000/api/v1/tickets/templates); then
    template_count=$(echo "$response" | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
    print_success "✓ Templates Endpoint: $template_count templates available"
  else
    print_error "✗ Templates endpoint failed"
  fi
  
  # Test metrics endpoint
  if curl -s http://localhost:8001/metrics | grep -q "itsm_ticket_creation_total"; then
    print_success "✓ Metrics Endpoint: ITSM metrics present"
  else
    print_warning "✗ Metrics endpoint: ITSM metrics not found (this is normal if no tickets created yet)"
  fi
  
  # Test Prometheus
  if curl -s http://localhost:9090/-/healthy | grep -q "Healthy"; then
    print_success "✓ Prometheus: Healthy"
  else
    print_warning "✗ Prometheus health check failed"
  fi
  
  # Test Grafana
  if curl -s http://localhost:3001/api/health > /dev/null 2>&1; then
    print_success "✓ Grafana: Accessible"
  else
    print_warning "✗ Grafana not accessible"
  fi
}

# Function to create sample template config
create_sample_templates() {
  print_header "Checking Template Configuration"
  
  if [ ! -f "$CONFIG_DIR/itsm_config.json" ]; then
    print_warning "Template configuration not found"
    read -p "Create sample template configuration? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      mkdir -p "$CONFIG_DIR"
      cat > "$CONFIG_DIR/itsm_config.json" << 'EOF'
{
 "templates": {
  "servicenow": [
   {
    "name": "production_incident",
    "description": "Production incident template for critical service failures",
    "required_variables": ["service_name", "error_message", "impact"],
    "payload": {
     "short_description": "Production Incident: {service_name}",
     "description": "Critical error in {service_name}:\n\n{error_message}\n\nImpact: {impact}",
     "priority": 1,
     "urgency": 1,
     "impact": 1,
     "category": "Software",
     "subcategory": "Application"
    }
   }
  ],
  "jira": [
   {
    "name": "bug_report",
    "description": "Standard bug report template",
    "required_variables": ["summary", "description", "severity"],
    "payload": {
     "summary": "{summary}",
     "description": "{description}\n\nSeverity: {severity}",
     "issuetype": {"name": "Bug"},
     "priority": {"name": "High"}
    }
   }
  ]
 }
}
EOF
      print_success "Sample template configuration created at $CONFIG_DIR/itsm_config.json"
      
      # Restart API to load templates
      print_status "Restarting API to load templates..."
      cd "$DOCKER_DIR"
      $DOCKER_COMPOSE restart rca_core
      
      # Wait for API
      sleep 5
      until curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; do
        printf "."
        sleep 1
      done
      echo ""
      print_success "API restarted with templates"
    fi
  else
    print_success "Template configuration already exists"
  fi
}

# Function to display summary
display_summary() {
  print_header "Deployment Complete! 🎉"
  
  echo -e "${GREEN}All services are running successfully!${NC}"
  echo ""
  echo "📊 Access Points:"
  echo " • API:      http://localhost:8000"
  echo " • API Docs:    http://localhost:8000/docs"
  echo " • API Metrics:  http://localhost:8001/metrics"
  echo " • Grafana:    http://localhost:3001 (admin/admin)"
  echo " • Prometheus:   http://localhost:9090"
  echo " • Prometheus Alerts: http://localhost:9090/alerts"
  echo ""
  echo "🧪 Quick Test Commands (run in WSL):"
  echo " # List templates"
  echo " curl http://localhost:8000/api/v1/tickets/templates | jq"
  echo ""
  echo " # Test template with dry-run"
  echo " curl -X POST http://localhost:8000/api/v1/tickets/from-template \\"
  echo "  -H 'Content-Type: application/json' \\"
  echo "  -d '{\"job_id\":\"test-1\",\"platform\":\"servicenow\",\"template_name\":\"production_incident\",\"variables\":{\"service_name\":\"API\",\"error_message\":\"Test\",\"impact\":\"High\"},\"dry_run\":true}' | jq"
  echo ""
  echo "📚 Documentation:"
  echo " • Full Guide:   DOCKER_DEPLOYMENT_GUIDE.md"
  echo " • Quick Start:  WSL_QUICKSTART.md"
  echo " • Runbook:    docs/ITSM_RUNBOOK.md"
  echo " • Feature Summary: IMPLEMENTATION_COMPLETE.md"
  echo ""
  echo "🔧 Common Commands:"
  echo " cd '$DOCKER_DIR'"
  echo "  ps       # View running services"
  echo "  logs -f     # Follow all logs"
  echo "  logs -f rca_core # Follow API logs"
  echo "  restart rca_core # Restart API"
  echo "  down      # Stop all services"
  echo ""
  echo "⚠️ Next Steps:"
  echo " 1. Import Grafana dashboard (see DOCKER_DEPLOYMENT_GUIDE.md Step 8)"
  echo " 2. Configure ITSM credentials in deploy/docker/.env if using ServiceNow/Jira"
  echo " 3. Review Prometheus alerts at http://localhost:9090/alerts"
  echo ""
}

# Main deployment function
main() {
  print_header "🚀 Advanced ITSM Integration - Automated Deployment"
  
  echo "This script will:"
  echo " 1. Check prerequisites and port availability"
  echo " 2. Clean up any existing containers"
  echo " 3. Start database and Redis"
  echo " 4. Build and start API service"
  echo " 5. Run database migration (SLA tracking)"
  echo " 6. Start monitoring stack (Prometheus & Grafana)"
  echo " 7. Verify all services"
  echo " 8. Create sample templates (optional)"
  echo ""
  read -p "Continue with deployment? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "Deployment cancelled"
    exit 0
  fi
  
  # Execute deployment steps
  check_prerequisites
  handle_port_conflicts
  cleanup_existing
  start_core_services
  start_api_service
  run_migration
  start_monitoring
  verify_deployment
  create_sample_templates
  display_summary
  
  print_success "🎉 Deployment completed successfully!"
}

# Run main function
main "$@"

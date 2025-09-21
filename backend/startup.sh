#!/bin/sh

# Exit on any failure
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ✓ $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ⚠ $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ✗ $1"
}

ensure_directories() {
    log "Ensuring required directories exist with proper permissions..."

    # Create directories if they don't exist
    mkdir -p "${STATIC_ROOT}" "${MEDIA_ROOT}" "${RASTER_ROOT}" "${LOGS_ROOT}" || {
        log_warning "Could not create directories, they may already exist"
    }

    # Try to fix permissions (will only work if we have write access)
    if [ -w "${STATIC_ROOT%/*}" ]; then
        chmod -R 755 "${STATIC_ROOT}" "${MEDIA_ROOT}" "${RASTER_ROOT}" "${LOGS_ROOT}" 2>/dev/null || true
    fi

    log_success "Directory setup completed"
}

# Handle permissions if running as root
handle_permissions() {
    if [ "$(id -u)" = "0" ]; then
        log "Running as root, fixing permissions and switching to appuser..."
        
        # Create directories if they don't exist
        mkdir -p "${STATIC_ROOT}" "${MEDIA_ROOT}" "${RASTER_ROOT}" "${LOGS_ROOT}"
        
        # Fix ownership
        chown -R appuser:appgroup "${STATIC_ROOT}" "${MEDIA_ROOT}" "${RASTER_ROOT}" "${LOGS_ROOT}"
        
        log_success "Permissions fixed, switching to appuser"
        exec su-exec appuser "$0" "$@"
    fi
}

# Wait for database connection
wait_for_db() {
    local db_host="${DB_HOST:-db}"
    local db_port="${DB_PORT:-5432}"
    local max_attempts=30
    local attempt=1
    
    log "Waiting for database at ${db_host}:${db_port}..."
    
    while ! nc -z "${db_host}" "${db_port}"; do
        if [ ${attempt} -gt ${max_attempts} ]; then
            log_error "Database connection failed after ${max_attempts} attempts"
            exit 1
        fi
        
        log "Database not ready, attempt ${attempt}/${max_attempts}..."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    log_success "Database connection established"
}

# Run Django migrations
run_migrations() {
    log "Running database migrations..."
    if python manage.py migrate --noinput; then
        log_success "Database migrations completed"
    else
        log_error "Database migrations failed"
        exit 1
    fi
}

# Collect static files
collect_static() {
    log "Collecting static files..."
    if python manage.py collectstatic --noinput --clear; then
        log_success "Static files collected"
    else
        log_error "Static files collection failed"
        exit 1
    fi
}

# Create superuser if needed
create_superuser() {
    if [ -n "${DJANGO_SUPERUSER_USERNAME}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD}" ]; then
        log "Creating superuser..."
        if python manage.py createsuperuser --noinput 2>/dev/null; then
            log_success "Superuser created"
        else
            log_warning "Superuser already exists or creation failed"
        fi
    else
        log_warning "Superuser environment variables not set, skipping creation"
    fi
}

# Start Gunicorn
start_gunicorn() {
    log "Starting Gunicorn server..."
    exec gunicorn --config config/gunicorn_config.py config.wsgi:application
}

# Main execution
main() {
    log "🚀 Starting Django application initialization..."
    
    handle_permissions "$@"
    ensure_directories
    wait_for_db
    run_migrations
    collect_static
    create_superuser
    start_gunicorn
}

# Run main function
main "$@"#!/bin/sh

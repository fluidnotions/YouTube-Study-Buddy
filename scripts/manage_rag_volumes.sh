#!/bin/bash
#
# RAG Volume Management Script
# Backup, restore, and reset RAG-related Docker volumes
#
# Usage:
#   ./scripts/manage_rag_volumes.sh backup         # Create backup of ChromaDB and model cache
#   ./scripts/manage_rag_volumes.sh restore FILE   # Restore from backup file
#   ./scripts/manage_rag_volumes.sh reset          # Reset (delete) RAG volumes
#   ./scripts/manage_rag_volumes.sh list           # List available backups
#   ./scripts/manage_rag_volumes.sh info           # Show volume information
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups/rag-volumes}"
PROJECT_NAME="ytstudybuddy"
CHROMA_VOLUME="${PROJECT_NAME}_chroma_data"
MODEL_VOLUME="${PROJECT_NAME}_model_cache"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Function to print colored messages
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

# Function to check if volume exists
volume_exists() {
    docker volume inspect "$1" &>/dev/null
}

# Backup ChromaDB volume
backup_chroma() {
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="$BACKUP_DIR/chroma-backup-${timestamp}.tar.gz"

    log_info "Backing up ChromaDB volume to: $backup_file"

    if ! volume_exists "$CHROMA_VOLUME"; then
        log_warning "Volume $CHROMA_VOLUME does not exist. Creating empty backup."
        touch "$backup_file"
        return
    fi

    docker run --rm \
        -v "${CHROMA_VOLUME}:/data" \
        -v "$(realpath $BACKUP_DIR):/backup" \
        alpine \
        tar czf "/backup/chroma-backup-${timestamp}.tar.gz" -C /data .

    log_success "ChromaDB backup created: $backup_file"
    echo "$backup_file"
}

# Backup model cache volume
backup_models() {
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="$BACKUP_DIR/models-backup-${timestamp}.tar.gz"

    log_info "Backing up model cache volume to: $backup_file"

    if ! volume_exists "$MODEL_VOLUME"; then
        log_warning "Volume $MODEL_VOLUME does not exist. Creating empty backup."
        touch "$backup_file"
        return
    fi

    docker run --rm \
        -v "${MODEL_VOLUME}:/data" \
        -v "$(realpath $BACKUP_DIR):/backup" \
        alpine \
        tar czf "/backup/models-backup-${timestamp}.tar.gz" -C /data .

    log_success "Model cache backup created: $backup_file"
    echo "$backup_file"
}

# Backup all RAG volumes
backup_all() {
    log_info "Starting full RAG backup..."
    backup_chroma
    backup_models
    log_success "Full backup complete!"
    list_backups
}

# Restore ChromaDB volume from backup
restore_chroma() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_warning "This will replace the current ChromaDB data!"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restore cancelled."
        exit 0
    fi

    log_info "Stopping containers..."
    docker-compose down || true

    log_info "Removing old ChromaDB volume..."
    docker volume rm "$CHROMA_VOLUME" 2>/dev/null || true

    log_info "Creating new volume and restoring data..."
    docker volume create "$CHROMA_VOLUME"

    docker run --rm \
        -v "${CHROMA_VOLUME}:/data" \
        -v "$(realpath $(dirname $backup_file)):/backup" \
        alpine \
        tar xzf "/backup/$(basename $backup_file)" -C /data

    log_success "ChromaDB restore complete!"
    log_info "Start containers with: docker-compose up -d"
}

# Restore model cache from backup
restore_models() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_warning "This will replace the current model cache!"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restore cancelled."
        exit 0
    fi

    log_info "Stopping containers..."
    docker-compose down || true

    log_info "Removing old model cache volume..."
    docker volume rm "$MODEL_VOLUME" 2>/dev/null || true

    log_info "Creating new volume and restoring data..."
    docker volume create "$MODEL_VOLUME"

    docker run --rm \
        -v "${MODEL_VOLUME}:/data" \
        -v "$(realpath $(dirname $backup_file)):/backup" \
        alpine \
        tar xzf "/backup/$(basename $backup_file)" -C /data

    log_success "Model cache restore complete!"
    log_info "Start containers with: docker-compose up -d"
}

# Reset (delete) all RAG volumes
reset_volumes() {
    log_warning "This will DELETE all RAG data (ChromaDB and model cache)!"
    log_warning "This action CANNOT be undone!"
    read -p "Are you sure? Type 'yes' to confirm: " -r
    echo
    if [[ ! $REPLY == "yes" ]]; then
        log_info "Reset cancelled."
        exit 0
    fi

    log_info "Stopping containers..."
    docker-compose down || true

    log_info "Removing RAG volumes..."
    docker volume rm "$CHROMA_VOLUME" 2>/dev/null && log_success "Removed $CHROMA_VOLUME" || log_warning "$CHROMA_VOLUME not found"
    docker volume rm "$MODEL_VOLUME" 2>/dev/null && log_success "Removed $MODEL_VOLUME" || log_warning "$MODEL_VOLUME not found"

    log_success "Reset complete! Volumes will be recreated on next startup."
    log_info "Start containers with: docker-compose up -d"
}

# List available backups
list_backups() {
    log_info "Available backups in $BACKUP_DIR:"
    echo

    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A $BACKUP_DIR 2>/dev/null)" ]; then
        log_warning "No backups found."
        return
    fi

    echo "ChromaDB backups:"
    ls -lh "$BACKUP_DIR"/chroma-backup-*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
    echo
    echo "Model cache backups:"
    ls -lh "$BACKUP_DIR"/models-backup-*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
}

# Show volume information
show_info() {
    log_info "RAG Volume Information:"
    echo

    if volume_exists "$CHROMA_VOLUME"; then
        echo "ChromaDB Volume: $CHROMA_VOLUME"
        docker volume inspect "$CHROMA_VOLUME" | grep -E '"Mountpoint"|"CreatedAt"' | sed 's/^/  /'
        local size=$(docker run --rm -v "${CHROMA_VOLUME}:/data" alpine du -sh /data 2>/dev/null | cut -f1)
        echo "  Size: $size"
    else
        log_warning "ChromaDB volume does not exist: $CHROMA_VOLUME"
    fi

    echo

    if volume_exists "$MODEL_VOLUME"; then
        echo "Model Cache Volume: $MODEL_VOLUME"
        docker volume inspect "$MODEL_VOLUME" | grep -E '"Mountpoint"|"CreatedAt"' | sed 's/^/  /'
        local size=$(docker run --rm -v "${MODEL_VOLUME}:/data" alpine du -sh /data 2>/dev/null | cut -f1)
        echo "  Size: $size"
    else
        log_warning "Model cache volume does not exist: $MODEL_VOLUME"
    fi
}

# Show usage
show_usage() {
    cat << EOF
RAG Volume Management Script

Usage:
  $0 backup              Backup all RAG volumes (ChromaDB + model cache)
  $0 backup-chroma       Backup only ChromaDB volume
  $0 backup-models       Backup only model cache volume
  $0 restore FILE        Restore from a backup file
  $0 reset               Delete all RAG volumes (requires confirmation)
  $0 list                List available backups
  $0 info                Show volume information
  $0 help                Show this help message

Examples:
  # Create full backup
  $0 backup

  # Restore ChromaDB from backup
  $0 restore backups/rag-volumes/chroma-backup-20251017-143022.tar.gz

  # Reset all RAG data
  $0 reset

  # List backups
  $0 list

Environment Variables:
  BACKUP_DIR             Backup directory (default: ./backups/rag-volumes)

EOF
}

# Main command dispatcher
case "${1:-help}" in
    backup)
        backup_all
        ;;
    backup-chroma)
        backup_chroma
        ;;
    backup-models)
        backup_models
        ;;
    restore)
        if [ -z "$2" ]; then
            log_error "Please specify a backup file to restore."
            echo "Usage: $0 restore FILE"
            exit 1
        fi

        # Detect if it's a chroma or model backup based on filename
        if [[ "$2" == *"chroma"* ]]; then
            restore_chroma "$2"
        elif [[ "$2" == *"models"* ]]; then
            restore_models "$2"
        else
            log_error "Cannot determine backup type. Filename should contain 'chroma' or 'models'."
            exit 1
        fi
        ;;
    reset)
        reset_volumes
        ;;
    list)
        list_backups
        ;;
    info)
        show_info
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        log_error "Unknown command: $1"
        echo
        show_usage
        exit 1
        ;;
esac

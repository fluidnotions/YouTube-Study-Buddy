#!/bin/bash
#
# RAG Health Check Script
# Verify RAG components are working correctly
#
# Usage:
#   ./scripts/check_rag_health.sh           # Check all RAG components
#   ./scripts/check_rag_health.sh --quick   # Quick check (basic connectivity only)
#   ./scripts/check_rag_health.sh --verbose # Verbose output with details
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="youtube-study-buddy"
VERBOSE=false
QUICK=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --quick|-q)
            QUICK=true
            shift
            ;;
        --help|-h)
            cat << EOF
RAG Health Check Script

Usage:
  $0 [OPTIONS]

Options:
  --quick, -q      Quick check (basic connectivity only)
  --verbose, -v    Verbose output with detailed information
  --help, -h       Show this help message

Examples:
  # Full health check
  $0

  # Quick check
  $0 --quick

  # Verbose check
  $0 --verbose

EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Function to print colored messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# Check if container is running
check_container() {
    log_info "Checking if container is running..."

    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_error "Container '$CONTAINER_NAME' is not running"
        log_info "Start it with: docker-compose up -d"
        exit 1
    fi

    log_success "Container is running"
}

# Check if RAG is enabled
check_rag_enabled() {
    log_info "Checking if RAG is enabled..."

    local rag_enabled=$(docker exec "$CONTAINER_NAME" printenv RAG_ENABLED 2>/dev/null || echo "false")

    if [ "$rag_enabled" != "true" ]; then
        log_warning "RAG is disabled (RAG_ENABLED=$rag_enabled)"
        log_info "Enable it in your .env file: RAG_ENABLED=true"
        return 1
    fi

    log_success "RAG is enabled"
    return 0
}

# Check environment variables
check_environment() {
    log_info "Checking RAG environment variables..."

    local vars=(
        "RAG_ENABLED"
        "RAG_MODEL"
        "RAG_SIMILARITY_THRESHOLD"
        "RAG_MAX_RESULTS"
        "RAG_BATCH_SIZE"
        "CHROMA_PERSIST_DIR"
        "MODEL_CACHE_DIR"
    )

    local all_ok=true
    for var in "${vars[@]}"; do
        local value=$(docker exec "$CONTAINER_NAME" printenv "$var" 2>/dev/null || echo "NOT_SET")
        if [ "$value" = "NOT_SET" ]; then
            log_warning "$var is not set"
            all_ok=false
        else
            log_verbose "$var=$value"
        fi
    done

    if [ "$all_ok" = true ]; then
        log_success "All environment variables are set"
    else
        log_warning "Some environment variables are missing"
    fi
}

# Check directories exist
check_directories() {
    log_info "Checking RAG directories..."

    local dirs=("/app/.chroma_db" "/app/.cache")
    local all_ok=true

    for dir in "${dirs[@]}"; do
        if docker exec "$CONTAINER_NAME" test -d "$dir" 2>/dev/null; then
            log_verbose "Directory exists: $dir"
        else
            log_error "Directory missing: $dir"
            all_ok=false
        fi
    done

    if [ "$all_ok" = true ]; then
        log_success "All directories exist"
    else
        log_error "Some directories are missing"
        return 1
    fi
}

# Check Python dependencies
check_dependencies() {
    log_info "Checking Python dependencies..."

    local check_script='
import sys
try:
    import chromadb
    import sentence_transformers
    print("OK")
except ImportError as e:
    print(f"MISSING: {e}")
    sys.exit(1)
'

    local result=$(docker exec "$CONTAINER_NAME" python -c "$check_script" 2>&1)

    if [[ "$result" == "OK" ]]; then
        log_success "Python dependencies installed"
    else
        log_error "Missing dependencies: $result"
        return 1
    fi
}

# Check VectorStore health
check_vector_store() {
    log_info "Checking VectorStore health..."

    local check_script='
import sys
import os
sys.path.insert(0, "/app/src")

try:
    from yt_study_buddy.rag.vector_store import VectorStore

    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "/app/.chroma_db")
    vs = VectorStore(persist_dir=persist_dir, collection_name="study_notes")

    if vs.health_check():
        stats = vs.collection_stats()
        print(f"OK|{stats.get(\"count\", 0)}")
    else:
        print("UNHEALTHY")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
'

    local result=$(docker exec "$CONTAINER_NAME" python -c "$check_script" 2>&1)

    if [[ "$result" == OK* ]]; then
        local count=$(echo "$result" | cut -d'|' -f2)
        log_success "VectorStore is healthy (${count} documents indexed)"
        if [ "$VERBOSE" = true ] && [ "$count" -gt 0 ]; then
            log_verbose "Query test: Testing similarity search..."
            test_similarity_search
        fi
    else
        log_error "VectorStore check failed: $result"
        return 1
    fi
}

# Test similarity search
test_similarity_search() {
    local test_script='
import sys
import os
sys.path.insert(0, "/app/src")

try:
    from yt_study_buddy.rag.vector_store import VectorStore
    from yt_study_buddy.rag.embedding_service import EmbeddingService

    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "/app/.chroma_db")
    model_name = os.getenv("RAG_MODEL", "all-mpnet-base-v2")

    vs = VectorStore(persist_dir=persist_dir, collection_name="study_notes")
    es = EmbeddingService(model_name=model_name)

    # Test query
    query = "machine learning"
    embedding = es.embed_text(query)
    results = vs.search_similar(embedding, filters={}, top_k=3)

    print(f"Found {len(results)} results for test query")
except Exception as e:
    print(f"Search test failed: {e}")
'

    local result=$(docker exec "$CONTAINER_NAME" python -c "$test_script" 2>&1)
    log_verbose "$result"
}

# Check EmbeddingService health
check_embedding_service() {
    log_info "Checking EmbeddingService health..."

    local check_script='
import sys
import os
sys.path.insert(0, "/app/src")

try:
    from yt_study_buddy.rag.embedding_service import EmbeddingService

    model_name = os.getenv("RAG_MODEL", "all-mpnet-base-v2")
    es = EmbeddingService(model_name=model_name)

    # Test embedding generation
    test_text = "This is a test sentence."
    embedding = es.embed_text(test_text)

    info = es.model_info()
    print(f"OK|{info.get(\"model_name\", \"unknown\")}|{info.get(\"embedding_dim\", 0)}")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
'

    local result=$(docker exec "$CONTAINER_NAME" python -c "$check_script" 2>&1)

    if [[ "$result" == OK* ]]; then
        local model=$(echo "$result" | cut -d'|' -f2)
        local dim=$(echo "$result" | cut -d'|' -f3)
        log_success "EmbeddingService is healthy (model: $model, dim: $dim)"
    else
        log_error "EmbeddingService check failed: $result"
        return 1
    fi
}

# Check disk space
check_disk_space() {
    log_info "Checking disk space usage..."

    local chroma_size=$(docker exec "$CONTAINER_NAME" du -sh /app/.chroma_db 2>/dev/null | cut -f1)
    local cache_size=$(docker exec "$CONTAINER_NAME" du -sh /app/.cache 2>/dev/null | cut -f1)

    log_verbose "ChromaDB size: $chroma_size"
    log_verbose "Model cache size: $cache_size"
    log_success "Disk space check complete"
}

# Quick check (only container and basic connectivity)
quick_check() {
    log_info "Running quick health check..."
    echo

    check_container
    check_rag_enabled
    check_directories

    echo
    log_success "Quick health check complete!"
}

# Full health check
full_check() {
    log_info "Running full health check..."
    echo

    local checks_passed=0
    local checks_failed=0

    # Container check
    if check_container; then
        ((checks_passed++))
    else
        ((checks_failed++))
        exit 1  # Can't continue without container
    fi

    echo

    # RAG enabled check
    if ! check_rag_enabled; then
        log_warning "Skipping remaining checks (RAG disabled)"
        exit 0
    fi
    ((checks_passed++))

    echo

    # Environment variables
    check_environment
    ((checks_passed++))

    echo

    # Directories
    if check_directories; then
        ((checks_passed++))
    else
        ((checks_failed++))
    fi

    echo

    # Python dependencies
    if check_dependencies; then
        ((checks_passed++))
    else
        ((checks_failed++))
        log_warning "Skipping component checks (dependencies missing)"
        echo
        echo "Summary: $checks_passed passed, $checks_failed failed"
        exit 1
    fi

    echo

    # VectorStore
    if check_vector_store; then
        ((checks_passed++))
    else
        ((checks_failed++))
    fi

    echo

    # EmbeddingService
    if check_embedding_service; then
        ((checks_passed++))
    else
        ((checks_failed++))
    fi

    echo

    # Disk space
    if [ "$VERBOSE" = true ]; then
        check_disk_space
        echo
    fi

    # Summary
    echo "═══════════════════════════════════════"
    if [ $checks_failed -eq 0 ]; then
        log_success "All health checks passed! ($checks_passed/$checks_passed)"
        echo
        log_info "RAG system is fully operational ✨"
    else
        log_warning "Health check summary: $checks_passed passed, $checks_failed failed"
        echo
        log_info "Fix the issues above and run the check again"
        exit 1
    fi
}

# Main execution
echo "RAG Health Check"
echo "═══════════════════════════════════════"
echo

if [ "$QUICK" = true ]; then
    quick_check
else
    full_check
fi

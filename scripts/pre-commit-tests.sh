#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🧪 Running pre-commit tests..."

# Get the backend directory
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BACKEND_DIR"

# Activate virtual environment if it exists
if [ -d "venv/bin" ]; then
    source venv/bin/activate
fi

# Minimum coverage threshold
MIN_COVERAGE=20

echo ""
echo "📊 Running unit tests with coverage..."

# Run tests with coverage
if pytest src/unit_tests/ \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-fail-under=$MIN_COVERAGE \
    -v \
    --tb=short; then
    
    echo ""
    echo -e "${GREEN}✅ All unit tests passed!${NC}"
    echo -e "${GREEN}✅ Coverage meets minimum threshold (${MIN_COVERAGE}%)${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Tests failed or coverage below ${MIN_COVERAGE}%${NC}"
    echo ""
    echo "To view detailed coverage report, open:"
    echo "  file://$BACKEND_DIR/htmlcov/index.html"
    exit 1
fi

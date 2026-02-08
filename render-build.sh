#!/usr/bin/env bash
# exit on error
set -o errexit

# Define the persistent cache directory for Prisma binaries
export PROJECT_ROOT=$(pwd)
export PRISMA_BINARY_CACHE_DIR="$PROJECT_ROOT/.prisma_engines"
export PRISMA_PY_BINARY_CACHE_DIR="$PRISMA_BINARY_CACHE_DIR"

# Install dependencies
pip install -r requirements.txt

# Fetch Prisma binaries into our persistent directory
echo "Fetching Prisma binaries..."
python -m prisma py fetch

# Generate the client
echo "Generating Prisma Client..."
python -m prisma generate

# Final check of the binary directory
ls -R .prisma_engines || echo "Warning: .prisma_engines directory not found"

# Push the database schema
echo "Pushing database schema..."
python -m prisma db push --accept-data-loss

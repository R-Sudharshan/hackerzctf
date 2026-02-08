#!/bin/bash
echo "--- Starting HACKERZ Build Process ---"

# Install dependencies
echo "Installing requirements..."
pip install -r requirements.txt

# Generate Prisma Client
echo "Generating Prisma Client..."
python -m prisma generate

# Sync Database Schema
echo "Syncing Database Schema..."
python -m prisma db push

echo "--- Build Process Complete ---"

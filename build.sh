#!/bin/bash
# Install dependencies
pip install -r requirements.txt

# Generate Prisma Client
python -m prisma generate

# Final check
echo "Prisma Client Generated Successfully"

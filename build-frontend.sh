#!/bin/bash
set -e

echo "Building React frontend..."
cd "$(dirname "$0")/frontend"

if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

echo "Running Vite build..."
npm run build

echo "Frontend built to social_arb/static/"

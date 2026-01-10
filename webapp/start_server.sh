#!/bin/bash
# Simple script to start a local web server for the visualization

echo "Starting web server for Velour Live Artist Network Visualization..."
echo "Open your browser to: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")"
python3 -m http.server 8000


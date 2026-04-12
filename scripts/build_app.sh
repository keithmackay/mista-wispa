#!/bin/bash
# Build mista-wispa.app bundle
set -e

echo "Building mista-wispa.app..."
python setup_app.py py2app

echo ""
echo "Build complete: dist/mista-wispa.app"
echo ""
echo "To install, copy to /Applications:"
echo "  cp -r dist/mista-wispa.app /Applications/"
echo ""
echo "To run:"
echo "  open /Applications/mista-wispa.app"

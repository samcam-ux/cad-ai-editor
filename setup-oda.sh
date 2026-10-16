#!/bin/bash
# Setup ODA File Converter for Docker build
# Run this before `docker build` to include ODA in the image
#
# 1. Download ODAFileConverter .deb from:
#    https://www.opendesign.com/guestfiles/oda_file_converter
# 2. Place the .deb in this directory as oda-converter.deb
# 3. Uncomment the ODA lines in Dockerfile
# 4. docker build -t cad-ai-editor .

set -e

if [ ! -f "oda-converter.deb" ]; then
    echo "❌ oda-converter.deb not found."
    echo ""
    echo "Download from: https://www.opendesign.com/guestfiles/oda_file_converter"
    echo "Choose: Linux 64-bit .deb package"
    echo "Rename to: oda-converter.deb"
    echo "Place in: $(pwd)/"
    echo ""
    echo "Note: ODA is free to use. Check their license for redistribution"
    echo "in commercial products - you may need OEM licensing."
    exit 1
fi

echo "✅ Found oda-converter.deb"
echo ""
echo "Next steps:"
echo "1. Uncomment ODA lines in Dockerfile"
echo "2. Run: docker build -t cad-ai-editor ."
